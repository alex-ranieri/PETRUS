-- Evolve the existing log. Historical payloads/IDs/timestamps remain untouched.
ALTER TABLE research_events ADD COLUMN actor_type TEXT NOT NULL DEFAULT 'system'
 CHECK(actor_type IN ('user','ai','system'));
ALTER TABLE research_events ADD COLUMN object_type TEXT;
ALTER TABLE research_events ADD COLUMN object_id TEXT;
ALTER TABLE research_events ADD COLUMN payload_version INTEGER NOT NULL DEFAULT 1 CHECK(payload_version=1);
ALTER TABLE research_events ADD COLUMN legacy INTEGER NOT NULL DEFAULT 1 CHECK(legacy IN (0,1));
UPDATE research_events SET actor_type='user'
 WHERE event_type IN ('session_created','ask','evidence_saved','evidence_decision_changed','evidence_note_updated','evidence_removed');
UPDATE research_events SET object_type=CASE
 WHEN event_type='session_created' THEN 'session'
 WHEN event_type='ask' THEN 'ask_snapshot'
 WHEN event_type LIKE 'evidence_%' THEN 'research_evidence' ELSE NULL END,
 object_id=CASE WHEN event_type='session_created' THEN CAST(session_id AS TEXT)
 WHEN event_type='ask' THEN CAST(id AS TEXT)
 WHEN event_type LIKE 'evidence_%' THEN CAST(json_extract(CASE WHEN json_valid(payload_json) THEN payload_json ELSE '{}' END,'$.id') AS TEXT)
 ELSE NULL END;
CREATE INDEX research_events_chronology ON research_events(session_id,created_at,id);
CREATE UNIQUE INDEX research_trail_boundary ON research_events(session_id) WHERE event_type='trail_tracking_started';
INSERT INTO research_events(session_id,event_type,actor_type,object_type,object_id,payload_version,legacy,payload_json,created_at)
 SELECT id,'trail_tracking_started','system','session',CAST(id AS TEXT),1,0,
 json_object('stage','0.4b','prior_activity_may_be_incomplete',json('true')),
 strftime('%Y-%m-%d %H:%M:%f','now') FROM research_sessions;
CREATE TRIGGER research_events_no_update BEFORE UPDATE ON research_events
 BEGIN SELECT RAISE(ABORT,'research_trail_append_only'); END;
-- Preserve the existing session-FK CASCADE policy; individual events are immutable.
CREATE TRIGGER research_events_no_delete BEFORE DELETE ON research_events
 WHEN OLD.session_id IS NULL OR EXISTS(SELECT 1 FROM research_sessions WHERE id=OLD.session_id)
 BEGIN SELECT RAISE(ABORT,'research_trail_append_only'); END;
CREATE TRIGGER research_events_payload_limit BEFORE INSERT ON research_events
 WHEN NEW.payload_json IS NOT NULL AND (NOT json_valid(NEW.payload_json) OR length(CAST(NEW.payload_json AS BLOB))>2500000)
 BEGIN SELECT RAISE(ABORT,'trail.invalidPayload'); END;
