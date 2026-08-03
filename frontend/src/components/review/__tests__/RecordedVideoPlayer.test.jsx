import React, { createRef } from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RecordedVideoPlayer, { RecordedVideoPlayerDemo } from "../RecordedVideoPlayer";

describe("RecordedVideoPlayer Component", () => {
  const sampleVideoUrl = "https://example.com/test-video.mp4";
  const sampleCaptions = [
    { start: 0, end: 5, text: "First caption snippet" },
    { start: 10, end: 20, text: "Second caption snippet" },
    { start: 25, end: 35, text: "Third caption snippet at 30 seconds" },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the video element with correct source URL", () => {
    const { container } = render(
      <RecordedVideoPlayer videoUrl={sampleVideoUrl} captions={sampleCaptions} />
    );

    const videoEl = container.querySelector("video");
    expect(videoEl).toBeInTheDocument();
    expect(videoEl).toHaveAttribute("src", sampleVideoUrl);
  });

  it("displays synchronized closed captions when currentTime matches caption range", () => {
    const { container } = render(
      <RecordedVideoPlayer videoUrl={sampleVideoUrl} captions={sampleCaptions} />
    );

    const videoEl = container.querySelector("video");

    // Initially at 0s, first caption should be visible
    act(() => {
      Object.defineProperty(videoEl, "currentTime", {
        writable: true,
        value: 2,
      });
      fireEvent.timeUpdate(videoEl);
    });

    expect(screen.getByText("First caption snippet")).toBeInTheDocument();

    // Move time to 15s (Second caption snippet)
    act(() => {
      videoEl.currentTime = 15;
      fireEvent.timeUpdate(videoEl);
    });

    expect(screen.getByText("Second caption snippet")).toBeInTheDocument();
    expect(screen.queryByText("First caption snippet")).not.toBeInTheDocument();
  });

  it("exposes seekTo(seconds) via imperative ref handle", () => {
    const ref = createRef();
    const { container } = render(
      <RecordedVideoPlayer ref={ref} videoUrl={sampleVideoUrl} captions={sampleCaptions} />
    );

    const videoEl = container.querySelector("video");

    act(() => {
      ref.current.seekTo(30);
    });

    expect(videoEl.currentTime).toBe(30);
  });

  it("toggles closed captions overlay on and off", () => {
    const { container } = render(
      <RecordedVideoPlayer videoUrl={sampleVideoUrl} captions={sampleCaptions} />
    );

    const videoEl = container.querySelector("video");

    act(() => {
      videoEl.currentTime = 2;
      fireEvent.timeUpdate(videoEl);
    });

    expect(screen.getByText("First caption snippet")).toBeInTheDocument();

    // Click CC toggle button
    const ccBtn = screen.getByTitle("Toggle Closed Captions");
    fireEvent.click(ccBtn);

    // Caption should be hidden
    expect(screen.queryByText("First caption snippet")).not.toBeInTheDocument();

    // Click again to turn back ON
    fireEvent.click(ccBtn);
    expect(screen.getByText("First caption snippet")).toBeInTheDocument();
  });

  it("handles empty or null captions gracefully without crashing", () => {
    const { container } = render(
      <RecordedVideoPlayer videoUrl={sampleVideoUrl} captions={[]} />
    );

    const videoEl = container.querySelector("video");

    act(() => {
      videoEl.currentTime = 10;
      fireEvent.timeUpdate(videoEl);
    });

    expect(container.querySelector("[data-testid='caption-overlay']")).not.toBeInTheDocument();
  });
});

describe("RecordedVideoPlayerDemo Component", () => {
  it("renders demo component with Jump to 30s button and triggers seekTo", () => {
    const { container } = render(<RecordedVideoPlayerDemo />);

    const jumpBtn = screen.getByTestId("jump-30s-btn");
    expect(jumpBtn).toBeInTheDocument();

    const videoEl = container.querySelector("video");
    expect(videoEl).toBeInTheDocument();

    fireEvent.click(jumpBtn);
    expect(videoEl.currentTime).toBe(30);
  });
});
