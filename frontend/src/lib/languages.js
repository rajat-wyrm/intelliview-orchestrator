export const DEFAULT_LANGUAGE = "en";

export const LANGUAGE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi" },
  { value: "fr", label: "French" },
  { value: "es", label: "Spanish" },
  { value: "de", label: "German" },
  { value: "ja", label: "Japanese" },
];

export const isSupportedLanguage = (value) =>
  LANGUAGE_OPTIONS.some((option) => option.value === value);

export const getLanguageLabel = (value) =>
  LANGUAGE_OPTIONS.find((option) => option.value === value)?.label ??
  LANGUAGE_OPTIONS.find((option) => option.value === DEFAULT_LANGUAGE)?.label;
