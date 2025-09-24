# graph.py

from typing import TypedDict, List
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END

# Import các node và router đã được cập nhật
from src.test_agent.node import (
    list_tables,
    generate_query,
    run_query_and_handle_errors,
    should_continue_generating,
    decide_after_run
)

class GraphState(TypedDict):
    messages: List[BaseMessage]
    table_names: List[str]

# Xây dựng StateGraph với State mới
builder = StateGraph(GraphState)

# Thêm các node vào graph
builder.add_node("list_tables", list_tables)
builder.add_node("generate_query", generate_query)
builder.add_node("run_query", run_query_and_handle_errors)

# Thiết lập điểm bắt đầu của graph là node chọn bảng
builder.set_entry_point("list_tables")

# --- Liên kết các node với nhau ---

# 1. Sau khi chọn bảng, chuyển đến bước tạo query
builder.add_edge("list_tables", "generate_query")

# 2. Sau khi tạo query, quyết định xem nên chạy query hay kết thúc
builder.add_conditional_edges(
    "generate_query",
    should_continue_generating,
    {
        "run_query": "run_query",
        END: END
    }
)

# 3. Sau khi chạy query, quyết định xem có cần tạo lại query (nếu lỗi) hay không
builder.add_conditional_edges(
    "run_query",
    decide_after_run,
    {
        # Nếu lỗi, quay lại bước generate_query (không cần chọn lại bảng)
        "generate_query": "generate_query", 
        END: END
    }
)

# Biên dịch graph
agent = builder.compile()

# --- Cách sử dụng ---
# from langchain_core.messages import HumanMessage
#
# question = "Which customer from Germany has the most orders?"
# inputs = {"messages": [HumanMessage(content=question)]}
#
# for output in agent.stream(inputs):
#     for key, value in output.items():
#         print(f"--- Output from node '{key}' ---")
#         print(value)
#         print("\n")