# ... (thêm vào cuối file index_schemas.py hoặc một file mới)

def verify_point_zero():
    """Hàm để kiểm tra và in ra dữ liệu của Point 0."""
    from qdrant_client import QdrantClient

    client = QdrantClient(host="localhost", port=6333)
    COLLECTION_NAME = "db_table_schemas"

    # Lấy lại point có id = 0 từ collection
    # Đặt with_vectors=True để Qdrant trả về cả vector
    retrieved_point = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=[0],
        with_vectors=True 
    )

    if retrieved_point:
        point = retrieved_point[0]
        print("--- Dữ liệu của Point 0 ---")
        print(f"ID: {point.id}")
        print(f"Payload: {point.payload}")
        
        if point.vector:
            print(f"Vector (10 giá trị đầu tiên): {point.vector[:20]}")
            print(f"Tổng độ dài vector: {len(point.vector)}")
        else:
            print("Không tìm thấy vector.")
    else:
        print("Không tìm thấy Point 0.")


if __name__ == "__main__":
    # index_database_schemas() # Bạn có thể comment dòng này đi nếu đã chạy rồi
    verify_point_zero() # Chạy hàm kiểm tra