"""
AWS Bulut Servisleri Entegrasyonu
- S3: Doküman depolama
- Bedrock: LLM API
- OpenSearch: Ölçeklenebilir vektör arama
"""

import os
import json
from typing import Dict, List, Optional


class S3Manager:
    """AWS S3 ile dosya yönetimi"""
    
    def __init__(self, bucket_name: str = None, region: str = "eu-west-1"):
        """
        S3 client'ı başlat
        
        Args:
            bucket_name: S3 bucket adı (env variable'dan alınabilir)
            region: AWS region
        """
        try:
            import boto3
            self.s3_client = boto3.client('s3', region_name=region)
            self.bucket_name = bucket_name or os.getenv('AWS_S3_BUCKET_NAME')
            
            if not self.bucket_name:
                raise ValueError("S3_BUCKET_NAME belirtilmeli")
                
        except ImportError:
            raise ImportError("boto3 paketi eksik. 'pip install boto3' komutunu çalıştırın.")
    
    def upload_file(self, file_path: str, s3_key: str = None) -> Dict:
        """
        Dosyayı S3'e yükle
        
        Args:
            file_path: Yerel dosya yolu
            s3_key: S3 object key (varsayılan: filename)
            
        Returns:
            Upload sonuç bilgileri
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
            
            if s3_key is None:
                s3_key = os.path.basename(file_path)
            
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            
            return {
                "success": True,
                "bucket": self.bucket_name,
                "key": s3_key,
                "url": f"s3://{self.bucket_name}/{s3_key}"
            }
            
        except Exception as e:
            raise Exception(f"S3 upload hatası: {str(e)}")
    
    def download_file(self, s3_key: str, local_path: str) -> Dict:
        """
        S3'ten dosyayı indir
        
        Args:
            s3_key: S3 object key
            local_path: İndirilecek yerel yol
            
        Returns:
            Download sonuç bilgileri
        """
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            
            return {
                "success": True,
                "local_path": local_path,
                "size": os.path.getsize(local_path)
            }
            
        except Exception as e:
            raise Exception(f"S3 download hatası: {str(e)}")
    
    def list_files(self, prefix: str = "") -> List[Dict]:
        """
        S3 bucket'ta dosyaları listele
        
        Args:
            prefix: Dosya adı ön eki (filtreleme)
            
        Returns:
            Dosya listesi
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        "key": obj['Key'],
                        "size": obj['Size'],
                        "modified": obj['LastModified'].isoformat()
                    })
            
            return files
            
        except Exception as e:
            raise Exception(f"S3 listeleme hatası: {str(e)}")


class BedrockLLM:
    """AWS Bedrock ile LLM integrasyon"""
    
    def __init__(self, model_id: str = "anthropic.claude-v2", region: str = "eu-west-1"):
        """
        Bedrock client'ı başlat
        
        Args:
            model_id: Bedrock model ID (Claude, Llama, Mistral, vb.)
            region: AWS region
        """
        try:
            import boto3
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
            self.model_id = model_id
            
        except ImportError:
            raise ImportError("boto3 paketi eksik")
    
    def generate_response(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Bedrock LLM'den cevap al
        
        Args:
            prompt: İstem metni
            max_tokens: Maksimum token sayısı
            
        Returns:
            Model cevabı
        """
        try:
            body = {
                "prompt": prompt,
                "max_tokens_to_sample": max_tokens,
                "temperature": 0.7,
                "top_k": 250,
                "top_p": 0.95
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            
            result = json.loads(response['body'].read())
            return result['completion'].strip()
            
        except Exception as e:
            raise Exception(f"Bedrock API hatası: {str(e)}")


class OpenSearchManager:
    """AWS OpenSearch ile vektör arama"""
    
    def __init__(self, host: str = None, region: str = "eu-west-1"):
        """
        OpenSearch client'ı başlat
        
        Args:
            host: OpenSearch domain endpoint
            region: AWS region
        """
        try:
            from opensearchpy import OpenSearch
            from opensearchpy.helpers import BulkIndexError
            
            self.host = host or os.getenv('OPENSEARCH_ENDPOINT')
            self.region = region
            
            # AWS Signature Version 4 ile bağlantı
            self.client = OpenSearch(
                hosts=[{'host': self.host, 'port': 443}],
                use_ssl=True,
                verify_certs=True,
                http_auth=self._get_auth(),
                timeout=30
            )
            
        except ImportError:
            raise ImportError("opensearch-py paketi eksik. 'pip install opensearch-py' çalıştırın.")
    
    def _get_auth(self):
        """AWS credentials'ı al"""
        import boto3
        credentials = boto3.Session().get_credentials()
        return (credentials.access_key, credentials.secret_key)
    
    def create_index(self, index_name: str, vector_size: int = 385) -> Dict:
        """
        Vektör arama için index oluştur
        
        Args:
            index_name: Index adı
            vector_size: Embedding boyutu
            
        Returns:
            İşlem sonucu
        """
        try:
            body = {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "knn": True,
                        "knn.algo_param.ef_construction": 256
                    }
                },
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": vector_size,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 24
                                }
                            }
                        }
                    }
                }
            }
            
            response = self.client.indices.create(
                index=index_name,
                body=body,
                ignore=400  # Zaten varsa hata verme
            )
            
            return {"success": True, "index": index_name}
            
        except Exception as e:
            raise Exception(f"OpenSearch index hatası: {str(e)}")
    
    def add_document(self, index_name: str, doc_id: str, text: str, embedding: list) -> Dict:
        """
        OpenSearch'e doküman ve embedding ekle
        
        Args:
            index_name: Target index
            doc_id: Doküman ID
            text: Metin içeriği
            embedding: Embedding vektörü
            
        Returns:
            İşlem sonucu
        """
        try:
            document = {
                "text": text,
                "embedding": embedding
            }
            
            response = self.client.index(
                index=index_name,
                id=doc_id,
                body=document
            )
            
            return {"success": True, "doc_id": doc_id}
            
        except Exception as e:
            raise Exception(f"Doküman ekleme hatası: {str(e)}")
    
    def search(self, index_name: str, embedding: list, k: int = 3) -> List[Dict]:
        """
        Vektör tabanında arama yap
        
        Args:
            index_name: Target index
            embedding: Sorgu embedding'i
            k: Kaç sonuç döndürülecek
            
        Returns:
            Benzer dokümanlar
        """
        try:
            body = {
                "size": k,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": embedding,
                            "k": k
                        }
                    }
                }
            }
            
            response = self.client.search(index=index_name, body=body)
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    "id": hit['_id'],
                    "score": hit['_score'],
                    "text": hit['_source']['text']
                })
            
            return results
            
        except Exception as e:
            raise Exception(f"Arama hatası: {str(e)}")


# AWS entegrasyonunun özeti
AWS_SERVICES = {
    "S3": "Doküman depolama ve yönetimi",
    "Bedrock": "Managed LLM API (Claude, Llama, vb.)",
    "OpenSearch": "Ölçeklenebilir vektör arama (KNN)"
}

print("AWS entegrasyonu hazırlandı. Kullanabileceğiniz servisler:", AWS_SERVICES)
