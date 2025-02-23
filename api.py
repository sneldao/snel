import os
import asyncio
import logging
from typing import Optional
from pathlib import Path
from enum import StrEnum
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from eth_rpc import set_alchemy_key
from dowse import Pipeline
from dowse.impls.basic.llms import BasicTweetClassifier, BasicTwitterCommands, BasicTwitterQuestion
from dowse.impls.basic.effects import Printer
from dowse.impls.basic.source import TwitterMock
from dowse.models import Tweet

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Classifications(StrEnum):
    """A class that defines the different classifications that can be made by the pipeline."""
    COMMANDS = "commands"
    QUESTION = "question"

# Load environment variables
env_path = Path('.env').absolute()
if not env_path.exists():
    raise FileNotFoundError(f"Could not find .env file at {env_path}")
load_dotenv(dotenv_path=env_path, override=True)

# Ensure all required environment variables are in os.environ
required_vars = {
    "ALCHEMY_KEY": os.getenv("ALCHEMY_KEY"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "QUICKNODE_ENDPOINT": os.getenv("QUICKNODE_ENDPOINT")
}

for var_name, value in required_vars.items():
    if not value:
        raise ValueError(f"{var_name} environment variable is required")
    os.environ[var_name] = value

# Set Alchemy key
set_alchemy_key(required_vars["ALCHEMY_KEY"])

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandRequest(BaseModel):
    content: str
    creator_name: str = "@user"
    creator_id: int = 1

class CommandResponse(BaseModel):
    content: Optional[str] = None
    error_message: Optional[str] = None

@app.post("/api/process-command")
async def process_command(request: CommandRequest) -> CommandResponse:
    try:
        logger.info(f"Processing command: {request.content}")
        
        # Create a pipeline for processing the command
        pipeline = Pipeline[Tweet, Tweet, Classifications](
            classifier=BasicTweetClassifier,
            handlers={
                Classifications.COMMANDS: BasicTwitterCommands.add_effect(Printer(prefix="COMMANDS")),
                Classifications.QUESTION: BasicTwitterQuestion.add_effects([Printer(prefix="QUESTION")]),
            },
            source=TwitterMock(),
        )

        # Process the command
        result = await pipeline.process(
            Tweet(
                id=1,  # Dummy ID
                content=request.content,
                creator_id=request.creator_id,
                creator_name=request.creator_name,
            )
        )

        if not result or not result.content:
            logger.warning("Pipeline returned no result")
            raise HTTPException(
                status_code=500,
                detail="Failed to process command. Please try again."
            )

        # Log the result for debugging
        logger.info(f"Command processed successfully. Result type: {type(result)}")
        logger.info(f"Result content: {result.content}")

        return CommandResponse(content=str(result.content))
    
    except ValueError as ve:
        logger.error(f"ValueError in command processing: {str(ve)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid command format: {str(ve)}"
        ) from ve
    
    except Exception as e:
        logger.error(f"Unexpected error in command processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your command: {str(e)}"
        ) from e

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 