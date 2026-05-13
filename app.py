import streamlit as st
import tempfile
import os
import time
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from src.s3_handler import upload_file_to_s3


from src.rag_pipeline import build_index, ask_question
from src.llm_handler import generate_answer_mock

st.set_page_config(
    page_title="RAG Sistem",
    page_icon="📄",
    layout="wide"
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

    elif answer_mode == "Detaylı":
        chunk_size = 800
        chunk_overlap = 200
        top_k = 8
        search_type = "mmr"
    manual_search_type = st.selectbox(
        "Deneysel Arama Yöntemi",
        ["Otomatik", "keyword", "similarity", "mmr"]
    )
    search_explanations = {
        "Otomatik": "Seçilen cevap moduna göre sistem en uygun arama yöntemini otomatik belirler.",
        "keyword": "Anahtar kelime araması yapar. Soru içindeki kelimeler dokümanda birebir aranır. Basittir ama anlam benzerliğini yakalayamaz.",
        "similarity": "Semantik benzerlik araması yapar. Sorunun anlamına en yakın doküman parçalarını getirir.",
        "mmr": "MMR araması yapar. Hem alakalı hem de birbirinden farklı parçaları getirir. Uzun dokümanlarda daha kapsamlı cevaplar için daha uygundur."
    }


    if manual_search_type != "Otomatik":
        search_type = manual_search_type

       

    st.caption(f"ℹ️ {search_explanations[manual_search_type]}")


    st.info(
        f"""
    Cevap Modu: {answer_mode}
    Chunk Size: {chunk_size}
    Chunk Overlap: {chunk_overlap}
    Top-k: {top_k}
    Arama: {search_type}

    Not: Chunk ayarları değişirse PDF'yi tekrar işlemeniz gerekir.
    """
    )

    st.header("🔑 LLM Seçimi")
    llm_option = st.radio(
        "LLM Türü",
        ["Mock (Test)", "OpenAI API", "AWS Bedrock"],
        help="Hangi LLM'i kullanmak istersiniz?"
    )

    if llm_option == "OpenAI API":
        api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    else:
        api_key = None

# File upload section
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📥 Adım 1: Doküman Yükle")
    uploaded_file = st.file_uploader(
        "PDF dosyası seçin",
        type=["pdf"],
        key="pdf_uploader"
    )

with col2:
    st.subheader("📊 Durum")
    if st.session_state.vector_store is not None:
        st.success(f"✅ Yüklü: {st.session_state.document_name}")
        st.info(f"Chunkların Sayısı: {st.session_state.chunk_count}")
    else:
        st.warning("❌ Henüz doküman yüklenmedi")

# Process document
if uploaded_file is not None:
    st.subheader("📋 Adım 2: Dokümanı İşle")

    if st.button("Dokümanı İşle", key="process_btn", help="PDF'i parçalara ayır ve embedding oluştur"):
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
            st.info("Lütfen PDF dosyasının geçerli olduğundan emin olun.")

# Question answering
st.subheader("❓ Adım 3: Soru Sor ve Cevap Al")

question = st.text_input(
    "Sorunuzu yazın",
    placeholder="Örnek: Bu doküman hakkında ana konular nelerdir?",
    key="question_input"
)

if st.button("Cevabını Al 🔍", key="answer_btn"):
    if st.session_state.vector_store is None:
        st.warning("⚠️ Önce PDF yükleyip işlemeniz gerekli!")

    elif not question.strip():
        st.warning("⚠️ Lütfen bir soru yazın!")

    else:
        try:
            with st.spinner("🤔 İlgili doküman parçaları aranıyor..."):
                retrieved_docs = ask_question(
                st.session_state.vector_store,
                question,
                k=top_k,
                search_type=search_type
            )

            if not retrieved_docs:
                st.info("Hiç sonuç bulunamadı.")

            else:
                answer = None
                start_time = time.time()

                with st.spinner("✍️ Cevap oluşturuluyor..."):
                    if llm_option == "Mock (Test)":
                        answer = generate_answer_mock(
                            question,
                            retrieved_docs
                        )

                    elif llm_option == "OpenAI API":
                        from src.llm_handler import generate_answer_openai

                        if not api_key:
                            st.error("❌ OpenAI API Key gerekli!")
                            answer = None
                        else:
                            answer = generate_answer_openai(
                                question,
                                retrieved_docs,
                                api_key
                            )

                    elif llm_option == "AWS Bedrock":
                        from src.llm_handler import generate_answer_bedrock

                        answer = generate_answer_bedrock(
                            question,
                            retrieved_docs
                        )

                end_time = time.time()
                elapsed_time = end_time - start_time

                if answer:
                    st.subheader("💡 Cevap")
                    st.write(answer)

                    st.info(
                        f"⏱️ Cevap süresi: {elapsed_time:.2f} saniye | "
                        f"Model: {llm_option} | "
                        f"Chunk size: {chunk_size} | "
                        f"Top-k: {top_k}"
                    )

                    st.session_state.experiment_logs.append({
                        "Doküman": st.session_state.document_name,
                        "Soru": question,
                        "Model": llm_option,
                        "Cevap Modu": answer_mode,
                        "Chunk Size": chunk_size,
                        "Chunk Overlap": chunk_overlap,
                        "Top-k": top_k,
                        "Arama Yöntemi": search_type,
                        "Chunk Sayısı": st.session_state.chunk_count,
                        "Cevap Süresi (sn)": round(elapsed_time, 2),
                        "Kaynak Sayısı": len(retrieved_docs),
                        "Doğruluk": "Değerlendirilmedi"
                    })

                    with st.expander("📚 Kaynaklar", expanded=False):
                        st.subheader("İlgili Doküman Parçaları")

                        for i, doc in enumerate(retrieved_docs, 1):
                            score = None

                            if hasattr(doc, "metadata") and doc.metadata:
                                score = doc.metadata.get("score")

                            label = f"Kaynak {i}"
                            if score is not None:
                                label += f" (skor: {score:.4f})"

                            with st.expander(label):
                                st.write(doc.page_content)

                                if score is not None:
                                    st.caption(f"Skor: {score:.4f}")
                                    if hasattr(doc, "metadata") and doc.metadata.get("search_type"):
                                        st.caption(f"Arama Yöntemi: {doc.metadata.get('search_type')}")
                                elif hasattr(doc, "metadata") and doc.metadata:
                                    st.caption(f"Metadata: {doc.metadata}")

        except Exception as e:
            st.error(f"❌ Cevap oluşturulurken hata: {str(e)}")

# Experiment table
if st.session_state.experiment_logs:
    import pandas as pd
    import matplotlib.pyplot as plt

    df = pd.DataFrame(st.session_state.experiment_logs)

    st.divider()
    st.subheader("📊 Deney Sonuçları")

    st.dataframe(
        df,
        use_container_width=True
    )
    st.subheader("✅ Son Cevap Doğruluk Değerlendirmesi")

    accuracy_value = st.selectbox(
        "Son cevabın doğruluğunu seçin",
        ["Değerlendirilmedi", "Doğru", "Kısmen Doğru", "Yanlış"]
    )

    if st.button("Son Kaydı Güncelle"):
        if st.session_state.experiment_logs:
            st.session_state.experiment_logs[-1]["Doğruluk"] = accuracy_value
            st.success(f"Son kayıt '{accuracy_value}' olarak güncellendi.")
            st.rerun()

    if len(df) > 1:
        st.subheader("📈 Cevap Süresi Grafiği")

        fig, ax = plt.subplots(figsize=(8, 4))

        ax.plot(
            range(len(df)),
            df["Cevap Süresi (sn)"],
            marker="o"
        )

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

# Footer
st.divider()
st.caption("🔬 AWS Bulut Altyapısında RAG Sistemi | Lokal RAG + AWS Bedrock ✅")