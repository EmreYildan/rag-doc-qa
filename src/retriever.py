from langchain_community.vectorstores import FAISS


def create_vector_store(chunks, embeddings):
    """
    FAISS vector store oluştur.
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


def keyword_search_chunks(vector_store, query, k=3):
    """
    Basit keyword search.
    FAISS docstore içindeki chunk metinlerinde kelime eşleşmesi arar.
    """
    try:
        query_words = [
            word.lower()
            for word in query.split()
            if len(word.strip()) > 2
        ]

        if not query_words:
            return []

        docs_with_scores = []

        # FAISS içindeki tüm dokümanları al
        all_docs = list(vector_store.docstore._dict.values())

        for doc in all_docs:
            text = doc.page_content.lower()

            match_count = sum(
                1 for word in query_words if word in text
            )

            if match_count > 0:
                if not hasattr(doc, "metadata") or doc.metadata is None:
                    doc.metadata = {}

                doc.metadata["score"] = match_count
                doc.metadata["search_type"] = "Keyword"

                docs_with_scores.append((doc, match_count))

        docs_with_scores.sort(
            key=lambda x: x[1],
            reverse=True
        )

        return [doc for doc, score in docs_with_scores[:k]]

    except Exception as e:
        raise Exception(f"Keyword arama hatası: {str(e)}")


def search_similar_chunks(vector_store, query, k=3, search_type="similarity"):
    """
    Vector store içinde arama yapar.

    search_type:
    - similarity: en benzer doküman parçalarını getirir.
    - mmr: hem alakalı hem birbirinden farklı doküman parçalarını getirir.
    - keyword: klasik anahtar kelime araması yapar.
    """
    try:
        if not query.strip():
            raise ValueError("Sorgu boş olamaz")

        if k < 1:
            raise ValueError("k en az 1 olmalı")

        docs = []

        if search_type == "keyword":
            docs = keyword_search_chunks(
                vector_store,
                query,
                k=k
            )

        elif search_type == "mmr":
            mmr_docs = vector_store.max_marginal_relevance_search(
                query,
                k=k,
                fetch_k=max(k * 3, 10)
            )

            for doc in mmr_docs:
                if not hasattr(doc, "metadata") or doc.metadata is None:
                    doc.metadata = {}

                doc.metadata["score"] = None
                doc.metadata["search_type"] = "MMR"
                docs.append(doc)

        else:
            results = vector_store.similarity_search_with_score(
                query,
                k=k
            )

            for doc, score in results:
                if not hasattr(doc, "metadata") or doc.metadata is None:
                    doc.metadata = {}

                doc.metadata["score"] = float(score)
                doc.metadata["search_type"] = "Similarity"
                docs.append(doc)

        return docs

    except Exception as e:
        raise Exception(f"Arama yapılırken hata: {str(e)}")