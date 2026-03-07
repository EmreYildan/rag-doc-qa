"""
LLM (Large Language Model) işlemleri
Aşama 1: Mock LLM (test için)
Aşama 2: OpenAI API ve AWS Bedrock
"""


def generate_answer_mock(question: str, retrieved_docs: list) -> str:
    """
    Mock LLM - test amaçlı basit cevap oluşturma
    
    Args:
        question: Kullanıcı sorusu
        retrieved_docs: İlgili doküman parçaları
        
    Returns:
        Oluşturulan cevap
    """
    try:
        if not retrieved_docs:
            return f"Maalesef, '{question}' sorusuna cevap bulunamamıştır."
        
        # Çoklu kaynakları, skoru da göstererek birleştir
        combined_parts = []
        for doc in retrieved_docs:
            score = doc.metadata.get("score") if hasattr(doc, "metadata") else None
            if score is not None:
                combined_parts.append(f"[skor: {score:.4f}] {doc.page_content}")
            else:
                combined_parts.append(doc.page_content)
        combined_context = "\n\n".join(combined_parts)
        
        # Mock answer generator
        answer = f"""
Sorunuz: {question}

Bulunan Bilgi:
{combined_context[:500]}...

Not: Bu bir test cevabıdır. Aşama 2'de OpenAI API veya AWS Bedrock ile gerçek AI cevaplar alacaksınız.
"""
        
        return answer.strip()
        
    except Exception as e:
        raise Exception(f"Cevap oluşturulurken hata: {str(e)}")


def generate_answer_openai(question: str, retrieved_docs: list, api_key: str = None) -> str:
    """
    OpenAI API ile gerçek cevap oluşturma
    Aşama 2: AWS entegrasyonunda kullanılacak
    
    Args:
        question: Kullanıcı sorusu
        retrieved_docs: İlgili doküman parçaları
        api_key: OpenAI API anahtarı (environment variable'dan alınabilir)
        
    Returns:
        AI tarafından oluşturulan cevap
    """
    try:
        import os
        from openai import OpenAI
        
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable'ı ayarlanmamıştır")
        
        client = OpenAI(api_key=api_key)
        
        # Konteks oluştur
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        
        # Prompt oluştur
        system_prompt = """Sen bir yardımcı asistansın. Kullanıcının sorusunu, verilen doküman parçalarında bulunan bilgiye dayanarak 
cevaplamalısın. Eğer bilgi yeterli değilse, bunu açıkça söylemelisin."""
        
        user_message = f"""Soru: {question}

Doküman İçeriği:
{context}

Yukarıdaki bilgilere dayanarak soruyu Türkçe olarak cevapla."""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except ImportError:
        raise Exception("OpenAI paketi kurulu değil. 'pip install openai' çalıştırın.")
    except Exception as e:
        raise Exception(f"OpenAI API çağrısında hata: {str(e)}")
