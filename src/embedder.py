from langchain_community.embeddings import HuggingFaceEmbeddings


def get_embedding_model():
    """
    HuggingFace embedding modeli yükle
    """
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        return embeddings
    except Exception as e:
        raise Exception(f"Embedding modeli yüklenirken hata: {str(e)}")