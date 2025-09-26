# supervisor.py

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import ToolExecutor
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
import operator

# 1. Import agent SQL và hàm tạo công cụ
from src.db_sqlite.graph import agent as sql_agent # Đổi tên để tránh nhầm lẫn
from agent_tool import create_sql_agent_tool

# 2. Tạo công cụ từ agent SQL
sql_agent_tool = create_sql_agent_tool(sql_agent)

# 3. (Tùy chọn) Tạo thêm các công cụ khác để Supervisor lựa chọn
# Ví dụ, một công cụ tìm kiếm trên web
from langchain_community.tools.tavily_search import TavilySearchResults
# Cần cài đặt: pip install tavily-python
# Cần set TAVILY_API_KEY trong file .env
web_search_tool = TavilySearchResults(max_results=2, name="web_search")

# 4. Định nghĩa các thành phần cho Supervisor Agent

# Tập hợp tất cả các công cụ mà Supervisor có thể gọi
tools = [sql_agent_tool, web_search_tool]
tool_executor = ToolExecutor(tools)

# Mô hình ngôn ngữ cho Supervisor
supervisor_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
model_with_tools = supervisor_llm.bind_tools(tools)

# Định nghĩa trạng thái (State) cho Supervisor
class AgentState(TypedDict):
    messages: Annotated[Sequence[HumanMessage], operator.add]

# Định nghĩa các node trong đồ thị của Supervisor
def supervisor_node(state):
    """Node chính của Supervisor: quyết định hành động tiếp theo."""
    response = model_with_tools.invoke(state['messages'])
    return {"messages": [response]}

def tool_node(state):
    """Node thực thi công cụ và trả về kết quả."""
    last_message = state['messages'][-1]
    tool_call = last_message.tool_calls[0]
    
    # In ra công cụ nào đang được gọi
    print(f"--- 🤖 Supervisor is calling tool: {tool_call['name']} ---")
    
    result = tool_executor.invoke(tool_call)
    return {"messages": [HumanMessage(content=str(result), name=tool_call['name'])]}

# Hàm quyết định luồng đi tiếp theo
def should_continue(state):
    if state['messages'][-1].tool_calls:
        return "continue"
    return "end"

# 5. Xây dựng đồ thị (Graph) cho Supervisor
builder = StateGraph(AgentState)

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

# 6. Chạy thử Supervisor
if __name__ == "__main__":
    # Câu hỏi này nên được chuyển đến sql_agent_tool
    question1 = "Liệt kê 5 diễn viên có họ là 'GUINESS'."
    result1 = supervisor_agent.invoke({"messages": [HumanMessage(content=question1)]})
    print("\n--- FINAL ANSWER 1 ---")
    print(result1['messages'][-1].content)

    print("\n" + "="*50 + "\n")

    # Câu hỏi này nên được chuyển đến web_search_tool
    question2 = "What is the latest news about LangGraph?"
    result2 = supervisor_agent.invoke({"messages": [HumanMessage(content=question2)]})
    print("\n--- FINAL ANSWER 2 ---")
    print(result2['messages'][-1].content)