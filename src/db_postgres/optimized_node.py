from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.graph import END
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from typing import Literal

from src.db_postgres.optimized_prompts import generate_query_system_prompt

load_dotenv()
db=SQLDatabase.from_uri("postgresql://postgres:postgres@localhost:5432/pagila")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

run_query_tool = next(tool for tool in tools if tool.name == "sql_db_query")

db_schema = db.get_table_info()


def generate_query(state: dict):
    """
    Generate a SQL query based on the chat history and full DB schema.
    """
    messages = state['messages']
    
    system_message_content = generate_query_system_prompt(db.dialect, 5, db_schema)
    system_message = SystemMessage(content=system_message_content)
    
    llm_with_tools = llm.bind_tools([run_query_tool])
    
    # user_messages = [msg for msg in messages if isinstance(msg, (HumanMessage, AIMessage, ToolMessage))]
    
    response = llm_with_tools.invoke([system_message] + messages)
    
    return {"messages": [response]}

def run_query_and_handle_errors(state: dict):
    """
    Runs the query tool and catches any database errors,
    returning them as a ToolMessage to be fed back to the LLM.
    """
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    try:
        result = run_query_tool.invoke(tool_call["args"])
        message = ToolMessage(content=str(result), tool_call_id=tool_call["id"])
    except Exception as e:
        error_message = f"Error executing query: {e}"
        print(f"--- ERROR ---\n{error_message}") 
        message = ToolMessage(content=error_message, tool_call_id=tool_call["id"])
        
    return {"messages": [message]}



def should_continue_generating(state: dict) -> Literal[END, "run_query"]:
    """
    Router: decides whether to proceed to running the query or end the flow.
    """
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "run_query"
    return END

def decide_after_run(state: dict) -> Literal["generate_query", END]:
    """
    Router: checks the result of the query execution.
    If it's an error, loop back to the generator. Otherwise, end.
    """
    last_message = state["messages"][-1]
    if isinstance(last_message, ToolMessage) and "error" in last_message.content.lower():
        return "generate_query"
    return END