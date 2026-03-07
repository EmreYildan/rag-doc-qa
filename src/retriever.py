from langchain_community.vectorstores import FAISS


def create_vector_store(chunks, embeddings):
    """
    FAISS vector store oluştur
    """
    try:
        if not chunks:
            raise ValueError("Chunk listesi boş olamaz")

        vector_store = FAISS.from_texts(
            chunks,
            embeddings
        )

        return vector_store

    except Exception as e:
        raise Exception(f"Vector store oluşturulurken hata: {str(e)}")


def search_similar_chunks(vector_store, query, k=3):
    """
    Vector store'da benzer chunklari ara ve skor bilgisini ekle
    """
    try:
        if not query.strip():
            raise ValueError("Sorgu boş olamaz")

        if k < 1:
            raise ValueError("k en az 1 olmalı")

        results = vector_store.similarity_search_with_score(query, k=k)

        docs = []
        for doc, score in results:
            if not hasattr(doc, "metadata") or doc.metadata is None:
                doc.metadata = {}
            doc.metadata["score"] = score
            docs.append(doc)

        return docs

    except Exception as e:
        raise Exception(f"Arama yapılırken hata: {str(e)}")