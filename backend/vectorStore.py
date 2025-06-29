import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
import tiktoken
import os
from dotenv import load_dotenv

load_dotenv()

# Use persistent storage instead of in-memory
chroma_client = chromadb.PersistentClient(path="./chroma_db")


# 300 tokens / chars, need to build custom chunker
# because text splitter loses timestamp context


# return chunks with metadata
def split_text_to_chunks(document, chunk_size=50, max_pause=1.25, chunk_overlap=0):
    chunks = []
    cur_chunk = []
    cur_tokens = 0
    last_end = 0.0

    # get_encoding
    try:
        enc = tiktoken.encoding_for_model("gpt-4o")
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")

    # if pause less than certain amount, combine them
    for entry in document:
        text = entry["text"]
        start = entry["start"]
        end = entry["end"]

        pause = start - last_end

        tokens = len(enc.encode(text))

        # start new chunk if too big
        if cur_chunk and (cur_tokens + tokens > chunk_size or pause > max_pause):
            # join all the entries in the current chunk together
            chunk_text = " ".join([chunk_entry["text"] for chunk_entry in cur_chunk])
            chunks.append(
                {
                    "text": chunk_text,
                    "start": cur_chunk[0]["start"],
                    "end": cur_chunk[-1][
                        "end"
                    ],  # get first timestamp and last entry timestap of all in the chunk
                }
            )
            cur_chunk = []
            cur_tokens = 0

        cur_chunk.append(entry)
        cur_tokens += tokens

        last_end = end

    # add last chunk
    if cur_chunk:
        chunk_text = " ".join([chunk_entry["text"] for chunk_entry in cur_chunk])
        chunks.append(
            {
                "text": chunk_text,
                "start": cur_chunk[0]["start"],
                "end": cur_chunk[-1][
                    "end"
                ],  # get first timestamp and last entry timestap of all in the chunk
            }
        )

    print("Chunks Here", chunks)
    return chunks


def embed_texts(texts):
    # print("Embed Texts", texts)
    openai_client = OpenAI()

    response = openai_client.embeddings.create(
        input=texts, model="text-embedding-3-small"
    )
    # print("Response Data", response.data)
    return [text_embed.embedding for text_embed in response.data]


def store_chunks(video_id, texts, metadatas=None):
    filtered_texts = [t for t in texts if isinstance(t, str) and t.strip()]
    if not filtered_texts:
        print("No non-empty texts to store.")
        return
    embeddings = embed_texts(filtered_texts)
    print("Issue Here")
    # ChromaDB expects string IDs
    ids = [str(i) for i in range(len(filtered_texts))]
    collection = chroma_client.get_or_create_collection(name=f"transcript_{video_id}")
    collection.add(
        ids=ids, documents=filtered_texts, embeddings=embeddings, metadatas=metadatas
    )


def query_chunks(video_id, query, n_results):
    # have to use embedding query, since prev used gpt model,
    # and don't want to use chromaDB internals
    print(f"Querying collection: transcript_{video_id}")
    query_embedding = embed_texts([query])[0]
    collection = chroma_client.get_or_create_collection(name=f"transcript_{video_id}")

    # Debug: Check if collection has any data
    count = collection.count()
    print(f"Collection has {count} documents")

    if count == 0:
        print("WARNING: Collection is empty! No transcript was loaded for this video.")
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    print(f"Query results: {len(results['documents'][0])} documents found")
    return results
