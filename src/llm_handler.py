"""
LLM (Large Language Model) işlemleri
Aşama 1: Mock LLM (test için)
Aşama 2: OpenAI API ve AWS Bedrock
"""


def generate_answer_mock(question: str, retrieved_docs: list) -> str:
    """
    Mock cevap üretici.
    Gerçek LLM kullanmadan, en alakalı ilk doküman parçasına göre
    düzenli bir test cevabı oluşturur.
    """
    try:
        if not retrieved_docs:
            return f"Bu soruya uygun bilgi bulunamadı: '{question}'"

        top_doc = retrieved_docs[0].page_content.strip()
        top_doc = " ".join(top_doc.split())

        score = None
        if hasattr(retrieved_docs[0], "metadata") and retrieved_docs[0].metadata:
            score = retrieved_docs[0].metadata.get("score")

        if len(top_doc) > 400:
            top_doc = top_doc[:400] + "..."

        answer = "Dokümanda soruya en yakın bulunan bilgi:\n\n"
        answer += top_doc

        if score is not None:
            answer += f"\n\nBenzerlik skoru: {score:.4f}"

        answer += "\n\nNot: Bu hâlâ test amaçlı mock cevaptır. Gerçek AI cevabı sonraki aşamada eklenecektir."

        return answer

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


def generate_answer_bedrock(question: str, retrieved_docs: list) -> str:
    """
    AWS Bedrock Claude ile cevap üretir.
    """

    try:
        import os
        import boto3
        from dotenv import load_dotenv

        load_dotenv()

        if not retrieved_docs:
            return "Bu soruya uygun kaynak bulunamadı."

        # AWS ayarları
        region = os.getenv("AWS_REGION", "eu-west-1")

        model_id = os.getenv(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-3-haiku-20240307-v1:0"
        )

        max_tokens = int(
            os.getenv("BEDROCK_MAX_TOKENS", "600")
        )

        temperature = float(
            os.getenv("BEDROCK_TEMPERATURE", "0.1")
        )

        # Context oluştur
        context_parts = []

        for i, doc in enumerate(retrieved_docs[:8], start=1):

            text = " ".join(doc.page_content.split())

            context_parts.append(
                f"Kaynak {i}:\n{text[:3000]}"
            )

        context = "\n\n".join(context_parts)

        # Liste / başlık sorusu algılama
        question_lower = question.lower()

        list_question_keywords = [
            "nelerdir",
            "listele",
            "maddeler",
            "kriterler",
            "isterler",
            "gereksinimler",
            "başlıklar",
            "hangi maddeler",
            "hangi kriterler"
        ]

        is_list_question = any(
            keyword in question_lower
            for keyword in list_question_keywords
        )

        extra_instruction = ""

        if is_list_question:
            extra_instruction = """
ÖNEMLİ:
- Eğer dokümanda maddeler veya liste varsa eksiksiz aktar.
- Özetleme yapma.
- Madde atlama.
- Numara sırasını koru.
- Listeyi birebir çıkarmaya çalış.
- Yalnızca dokümanda bulunan bilgileri kullan.
"""

        # Prompt
        prompt = f"""
        Sen bir akademik doküman analiz sistemisin.

        Kurallar:
        - Cevabı Türkçe ver.
        - Cevabı iki ana bölüm halinde ver:
        1. Dokümandaki Bilgi
        2. Ek Açıklama
        - "Dokümandaki Bilgi" bölümünde yalnızca verilen doküman içeriğine dayan.
        - Dokümanda olmayan bilgileri bu bölümde yazma.
        - Eğer dokümanda bilgi yoksa açıkça "Bu bilgi dokümanda bulunamadı." de.
        - "Ek Açıklama" bölümünde konuyu daha anlaşılır hale getiren kısa açıklamalar yapabilirsin.
        - Ek açıklamada verdiğin bilgilerin dokümanda doğrudan geçmeyebileceğini belli et.
        - Teknik başlıkları ve maddeleri koru.
        - Eğer soru liste/madde sorusuysa dokümandaki maddeleri eksiksiz aktar.
        - Gereksiz uzun yorum yapma.

        {extra_instruction}

        Doküman İçeriği:
        {context}

        Soru:
        {question}
        """

        # Bedrock client
        client = boto3.client(
            "bedrock-runtime",
            region_name=region
        )

        # Claude çağrısı
        response = client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature
            }
        )

        answer = response["output"]["message"]["content"][0]["text"]

        return answer

    except Exception as e:
        raise Exception(f"Bedrock cevap hatası: {str(e)}")