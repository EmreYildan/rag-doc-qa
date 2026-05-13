from src.pdf_reader import read_pdf
from src.splitter import split_text
from src.embedder import get_embedding_model
from src.retriever import create_vector_store
from src.retriever import search_similar_chunks


def build_index(pdf_path, chunk_size=500, chunk_overlap=100):
    """
    PDF dosyasını oku, chunk'la, embedding oluştur ve vector store'da sakla
    """
    try:
        # PDF'i oku
        text = read_pdf(pdf_path)
        
        if not text.strip():
            raise ValueError("PDF dosyasından metin çıkarılamadı")
        
        # Metni parçalara böl
        chunks = split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        if not chunks:
            raise ValueError("Metin parçalanırken hata oluştu")
        
        # Embedding modeli yükle
        embeddings = get_embedding_model()
        
        # Vector store oluştur
        vector_store = create_vector_store(chunks, embeddings)
        
        return {
            "vector_store": vector_store,
            "chunk_count": len(chunks),
            "text_length": len(text)
        }
        
    except Exception as e:
        raise Exception(f"Index oluşturulurken hata: {str(e)}")


def ask_question(vector_store, question, k=3, search_type="similarity"):
    """
    Soruya göre ilgili doküman parçalarını getirir.

    search_type:
    - similarity
    - mmr
    """
    try:
        if not question.strip():
            raise ValueError("Soru boş olamaz")

        docs = search_similar_chunks(
            vector_store=vector_store,
            query=question,
            k=k,
            search_type=search_type
        )

        return docs

    except Exception as e:
        raise Exception(f"Soru cevaplanırken hata: {str(e)}")