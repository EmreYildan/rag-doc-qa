# AWS Bulut Altyapısı Üzerinde RAG Tabanlı Doküman Soru-Cevap Sistemi

## 📋 Proje Açıklaması

Bu proje, kullanıcıların yüklediği dokümanlardan doğal dilde soru sorarak hızlı ve anlamlı bilgi almasını sağlayan bulut tabanlı bir akıllı sistem geliştirmektedir. 

Sistem, doküman içeriklerini analiz ederek kullanıcı sorularına bağlama uygun cevaplar üretecek ve ilgili doküman bölümlerini kullanıcıya sunacaktır.

## 🏗️ Proje Mimarisi

```
Kullanıcı (Streamlit Arayüz)
    ↓
Python Backend
    ├── PDF Yükleme
    ├── Chunking
    ├── Embedding Oluşturma
    ↓
Vector Database (FAISS / OpenSearch)
    ↓
Retriever
    ↓
LLM (AWS Bedrock / OpenAI)
    ↓
Cevap + Kaynak Parça
```

## 🚀 Aşamalar

### ✅ Aşama 1: Lokal RAG (Tamamlandı)

- **Python**: Backend dili
- **FAISS**: Vektör database
- **LangChain**: Orchestration
- **Streamlit**: Web arayüzü

**Özellikler:**
- PDF yükleme ve okuma
- Metin parçalama (chunking)
- Embedding oluşturma (HuggingFace)
- Vektör tabanında arama
- Benzer doküman parçalarını bulma

### 🔄 Aşama 2: AWS Entegrasyonu (Yapılacak)

- **S3**: Doküman depolama
- **AWS Bedrock**: LLM servisi
- **OpenSearch**: Daha büyük ölçekli vektör arama
- **Lambda**: Serverless backend

### 📊 Aşama 3: Deneyler & Rapor (Yapılacak)

- Keyword search vs RAG karşılaştırması
- Farklı chunk size'ları ile deney
- Farklı soru tipleri ile test
- Detaylı sonuç raporu

## 📦 Kurulum

### Gereksinimler
- Python 3.11+
- Virtual Environment

### Adımlar

```bash
# Virtual environment oluştur
python -m venv .venv

# Virtual environment'ı aktifleştir (Windows)
.venv\Scripts\activate

# Paketleri yükle
pip install -r requirements.txt
```

## 🏃 Çalıştırma

```bash
# Streamlit uygulamasını başlat
streamlit run app.py
```

Tarayıcı otomatik olarak `http://localhost:8503` adresinde açılacaktır.

## 📁 Dosya Yapısı

```
rag-doc-qa/
├── app.py                 # Streamlit arayüzü
├── requirements.txt       # Python paketleri
├── README.md             # Bu dosya
├── src/
│   ├── __init__.py       # Package initializer
│   ├── pdf_reader.py     # PDF okuma
│   ├── splitter.py       # Metin parçalama
│   ├── embedder.py       # Embedding modeli
│   ├── retriever.py      # Vector store & arama
│   └── rag_pipeline.py   # Ana RAG pipeline
```

## 💡 Kullanım

1. **PDF Yükle**: Sağ taraftaki dosya yükleyicisinden PDF dosyası seçin
2. **Dokümanı İşle**: "Dokümanı İşle" butonuna tıklayın
3. **Soru Sor**: Metin alanına sorunuzu yazın
4. **Cevabını Al**: "Cevabını Al" butonuna tıklayarak sonuçları görün

## ⚙️ Ayarlar (Sidebar)

- **Chunk Boyutu** (200-1000): Metin parçalarının boyutu
- **Chunk Overlap** (0-200): Parçalar arasındaki örtüşme
- **Döndürülecek Sonuç Sayısı** (1-10): Kaç sonuç görüntülensin

## 🔧 Teknik Detaylar

### Teknolojiler
- **LangChain**: LLM orchestration
- **FAISS**: Vektör arama (CPU)
- **HuggingFace Embeddings**: Metin embedding (all-MiniLM-L6-v2)
- **Streamlit**: Web UI
- **PyPDF**: PDF okuma
- **RecursiveCharacterTextSplitter**: Metin parçalama

### Workflow

1. **PDF Processing**
   - PDF dosyası okuan
   - Sayfa sayfa metin çıkarılır
   - Sayfalar arabelleğe eklenir

2. **Chunking**
   - Metin belirlenen chunk_size'a göre bölünür
   - Chunk'lar arasında overlap korunur
   - Ortalama 20-50 chunk oluşturulur

3. **Embedding**
   - Her chunk için embedding vektörü oluşturulur
   - 385 boyutlu vektör (all-MiniLM-L6-v2)
   - FAISS'de indeksleme yapılır

4. **Retrieval**
   - Kullanıcı sorusu embedding'e çevrilir
   - Kosinüs benzerliği ile arama yapılır
   - En benzer k chunk döndürülür

## 📊 Deneysel Sonuçlar

### Aşama 1 Testleri

| Test | Durum | Notlar |
|------|-------|--------|
| PDF Okuma | ✅ | Sorunsuz |
| Chunking | ✅ | Custom parametreler destekleniyor |
| Embedding | ✅ | HuggingFace modeli kullanılıyor |
| FAISS Arama | ✅ | Hızlı ve doğru sonuçlar |
| UI/UX | ✅ | Streamlit arayüzü responsive |

## 🎯 Sonraki Adımlar

1. [ ] OpenAI API entegrasyonu
2. [ ] AWS S3 dosya depolama
3. [ ] AWS Bedrock LLM entegrasyonu
4. [ ] OpenSearch vektör tabanı
5. [ ] Deneyler ve karşılaştırma
6. [ ] Rapor oluşturma

## 📝 Notlar

- İlk kez çalıştırıldığında embedding modeli indirilir (~1 GB)
- Her PDF işlendiğinde FAISS indeksi hafızada tutulur
- Çok büyük PDF'ler için OpenSearch tercih edilir

## 📞 İletişim & Destek

Proje sahibi: E.
