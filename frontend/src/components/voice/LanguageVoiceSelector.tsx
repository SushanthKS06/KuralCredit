import { useEffect, useState } from "react";
import type { ChangeEvent } from "react";
import { api } from "../../api/client";
import type { Capabilities, Language, Voice } from "../../api/types";
import styles from "./LanguageVoiceSelector.module.css";

interface Props {
  selectedLanguage: string;
  selectedVoice: string;
  onLanguageChange: (language: string) => void;
  onVoiceChange: (voice: string) => void;
  disabled?: boolean;
}

export function LanguageVoiceSelector({
  selectedLanguage,
  selectedVoice,
  onLanguageChange,
  onVoiceChange,
  disabled = false,
}: Props) {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .capabilities()
      .then((data) => {
        setCapabilities(data);
      })
      .catch((err) => {
        console.error("Failed to load capabilities:", err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const languages: Language[] = capabilities?.languages ?? [
    { code: "ta-IN", name: "Tamil", native_name: "தமிழ்", script: "Taml", stt_supported: true, voices: [] },
    { code: "en-IN", name: "English (India)", native_name: "English", script: "Latn", stt_supported: true, voices: [] },
  ];

  const currentLang = languages.find((l) => l.code === selectedLanguage);
  const availableVoices: Voice[] = currentLang?.voices && currentLang.voices.length > 0
    ? currentLang.voices
    : [
        { name: "Trisha", gender: "female", model: "timbre-v2.5", languages: ["ta-IN"], persona: null, description: null },
        { name: "Kaveri", gender: "female", model: "timbre-v2.5", languages: ["en-IN", "ta-IN"], persona: null, description: null },
      ];

  function handleLangSelect(e: ChangeEvent<HTMLSelectElement>) {
    const langCode = e.target.value;
    onLanguageChange(langCode);
    const targetLang = languages.find((l) => l.code === langCode);
    if (targetLang && targetLang.voices.length > 0) {
      if (!targetLang.voices.some((v) => v.name === selectedVoice)) {
        onVoiceChange(targetLang.voices[0].name);
      }
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="lang-select">
          Interview Language
        </label>
        <select
          id="lang-select"
          className={styles.select}
          value={selectedLanguage}
          onChange={handleLangSelect}
          disabled={disabled || loading}
        >
          {languages.map((l) => (
            <option key={l.code} value={l.code}>
              {l.name} ({l.native_name})
            </option>
          ))}
        </select>
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="voice-select">
          Spoken Voice (Gnani Timbre)
        </label>
        <select
          id="voice-select"
          className={styles.select}
          value={selectedVoice}
          onChange={(e) => onVoiceChange(e.target.value)}
          disabled={disabled || loading || availableVoices.length === 0}
        >
          {availableVoices.map((v) => (
            <option key={v.name} value={v.name}>
              {v.name} ({v.gender})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
