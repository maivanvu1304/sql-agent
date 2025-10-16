

from langchain_core.tools import tool
from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage

def create_sql_agent_tool(sql_agent_runnable: Runnable):
    """
    This function creates a tool from a compiled agent.
    This tool can be called by another agent (supervisor).
    """
    
    @tool("sql_database_tool", return_direct=False)
    def sql_agent_as_tool(question: str) -> str:
        """
        This is a specialized tool for answering questions by interacting with the Pagila SQL database.
        Use this tool for any questions related to movies, actors, customers, revenue, stores.
        This tool will automatically create and execute SQL queries to get the correct answer.
        
        Example: "How many movies are in the 'Action' genre?" or "List the top 5 customers by spending".
        """
        print(f"--- 📞 Calling SQL Agent with question: '{question}' ---")
        
        # Format the input for your agent (based on MessagesState)
        input_data = {"messages": [HumanMessage(content=question)]}
        
        # Call agent and return the final state
        final_state = sql_agent_runnable.invoke(input_data)
        
        # Extract the answer from the last message in the state
        last_message = final_state["messages"][-1]
        
        print(f"--- ✅ SQL Agent finished. Returning result. ---")
        return f"The result from the database is: {last_message.content}"

    return sql_agent_as_tool