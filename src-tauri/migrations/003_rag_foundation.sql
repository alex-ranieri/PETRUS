-- Additive machine-readable codes; legacy UI warnings remain unchanged.
ALTER TABLE papers ADD COLUMN scientific_warning_codes TEXT NOT NULL DEFAULT '[]';
ALTER TABLE parser_runs ADD COLUMN warning_codes_json TEXT NOT NULL DEFAULT '[]';
-- Backfill only known stable keys, never human message text.
UPDATE papers SET scientific_warning_codes = CASE scientific_warning
 WHEN 'errors.invalidTei' THEN '["grobid_invalid_response"]'
 WHEN 'errors.grobidResponse' THEN '["grobid_invalid_response"]'
 WHEN 'errors.pdfTooLarge' THEN '["pdf_size_limit"]'
 WHEN 'errors.grobidUnavailable' THEN '["grobid_unavailable"]'
 WHEN 'errors.fileUnavailable' THEN '["file_unavailable"]'
 WHEN 'errors.rescanBeforeReprocess' THEN '["rescan_required"]'
 WHEN 'errors.fileChanged' THEN '["file_changed"]'
 WHEN 'errors.grobidFailed' THEN '["grobid_failed"]'
 ELSE '[]' END;
UPDATE papers SET scientific_warning_codes = (
 SELECT json_group_array(code) FROM (
 SELECT 'page_mapping_partial' AS code WHERE EXISTS (
 SELECT 1 FROM sections s WHERE s.paper_id=papers.id AND s.page_start IS NULL
 AND length(trim(s.text))>0 AND EXISTS(SELECT 1 FROM source_spans sp WHERE sp.section_id=s.id))
 UNION ALL SELECT 'page_mapping_missing' WHERE EXISTS (
 SELECT 1 FROM sections s WHERE s.paper_id=papers.id AND s.page_start IS NULL
 AND length(trim(s.text))>0 AND NOT EXISTS(SELECT 1 FROM source_spans sp WHERE sp.section_id=s.id))
 )) WHERE scientific_warning_codes='[]';
UPDATE parser_runs SET warning_codes_json = CASE
 json_extract(CASE WHEN json_valid(warnings_json) THEN warnings_json ELSE '[]' END,'$[0]')
 WHEN 'errors.invalidTei' THEN '["grobid_invalid_response"]'
 WHEN 'errors.grobidResponse' THEN '["grobid_invalid_response"]'
 WHEN 'errors.pdfTooLarge' THEN '["pdf_size_limit"]'
 WHEN 'errors.grobidUnavailable' THEN '["grobid_unavailable"]'
 WHEN 'errors.fileUnavailable' THEN '["file_unavailable"]'
 WHEN 'errors.rescanBeforeReprocess' THEN '["rescan_required"]'
 WHEN 'errors.fileChanged' THEN '["file_changed"]'
 WHEN 'errors.grobidFailed' THEN '["grobid_failed"]'
 ELSE '[]' END;
