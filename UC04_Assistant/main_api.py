from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from assistant_agent import get_assistant_response
from logger_config import logger

app = FastAPI(title="BRI Investigation Assistant API")

# Add CORS Middleware to allow requests from the test UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = []
    ai_mode: Optional[str] = "Simulated Mock"

@app.get("/")
async def root():
    return {"status": "online", "message": "BRI Investigation Assistant API is running"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint for third-party UIs to interact with the BRI Assistant.
    Supports both 'Simulated Mock' and 'Live Azure Foundry' modes.
    """
    logger.info(f"API Request: {request.query} (Mode: {request.ai_mode})")
    try:
        # Route to original agent logic
        response = await get_assistant_response(
            user_query=request.query,
            chat_history=request.history,
            ai_mode=request.ai_mode
        )
        logger.info("API Response generated successfully")
        return response
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
