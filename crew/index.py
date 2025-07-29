
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Union, List, Dict, Any
from src.crew.cook_crew import CookCrew
from src.crew.tools.contextsaver import add_to_history
import json
import os
# Initialize FastAPI app
app = FastAPI(
    title="CookCrew Assistant API",
    description="AI-powered cooking assistant with memory for personalized recipe recommendations",
    version="1.0.0"
)

# Initialize CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize CookCrew instance (reuse for memory efficiency)
cook_crew = CookCrew()

# Pydantic models for structured input
class CookingQuery(BaseModel):
    user_query: str
    user_id: Optional[str] = "dishes"
    save_to_memory: Optional[bool] = True

class MemoryRequest(BaseModel):
    content: Union[str, List[Dict[str, str]], Dict[str, str]]
    user_id: Optional[str] = "dishes"

@app.get("/")
async def root():
    return {
        "message": "👩‍🍳 Welcome to the CookCrew Assistant API!",
        "description": "AI-powered cooking assistant with memory for personalized recommendations",
        "version": "1.0.0",
        "features": [
            "Recipe recommendations and cooking advice",
            "Ingredient substitutions and alternatives", 
            "Cooking techniques and tips",
            "Dietary restrictions and preferences support",
            "Conversation memory for personalized experience"
        ],
        "endpoints": {
            "POST /cook": "Ask cooking questions with memory support",
            "POST /add_memory": "Add specific content to user memory",
            "GET /health": "Health check endpoint"
        }
    }

@app.post("/cook")
async def ask_cooking_question(request: CookingQuery):
    """
    Ask cooking-related questions with optional memory storage
    """
    try:
        if not request.user_query.strip():
            raise HTTPException(status_code=400, detail="Cooking query cannot be empty")
        
        # Get the crew instance (reuse the global instance for memory efficiency)
        crew = cook_crew.cooking_crew()
        
        # Pass the query as inputs to kickoff method
        result = crew.kickoff(inputs={"user_query": "user is looking for recipe + " + request.user_query, "user_id": request.user_id})

        # Save conversation to memory if requested
        memory_status = None
        if request.save_to_memory:
            try:
                # Save user query to memory
                user_memory = add_to_history(
                    {"role": "user", "content": request.user_query},
                    user_id=request.user_id
                )
                
                # Save assistant response to memory
                assistant_memory = add_to_history(
                    {"role": "assistant", "content": str(result)},
                    user_id=request.user_id
                )
                
                memory_status = {
                    "user_message": user_memory,
                    "assistant_response": assistant_memory
                }
            except Exception as memory_error:
                memory_status = f"Memory save failed: {str(memory_error)}"
        
        return {
            "status": "success",
            "user_id": request.user_id,
            "query": request.user_query,
            "result": result,
            "memory_saved": request.save_to_memory,
            "memory_status": memory_status
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cooking assistant failed: {str(e)}")

@app.post("/add_memory")
async def add_to_memory_endpoint(request: MemoryRequest):
    """
    Add specific content to user memory
    """
    try:
        memory_result = add_to_history(
            content=request.content,
            user_id=request.user_id
        )
        
        return {
            "status": "success",
            "user_id": request.user_id,
            "memory_result": memory_result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add to memory: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    try:
        # Test CookCrew initialization
        test_crew = cook_crew.cooking_crew()
        
        return {
            "status": "healthy",
            "message": "CookCrew Assistant API is running successfully",
            "cooking_crew_status": "initialized",
            "memory_system": "active"
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"CookCrew initialization failed: {str(e)}",
            "cooking_crew_status": "failed"
        }