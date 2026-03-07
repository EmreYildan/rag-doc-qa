from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100):
    """
    Metni parçalara böl (chunking)
    """
    try:
        if not text.strip():
            raise ValueError("Metin boş olamaz")

        if chunk_size < 1:
            raise ValueError("Chunk size en az 1 olmalı")

        if chunk_overlap < 0:
            raise ValueError("Chunk overlap negatif olamaz")

        if chunk_overlap >= chunk_size:
            raise ValueError("Chunk overlap chunk size'dan küçük olmalı")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

        chunks = splitter.split_text(text)

        if not chunks:
            raise ValueError("Metin parçalanırken hata oluştu")

        return chunks

    except Exception as e:
        raise Exception(f"Metin parçalama hatası: {str(e)}")