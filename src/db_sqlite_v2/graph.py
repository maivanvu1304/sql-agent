from langgraph.graph import END, START, MessagesState, StateGraph
from src.db_sqlite_v2.node import list_tables,  generate_query,  run_query_and_handle_errors, should_continue_generating, get_schema_node, decide_after_run, find_and_get_relevant_schemas


builder = StateGraph(MessagesState)

builder.add_node("list_tables", list_tables)
builder.add_node("find_schemas", find_and_get_relevant_schemas)
builder.add_node("generate_query", generate_query)
builder.add_node("run_query", run_query_and_handle_errors)


builder.set_entry_point("list_tables")

builder.add_edge("list_tables", "find_schemas")
builder.add_edge("find_schemas", "generate_query")

builder.add_edge("generate_query", "run_query")


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
# builder.add_edge("run_query", END)
agent = builder.compile()