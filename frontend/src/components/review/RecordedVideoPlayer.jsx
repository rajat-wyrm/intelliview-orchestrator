"use client";

import React, {
  forwardRef,
  useImperativeHandle,
  useRef,
  useState,
  useEffect,
  useCallback
} from "react";
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Subtitles,
  Maximize,
  RotateCcw,
  SkipForward
} from "lucide-react";

/**
 * Format time in seconds to MM:SS or HH:MM:SS format.
 */
function formatTime(seconds) {
  if (!seconds || isNaN(seconds) || seconds < 0) return "00:00";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);

  const pad = (num) => String(num).padStart(2, "0");

  if (h > 0) {
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
  }
  return `${pad(m)}:${pad(s)}`;
}

/**
 * RecordedVideoPlayer
 * 
 * Synchronized video player component supporting closed captions / subtitle overlay.
 * 
 * Props:
 * - videoUrl (string): URL of the video source.
 * - captions (Array<{ start: number, end: number, text: string }>): Closed captions list.
 * - initialCaptionsEnabled (boolean): Default caption visibility state.
 * - autoPlay (boolean): Auto play on load.
 * - className (string): Container custom CSS classes.
 * - onTimeUpdate (function): Callback when playback time changes.
 * - onEnded (function): Callback when video reaches end.
 * 
 * Exposed Ref Handle:
 * - seekTo(seconds: number): Jumps playback to the specified timestamp in seconds.
 * - play(): Starts playback.
 * - pause(): Pauses playback.
 * - toggleCaptions(): Toggles closed captions overlay state.
 */
export const RecordedVideoPlayer = forwardRef(function RecordedVideoPlayer(
  {
    videoUrl,
    captions = [],
    initialCaptionsEnabled = true,
    autoPlay = false,
    className = "",
    onTimeUpdate,
    onEnded
  },
  ref
) {
  const videoRef = useRef(null);
  const containerRef = useRef(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [captionsEnabled, setCaptionsEnabled] = useState(initialCaptionsEnabled);
  const [activeCaption, setActiveCaption] = useState(null);
  const [showControls, setShowControls] = useState(true);
  const controlsTimeoutRef = useRef(null);

  // Imperative ref method exposing seekTo as specified by issue requirements
  useImperativeHandle(
    ref,
    () => ({
      seekTo: (seconds) => {
        if (videoRef.current) {
          const targetTime = Math.max(0, Math.min(seconds, videoRef.current.duration || seconds));
          videoRef.current.currentTime = targetTime;
          setCurrentTime(targetTime);
        }
      },
      play: () => {
        if (videoRef.current) {
          videoRef.current.play();
        }
      },
      pause: () => {
        if (videoRef.current) {
          videoRef.current.pause();
        }
      },
      toggleCaptions: () => {
        setCaptionsEnabled((prev) => !prev);
      },
      getCurrentTime: () => currentTime,
      videoElement: videoRef.current
    }),
    [currentTime]
  );

  // Sync active caption with currentTime
  useEffect(() => {
    if (!captions || captions.length === 0) {
      setActiveCaption(null);
      return;
    }

    const currentMatch = captions.find(
      (cap) => currentTime >= cap.start && currentTime <= cap.end
    );

    setActiveCaption(currentMatch || null);
  }, [currentTime, captions]);

  // Video event handlers
  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) {
      const time = videoRef.current.currentTime;
      setCurrentTime(time);
      if (onTimeUpdate) {
        onTimeUpdate(time);
      }
    }
  }, [onTimeUpdate]);

  const handleLoadedMetadata = useCallback(() => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  }, []);

  const togglePlay = useCallback(() => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  const handleSeek = (e) => {
    const seekTime = parseFloat(e.target.value);
    if (videoRef.current) {
      videoRef.current.currentTime = seekTime;
      setCurrentTime(seekTime);
    }
  };

  const handleVolumeChange = (e) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (videoRef.current) {
      videoRef.current.volume = val;
      if (val === 0) {
        setIsMuted(true);
      } else if (isMuted) {
        setIsMuted(false);
      }
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    if (isMuted) {
      videoRef.current.muted = false;
      videoRef.current.volume = volume || 1;
      setIsMuted(false);
    } else {
      videoRef.current.muted = true;
      setIsMuted(true);
    }
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
  };

  // Hide controls after inactivity
  const handleMouseMove = () => {
    setShowControls(true);
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    controlsTimeoutRef.current = setTimeout(() => {
      if (isPlaying) {
        setShowControls(false);
      }
    }, 3000);
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => isPlaying && setShowControls(false)}
      className={`relative group bg-zinc-950 text-white rounded-xl overflow-hidden shadow-2xl border border-zinc-800 select-none ${className}`}
    >
      {/* Video Element */}
      <video
        ref={videoRef}
        src={videoUrl}
        autoPlay={autoPlay}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => {
          setIsPlaying(false);
          if (onEnded) onEnded();
        }}
        onClick={togglePlay}
        className="w-full h-auto max-h-[600px] object-contain bg-black cursor-pointer"
      />

      {/* Closed Captions Overlay */}
      {captionsEnabled && activeCaption && (
        <div
          data-testid="caption-overlay"
          className="absolute bottom-16 left-1/2 -translate-x-1/2 max-w-[85%] px-4 py-2 bg-black/80 backdrop-blur-md rounded-lg text-center transition-all duration-200 shadow-lg border border-white/10 z-20 pointer-events-none"
        >
          <p className="text-sm sm:text-base md:text-lg font-medium text-amber-200 tracking-wide leading-snug">
            {activeCaption.text}
          </p>
        </div>
      )}

      {/* Control Overlay */}
      <div
        className={`absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20 flex flex-col justify-between p-4 transition-opacity duration-300 ${
          showControls || !isPlaying ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      >
        {/* Top Header Bar */}
        <div className="flex items-center justify-between z-10">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Recorded Interview
            </span>
          </div>

          {/* CC Active Status Pill */}
          <button
            type="button"
            onClick={() => setCaptionsEnabled(!captionsEnabled)}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors border ${
              captionsEnabled
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                : "bg-zinc-800/80 text-zinc-400 border-zinc-700 hover:text-white"
            }`}
          >
            CC {captionsEnabled ? "ON" : "OFF"}
          </button>
        </div>

        {/* Bottom Control Bar */}
        <div className="flex flex-col gap-2 z-10">
          {/* Progress / Scrubber Bar */}
          <div className="flex items-center gap-3">
            <input
              type="range"
              min="0"
              max={duration || 100}
              step="0.1"
              value={currentTime}
              onChange={handleSeek}
              className="w-full h-1.5 bg-zinc-700/80 accent-amber-500 hover:accent-amber-400 rounded-lg cursor-pointer transition-all"
              aria-label="Video scrubber"
            />
          </div>

          {/* Controls Row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Play / Pause */}
              <button
                type="button"
                onClick={togglePlay}
                aria-label={isPlaying ? "Pause" : "Play"}
                className="p-2 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-white transition-colors border border-zinc-700"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>

              {/* Volume / Mute */}
              <div className="flex items-center gap-2 group/vol">
                <button
                  type="button"
                  onClick={toggleMute}
                  aria-label={isMuted ? "Unmute" : "Mute"}
                  className="p-2 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-white transition-colors border border-zinc-700"
                >
                  {isMuted || volume === 0 ? (
                    <VolumeX className="w-4 h-4 text-red-400" />
                  ) : (
                    <Volume2 className="w-4 h-4" />
                  )}
                </button>

                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={isMuted ? 0 : volume}
                  onChange={handleVolumeChange}
                  className="w-16 sm:w-20 h-1.5 bg-zinc-700 accent-amber-500 rounded-lg cursor-pointer"
                  aria-label="Volume slider"
                />
              </div>

              {/* Time Display */}
              <span className="text-xs font-mono text-zinc-300">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
            </div>

            <div className="flex items-center gap-2">
              {/* CC Toggle Button */}
              <button
                type="button"
                onClick={() => setCaptionsEnabled(!captionsEnabled)}
                aria-label="Toggle Captions"
                title="Toggle Closed Captions"
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                  captionsEnabled
                    ? "bg-amber-500 text-black border-amber-400 font-semibold"
                    : "bg-zinc-800/80 text-zinc-400 border-zinc-700 hover:text-white"
                }`}
              >
                <Subtitles className="w-4 h-4" />
                <span>CC</span>
              </button>

              {/* Fullscreen Button */}
              <button
                type="button"
                onClick={toggleFullscreen}
                aria-label="Toggle Fullscreen"
                className="p-2 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-white transition-colors border border-zinc-700"
              >
                <Maximize className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

RecordedVideoPlayer.displayName = "RecordedVideoPlayer";

/**
 * RecordedVideoPlayerDemo
 * 
 * Standalone demo component demonstrating synced video playback, closed captions,
 * caption toggling, and the seekTo(seconds) imperative ref method.
 */
export function RecordedVideoPlayerDemo() {
  const playerRef = useRef(null);

  // Sample mock video & closed captions data
  const sampleVideoUrl =
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4";

  const sampleCaptions = [
    { start: 0, end: 4, text: "Welcome to the candidate interview technical review session." },
    { start: 5, end: 9, text: "Today we will discuss distributed system architecture design." },
    { start: 10, end: 16, text: "Can you explain how you handle cache invalidation in microservices?" },
    { start: 17, end: 24, text: "We use write-through caching combined with pub/sub event channels." },
    { start: 25, end: 32, text: "That prevents stale reads across multiple instance nodes effectively." },
    { start: 33, end: 40, text: "Notice how captions automatically stay synchronized with playback time." },
    { start: 41, end: 50, text: "You can click any timestamp or use seekTo to jump directly." }
  ];

  const handleJumpTo30s = () => {
    if (playerRef.current) {
      playerRef.current.seekTo(30);
    }
  };

  const handleSeekTo = (seconds) => {
    if (playerRef.current) {
      playerRef.current.seekTo(seconds);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6 bg-zinc-900 text-zinc-100 rounded-2xl border border-zinc-800 shadow-xl">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Subtitles className="w-5 h-5 text-amber-400" />
            Synced Video Playback with Closed Captions
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Standalone demo featuring synced captions overlay and imperative ref controls.
          </p>
        </div>

        {/* Demo Jump Test Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleJumpTo30s}
            data-testid="jump-30s-btn"
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950 transition-colors shadow-md flex items-center gap-1.5"
          >
            <SkipForward className="w-3.5 h-3.5" />
            Jump to 30s
          </button>

          <button
            type="button"
            onClick={() => playerRef.current?.toggleCaptions()}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition-colors"
          >
            Toggle CC
          </button>
        </div>
      </header>

      {/* Main Video Component */}
      <RecordedVideoPlayer
        ref={playerRef}
        videoUrl={sampleVideoUrl}
        captions={sampleCaptions}
      />

      {/* Interactive Timestamp Seekers */}
      <section className="space-y-3 bg-zinc-950 p-4 rounded-xl border border-zinc-800">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
          <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
          Interactive Caption Cue Markers (Click to Seek)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {sampleCaptions.map((cap, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSeekTo(cap.start)}
              className="flex items-start gap-2.5 p-2.5 rounded-lg bg-zinc-900/90 hover:bg-zinc-800 text-left border border-zinc-800 hover:border-amber-500/40 transition-all group"
            >
              <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 group-hover:bg-amber-500 group-hover:text-black transition-colors shrink-0">
                {formatTime(cap.start)}
              </span>
              <span className="text-xs text-zinc-300 line-clamp-1 group-hover:text-white">
                {cap.text}
              </span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

export default RecordedVideoPlayer;
