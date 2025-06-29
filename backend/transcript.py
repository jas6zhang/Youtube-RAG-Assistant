from youtube_transcript_api import YouTubeTranscriptApi
from fastapi import HTTPException
import os
import subprocess
from openai import OpenAI
import tempfile

ytt_api = YouTubeTranscriptApi()


def fetch_transcript_openai(video_id: str):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = download_audio(video_id, temp_dir)
            print("Downloaded Audio")
            sped_up_audio_path = speed_up_audio(audio_path)
            print("Sped Up Audio")
            transcript = transcribe_with_openai(sped_up_audio_path)
            print("Audio Transcribed")

            return transcript
    except Exception as e:
        print(f"Error in fetching transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def download_audio(video_id: str, temp_dir: str):
    # temp store audio for use
    audio_path = os.path.join(temp_dir, "video-audio.m4a")
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        # to run similar to a script line
        # either one string, or a list where each command is an item in the list
        subprocess.run(
            [
                "yt-dlp",
                "-f",
                "bestaudio[ext=m4a]",
                "--extract-audio",
                "--audio-format",
                "m4a",
                "-o",
                audio_path,
                video_url,
                "-k",
            ],
            check=True,
            capture_output=True,
        )
        return audio_path
    except subprocess.CalledProcessError as e:
        # stderr in bytes
        raise HTTPException(
            status_code=500, detail=f"failed to download audio: {e.stderr.decode()}"
        )


def speed_up_audio(audio_path: str, temp_dir: str) -> str:
    sped_up_audio_path = os.path.join(temp_dir, "video-audio-3x.mp3")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                audio_path,
                "-af",
                "highpass=f=200",
                "-filter:a",
                "atempo=3.0" "-ac",
                "1" "-b:a",
                "64k",
                sped_up_audio_path,
            ]
        )
        return sped_up_audio_path
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500, detail=f"failed to speed up audio: {e.stderr.decode()}"
        )


def transcribe_with_openai(audio_path: str) -> list:
    client = OpenAI()

    # read bytes to decode audio
    try:
        # default json

        # returns verbose transcription object
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        segments = []

        for segment in transcription.segments:
            segments.append(
                {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                }
            )
        return segments
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"OpenAI transcription failed {(str(e))}"
        )


# using youtube captions as transcription
def fetch_transcript_youtube(video_id: str) -> str:
    print("video_id for", video_id)
    try:
        transcript = ytt_api.fetch(video_id)
        # transcript = ytt_api.get_transcript(video_id)

        print("Transcript Retrieved: ", transcript)

        return [
            {
                "start": round(entry.start, 2),
                "end": round(entry.start, 2) + round(entry.duration, 2),
                "text": entry.text,
            }
            for entry in transcript
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
