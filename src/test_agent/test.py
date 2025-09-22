from typing import Literal
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from dotenv import load_dotenv
load_dotenv()


db = SQLDatabase.from_uri("sqlite:///src/database/Chinook.db")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")
run_query_tool = next(tool for tool in tools if tool.name == "sql_db_query")


get_schema_node = ToolNode([get_schema_tool], name="get_schema")
run_query_node = ToolNode([run_query_tool], name="run_query")


def list_tables(state: MessagesState):
    """
    Predetermined tool call to list all tables and add the result to the state.
    """
    tool_call = {
        "name": "sql_db_list_tables",
        "args": {},
        "id": "predetermined_list_tables",
    }

    result = list_tables_tool.invoke(tool_call)
    response = AIMessage(content=f"Available tables: {result}")
    return {"messages": [response]}

 
def call_get_schema(state: MessagesState):
    """
    Forces the LLM to call the schema tool based on the conversation history.
    """
    llm_with_tools = llm.bind_tools([get_schema_tool], tool_choice=get_schema_tool.name)
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}



# generate_query_system_prompt = """
# You are an agent designed to interact with a SQL database by generating queries.
# Your single task is to construct a syntactically correct {dialect} query to answer the user's question.

# The database schema and available tables have been provided in the chat history. Refer to this information to create the query.

# ## Query Rules:
# - Unless the user specifies a number of examples, always limit your query to at most {top_k} results using the appropriate clause for {dialect}.
# - Never query for all columns from a table (`SELECT *`). Only select the relevant columns given the question.
# - You can order the results by a relevant column to return the most interesting examples.
# - DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.). Your task is solely to retrieve information.

# Based on the conversation, call the `sql_db_query` tool with the generated query.
# """.format(
#     dialect=db.dialect,
#     top_k=5,
# )
generate_query_system_prompt = """
You are an agent designed to interact with a SQL database by generating queries.
Your single task is to construct a syntactically correct {dialect} query to answer the user's question.

The database schema and available tables have been provided in the chat history. Refer to this information to create the query.

## Query Rules:
- Unless the user specifies a number of examples, always limit your query to at most {top_k} results using the appropriate clause for {dialect}.
- Never query for all columns from a table (`SELECT *`). Only select the relevant columns given the question.
- **IMPORTANT**: When filtering on text fields (like names, titles, etc.), always use the `LOWER()` function on both the column and the value to ensure case-insensitive matching. For example: `WHERE LOWER(ColumnName) = LOWER('search value')`.
- You can order the results by a relevant column to return the most interesting examples.
- DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.). Your task is solely to retrieve information.

Based on the conversation, call the `sql_db_query` tool with the generated query.
""".format(
    dialect=db.dialect,
    top_k=5,
)

def generate_query(state: MessagesState):
    """
    Generates a SQL query based on the full conversation history.
    """
    system_message = SystemMessage(content=generate_query_system_prompt)
    llm_with_tools = llm.bind_tools([run_query_tool])
    response = llm_with_tools.invoke([system_message] + state["messages"])
    return {"messages": [response]}



check_query_system_prompt = """
You are a SQL expert with a strong attention to detail.
Double-check the following {dialect} query for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins
- Not using any CREATE, DROP, INSERT, UPDATE, or DELETE statements
- Using CAST or CONVERT methods to bring date strings into the correct data type

If the query has mistakes, rewrite it. If it is correct, use the original query.
Finally, you MUST call the `sql_db_query` tool with the corrected (or original) query.
""".format(dialect=db.dialect)



def check_query(state: MessagesState):
    """
    Takes the query from the previous step, asks the LLM to validate/correct it,
    and then replaces the original tool call with the corrected one.
    """

    original_ai_message = state["messages"][-1]
    original_tool_call = original_ai_message.tool_calls[0]
    query_to_check = original_tool_call["args"]["query"]


    check_request_message = HumanMessage(content=query_to_check)
    system_message = SystemMessage(content=check_query_system_prompt)

    llm_with_tools = llm.bind_tools([run_query_tool], tool_choice=run_query_tool.name)
    

    checked_response = llm_with_tools.invoke([system_message, check_request_message])

    original_ai_message.tool_calls = checked_response.tool_calls

    return {"messages": [original_ai_message]}


def should_continue(state: MessagesState) -> Literal[END, "check_query"]:
    """
    Router: decides whether to proceed to checking the query or end the flow.
    """
    last_message = state["messages"][-1]
    return "check_query" if last_message.tool_calls else END



builder = StateGraph(MessagesState)
builder.add_node("list_tables", list_tables)
builder.add_node("call_get_schema", call_get_schema)
builder.add_node("get_schema", get_schema_node)
builder.add_node("generate_query", generate_query)
builder.add_node("check_query", check_query)
builder.add_node("run_query", run_query_node)

builder.set_entry_point("list_tables")
builder.add_edge("list_tables", "call_get_schema")
builder.add_edge("call_get_schema", "get_schema")
builder.add_edge("get_schema", "generate_query")
builder.add_conditional_edges(
    "generate_query",
    should_continue,
    {"check_query": "check_query", END: END}
)
builder.add_edge("check_query", "run_query")
builder.add_edge("run_query", "generate_query")

agent = builder.compile()








