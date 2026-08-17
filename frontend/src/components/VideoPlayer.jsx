"use client";

import { useEffect, useRef, useState } from "react";
import { Captions, FileVideo, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";

export default function VideoPlayer() {
  const videoRef = useRef(null);
  const [videoFile, setVideoFile] = useState(null);
  const [captionFile, setCaptionFile] = useState(null);
  const [videoUrl, setVideoUrl] = useState("");
  const [captionUrl, setCaptionUrl] = useState("");

  useEffect(() => {
    if (!videoFile) {
      setVideoUrl("");
      return;
    }

    const nextUrl = URL.createObjectURL(videoFile);
    setVideoUrl(nextUrl);

    return () => URL.revokeObjectURL(nextUrl);
  }, [videoFile]);

  useEffect(() => {
    if (!captionFile) {
      setCaptionUrl("");
      return;
    }

    const nextUrl = URL.createObjectURL(captionFile);
    setCaptionUrl(nextUrl);

    return () => URL.revokeObjectURL(nextUrl);
  }, [captionFile]);

  const handleVideoChange = (event) => {
    const file = event.target.files?.[0];
    if (file) setVideoFile(file);
    event.target.value = "";
  };

  const handleCaptionChange = (event) => {
    const file = event.target.files?.[0];
    if (file) setCaptionFile(file);
    event.target.value = "";
  };

  const clearFiles = () => {
    setVideoFile(null);
    setCaptionFile(null);
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.removeAttribute("src");
      videoRef.current.load();
    }
  };

  return (
    <div className="space-y-4">
      <div className="relative aspect-video overflow-hidden rounded-lg border border-border bg-bg-card">
        {videoUrl ? (
          <video
            ref={videoRef}
            controls
            className="h-full w-full bg-black object-contain"
            src={videoUrl}
          >
            {captionUrl && (
              <track
                key={captionUrl}
                default
                kind="captions"
                label="English"
                src={captionUrl}
                srcLang="en"
                onLoad={() => {
                  if (videoRef.current?.textTracks?.[0]) {
                    videoRef.current.textTracks[0].mode = "showing";
                  }
                }}
              />
            )}
            Your browser does not support the video tag.
          </video>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center text-muted">
            <FileVideo size={44} className="mb-3 opacity-40" />
            <p className="text-sm font-medium text-zinc-300">Select a video to begin</p>
            <p className="mt-1 max-w-sm text-xs">
              Choose an interview recording, then add a WebVTT caption file if one is available.
            </p>
          </div>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="block rounded-lg border border-border bg-bg-card p-3">
          <span className="mb-2 flex items-center gap-2 text-xs font-medium text-zinc-300">
            <FileVideo size={14} />
            Interview video
          </span>
          <input
            type="file"
            accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov"
            onChange={handleVideoChange}
            className="block w-full text-xs text-muted file:mr-3 file:rounded-md file:border-0 file:bg-accent file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-white hover:file:bg-accent-dark"
          />
          <span className={cn("mt-2 block truncate text-xs", videoFile ? "text-zinc-300" : "text-muted")}>
            {videoFile ? videoFile.name : "No video selected"}
          </span>
        </label>

        <label className="block rounded-lg border border-border bg-bg-card p-3">
          <span className="mb-2 flex items-center gap-2 text-xs font-medium text-zinc-300">
            <Captions size={14} />
            WebVTT captions
          </span>
          <input
            type="file"
            accept=".vtt,text/vtt"
            onChange={handleCaptionChange}
            className="block w-full text-xs text-muted file:mr-3 file:rounded-md file:border-0 file:bg-bg-panel file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-zinc-200 hover:file:bg-border"
          />
          <span className={cn("mt-2 block truncate text-xs", captionFile ? "text-zinc-300" : "text-muted")}>
            {captionFile ? captionFile.name : "No captions selected"}
          </span>
        </label>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted">
          Captions must be in WebVTT format. Playback controls and caption timing are handled by the browser.
        </p>
        {(videoFile || captionFile) && (
          <button
            type="button"
            onClick={clearFiles}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-bg-card"
          >
            <RotateCcw size={13} />
            Reset
          </button>
        )}
      </div>
    </div>
  );
}
