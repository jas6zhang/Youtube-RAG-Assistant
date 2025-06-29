RAG:
- Add context to LLM 
- 2 Components: Indexing, Retrieval and Gen

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

Embeds it

Stores in vector DB (local or memory)

Handles GPT queries


don't need the chrome action API because those should be used to communicate to background scripts etc. 


Uvicorn is an ASGI (Asynchronous Server Gateway Interface) web server implementation for Python. It's specifically designed to run Python web applications that use the ASGI standard, which is the modern successor to WSGI.


# Primary Issues
# Can only determine from audio context, image context not supported
