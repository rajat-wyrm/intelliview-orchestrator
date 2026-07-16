"use client";

import styles from "./VideoPlayer.module.css";
import { TranscriptItem } from "@/types/transcript";

interface TranscriptPanelProps {
  transcript: TranscriptItem[];
  active: TranscriptItem | null;
}

export default function TranscriptPanel({
  transcript,
  active,
}: TranscriptPanelProps) {
  return (
    <div className={styles.transcriptPanel}>
      <h2 className={styles.transcriptTitle}>
        Interview Transcript
      </h2>

      <div className={styles.transcriptList}>
        {transcript.map((item) => (
          <div
            key={item.id}
            className={
              active?.id === item.id
                ? styles.activeTranscript
                : styles.transcriptItem
            }
          >
            <span className={styles.time}>
              {formatTime(item.start)}
            </span>

            <p>{item.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTime(seconds: number) {
  const mins = Math.floor(seconds / 60);

  const secs = Math.floor(seconds % 60);

  return `${mins.toString().padStart(2, "0")}:${secs
    .toString()
    .padStart(2, "0")}`;
}