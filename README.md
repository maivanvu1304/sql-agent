# SQL Database Agent với LangGraph

Dự án này triển khai một AI agent thông minh có khả năng tương tác với cơ sở dữ liệu SQLite thông qua ngôn ngữ tự nhiên. Agent sử dụng LangGraph để tạo ra một workflow tự động, có thể hiểu câu hỏi của người dùng, tạo truy vấn SQL tương ứng, kiểm tra và sửa lỗi tự động, sau đó thực thi truy vấn và trả về kết quả.

## ✨ Tính năng chính

- **Truy vấn bằng ngôn ngữ tự nhiên**: Đặt câu hỏi bằng tiếng Việt hoặc tiếng Anh, agent sẽ tự động chuyển đổi thành SQL
- **Tự động kiểm tra và sửa lỗi**: Agent có khả năng phát hiện và sửa chữa các lỗi SQL phổ biến
- **Workflow thông minh**: Sử dụng LangGraph để tạo ra quy trình xử lý có cấu trúc
- **Hỗ trợ database schema**: Tự động lấy thông tin về bảng và cấu trúc database
- **Xử lý lỗi mạnh mẽ**: Tự động thử lại khi gặp lỗi SQL

## 🏗️ Kiến trúc hệ thống

Dự án sử dụng kiến trúc graph-based với các node sau:

1. **list_tables**: Liệt kê tất cả bảng trong database
2. **call_get_schema**: Yêu cầu thông tin schema của bảng
3. **get_schema**: Lấy chi tiết cấu trúc bảng
4. **generate_query**: Tạo truy vấn SQL từ yêu cầu người dùng
5. **check_query**: Kiểm tra và sửa lỗi SQL
6. **run_query**: Thực thi truy vấn và xử lý lỗi

## 📁 Cấu trúc thư mục

```
project_db/
├── src/
│   ├── database/
│   │   └── Chinook.db          # Database SQLite mẫu
│   ├── db_sqlite/
│   │   ├── __init__.py
│   │   ├── graph.py            # Định nghĩa workflow chính
│   │   ├── node.py             # Các node xử lý logic
│   │   └── prompts.py          # System prompts cho LLM
│   └── test_agent/
│       ├── test.py             # Test cases cũ
│       └── test_v2.py          # Test cases mới
├── main.py                     # Entry point chính
├── pyproject.toml              # Cấu hình dependencies
├── langgraph.json              # Cấu hình LangGraph
├── uv.lock                     # Lock file cho dependencies
└── README.md                   # Tài liệu này
```

## 🚀 Cài đặt và chạy

### Yêu cầu hệ thống
- Python >= 3.13
- OpenAI API key

### Cài đặt dependencies

```bash
# Sử dụng uv (khuyến nghị)
uv install

# Hoặc sử dụng pip
pip install -e .
```

### Cấu hình môi trường

Tạo file `.env` trong thư mục gốc với nội dung:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Chạy ứng dụng

```bash
# Chạy với LangGraph CLI
langgraph dev

# Hoặc chạy trực tiếp
python main.py
```

## 📖 Cách sử dụng

### Ví dụ truy vấn cơ bản

```python
from src.db_sqlite.graph import agent

# Gửi câu hỏi bằng ngôn ngữ tự nhiên
question = "Cho tôi xem 5 khách hàng có doanh thu cao nhất"

# Chạy agent
result = agent.invoke({
    "messages": [{"role": "user", "content": question}]
})

print(result)
```

### Các loại câu hỏi được hỗ trợ

- **Truy vấn thông tin**: "Có bao nhiêu khách hàng trong database?"
- **Lọc dữ liệu**: "Tìm tất cả album của nghệ sĩ 'AC/DC'"
- **Thống kê**: "Doanh thu trung bình theo tháng trong năm 2023"
- **Join bảng**: "Danh sách bài hát và tên album tương ứng"

## 🛠️ Tùy chỉnh

### Thay đổi database

Để sử dụng database khác, chỉnh sửa trong `src/db_sqlite/node.py`:

```python
db = SQLDatabase.from_uri("sqlite:///path/to/your/database.db")
```

### Tùy chỉnh prompts

Chỉnh sửa các system prompts trong `src/db_sqlite/prompts.py` để phù hợp với domain cụ thể.

### Thay đổi LLM model

Trong `src/db_sqlite/node.py`:

```python
llm = ChatOpenAI(model="gpt-4", temperature=0)  # Thay đổi model
```

## 🧪 Testing

Chạy test cases:

```bash
python src/test_agent/test.py
```

Hoặc test với phiên bản mới:

```bash
python src/test_agent/test_v2.py
```

## 📊 Database mẫu

Dự án sử dụng database Chinook.db - một database mẫu mô phỏng cửa hàng nhạc số với các bảng:

- **Customer**: Thông tin khách hàng
- **Invoice**: Hóa đơn bán hàng
- **Track**: Danh sách bài hát
- **Album**: Thông tin album
- **Artist**: Nghệ sĩ
- **Genre**: Thể loại nhạc
- **Playlist**: Danh sách phát

## 🔧 Troubleshooting

### Lỗi thường gặp

1. **OpenAI API key không hợp lệ**
   ```bash
   Error: Authentication failed
   ```
   Kiểm tra lại OPENAI_API_KEY trong file .env

2. **Database không tìm thấy**
   ```bash
   Error: No such file or directory
   ```
   Đảm bảo file Chinook.db tồn tại trong src/database/

3. **Dependencies bị thiếu**
   ```bash
   ModuleNotFoundError: No module named 'langchain'
   ```
   Chạy lại `uv install` hoặc `pip install -e .`

## 🤝 Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng:

1. Fork project
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

## 📝 License

Dự án này được phân phối dưới MIT License. Xem file `LICENSE` để biết thêm chi tiết.

## 📞 Liên hệ

Nếu có câu hỏi hoặc cần hỗ trợ, vui lòng tạo issue trong repository này.

---

**Lưu ý**: Đây là dự án demo/học tập. Khi triển khai production, cần thêm các biện pháp bảo mật như SQL injection protection, rate limiting, và authentication.
