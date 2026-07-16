"use client";

import { useEffect, useRef, useState } from "react";

import styles from "./VideoPlayer.module.css";

import { TranscriptItem } from "@/types/transcript";
import transcriptData from "@/data/transcript";

import VideoControls from "./VideoControls";
import TranscriptPanel from "./TranscriptPanel";
import SubtitleDisplay from "./SubtitleDisplay";

export default function VideoPlayer() {
  const videoRef = useRef<HTMLVideoElement>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [videoError, setVideoError] = useState(false);
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [videoSrc, setVideoSrc] = useState("/videos/interview.mp4");
  const [playbackHint, setPlaybackHint] = useState("Preparing local video...");

  const [activeTranscript, setActiveTranscript] =
    useState<TranscriptItem | null>(null);

  useEffect(() => {
    const video = videoRef.current;

    if (!video) return;

    const updateTime = () => {
      const time = video.currentTime;

      setCurrentTime(time);

      const current = transcriptData.find(
        (item) => time >= item.start && time <= item.end
      );

      setActiveTranscript(current || null);

      setIsPlaying(!video.paused);
    };

    const loadedMetadata = () => {
      setDuration(video.duration || 0);
      setVideoError(false);
      setVideoLoaded(true);
      setPlaybackHint("Video ready to play");
    };

    const handleVideoError = () => {
      setVideoError(true);
      setVideoLoaded(false);
      setPlaybackHint("Media could not be loaded in this browser");
    };

    const handlePlay = () => setIsPlaying(true);

    const handlePause = () => setIsPlaying(false);

    video.addEventListener("timeupdate", updateTime);
    video.addEventListener("loadedmetadata", loadedMetadata);
    video.addEventListener("play", handlePlay);
    video.addEventListener("pause", handlePause);
    video.addEventListener("error", handleVideoError);

    return () => {
      video.removeEventListener("timeupdate", updateTime);
      video.removeEventListener("loadedmetadata", loadedMetadata);
      video.removeEventListener("play", handlePlay);
      video.removeEventListener("pause", handlePause);
      video.removeEventListener("error", handleVideoError);
    };
  }, [videoSrc]);

  const togglePlay = () => {
    const video = videoRef.current;

    if (!video) return;

    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  };

  const skipForward = () => {
    const video = videoRef.current;

    if (!video) return;

    video.currentTime = Math.min(video.currentTime + 10, duration);
  };

  const skipBackward = () => {
    const video = videoRef.current;

    if (!video) return;

    video.currentTime = Math.max(video.currentTime - 10, 0);
  };

  const handleSeek = (time: number) => {
    const video = videoRef.current;

    if (!video) return;

    video.currentTime = time;
    setCurrentTime(time);
  };

  const handleVolume = (value: number) => {
    const video = videoRef.current;

    if (!video) return;

    video.volume = value;
    setVolume(value);
  };

  const handleFullscreen = () => {
    const video = videoRef.current;

    if (!video) return;

    if (video.requestFullscreen) {
      video.requestFullscreen();
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.videoSection}>
        <div className={styles.videoFrame}>
          <video
            ref={videoRef}
            className={styles.video}
            preload="metadata"
            playsInline
            poster="https://images.unsplash.com/photo-1516321497487-e288fb19713f?auto=format&fit=crop&w=1200&q=80"
            onLoadedData={() => {
              setVideoError(false);
              setVideoLoaded(true);
              setPlaybackHint("Video ready to play");
            }}
            onError={() => {
              setVideoError(true);
              setVideoLoaded(false);
              setPlaybackHint("Media could not be loaded in this browser");
            }}
          >
            <source src={videoSrc} type="video/mp4" />

            <track
              src="/subtitles/interview.vtt"
              kind="subtitles"
              srcLang="en"
              label="English"
              default
            />

            Your browser does not support the video tag.
          </video>

          {(!videoLoaded || videoError) && (
            <div className={styles.videoOverlay}>
              <span className={styles.videoBadge}>Preview mode</span>
              <p>{playbackHint}</p>
            </div>
          )}
        </div>

        <SubtitleDisplay text={activeTranscript?.text ?? ""} />

        <VideoControls
          playing={isPlaying}
          currentTime={currentTime}
          duration={duration}
          volume={volume}
          onPlayPause={togglePlay}
          onForward={skipForward}
          onBackward={skipBackward}
          onSeek={handleSeek}
          onVolume={handleVolume}
          onFullscreen={handleFullscreen}
        />
      </div>

      <TranscriptPanel
        transcript={transcriptData}
        active={activeTranscript}
      />
    </div>
  );
}