# Youtube RAG Assistant - Optimized with Audio Speed 

Insipired by article: https://george.mand.is/2025/06/openai-charges-by-the-minute-so-make-the-minutes-shorter/

## Setup



## Architecture

Vector DB: 
- Enable fast semantic search

Similarity Search	Finds the closest vectors to a query using cosine/L2 distance (Euclidean)

- Use local instead of cloud vector DB ==> transcript size is small enough, only one user at a time 

Frontend gets the video_id
- Inject an element into page with extension content script 

- scripting API to inject JS into websites
Sends it to a minimal backend that:

Fetches the transcript

Chunks it

The Google Chrome Extension is hosted on Railway and uses FastAPI for the backend API, ChromaDB for storing and quering vector embeddings, and JS for the interface. We utilize the audio optimization method by first using yt-dlp to extract audio, ffmpeg to handle and speed the audio, and then send the chunks to OpenAI transcription service

The backend is built on . and stored on 

Create venv and setup dependencies:

```
pip install requirements.txt
```

Install the source distribution locally:

```
pip install -e .
```

To install from PyPi:

```
pip install simdlib
```

PyPi distribution page: https://pypi.org/project/simdlib/
