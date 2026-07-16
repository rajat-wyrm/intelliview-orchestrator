import { useRef, useState } from "react";

export default function useVideo() {
  const videoRef = useRef<HTMLVideoElement>(null);

  const [playing, setPlaying] = useState(false);

  const [volume, setVolume] = useState(1);

  const [currentTime, setCurrentTime] = useState(0);

  const [duration, setDuration] = useState(0);

  const togglePlay = () => {
    const video = videoRef.current;

    if (!video) return;

    if (video.paused) {
      video.play();
      setPlaying(true);
    } else {
      video.pause();
      setPlaying(false);
    }
  };

  const seek = (time: number) => {
    if (!videoRef.current) return;

    videoRef.current.currentTime = time;

    setCurrentTime(time);
  };

  const forward = () => {
    if (!videoRef.current) return;

    videoRef.current.currentTime += 10;
  };

  const backward = () => {
    if (!videoRef.current) return;

    videoRef.current.currentTime -= 10;
  };

  const changeVolume = (value: number) => {
    if (!videoRef.current) return;

    videoRef.current.volume = value;

    setVolume(value);
  };

  const fullscreen = () => {
    if (!videoRef.current) return;

    videoRef.current.requestFullscreen();
  };

  return {
    videoRef,

    playing,

    volume,

    currentTime,

    duration,

    setCurrentTime,

    setDuration,

    togglePlay,

    seek,

    forward,

    backward,

    changeVolume,

    fullscreen,
  };
}