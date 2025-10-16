# from langchain_openai import ChatOpenAI
# from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, SystemMessage
# from langgraph.prebuilt import ToolNode
# from langgraph.graph import StateGraph, END, MessagesState
# from typing import Literal, TypedDict, Annotated, Sequence
# from operator import add
# from langchain_core.messages import BaseMessage
# from src.db_sqlite.graph import agent as sql_agent
# from src.db_sqlite.agent_tool import create_sql_agent_tool

# sql_agent_tool = create_sql_agent_tool(sql_agent)

# from langchain_community.tools.tavily_search import TavilySearchResults
# web_search_tool = TavilySearchResults(max_results=2, name="web_search")

# tools = [sql_agent_tool, web_search_tool]
# tool_node = ToolNode(tools)

# supervisor_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# model_with_tools = supervisor_llm.bind_tools(tools)

# # def supervisor_node(state: MessagesState) -> dict:
# #     """Main supervisor node: decides the next action."""
# #     response = model_with_tools.invoke(state['messages'])
# #     return {"messages": [response]}

# class CustomAgentState(TypedDict):
#     messages: Annotated[Sequence[BaseMessage], add]
#     tool: str | None  # Tool được chọn từ frontend


# def supervisor_node(state: CustomAgentState) -> dict:
#     """
#     Main supervisor node: decides the next action.
    
#     Logic:
#     1. Nếu user đã chọn tool → BẮT BUỘC dùng tool đó
#     2. Nếu tool không trả lời được → Thông báo rõ ràng
#     3. Nếu không chọn tool → Để LLM tự quyết định
#     """
    
#     preferred_tool = state.get('tool')
    
#     # ===== CASE 1: User đã chọn tool cụ thể =====
#     if preferred_tool:
#         print(f"🔒 User chọn tool: {preferred_tool}")
        
#         # Kiểm tra tool có tồn tại không
#         tool_info = next((t for t in tools if t.name == preferred_tool), None)
        
#         if not tool_info:
#             # Tool không tồn tại → Trả về error message
#             error_msg = AIMessage(
#                 content=f"❌ Không tìm thấy tool '{preferred_tool}'. Vui lòng chọn tool khác từ danh sách có sẵn."
#             )
#             return {"messages": [error_msg]}
        
#         try:
#             # 🔥 BẮT BUỘC sử dụng tool được chọn
#             model_with_forced_tool = supervisor_llm.bind_tools(
#                 tools,
#                 tool_choice={"type": "function", "function": {"name": preferred_tool}}
#             )
            
#             # Tạo instruction cho model
#             instruction = f"""Bạn PHẢI sử dụng tool '{preferred_tool}' để trả lời câu hỏi này.

# Tool: {tool_info.name}
# Mô tả: {tool_info.description}

# Nếu tool này không thể trả lời câu hỏi, hãy nói rõ lý do và đề xuất tool phù hợp hơn."""
            
#             messages_with_instruction = [
#                 SystemMessage(content=instruction)
#             ] + state['messages']
            
#             # Gọi model với tool bắt buộc
#             response = model_with_forced_tool.invoke(messages_with_instruction)
            
#             # Verify tool đã được gọi
#             if hasattr(response, 'tool_calls') and response.tool_calls:
#                 used_tool = response.tool_calls[0]['name']
#                 print(f"✅ Tool được sử dụng: {used_tool}")
                
#                 if used_tool == preferred_tool:
#                     return {"messages": [response]}
#                 else:
#                     print(f"⚠️ Warning: Model dùng {used_tool} thay vì {preferred_tool}")
            
#             return {"messages": [response]}
            
#         except Exception as e:
#             # Xử lý lỗi khi force tool
#             print(f"❌ Lỗi khi sử dụng tool '{preferred_tool}': {e}")
#             error_msg = AIMessage(
#                 content=f"❌ Không thể sử dụng tool '{preferred_tool}' để trả lời câu hỏi này.\n\n"
#                         f"Lý do: {str(e)}\n\n"
#                         f"💡 Đề xuất: Vui lòng chọn tool khác phù hợp hơn với câu hỏi của bạn."
#             )
#             return {"messages": [error_msg]}
    
#     # ===== CASE 2: Không chọn tool → LLM tự quyết định =====
#     else:
#         print("🤖 Không có tool preference - LLM tự quyết định")
#         response = model_with_tools.invoke(state['messages'])
#         return {"messages": [response]}


# def should_continue(state: MessagesState) -> Literal["continue", "end"]:
#     """Determines whether to continue to tools or end."""
#     last_message = state['messages'][-1]
#     if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
#         return "continue"
#     return "end"

# builder = StateGraph(MessagesState)

# builder.add_node("supervisor", supervisor_node)
# builder.add_node("tools", tool_node)

# builder.set_entry_point("supervisor")

# builder.add_conditional_edges(
#     "supervisor",
#     should_continue,
#     {"continue": "tools", "end": END}
# )
# builder.add_edge("tools", "supervisor")

# supervisor_agent = builder.compile()

# import uvicorn
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI()

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.get("/tools")
# async def get_tools():
#     """Endpoint to get the list of tools"""
#     tools_info = []
    
#     for tool in tools:
#         tool_info = {
#             "name": tool.name,
#             "description": tool.description,
#             "args_schema": tool.args_schema.schema() if hasattr(tool, 'args_schema') else None,
#         }
#         tools_info.append(tool_info)
    
#     return tools_info
# if __name__ == "__main__":
#     # Chạy FastAPI server
#     uvicorn.run(app, host="0.0.0.0", port=8000)

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, SystemMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END, MessagesState
from typing import Literal

from src.db_sqlite.graph import agent as sql_agent
from src.db_sqlite.agent_tool import create_sql_agent_tool

sql_agent_tool = create_sql_agent_tool(sql_agent)

from langchain_community.tools.tavily_search import TavilySearchResults
web_search_tool = TavilySearchResults(max_results=2, name="web_search")

tools = [sql_agent_tool, web_search_tool]
tool_node = ToolNode(tools)

supervisor_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
model_with_tools = supervisor_llm.bind_tools(tools)


class CustomAgentState(MessagesState):
    """Custom state with tool preference"""
    tool: str | None = None


def supervisor_node(state: CustomAgentState) -> dict:
    """
    Main supervisor node: decides the next action.
    If the user has selected a tool and it has not been executed, it must be used.
    If the tool has been executed, the result is summarized.
    If no tool is selected, the LLM decides.
    """
    
    preferred_tool = state.get('tool')
    messages = state['messages']
    
    tool_already_called = False
    if preferred_tool and len(messages) > 1:
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                tool_already_called = True
                break
            elif isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get('name') == preferred_tool:
                        tool_already_called = True
                        break
                if tool_already_called:
                    break
    
    if preferred_tool and tool_already_called:
        print(f"✅ Tool '{preferred_tool}' đã được execute, đang tổng hợp kết quả...")
        
        response = supervisor_llm.invoke(messages)
        
        return {"messages": [response], "tool": None}
    
    elif preferred_tool:
        print(f"🔒 User chọn tool: {preferred_tool} (lần đầu)")
        
        tool_info = next((t for t in tools if t.name == preferred_tool), None)
        
        if not tool_info:
            error_msg = AIMessage(
                content=f"❌ Không tìm thấy tool '{preferred_tool}'. Vui lòng chọn tool khác."
            )
            return {"messages": [error_msg], "tool": None}
        
        try:
            model_with_forced_tool = supervisor_llm.bind_tools(
                tools,
                tool_choice={"type": "function", "function": {"name": preferred_tool}}
            )
            
            instruction = f"""Sử dụng tool '{preferred_tool}' để trả lời câu hỏi này.

Tool: {tool_info.name}
Mô tả: {tool_info.description}"""
            
            messages_with_instruction = [
                SystemMessage(content=instruction)
            ] + messages
            
            response = model_with_forced_tool.invoke(messages_with_instruction)
            
            if hasattr(response, 'tool_calls') and response.tool_calls:
                used_tool = response.tool_calls[0]['name']
                print(f"✅ Tool được sử dụng: {used_tool}")
            
            return {"messages": [response]}
            
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            error_msg = AIMessage(
                content=f"❌ Không thể sử dụng tool '{preferred_tool}'.\n\nLý do: {str(e)}\n\n💡 Vui lòng chọn tool khác."
            )
            return {"messages": [error_msg], "tool": None}
    
    else:
        print("🤖 Không có tool preference - LLM tự quyết định")
        response = model_with_tools.invoke(messages)
        return {"messages": [response]}


def should_continue(state: CustomAgentState) -> Literal["continue", "end"]:
    """Determines whether to continue to tools or end."""
    last_message = state['messages'][-1]
    
    # Nếu có tool_calls → execute tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "continue"
    
    # Nếu không có tool_calls → kết thúc
    return "end"


builder = StateGraph(CustomAgentState)

builder.add_node("supervisor", supervisor_node)
builder.add_node("tools", tool_node)

builder.set_entry_point("supervisor")

builder.add_conditional_edges(
    "supervisor",
    should_continue,
    {"continue": "tools", "end": END}
)
builder.add_edge("tools", "supervisor")

supervisor_agent = builder.compile()


# FastAPI
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/tools")
async def get_tools():
    """Endpoint to get the list of tools"""
    tools_info = []
    
    for tool in tools:
        tool_info = {
            "name": tool.name,
            "description": tool.description,
            "args_schema": tool.args_schema.schema() if hasattr(tool, 'args_schema') else None,
        }
        tools_info.append(tool_info)
    
    return tools_info

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)