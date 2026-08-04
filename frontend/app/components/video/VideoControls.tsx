"use client";

import { FaBackward } from "react-icons/fa";
import { FaExpand } from "react-icons/fa";
import { FaForward } from "react-icons/fa";
import { FaPause } from "react-icons/fa";
import { FaPlay } from "react-icons/fa";
import { FaVolumeUp } from "react-icons/fa";

import Timeline from "./Timeline";

interface VideoControlsProps {
  playing: boolean;
  currentTime: number;
  duration: number;
  volume: number;

  onPlayPause: () => void;
  onForward: () => void;
  onBackward: () => void;
  onSeek: (time: number) => void;
  onVolume: (volume: number) => void;
  onFullscreen: () => void;
}

export default function VideoControls({
  playing,
  currentTime,
  duration,
  volume,
  onPlayPause,
  onForward,
  onBackward,
  onSeek,
  onVolume,
  onFullscreen,
}: VideoControlsProps) {
  const formatTime = (time: number) => {
    if (!time || Number.isNaN(time)) return "00:00";

    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);

    return `${mins.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}`;
  };

  return (
    <div
      style={{
        width: "100%",
        background: "#ffffff",
        borderRadius: "12px",
        padding: "15px",
        marginTop: "10px",
        boxShadow: "0 3px 10px rgba(0,0,0,.08)",
      }}
    >
      <Timeline
        currentTime={currentTime}
        duration={duration}
        onSeek={onSeek}
      />

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "15px",
          fontWeight: 600,
          color: "#444",
        }}
      >
        <span>{formatTime(currentTime)}</span>

        <span>{formatTime(duration)}</span>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: "18px",
          flexWrap: "wrap",
        }}
      >
        <button
          onClick={onBackward}
          style={buttonStyle}
        >
          <FaBackward />
        </button>

        <button
          onClick={onPlayPause}
          style={{
            ...buttonStyle,
            width: 55,
            height: 55,
            borderRadius: "50%",
            background: "#2563eb",
            color: "#fff",
            fontSize: "18px",
          }}
        >
          {playing ? <FaPause /> : <FaPlay />}
        </button>

        <button
          onClick={onForward}
          style={buttonStyle}
        >
          <FaForward />
        </button>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            minWidth: "180px",
          }}
        >
          <FaVolumeUp />

          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={volume}
            onChange={(e) =>
              onVolume(Number(e.target.value))
            }
            style={{ width: "100%" }}
          />
        </div>

        <button
          onClick={onFullscreen}
          style={buttonStyle}
        >
          <FaExpand />
        </button>
      </div>
    </div>
  );
}

const buttonStyle: React.CSSProperties = {
  width: 45,
  height: 45,
  borderRadius: "50%",
  border: "none",
  background: "#f1f5f9",
  cursor: "pointer",
  fontSize: "16px",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
};