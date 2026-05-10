import streamlit as st
import tempfile
import os
import time
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

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
    chunk_size = st.slider("Chunk Boyutu", 200, 1000, 500, step=100)
    chunk_overlap = st.slider("Chunk Overlap", 0, 200, 100, step=50)
    top_k = st.slider("Döndürülecek Sonuç Sayısı", 1, 10, 3)

    st.divider()

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
                    k=top_k
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
                        "Chunk Size": chunk_size,
                        "Chunk Overlap": chunk_overlap,
                        "Top-k": top_k,
                        "Chunk Sayısı": st.session_state.chunk_count,
                        "Cevap Süresi (sn)": round(elapsed_time, 2),
                        "Kaynak Sayısı": len(retrieved_docs)
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