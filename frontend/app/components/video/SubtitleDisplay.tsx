"use client";

interface SubtitleDisplayProps {
  text: string;
}

export default function SubtitleDisplay({
  text,
}: SubtitleDisplayProps) {
  if (!text) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: "80px",
        left: "50%",
        transform: "translateX(-50%)",
        background: "rgba(0,0,0,.7)",
        color: "#fff",
        padding: "10px 18px",
        borderRadius: "8px",
        fontSize: "18px",
        maxWidth: "80%",
        textAlign: "center",
        pointerEvents: "none",
      }}
    >
      {text}
    </div>
  );
}