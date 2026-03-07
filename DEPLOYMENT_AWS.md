# AWS Bulut Altyapısında RAG Sistemi - Aşama 2 Deployment Guide

## 📋 Ön Hazırlıklar

### AWS Hesabı & Servisler

1. **AWS Hesabı Oluştur**
   - [AWS Console](https://aws.amazon.com) adresinde kayıt ol
   - IAM kullanıcı oluştur (programmatic access ile)
   - Access Key ID ve Secret Access Key'i kaydet

2. **Gerekli AWS Servislerine Erişim İzni ver**
   - S3 (AmazonS3FullAccess)
   - Bedrock (AmazonBedrockFullAccess)
   - OpenSearch (AmazonOpenSearchFullAccess)
   - ECR (AmazonEC2ContainerRegistryFullAccess)
   - ECS (AdministratorAccess)

### Lokal Kurulum

```bash
# AWS CLI yükle
pip install awscli

# Kimlik doğrulamasını yapılandır
aws configure
# AWS Access Key ID: YOUR_KEY
# AWS Secret Access Key: YOUR_SECRET
# Default region: eu-west-1
# Default output format: json
```

## 🚀 Deployment Adımları

### Adım 1: S3 Bucket Oluştur

```bash
# Bucket oluştur
aws s3 mb s3://rag-documents-bucket --region eu-west-1

# Versioning aktifleştir
aws s3api put-bucket-versioning \
    --bucket rag-documents-bucket \
    --versioning-configuration Status=Enabled

# CORS yapılandırması
aws s3api put-bucket-cors \
    --bucket rag-documents-bucket \
    --cors-configuration '{
        "CORSRules": [
            {
                "AllowedOrigins": ["*"],
                "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
                "AllowedHeaders": ["*"],
                "MaxAgeSeconds": 3000
            }
        ]
    }'
```

### Adım 2: OpenSearch Domain Oluştur

```bash
# Terraform kullan (daha kolay)
# OR

# AWS CLI ile
aws opensearch create-domain \
    --domain-name rag-documents \
    --engine-version OpenSearch_2.3 \
    --node-type t3.small.search \
    --node-count 1 \
    --ebs-enabled \
    --ebs-volume-size 100 \
    --region eu-west-1
```

### Adım 3: Docker Image Oluştur & ECR'a Push Et

```bash
# ECR repository oluştur
aws ecr create-repository \
    --repository-name rag-app \
    --region eu-west-1

# Kimlik doğrulamasını login yap
aws ecr get-login-password --region eu-west-1 | \
    docker login --username AWS --password-stdin \
    123456789.dkr.ecr.eu-west-1.amazonaws.com

# Docker image build et
docker build -t rag-app:latest .

# ECR'a tag ve push yap
docker tag rag-app:latest \
    123456789.dkr.ecr.eu-west-1.amazonaws.com/rag-app:latest

docker push \
    123456789.dkr.ecr.eu-west-1.amazonaws.com/rag-app:latest
```

### Adım 4: ECS Task Definition Oluştur

```bash
# task-definition.json oluştur
cat > task-definition.json << 'EOF'
{
  "family": "rag-app",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskRole",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "rag-app",
      "image": "123456789.dkr.ecr.eu-west-1.amazonaws.com/rag-app:latest",
      "cpu": 512,
      "memory": 1024,
      "portMappings": [
        {
          "containerPort": 8503,
          "hostPort": 8503,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "eu-west-1"
        },
        {
          "name": "AWS_S3_BUCKET_NAME",
          "value": "rag-documents-bucket"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/rag-app",
          "awslogs-region": "eu-west-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024"
}
EOF

# Task definition kaydını oluştur
aws ecs register-task-definition \
    --cli-input-json file://task-definition.json \
    --region eu-west-1
```

### Adım 5: ECS Cluster & Service Oluştur

```bash
# CloudFormation ile sağlama (en kolay)
# OR

# AWS CLI ile
aws ecs create-cluster \
    --cluster-name rag-cluster \
    --region eu-west-1

aws ecs create-service \
    --cluster rag-cluster \
    --service-name rag-service \
    --task-definition rag-app:1 \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration \
        "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}" \
    --load-balancers \
        "targetGroupArn=arn:aws:elasticloadbalancing:...",containerName=rag-app,containerPort=8503 \
    --region eu-west-1
```

### Adım 6: Application Load Balancer Konfigürasyonu

```bash
# Target group oluştur
aws elbv2 create-target-group \
    --name rag-app-targets \
    --protocol HTTP \
    --port 8503 \
    --vpc-id vpc-xxxxx

# Load balancer oluştur
aws elbv2 create-load-balancer \
    --name rag-app-lb \
    --subnets subnet-1 subnet-2 \
    --security-groups sg-xxxxx

# Listener ekle
aws elbv2 create-listener \
    --load-balancer-arn arn:aws:elasticloadbalancing:... \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

## 🔧 Konfigürasyon

### .env Dosyasını Ayarla

```bash
cp .env.example .env

# Düzenle
nano .env
```

Şu değerleri güncelle:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_S3_BUCKET_NAME`
- `OPENSEARCH_ENDPOINT` (OpenSearch domain URL'i)
- `BEDROCK_MODEL_ID` (tercih ettiğin model)

## 💡 Test & Monitoring

### Application Test

```bash
# Lokal test
streamlit run app.py

# Docker'da test
docker run -p 8503:8503 \
    -e AWS_REGION=eu-west-1 \
    -e AWS_S3_BUCKET_NAME=rag-documents-bucket \
    rag-app:latest

# CloudWatch Logs
aws logs tail /ecs/rag-app --follow
```

### Metrics

```bash
# CloudWatch metrics sorgu
aws cloudwatch get-metric-statistics \
    --namespace AWS/ECS \
    --metric-name CPUUtilization \
    --dimensions Name=ServiceName,Value=rag-service \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average
```

## 📊 Cost Optimization

### Teklifler

1. **S3**: ~$0.023/GB/ay
2. **OpenSearch**: ~$100-300/ay (t3.small)
3. **Bedrock**: ~$0.01-0.75 per 1M tokens
4. **ECS Fargate**: ~50$ /ay (512 CPU, 1GB memory)

### Tasarruf İpuçları

- S3 Lifecycle policies
- OpenSearch node sayısını azalt (dev ortamında)
- Bedrock model seçimini optimize et
- CloudWatch log retention'ını ayarla

## 🔐 Güvenlik

### Best Practices

1. **S3 Encryption**
```bash
aws s3api put-bucket-encryption \
    --bucket rag-documents-bucket \
    --server-side-encryption-configuration \
        '{...}'
```

2. **IAM Role Restriction**
   - Policy'i principle of least privilege ile sınırla

3. **VPC & Security Groups**
   - EC2/ECS'i private subnet'de çalıştır
   - NAT Gateway kullan

4. **Secrets Management**
   - AWS Secrets Manager kullan
   - Credentials'ı .env dose kaydetme

## 📚 Kaynaklar

- [AWS ECS Docs](https://docs.aws.amazon.com/ecs/)
- [AWS Bedrock Docs](https://docs.aws.amazon.com/bedrock/)
- [AWS OpenSearch Docs](https://docs.aws.amazon.com/opensearch-service/)
- [LangChain AWS Integration](https://python.langchain.com/docs/integrations/llms/bedrock)

## 🆘 Troubleshooting

### OpenSearch TimeoutError

```bash
# OpenSearch engine.yml'ı kontrol et
aws opensearch get-domain-config --domain-name rag-documents
```

### S3 Access Denied

```bash
# IAM policy kontrol et
aws iam get-user-policy --user-name YOUR_USER --policy-name YOUR_POLICY
```

### Model bulunamıyor (Bedrock)

```bash
# Mevcut modelleri listele
aws bedrock list-foundation-models --region eu-west-1
```

---

**Yardıma İhtiyacınız Varsa**: AWS Support veya proje sahibiyle iletişim kurun.
