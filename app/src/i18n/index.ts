import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import pt from "./locales/pt-BR.json";

export function detectLocale(locale?: string): "en" | "pt-BR" {
  return (locale || "").toLowerCase().startsWith("pt") ? "pt-BR" : "en";
}
export function preferredLocale(preference: string, systemLocale?: string) {
  return preference === "en" || preference === "pt-BR"
    ? preference
    : detectLocale(systemLocale || navigator.language);
}
void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, "pt-BR": { translation: pt } },
  lng: detectLocale(navigator.language),
  fallbackLng: "en",
  supportedLngs: ["en", "pt-BR"],
  keySeparator: false,
  nsSeparator: false,
  returnNull: false,
  interpolation: { escapeValue: false },
  saveMissing: import.meta.env.DEV,
  missingKeyHandler: (_languages, _namespace, key) => {
    if (import.meta.env.DEV)
      console.warn("[PETRUS i18n] Missing translation:", key);
  },
  parseMissingKeyHandler: () =>
    i18n.getResource(
      i18n.resolvedLanguage || "en",
      "translation",
      "common.missing",
    ) || "…",
});
export default i18n;
export const label = (value: string) =>
  i18n.t("labels." + value, { defaultValue: value });
export const numberLabel = (value: number) =>
  new Intl.NumberFormat(i18n.resolvedLanguage || "en").format(value);
export function localizeMessage(value: string | null | undefined): string {
  if (!value) return "";
  if (i18n.exists(value)) return i18n.t(value);
  if (value.startsWith("[")) {
    try {
      return (JSON.parse(value) as string[]).map(localizeMessage).join(" ");
    } catch {
      /* legacy warning */
    }
  }
  const entry = [...Object.entries(en), ...Object.entries(pt)].find(
    ([, text]) => text === value,
  );
  return entry ? i18n.t(entry[0]) : i18n.t("errors.generic");
}
