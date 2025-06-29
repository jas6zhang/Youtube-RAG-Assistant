# set up api
from typing import Union
import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from transcript import fetch_transcript_openai, fetch_transcript_youtube
import vectorStore

load_dotenv()

app = FastAPI()

# Add CORS middleware for browser extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for browser extension
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# send api call to openai
class TranscriptRequest(BaseModel):
    video_id: str


class QuestionRequest(BaseModel):
    video_id: str
    question: str
    n_results: int


# accept video ID, fetch transcript, convert chunks into embeds, store in ChromaDB
# can test out diff chunking strats
# Strat: Test Later
# - Initialize empty chunk
# - For each subtitle segment:
#     - Add to current chunk
#     - If:
#         - chunk has > X tokens (e.g., 300), OR
#         - pause > Y seconds between current and next (e.g., 1.2s)
#       → finalize chunk, start new one


@app.get("/")
def test():
    return {"hello"}


@app.post("/load_transcript")
def load_transcript(req: TranscriptRequest):
    try:
        transcript = fetch_transcript_openai(req.video_id)
        # print(transcript)
        chunks = vectorStore.split_text_to_chunks(transcript)
        texts = [chunk["text"] for chunk in chunks]
        # metadatas must be a list of dicts, not floats
        metadatas = [{"start": chunk["start"], "end": chunk["end"]} for chunk in chunks]
        vectorStore.store_chunks(req.video_id, texts, metadatas)
        # need to retunr status code and response
        return {"status": "success", "chunks_stored": len(chunks)}
    except Exception as e:
        print("Exception", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask_question")
def ask_question(req: QuestionRequest):
    try:
        results = vectorStore.query_chunks(req.video_id, req.question, req.n_results)
        returned_chunks = results["documents"][
            0
        ]  # can make multiple queries at once # ?
        print("Documents", returned_chunks)
        returned_metadatas = results["metadatas"][0]
        print("Metadata", returned_metadatas)

        prompt = f"""Based on the following transcript chunks from a YouTube video, 
        answer the user's question as accurately as possible using only the provided context and be concise.

        User question: {req.question}

        Transcript Chunks: {returned_chunks}

        Timestamp to Transcript Chunks: {returned_metadatas}
        
        IMPORTANT: After your answer, list ONLY the timestamps that directly support your answer, 
        in TIMESTAMPS: times go here in seconds seperated by commas and by order of relevance (most relevant chunk goes first). If no specific timestamps are relevant, write: TIMESTAMPS: none"""

        client = OpenAI()
        completion = client.chat.completions.create(
            model="gpt-4o",
            # stream=true
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant to aid users when asking questions about videos.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        print("OPEN AI RESPONSE: ", completion.choices[0].message.content)

        return {"status": "success", "response": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
