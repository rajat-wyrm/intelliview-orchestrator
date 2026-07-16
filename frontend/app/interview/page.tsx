import VideoPlayer from "@/app/components/video/VideoPlayer";

export default function InterviewPage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f4f6f9",
        padding: "30px",
      }}
    >
      <h1
        style={{
          textAlign: "center",
          marginBottom: "30px",
          fontSize: "2rem",
          color: "#1f2937",
        }}
      >
        AI Interview Video Player
      </h1>

      <VideoPlayer />
    </main>
  );
}