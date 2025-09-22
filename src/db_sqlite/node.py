from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from typing import Literal
from src.db_sqlite.prompts import generate_query_system_prompt, check_query_system_prompt



load_dotenv()
db=SQLDatabase.from_uri("sqlite:///src/database/Chinook.db")
llm=ChatOpenAI(model="gpt-4o-mini", temperature=0)
toolkit=SQLDatabaseToolkit(db=db, llm=llm)
tools=toolkit.get_tools()

list_tables_tool=next(tool for tool in tools if tool.name=="sql_db_list_tables")
run_query_tool=next(tool for tool in tools if tool.name=="sql_db_query")
get_schema_tool=next(tool for tool in tools if tool.name=="sql_db_schema")

get_schema_node=ToolNode([get_schema_tool], name="get_schema")

def list_tables(state: MessagesState):
    """
    Predetermined tool call to list all tables and add the result to the state.
    """
    tool_call={
        "name":"sql_db_list_tables",
        "args":{},
        "id":"predetermined_list_tables",
    }
    result=list_tables_tool.invoke(tool_call)
    response=AIMessage(content=f"Available tables: {result}")
    return {"messages": [response]}

def call_get_schema(state: MessagesState):
    """
    Forces the LLM to call the schema tool based on the conversation history.
    """
    llm_with_tools=llm.bind_tools([get_schema_tool], tool_choice=get_schema_tool.name)
    response=llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def generate_query(state: MessagesState):
    """
    Generates a SQL query based on the full conversation history.
    """
    system_message = SystemMessage(content=generate_query_system_prompt(db.dialect, 5))
    llm_with_tools = llm.bind_tools([run_query_tool])
    response = llm_with_tools.invoke([system_message] + state["messages"])
    return {"messages": [response]}

def check_query(state: MessagesState):
    """
    Takes the query from the previous step, asks the LLM to validate/correct it,
    and then replaces the original tool call with the corrected one.
    """
    original_ai_message = state["messages"][-1]
    original_tool_call = original_ai_message.tool_calls[0]
    query_to_check = original_tool_call["args"]["query"]

    check_request_message = HumanMessage(content=query_to_check)
    system_message = SystemMessage(content=check_query_system_prompt(db.dialect))

    llm_with_tools = llm.bind_tools([run_query_tool], tool_choice=run_query_tool.name)
    checked_response = llm_with_tools.invoke([system_message, check_request_message])

    original_ai_message.tool_calls = checked_response.tool_calls

    return {"messages": [original_ai_message]}

def run_query_and_handle_errors(state: MessagesState):
    """
    Runs the query tool and catches any database errors,
    returning them as a ToolMessage to be fed back to the LLM.
    """
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    try:
        # Execute the query
        result = run_query_tool.invoke(tool_call["args"])
        # On success, create a normal tool message
        message = ToolMessage(content=str(result), tool_call_id=tool_call["id"])
    except Exception as e:
        # On failure, create a tool message with the error
        error_message = f"Error executing query: {e}"
        print(f"--- ERROR ---\n{error_message}") # For debugging
        message = ToolMessage(content=error_message, tool_call_id=tool_call["id"])
        
    return {"messages": [message]}    

def should_continue_generating(state: MessagesState) -> Literal[END, "check_query"]:
    """
    Router: decides whether to proceed to checking the query or end the flow.
    """
    last_message = state["messages"][-1]
    return "check_query" if last_message.tool_calls else END

def decide_after_run(state: MessagesState) -> Literal["generate_query", END]:
    """
    Router: checks the result of the query execution.
    If it's an error, loop back to the generator. Otherwise, end.
    """
    last_message = state["messages"][-1]
    # If the last message is a ToolMessage and contains an error, re-generate
    if isinstance(last_message, ToolMessage) and "error" in last_message.content.lower():
        return "generate_query"
    # Otherwise, the query was successful, so we can end
    return END

