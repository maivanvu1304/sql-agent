# agent_tool.py (Phiên bản đề xuất)

from langchain_core.tools import tool
from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage

def create_sql_agent_tool(sql_agent_runnable: Runnable):
    """
    Hàm này tạo ra một công cụ (tool) từ một agent đã được compile.
    Công cụ này có thể được gọi bởi một agent khác (supervisor).
    """
    
    @tool("sql_database_tool", return_direct=False)
    def sql_agent_as_tool(question: str) -> str:
        """
        Đây là một công cụ chuyên dụng để trả lời các câu hỏi bằng cách tương tác với cơ sở dữ liệu Pagila SQL.
        Hãy sử dụng công cụ này cho bất kỳ câu hỏi nào liên quan đến phim, diễn viên, khách hàng, doanh thu, cửa hàng.
        Công cụ này sẽ tự động tạo và thực thi các truy vấn SQL để lấy câu trả lời chính xác.
        
        Ví dụ: "Có bao nhiêu bộ phim trong thể loại 'Action'?" hoặc "Liệt kê 5 khách hàng chi tiêu nhiều nhất".
        """
        print(f"--- 📞 Calling SQL Agent with question: '{question}' ---")
        
        # Định dạng đầu vào cho agent của bạn (dựa trên MessagesState)
        input_data = {"messages": [HumanMessage(content=question)]}
        
        # Gọi agent và nhận về trạng thái cuối cùng
        final_state = sql_agent_runnable.invoke(input_data)
        
        # Trích xuất câu trả lời từ tin nhắn cuối cùng trong state
        last_message = final_state["messages"][-1]
        
        print(f"--- ✅ SQL Agent finished. Returning result. ---")
        return f"The result from the database is: {last_message.content}"

    return sql_agent_as_tool