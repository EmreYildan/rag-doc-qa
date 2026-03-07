from src.retriever import search_similar_chunks, create_vector_store
from src.splitter import split_text
from src.embedder import get_embedding_model

# prepare data
text = 'hello world this is a test of the processing pipeline'
chunks = split_text(text, chunk_size=5, chunk_overlap=1)
print('chunks',chunks)
emb = get_embedding_model()
store = create_vector_store(chunks, emb)
results = search_similar_chunks(store, 'test', k=3)
print('results count', len(results))
for d in results:
    print('CONTENT:', d.page_content)
    print('META:', d.metadata)
