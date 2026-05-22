import streamlit as st
import tempfile
import os
import time
import re
import pandas as pd
import matplotlib.pyplot as plt

from src.s3_handler import upload_file_to_s3
from src.rag_pipeline import build_index, ask_question
from src.llm_handler import generate_answer_mock

def calculate_confidence(retrieved_docs, search_type):
    """
    Basit güven skoru hesaplama.
    """

    if not retrieved_docs:
        return 0

    base_score = 50

    # Arama yöntemine göre
    if search_type == "keyword":
        base_score += 20

    elif search_type == "similarity":
        base_score += 15

    elif search_type == "mmr":
        base_score += 18

    elif search_type == "hybrid":
        base_score += 30

    # Kaynak sayısına göre
    source_bonus = min(len(retrieved_docs) * 3, 15)

    confidence = min(base_score + source_bonus, 100)

    return confidence


def extract_source_pages(retrieved_docs):
    pages = []

    for doc in retrieved_docs:
        text = doc.page_content
        page_match = re.search(r"Sayfa\s+(\d+)", text)

        if page_match:
            page_number = page_match.group(1)
            if page_number not in pages:
                pages.append(page_number)

    return pages


st.set_page_config(
    page_title="RAG Sistem",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📄 RAG Doküman Soru-Cevap Sistemi")
st.write("Doküman yükleyin ve yapay zekanın anlamasıyla sorular sorun.")

# Session state
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "document_name" not in st.session_state:
    st.session_state.document_name = None
if "chunk_count" not in st.session_state:
    st.session_state.chunk_count = 0
if "experiment_logs" not in st.session_state:
    st.session_state.experiment_logs = []

# Sidebar
with st.sidebar:
    st.header("⚙️ Ayarlar")

    answer_mode = st.selectbox(
        "Cevap Modu",
        ["Hızlı", "Dengeli", "Detaylı"]
    )

    if answer_mode == "Hızlı":
        chunk_size = 300
        chunk_overlap = 100
        top_k = 3
        search_type = "similarity"

    elif answer_mode == "Dengeli":
        chunk_size = 500
        chunk_overlap = 150
        top_k = 5
        search_type = "mmr"

    else:
        chunk_size = 800
        chunk_overlap = 200
        top_k = 8
        search_type = "mmr"

    manual_search_type = st.selectbox(
        "Deneysel Arama Yöntemi",
        ["Otomatik", "keyword", "similarity", "mmr", "hybrid"]    )

    search_explanations = {
        "Otomatik": "Seçilen cevap moduna göre sistem en uygun arama yöntemini otomatik belirler.",
        "keyword": "Anahtar kelime araması yapar. Soru içindeki kelimeler dokümanda birebir aranır.",
        "similarity": "Semantik benzerlik araması yapar. Sorunun anlamına en yakın doküman parçalarını getirir.",
        "mmr": "MMR araması yapar. Hem alakalı hem de birbirinden farklı parçaları getirir.",
        "hybrid" : "Keyword, similarity ve MMR sonuçlarını birleştirir. En kapsamlı ve yüksek doğruluk hedefleyen arama yöntemidir."
    }

    if manual_search_type != "Otomatik":
        search_type = manual_search_type

    st.caption(f"ℹ️ {search_explanations[manual_search_type]}")

    st.info(
        f"Cevap Modu: {answer_mode}\n"
        f"Chunk Size: {chunk_size}\n"
        f"Chunk Overlap: {chunk_overlap}\n"
        f"Top-k: {top_k}\n"
        f"Arama: {search_type}\n\n"
        f"Not: Chunk ayarları değişirse PDF'yi tekrar işlemeniz gerekir."
    )

    st.header("🔑 LLM Seçimi")
    llm_option = st.radio(
        "LLM Türü",
        ["Mock (Test)", "OpenAI API", "AWS Bedrock"]
    )

    if llm_option == "OpenAI API":
        api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    else:
        api_key = None

# Upload section
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📥 Adım 1: Doküman Yükle")
    uploaded_file = st.file_uploader("PDF dosyası seçin", type=["pdf"])

with col2:
    st.subheader("📊 Durum")
    if st.session_state.vector_store is not None:
        st.success(f"✅ Yüklü: {st.session_state.document_name}")
        st.info(f"Chunk Sayısı: {st.session_state.chunk_count}")
    else:
        st.warning("❌ Henüz doküman yüklenmedi")

# Process document
if uploaded_file is not None:
    st.subheader("📋 Adım 2: Dokümanı İşle")

    if st.button("Dokümanı İşle"):
        try:
            with st.spinner("⏳ Doküman işleniyor..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name

                s3_result = upload_file_to_s3(tmp_path, uploaded_file.name)

                if s3_result["success"]:
                    st.info(f"☁️ PDF AWS S3'e yüklendi: {s3_result['s3_uri']}")
                else:
                    st.warning(f"⚠️ S3 yükleme başarısız: {s3_result['error']}")

                result = build_index(
                    tmp_path,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )

                st.session_state.vector_store = result["vector_store"]
                st.session_state.document_name = uploaded_file.name
                st.session_state.chunk_count = result["chunk_count"]

                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

                st.success(f"✅ Doküman başarıyla işlendi! {result['chunk_count']} chunk oluşturuldu.")
                st.balloons()

        except Exception as e:
            st.error(f"❌ Hata oluştu: {str(e)}")

# Question answering
st.subheader("❓ Adım 3: Soru Sor ve Cevap Al")

question = st.text_input(
    "Sorunuzu yazın",
    placeholder="Örnek: Rapor isterleri nelerdir?"
)

if st.button("Cevabını Al 🔍"):
    if st.session_state.vector_store is None:
        st.warning("⚠️ Önce PDF yükleyip işlemeniz gerekli!")

    elif not question.strip():
        st.warning("⚠️ Lütfen bir soru yazın!")

    else:
        try:
            with st.spinner("🤔 İlgili doküman parçaları aranıyor..."):
                question_lower = question.lower()

                heading_keywords = [
                    "ister", "isterleri", "gereksinim", "gereksinimler",
                    "kriter", "kriterleri", "madde", "maddeler",
                    "listele", "nelerdir", "bölüm", "başlık"
                ]

                is_heading_or_list_question = any(
                    keyword in question_lower for keyword in heading_keywords
                )

                effective_top_k = top_k
                effective_search_type = search_type

                if is_heading_or_list_question:
                    effective_top_k = max(top_k, 8)
                    effective_search_type = "keyword"

                retrieved_docs = ask_question(
                    st.session_state.vector_store,
                    question,
                    k=effective_top_k,
                    search_type=effective_search_type
                )

            if not retrieved_docs:
                st.info("Hiç sonuç bulunamadı.")

            else:
                answer = None
                start_time = time.time()

                with st.spinner("✍️ Cevap oluşturuluyor..."):
                    if llm_option == "Mock (Test)":
                        answer = generate_answer_mock(question, retrieved_docs)

                    elif llm_option == "OpenAI API":
                        from src.llm_handler import generate_answer_openai

                        if not api_key:
                            st.error("❌ OpenAI API Key gerekli!")
                            answer = None
                        else:
                            answer = generate_answer_openai(question, retrieved_docs, api_key)

                    elif llm_option == "AWS Bedrock":
                        from src.llm_handler import generate_answer_bedrock
                        answer = generate_answer_bedrock(question, retrieved_docs)

                elapsed_time = time.time() - start_time

                if answer:
                    source_pages = extract_source_pages(retrieved_docs)
                    confidence_score = calculate_confidence(
                    retrieved_docs,
                    effective_search_type
                )

                    if source_pages:
                        source_text = ", ".join([f"Sayfa {page}" for page in source_pages])
                        answer_with_sources = (
                            f"{answer}\n\n"
                            f"📌 Kaynak: {source_text}\n"
                            f"📊 Güven Skoru: %{confidence_score}"
                        )
                    else:
                        answer_with_sources = answer

                    st.subheader("💡 Cevap")
                    st.write(answer_with_sources)

                    st.info(
                        f"⏱️ Cevap süresi: {elapsed_time:.2f} saniye | "
                        f"Model: {llm_option} | "
                        f"Chunk size: {chunk_size} | "
                        f"Top-k: {effective_top_k} | "
                        f"Arama: {effective_search_type}"
                    )

                    st.session_state.experiment_logs.append({
                        "Doküman": st.session_state.document_name,
                        "Soru": question,
                        "Model": llm_option,
                        "Cevap Modu": answer_mode,
                        "Chunk Size": chunk_size,
                        "Chunk Overlap": chunk_overlap,
                        "Top-k": effective_top_k,
                        "Arama Yöntemi": effective_search_type,
                        "Chunk Sayısı": st.session_state.chunk_count,
                        "Cevap Süresi (sn)": round(elapsed_time, 2),
                        "Kaynak Sayısı": len(retrieved_docs),
                        "Doğruluk": "Değerlendirilmedi"
                    })

                    with st.expander("📚 Kaynaklar", expanded=False):
                        st.subheader("Kaynak Gösterimi")

                        shown_pages = set()

                        for i, doc in enumerate(retrieved_docs, start=1):
                            text = doc.page_content

                            page_match = re.search(r"Sayfa\s+(\d+)", text)
                            page_number = page_match.group(1) if page_match else "Bilinmiyor"

                            if page_number in shown_pages:
                                continue

                            shown_pages.add(page_number)

                            score = None
                            search_method = "Bilinmiyor"

                            if hasattr(doc, "metadata") and doc.metadata:
                                score = doc.metadata.get("score")
                                search_method = doc.metadata.get("search_type", "Bilinmiyor")

                            citation_title = f"📄 Kaynak {i} | Sayfa {page_number}"

                            if score is not None:
                                citation_title += f" | Skor: {score:.4f}"

                            with st.expander(citation_title):
                                st.markdown(
                                    f"""
### 📚 Kaynak Bilgisi

- Sayfa: {page_number}
- Arama Yöntemi: {search_method}
- Chunk Uzunluğu: {len(text)} karakter
"""
                                )

                                st.code(text[:1500], language="text")
                                st.caption("Bu içerik retrieval aşamasında kullanılan doküman parçasıdır.")

        except Exception as e:
            st.error(f"❌ Cevap oluşturulurken hata: {str(e)}")

# Experiment table
if st.session_state.experiment_logs:
    df = pd.DataFrame(st.session_state.experiment_logs)

    st.divider()
    st.subheader("📊 Deney Sonuçları")

    st.dataframe(df, use_container_width=True)

    st.subheader("✅ Son Cevap Doğruluk Değerlendirmesi")

    accuracy_value = st.selectbox(
        "Son cevabın doğruluğunu seçin",
        ["Değerlendirilmedi", "Doğru", "Kısmen Doğru", "Yanlış"]
    )

    if st.button("Son Kaydı Güncelle"):
        st.session_state.experiment_logs[-1]["Doğruluk"] = accuracy_value
        st.success(f"Son kayıt '{accuracy_value}' olarak güncellendi.")
        st.rerun()

    if len(df) > 1:
        st.subheader("📈 Cevap Süresi Grafiği")

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(range(len(df)), df["Cevap Süresi (sn)"], marker="o")
        ax.set_xlabel("Test Numarası")
        ax.set_ylabel("Cevap Süresi (sn)")
        ax.set_title("RAG Sistem Performansı")

        st.pyplot(fig)

    csv = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="📥 CSV Olarak İndir",
        data=csv,
        file_name="experiment_results.csv",
        mime="text/csv"
    )

    if st.button("Deney Sonuçlarını Temizle"):
        st.session_state.experiment_logs = []
        st.rerun()

st.divider()
st.caption("🔬 AWS Bulut Altyapısında RAG Sistemi | Lokal RAG + AWS Bedrock ✅")