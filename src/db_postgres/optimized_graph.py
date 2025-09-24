
from langgraph.graph import MessagesState, StateGraph, END

# Import các node và router đã được cập nhật từ node.py
from src.db_postgres.optimized_node import (
    generate_query,
    run_query_and_handle_errors,
    should_continue_generating,
    decide_after_run
)

builder = StateGraph(MessagesState)

builder.add_node("generate_query", generate_query)
builder.add_node("run_query", run_query_and_handle_errors)

builder.set_entry_point("generate_query")

builder.add_conditional_edges(
    "generate_query",
    should_continue_generating,
    {
        "run_query": "run_query",
        END: END
    }
)

builder.add_conditional_edges(
    "run_query",
    decide_after_run,
    {
        "generate_query": "generate_query",
        END: END
    }
)

agent = builder.compile()

