from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import List, Dict, Any, Optional

# Import the existing pipeline logic from app.py
from app import run_full_pipeline

app = FastAPI(title="Retail AI Analyst API")

# Setup CORS for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    question: str
    conversation_history: List[Message] = []

@app.post("/api/query")
async def process_query(req: QueryRequest):
    try:
        # Run the pipeline
        history = [{"role": msg.role, "content": msg.content} for msg in req.conversation_history]
        result = run_full_pipeline(req.question, history)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
