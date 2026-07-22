# Youtube RAG Assistant - Optimized with Audio Speed 

Insipired by article: https://george.mand.is/2025/06/openai-charges-by-the-minute-so-make-the-minutes-shorter/

YouTube RAG Assistant is a Chrome extension that allows users to ask questions about any YouTube video and get contextually relevant answers, complete with clickable timestamps. It uses a backend powered by FastAPI, OpenAI, and ChromaDB to transcribe, chunk, embed, and semantically search video transcripts.

## Architecture
```
+-------------------+         +-------------------+         +-------------------+
|  Chrome Extension | <-----> |     FastAPI       | <-----> |   ChromaDB (Vec)  |
| (content-script)  |  HTTP   |   (Python, API)   |  Embeds |  + OpenAI API     |
+-------------------+         +-------------------+         +-------------------+                                                                    
                                        |                              
                                        |                              
                                        v                              
                            +-------------------+                    
                            | Transcript Logic  | 
                            | (YouTube API,     |
                            |  yt-dlp, ffmpeg,  |
                            |  OpenAI Whisper)  |
                            +-------------------+
```

The extension follows a simple architecture: 
- **Frontend:** Chrome extension injects a UI into YouTube, lets users ask questions, and displays answers with relevant timestamps.
- **Transcription:** Uses YouTube captions if available, otherwise downloads audio, peforms audio speedup optimization and transcribes into chunks with OpenAI Whisper.
- **Backend:** FastAPI server handles transcript loading, interacting with vector store and question answering.
- **Vector Store:** ChromaDB stores transcript chunks as embeddings for fast semantic search.

## Deployment & Security

- **Auth:** Set the `API_KEY` env var on the backend to require an `X-API-Key`
  header on every request. Set the same value in the extension's `API_KEY`
  constant (`frontend/content-script.js`). This is light gating — the real
  abuse protection is the server-side per-IP rate limit (`RATE_LIMIT_MAX` /
  `RATE_LIMIT_WINDOW`).
- **Vector store persistence:** ChromaDB writes to `CHROMA_DB_PATH` (default
  `./chroma_db`). Point this at a mounted persistent disk in production — the
  default filesystem on hosts like Render is ephemeral, so without a disk every
  restart silently re-embeds every video and re-bills OpenAI.
- **Transcript loading is async:** `POST /load_transcript` enqueues a background
  job and returns immediately; the extension polls `GET /transcript_status/{id}`
  (pending → loading_captions → transcribing → ready/error).
- **Answers stream** over Server-Sent Events from `POST /ask_question`; each
  cited timestamp comes back with the transcript snippet that supports it.
- See `backend/.env.example` for all config.

## Notes
- Realized that midway through the project, that the Youtube Auto-Generated captions are actually really accurate, and getting the transcript from the captions takes no time in comparision to the long delays of tedious process of having to download the audio, speed audio up and then using Whisper to transcribe. 
- Speeding up audio for transcription also means all timestamps are “compressed.” and needed to multiple the stored segment times by speedup factor. Currently at 2x, but the higher the speedup, the less accurate the transcription and mapping in general. 
- Idea is good for platforms that don't provide generated transcripts (next steps for extension), but generally for Youtube is very inefficient. 
- 50 tokens for chunk size can be considered very small, and is a trade-off for more accurate timestamping (valued for user experience), at the cost of higher storage and embedding costs, and less context for the LLM. 
- Supporting image context from videos in addition to audio could significantly improve the assistant’s ability to understand visual references and gain more context, but this remains a future goal, as extracting and processing relevant visual frames reliably can be very resource-intensive.

