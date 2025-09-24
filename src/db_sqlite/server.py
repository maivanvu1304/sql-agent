import ast 
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Tuple

from src.db_sqlite.graph import agent

from langchain_core.messages import HumanMessage, AIMessage



class Message(BaseModel):
    """
    Model for a message in chat history.
    LibreChat will send it as a tuple [sender, content].
    """
    role: str
    content: str

class LangChainRequest(BaseModel):
    """
    Model for request that LibreChat will send.
    It contains user's question and chat history.
    """
    input: str
    chat_history: Optional[List[Tuple[str, str]]] = []



app = FastAPI(
    title="LangGraph SQL Agent Server",
    description="An API server to run LangGraph SQL query agent.",
    version="1.0.0",
)

@app.post("/invoke")
async def invoke_agent(request: LangChainRequest):
    """
    Main endpoint to receive request from LibreChat and run agent.
    """
    messages = []
    
    if request.chat_history:
        for author, text in request.chat_history:
            if author.lower() == 'user':
                messages.append(HumanMessage(content=text))
            else:
                messages.append(AIMessage(content=text))

    messages.append(HumanMessage(content=request.input))

    try:
        result = agent.invoke({"messages": messages})
        
        final_response_str  = result['messages'][-1].content
        
        try:
            parsed_output = ast.literal_eval(final_response_str)
            return {"output": parsed_output}
        except (ValueError, SyntaxError):
            return {"output": final_response_str}

    except Exception as e:
        return {"output": f"An error occurred: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)