# Extract the audio from the video
yt-dlp -f 'bestaudio[ext=m4a]' --extract-audio --audio-format m4a -o 'video-audio.m4a' "https://www.youtube.com/watch?v=LCEmiRjPEtQ" -k;
 
# Create a low-bitrate MP3 version at 3x speed
ffmpeg -i "video-audio.m4a" -filter:a "atempo=3.0" -ac 1 -b:a 64k video-audio-3x.mp3;
 
# Send it along to OpenAI for a transcription

# alternative: use whisper (for local)  
# OpenAI charges for transcription based on audio tokens, which scale with the duration of the input
curl --request POST \
  --url https://api.openai.com/v1/audio/transcriptions \
  --header "Authorization: Bearer $OPENAI_API_KEY" \
  --header 'Content-Type: multipart/form-data' \
  --form file=@video-audio-3x.mp3 \
  --form model=gpt-4o-transcribe > video-transcript.txt;
