"use client";

interface TimelineProps {
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
}

export default function Timeline({
  currentTime,
  duration,
  onSeek,
}: TimelineProps) {
  return (
    <div style={{ width: "100%", margin: "15px 0" }}>
      <input
        type="range"
        min={0}
        max={duration || 0}
        step={0.1}
        value={currentTime}
        onChange={(e) => onSeek(Number(e.target.value))}
        style={{
          width: "100%",
          cursor: "pointer",
        }}
      />
    </div>
  );
}