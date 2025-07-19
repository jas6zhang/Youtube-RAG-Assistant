# set up api
from typing import Union
import os
from dotenv import load_dotenv
import requests

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
        if not vectorStore.check_exists(req.video_id):
            url = f'https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={req.video_id}&key={os.getenv("YOUTUBE_API_KEY")}'
            res = requests.get(url).json()
            caption = res["items"][0]["contentDetails"]["caption"]

            transcript = []
            if caption == "true":
                print("Fetch with Youtube")
                transcript = fetch_transcript_youtube(req.video_id)
            else:
                print("Fetch with OpenAI")
                transcript = fetch_transcript_openai(req.video_id)
            chunks = vectorStore.split_text_to_chunks(transcript)
            texts = [chunk["text"] for chunk in chunks]
            metadatas = [
                {"start": chunk["start"], "end": chunk["end"]} for chunk in chunks
            ]
            vectorStore.store_chunks(req.video_id, texts, metadatas)

            return {"status": "success", "chunks_stored": len(chunks)}
    except Exception as e:
        # print("Exception", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask_question")
def ask_question(req: QuestionRequest):
    try:
        results = vectorStore.query_chunks(req.video_id, req.question, req.n_results)
        returned_chunks = results["documents"][
            0
        ]  # can make multiple queries at once # ?
        # print("Documents", returned_chunks)
        returned_metadatas = results["metadatas"][0]
        # print("Metadata", returned_metadatas)

        prompt = f"""Based on the following transcript chunks from a YouTube video, 
        answer the user's question using the provided context and inferring additional context if there are 
        any inaccuracies or more details are needed. Only provide the answer to the question, the rest of the response is not needed. Provide a response if 
        no relevant information was found for the user (please provide a layer of transparency between the tool workings and the user, do not say things like transcript chunks).

        User question: {req.question}

        Transcript Chunks: {returned_chunks}

        Timestamp to Transcript Chunks: {returned_metadatas}
        
        IMPORTANT: After your answer, list the timestamps that directly support your answer. Please don't just only try to match
        the chunks that have the most matched words to the user's question but actually what you can infer gives the most accurate and context to the question.
        Please respond in TIMESTAMPS: times go here in seconds seperated by commas and by order of relevance (most relevant chunk goes first). If no specific timestamps are relevant, write: TIMESTAMPS: none"""

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
        # print("OPEN AI RESPONSE: ", completion.choices[0].message.content)

        return {"status": "success", "response": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
