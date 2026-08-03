from pydub import AudioSegment

AudioSegment.converter = r"C:\Users\Mukesh\Downloads\ffmpeg-8.1.2-essentials_build\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\Users\Mukesh\Downloads\ffmpeg-8.1.2-essentials_build\ffmpeg-8.1.2-essentials_build\bin\ffprobe.exe"
import shutil

from workers.audio_pipeline import split_audio_into_chunks
from workers.ai_client import transcribe_audio_file


AUDIO_PATH = r"D:\CHHOTINISHU\MP3 Song\MP3 Song\Mast Magan ( 2 States).mp3"


def main():
    chunk_paths, chunk_dir = split_audio_into_chunks(AUDIO_PATH)

    print(f"Chunks created: {len(chunk_paths)}")
    print("-" * 50)

    merged_text = []

    try:
        for i, chunk_path in enumerate(chunk_paths, start=1):
            print(f"Chunk {i}: {chunk_path}")

            result = transcribe_audio_file(chunk_path)

            if result is None:
                print("Transcription failed")
                continue

            text = result.get("text", "").strip()

            print(f"Transcript: {text}")
            print("-" * 50)

            merged_text.append(text)

        print("\nMerged Transcript")
        print("=" * 50)
        print(" ".join(merged_text))
        print("=" * 50)

    finally:
        shutil.rmtree(chunk_dir, ignore_errors=True)


if __name__ == "__main__":
    main()