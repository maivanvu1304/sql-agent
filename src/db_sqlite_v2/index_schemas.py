# file: index_schemas.py
import openai
from qdrant_client import QdrantClient, models
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv


load_dotenv()
openai_client = openai.OpenAI()
qdrant_client = QdrantClient(host="localhost", port=6333)
db = SQLDatabase.from_uri("postgresql://postgres:postgres@localhost:5432/pagila")

COLLECTION_NAME = "db_table_schemas"
EMBEDDING_MODEL = "text-embedding-3-small"
VECTOR_SIZE = 1536 


def get_detailed_table_description(table_name: str) -> str:
    """
    Lấy DDL (schema) của bảng và tạo một mô tả chi tiết.
    """
    ddl = db.get_table_info([table_name])
    
    prompt = (
        f"The user will ask questions about the '{table_name}' table. "
        f"This table has the following schema:\n\n{ddl}\n\n"
        f"This schema describes the columns and data types for the '{table_name}' table. "
        f"It is useful for answering questions related to its structure, columns, and content."
    )
    return prompt


def index_database_schemas():
    """
    Index the database schemas into Qdrant.
    """
    print("Bắt đầu quá trình nạp dữ liệu schema...")

    print(f"Xóa và tạo lại collection '{COLLECTION_NAME}'...")
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE
        )
    )

    table_names = db.get_usable_table_names()
    print(f"Tìm thấy {len(table_names)} bảng. Đang xử lý...")

    points_to_upload = []
    for i, table_name in enumerate(table_names):
        description = get_detailed_table_description(table_name)

        response = openai_client.embeddings.create(
            input=description,
            model=EMBEDDING_MODEL
        )
        embedding_vector = response.data[0].embedding

        points_to_upload.append(
            models.PointStruct(
                id=i,
                vector=embedding_vector,
                payload={"table_name": table_name, "description": description}
            )
        )
        print(f"  - Đã xử lý bảng: {table_name}")

    if points_to_upload:
        print("\nĐang tải dữ liệu lên Qdrant...")
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points_to_upload,
            wait=True
        )
        print("✅ Hoàn tất! Dữ liệu schema đã được nạp thành công vào Qdrant.")
    else:
        print("⚠️ Không tìm thấy bảng nào để xử lý.")

if __name__ == "__main__":
    index_database_schemas()