# src/db_sqlite/node.py

from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.graph import END
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from typing import Literal
from langgraph.graph import MessagesState
# Import các prompts đã được cập nhật
from src.test_agent.prompts import table_selector_prompt, generate_query_system_prompt

# --- Khởi tạo các đối tượng cần thiết ---
load_dotenv()
# db = SQLDatabase.from_uri("sqlite:///src/database/Chinook.db")
db=SQLDatabase.from_uri("postgresql://postgres:postgres@localhost:5432/pagila")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

run_query_tool = next(tool for tool in tools if tool.name == "sql_db_query")
list_tables_tool=next(tool for tool in tools if tool.name=="sql_db_list_tables")
# Lấy thông tin chi tiết các bảng một lần và cache lại
# Đây là thông tin sẽ được đưa cho agent chọn bảng
table_details = db.get_table_info()


# --- Định nghĩa các Node cho Graph ---

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

def generate_query(state: dict):
    """
    Node thứ hai: Tạo câu lệnh SQL chỉ dựa trên schema của các bảng đã được chọn.
    """
    messages = state['messages']
    selected_tables = state.get("table_names")
    
    if not selected_tables:
        raise ValueError("No tables selected in the previous step.")
        
    # Lấy schema chi tiết CHỈ cho các bảng liên quan
    relevant_schema = db.get_table_info(table_names=selected_tables)
    
    # Tạo system message với schema thu gọn
    system_message_content = generate_query_system_prompt(db.dialect, 5, relevant_schema)
    system_message = SystemMessage(content=system_message_content)
    
    llm_with_tools = llm.bind_tools([run_query_tool])
    
    # Gọi LLM để tạo query
    response = llm_with_tools.invoke([system_message] + messages)
    
    return {"messages": messages + [response]}


def run_query_and_handle_errors(state: dict):
    """
    Node thứ ba: Chạy query và xử lý lỗi (giữ nguyên như cũ).
    """
    messages = state["messages"]
    last_message = messages[-1]
    tool_call = last_message.tool_calls[0]
    
    try:
        result = run_query_tool.invoke(tool_call["args"])
        message = ToolMessage(content=str(result), tool_call_id=tool_call["id"])
    except Exception as e:
        error_message = f"Error executing query: {e}"
        print(f"--- ERROR ---\n{error_message}")
        message = ToolMessage(content=error_message, tool_call_id=tool_call["id"])
        
    return {"messages": messages + [message]}

# --- Định nghĩa các Router (Conditional Edges) ---

def should_continue_generating(state: dict) -> Literal[END, "run_query"]:
    """Router: Quyết định chạy query hay kết thúc."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "run_query"
    return END

def decide_after_run(state: dict) -> Literal["generate_query", END]:
    """Router: Nếu query lỗi, quay lại bước generate_query để sửa."""
    last_message = state["messages"][-1]
    if isinstance(last_message, ToolMessage) and "error" in last_message.content.lower():
        # Quay lại bước tạo query, không cần chọn lại bảng
        return "generate_query"
    return END