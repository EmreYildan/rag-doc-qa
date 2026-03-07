import streamlit as st
import tempfile
import os
from pathlib import Path

from src.rag_pipeline import build_index, ask_question
from src.llm_handler import generate_answer_mock

st.set_page_config(
    page_title="RAG Sistem",
    page_icon="📄",
    layout="wide"
)

st.title("📄 RAG Doküman Soru-Cevap Sistemi")
st.write("Doküman yükleyin ve yapay zekanın anlamasıyla sorular sorun.")

# Initialize session state
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "document_name" not in st.session_state:
    st.session_state.document_name = None
if "chunk_count" not in st.session_state:
    st.session_state.chunk_count = 0

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Ayarlar")
    chunk_size = st.slider("Chunk Boyutu", 200, 1000, 500, step=100)
    chunk_overlap = st.slider("Chunk Overlap", 0, 200, 100, step=50)
    top_k = st.slider("Döndürülecek Sonuç Sayısı", 1, 10, 3)
    
    st.divider()
    
    st.header("🔑 LLM Seçimi")
    llm_option = st.radio(
        "LLM Türü",
        ["Mock (Test)", "OpenAI API"],
        help="Hangi LLM'i kullanmak istersiniz?"
    )
    
    if llm_option == "OpenAI API":
        api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    else:
        api_key = None

# Main section - File upload
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📥 Adım 1: Doküman Yükle")
    uploaded_file = st.file_uploader("PDF dosyası seçin", type=["pdf"], key="pdf_uploader")

with col2:
    st.subheader("📊 Durum")
    if st.session_state.vector_store is not None:
        st.success(f"✅ Yüklü: {st.session_state.document_name}")
        st.info(f"Chunklarin Sayısı: {st.session_state.chunk_count}")
    else:
        st.warning("❌ Henüz doküman yükleniniz")

# Process document
if uploaded_file is not None:
    st.subheader("📋 Adım 2: Dokümanı İşle")
    
    if st.button("Dokümanı İşle", key="process_btn", help="PDF'i parçalara ayır ve embedding oluştur"):
        try:
            with st.spinner("⏳ Doküman işleniyor..."):
                # Create temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name
                
                # Build index
                result = build_index(tmp_path, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                
                st.session_state.vector_store = result["vector_store"]
                st.session_state.document_name = uploaded_file.name
                st.session_state.chunk_count = result["chunk_count"]
                
                # Cleanup
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                
                st.success(f"✅ Doküman başarıyla işlendi! {result['chunk_count']} chunk oluşturuldu.")
                st.balloons()
                
        except Exception as e:
            st.error(f"❌ Hata oluştu: {str(e)}")
            st.info("Lütfen PDF dosyasının geçerli olduğundan emin olun.")

# Question answering section
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
            with st.spinner("🤔 Cevap aranıyor..."):
                # Önce ilgili dokümanları bul
                retrieved_docs = ask_question(
                    st.session_state.vector_store,
                    question,
                    k=top_k
                )
            
            if not retrieved_docs:
                st.info("Hiç sonuç bulunamadı.")
            else:
                # Cevap oluştur
                with st.spinner("✍️ Cevap oluşturuluyor..."):
                    if llm_option == "Mock (Test)":
                        answer = generate_answer_mock(question, retrieved_docs)
                    else:
                        from src.llm_handler import generate_answer_openai
                        if not api_key:
                            st.error("❌ OpenAI API Key gerekli!")
                            answer = None
                        else:
                            answer = generate_answer_openai(question, retrieved_docs, api_key)
                
                if answer:
                    st.subheader("💡 Cevap")
                    st.write(answer)
                    
                    # İlgili doküman parçaları
                    with st.expander("📚 Kaynaklar", expanded=False):
                        st.subheader("İlgili Doküman Parçaları")
                        for i, doc in enumerate(retrieved_docs, 1):
                            score = None
                            if hasattr(doc, 'metadata') and doc.metadata:
                                score = doc.metadata.get('score')
                            label = f"Kaynak {i}"
                            if score is not None:
                                label += f" (skor: {score:.4f})"
                            with st.expander(label):
                                st.write(doc.page_content)
                                if score is not None:
                                    st.caption(f"Skor: {score}")
                                elif hasattr(doc, 'metadata') and doc.metadata:
                                    st.caption(f"Metadata: {doc.metadata}")
                        
        except Exception as e:
            st.error(f"❌ Cevap oluşturulurken hata: {str(e)}")

# Footer
st.divider()
st.caption("🔬 AWS Bulut Altyapısında RAG Sistemi | Aşama 1: Lokal RAG ✅")