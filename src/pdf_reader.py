from pypdf import PdfReader


def read_pdf(file_path: str) -> str:
    """
    PDF dosyasından metin çıkar
    
    Args:
        file_path: PDF dosyasının yolu
        
    Returns:
        PDF'den çıkartılan metin
    """
    try:
        reader = PdfReader(file_path)
        
        if len(reader.pages) == 0:
            raise ValueError("PDF dosyasında sayfa yok")
        
        text = ""
        
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Sayfa {page_num + 1} ---\n"
                    text += page_text + "\n"
            except Exception as e:
                print(f"⚠️ Sayfa {page_num + 1} okunurken hata: {str(e)}")
                continue
        
        if not text.strip():
            raise ValueError("PDF'den metin çıkarılamadı")
        
        return text
        
    except Exception as e:
        raise Exception(f"PDF dosyası okunurken hata: {str(e)}")