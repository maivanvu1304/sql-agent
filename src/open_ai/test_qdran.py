import openai
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv
load_dotenv()
# Khởi tạo client kết nối tới OpenAI và Qdrant
# (Giả sử bạn đã set OPENAI_API_KEY trong môi trường)
openai_client = openai.OpenAI()
qdrant_client = QdrantClient(host="localhost", port=6333)

# Tên collection trong Qdrant
collection_name = "db_schemas"

# --- CHẠY 1 LẦN ĐỂ TẠO COLLECTION ---
qdrant_client.recreate_collection(
    collection_name=collection_name,
    vectors_config=models.VectorParams(
        size=1536,  # Kích thước vector của model text-embedding-3-small
        distance=models.Distance.COSINE
    )
)

# --- CHUẨN BỊ DỮ LIỆU ---
# Giả sử bạn có danh sách mô tả các bảng
table_descriptions = {
    "actor": "Contains information about actors, including their first and last names (first_name, last_name). Use this for questions about specific actors.",
    "film": "Contains all data related to films and movies, including title, description, release year, rental rate, and most importantly, the duration or length of the movie (column: length). Use this for questions about movie attributes.",
    "customer": "Contains personal details of customers, such as their names (first_name, last_name), email, and address details (address_id). Use this for queries related to customer information."
}

# --- TẠO EMBEDDING VÀ TẢI LÊN QDRANT (CHẠY 1 LẦN) ---
points_to_upload = []
for i, (table_name, description) in enumerate(table_descriptions.items()):
    # 1. Dùng OpenAI để tạo embedding
    response = openai_client.embeddings.create(
        input=description,
        model="text-embedding-3-small"
    )
    embedding_vector = response.data[0].embedding
    
    # 2. Chuẩn bị "Point" để tải lên Qdrant
    # Bao gồm vector và payload (dữ liệu đi kèm)
    points_to_upload.append(
        models.PointStruct(
            id=i, 
            vector=embedding_vector,
            payload={"table_name": table_name} # Lưu tên bảng vào payload
        )
    )

# 3. Tải tất cả points lên collection
qdrant_client.upsert(
    collection_name=collection_name,
    points=points_to_upload,
    wait=True
)

print("Đã nạp thành công schema embeddings vào Qdrant!")
def find_relevant_schemas(user_query: str, top_k: int = 3, score_threshold: float = 0.80):
    """
    Tìm kiếm các schema bảng liên quan nhất, chỉ lấy những kết quả
    có điểm tương đồng cao hơn ngưỡng cho phép.
    """
    # 1. Tạo embedding cho câu hỏi
    response = openai_client.embeddings.create(
        input=user_query,
        model="text-embedding-3-small"
    )
    query_vector = response.data[0].embedding

    # 2. Dùng Qdrant để tìm kiếm
    search_results = qdrant_client.search(
        collection_name="db_schemas",
        query_vector=query_vector,
        limit=top_k
    )

    # 3. Lọc kết quả dựa trên ngưỡng điểm
    relevant_tables = []
    print("--- KẾT QUẢ TÌM KIẾM CHI TIẾT ---")
    for result in search_results:
        # In ra để debug và chọn ngưỡng phù hợp
        print(f"Bảng: {result.payload['table_name']}, Điểm: {result.score:.4f}")
        if result.score >= score_threshold:
            relevant_tables.append(result.payload["table_name"])
            
    print("---------------------------------")
    return relevant_tables

# --- VÍ DỤ SỬ DỤNG ---
my_question = "Which movies are the longest?"
# Bạn có thể thử nghiệm với các ngưỡng khác nhau, ví dụ 0.75, 0.8, 0.85
tables = find_relevant_schemas(my_question, score_threshold=0.4) 

print(f"\nCâu hỏi: '{my_question}'")
print(f"Các bảng liên quan nhất (sau khi lọc): {tables}")