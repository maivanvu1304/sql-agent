from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from typing import Literal
from src.db_sqlite_v2.prompts import generate_query_system_prompt, check_query_system_prompt
import openai
from qdrant_client import QdrantClient


load_dotenv()
# db=SQLDatabase.from_uri("sqlite:///src/database/Chinook.db")
db=SQLDatabase.from_uri("postgresql://postgres:postgres@localhost:5432/pagila")
llm=ChatOpenAI(model="gpt-4o-mini", temperature=0)
# llm=ChatOllama(model="codellama", temperature=0)
toolkit=SQLDatabaseToolkit(db=db, llm=llm)
tools=toolkit.get_tools()

openai_client = openai.OpenAI()
qdrant_client = QdrantClient(host="localhost", port=6333)
COLLECTION_NAME = "db_table_schemas" 
EMBEDDING_MODEL = "text-embedding-3-small"

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

# def call_get_schema(state: MessagesState):
#     """
#     Forces the LLM to call the schema tool based on the conversation history.
#     """
#     llm_with_tools=llm.bind_tools([get_schema_tool], tool_choice=get_schema_tool.name)
#     # llm_with_tools=llm.with_structured_output([get_schema_tool], tool_choice=get_schema_tool.name)
#     response=llm_with_tools.invoke(state["messages"])
#     return {"messages": [response]}
def find_and_get_relevant_schemas(state: MessagesState):
    """
    Sử dụng vector search để tìm các bảng liên quan và lấy schema của chúng.
    """
    print("--- TÌM KIẾM SCHEMA LIÊN QUAN BẰNG VECTOR SEARCH ---")
    user_question = state["messages"][-1].content
    
    # 1. Tạo embedding cho câu hỏi của người dùng
    response = openai_client.embeddings.create(
        input=user_question,
        model=EMBEDDING_MODEL
    )
    query_vector = response.data[0].embedding
    
    # 2. Tìm kiếm trong Qdrant
    search_results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=3,
        score_threshold=0.5 
    )
    
    if not search_results:
        return {"messages": [AIMessage(content="Không tìm thấy schema nào phù hợp.")]}
        
    # 3. Lấy tên các bảng liên quan
    relevant_tables = [result.payload["table_name"] for result in search_results]
    print(f"Các bảng liên quan được tìm thấy: {relevant_tables}")
    
    # 4. Lấy schema (DDL) của các bảng đó
    schema_info = db.get_table_info(relevant_tables)
    
    # 5. Thêm thông tin schema vào state cho node sau
    schema_message = AIMessage(
        content=f"Đây là schema của các bảng có thể liên quan: {', '.join(relevant_tables)}\n\n{schema_info}",
        name="schema_info"
    )
    
    return {"messages": [schema_message]}


def generate_query(state: MessagesState):
    """
    Generates a SQL query based on a condensed version of the conversation history.
    """
    system_message = SystemMessage(content=generate_query_system_prompt(db.dialect))
    
    # --- TỐI ƯU HÓA: TÓM TẮT LỊCH SỬ ---
    history = state["messages"]
    
    # Giữ lại các tin nhắn hệ thống quan trọng ban đầu (tên bảng, schema)
    # và các tin nhắn gần đây nhất để duy trì ngữ cảnh.
    # Chiến lược: Giữ 3 tin nhắn đầu tiên và 4 tin nhắn cuối cùng.
    if len(history) > 7:
        condensed_messages = history[:3] + history[-4:]
        print("--- History condensed ---") # For debugging
    else:
        condensed_messages = history
    # --- KẾT THÚC TỐI ƯU HÓA ---
    
    llm_with_tools = llm.bind_tools([run_query_tool])
    # Sử dụng lịch sử đã được rút gọn để gọi LLM
    response = llm_with_tools.invoke([system_message] + condensed_messages) 
    
    return {"messages": [response]}

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

def should_continue_generating(state: MessagesState) -> Literal[END, "run_query"]:
    """
    Router: decides whether to proceed to checking the query or end the flow.
    """
    last_message = state["messages"][-1]
    return "run_query" if last_message.tool_calls else END

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

