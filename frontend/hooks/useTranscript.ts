import { useEffect, useState } from "react";

import { TranscriptItem } from "@/types/transcript";

export default function useTranscript(
  currentTime: number,
  transcript: TranscriptItem[]
) {
  const [activeTranscript, setActiveTranscript] =
    useState<TranscriptItem | null>(null);

  useEffect(() => {
    const current = transcript.find(
      (item) =>
        currentTime >= item.start &&
        currentTime <= item.end
    );

    setActiveTranscript(current || null);
  }, [currentTime, transcript]);

  return activeTranscript;
}