# Rainmaker Deployment Guide

## Overview

Rainmaker is designed to be deployed on AWS using a containerized architecture with ECS Fargate for the backend and S3/CloudFront for the frontend.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed locally
- Domain name (optional but recommended)

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudFront    │    │  Application     │    │     TiDB        │
│   (Frontend)    │────│  Load Balancer   │────│   Serverless    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌────────┴────────┐
                       │   ECS Fargate   │
                       │   (Backend)     │
                       └─────────────────┘
                                │
                       ┌────────┴────────┐
                       │ Redis ElastiCache│
                       │   (Cache/Queue) │
                       └─────────────────┘
```

## Environment Setup

### 1. AWS Infrastructure

#### Create VPC and Networking
```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=rainmaker-vpc}]'

# Create subnets
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24 --availability-zone us-west-2a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.2.0/24 --availability-zone us-west-2b

# Create internet gateway
aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=rainmaker-igw}]'
```

#### Create ECS Cluster
```bash
aws ecs create-cluster --cluster-name rainmaker-cluster --capacity-providers FARGATE
```

#### Create Application Load Balancer
```bash
aws elbv2 create-load-balancer \
  --name rainmaker-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx
```

### 2. Database Setup

#### TiDB Serverless
1. Sign up for TiDB Cloud
2. Create a serverless cluster
3. Note the connection string for environment variables

#### Redis ElastiCache
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id rainmaker-redis \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --num-cache-nodes 1
```

### 3. S3 and CloudFront

#### Create S3 Bucket
```bash
aws s3 mb s3://rainmaker-frontend-bucket
aws s3 website s3://rainmaker-frontend-bucket --index-document index.html
```

#### Create CloudFront Distribution
```bash
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

## Application Deployment

### 1. Backend Deployment

#### Build and Push Docker Image
```bash
cd Rainmaker-backend

# Build image
docker build -t rainmaker-backend:latest .

# Tag for ECR
docker tag rainmaker-backend:latest 123456789012.dkr.ecr.us-west-2.amazonaws.com/rainmaker-backend:latest

# Push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-2.amazonaws.com
docker push 123456789012.dkr.ecr.us-west-2.amazonaws.com/rainmaker-backend:latest
```

#### Create ECS Task Definition
```json
{
  "family": "rainmaker-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "rainmaker-backend",
      "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/rainmaker-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "TIDB_URL",
          "value": "mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/rainmaker"
        },
        {
          "name": "REDIS_URL",
          "value": "redis://rainmaker-redis.xxx.cache.amazonaws.com:6379"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:123456789012:secret:rainmaker/openai-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/rainmaker-backend",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Create ECS Service
```bash
aws ecs create-service \
  --cluster rainmaker-cluster \
  --service-name rainmaker-backend-service \
  --task-definition rainmaker-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/rainmaker-backend-tg/xxx,containerName=rainmaker-backend,containerPort=8000
```

### 2. Frontend Deployment

#### Build and Deploy to S3
```bash
cd Rainmaker-frontend

# Build production bundle
npm run build

# Deploy to S3
aws s3 sync dist/ s3://rainmaker-frontend-bucket --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id E123456789 --paths "/*"
```

## Environment Variables

### Production Environment Variables
Create these in AWS Secrets Manager or Parameter Store:

```bash
# Required
OPENAI_API_KEY=sk-xxx
TIDB_URL=mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/rainmaker
REDIS_URL=redis://rainmaker-redis.xxx.cache.amazonaws.com:6379
SECRET_KEY=your-production-secret-key

# Optional
SONAR_API_KEY=pplx-xxx
SENDGRID_API_KEY=SG.xxx
CLEARBIT_API_KEY=pk_xxx
GOOGLE_CALENDAR_CREDENTIALS={"type": "service_account"...}
LINKEDIN_API_KEY=77xxx

# AWS
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET=rainmaker-files

# Feature flags
ENABLE_AUTOMATIC_OUTREACH=false
REQUIRE_HUMAN_APPROVAL=true

# Application
DEBUG=false
LOG_LEVEL=INFO
```

## SSL/TLS Configuration

### Certificate Manager
```bash
# Request SSL certificate
aws acm request-certificate \
  --domain-name rainmaker.yourdomain.com \
  --validation-method DNS \
  --subject-alternative-names "*.rainmaker.yourdomain.com"
```

### Update Load Balancer
```bash
# Add HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/rainmaker-alb/xxx \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-west-2:123456789012:certificate/xxx \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/rainmaker-backend-tg/xxx
```

## Monitoring and Logging

### CloudWatch Logs
```bash
# Create log groups
aws logs create-log-group --log-group-name /ecs/rainmaker-backend
aws logs create-log-group --log-group-name /ecs/rainmaker-celery
```

### CloudWatch Alarms
```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "rainmaker-high-cpu" \
  --alarm-description "High CPU utilization" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

## Backup and Recovery

### Database Backups
TiDB Serverless provides automatic backups. Configure additional backup policies as needed.

### Application Data Backup
```bash
# Backup S3 bucket
aws s3 sync s3://rainmaker-frontend-bucket s3://rainmaker-backup-bucket/frontend/$(date +%Y%m%d)/

# Backup secrets
aws secretsmanager describe-secret --secret-id rainmaker/openai-api-key > backup/secrets-$(date +%Y%m%d).json
```

## Scaling

### Auto Scaling
```bash
# Create auto scaling target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/rainmaker-cluster/rainmaker-backend-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/rainmaker-cluster/rainmaker-backend-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name rainmaker-cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

## Security

### IAM Roles
Create IAM roles with minimal required permissions:

- ECS Task Execution Role
- ECS Task Role
- Lambda Execution Role (if using Lambda functions)

### Security Groups
Configure security groups to allow only necessary traffic:

```bash
# Backend security group
aws ec2 create-security-group \
  --group-name rainmaker-backend-sg \
  --description "Security group for Rainmaker backend"

# Allow HTTP from ALB
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxx \
  --protocol tcp \
  --port 8000 \
  --source-group sg-alb-xxx
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   - Check CloudWatch logs
   - Verify environment variables
   - Check security group rules

2. **Database connection issues**
   - Verify TiDB connection string
   - Check network connectivity
   - Validate credentials

3. **High latency**
   - Check CloudWatch metrics
   - Scale up ECS service
   - Optimize database queries

### Useful Commands

```bash
# Check service status
aws ecs describe-services --cluster rainmaker-cluster --services rainmaker-backend-service

# View logs
aws logs tail /ecs/rainmaker-backend --follow

# Update service
aws ecs update-service --cluster rainmaker-cluster --service rainmaker-backend-service --task-definition rainmaker-backend:2

# Scale service
aws ecs update-service --cluster rainmaker-cluster --service rainmaker-backend-service --desired-count 4
```

## Cost Optimization

1. **Use Fargate Spot** for non-critical workloads
2. **Configure auto-scaling** to scale down during low usage
3. **Use S3 Intelligent Tiering** for file storage
4. **Monitor CloudWatch costs** and set up billing alerts
5. **Use Reserved Instances** for predictable workloads

## Maintenance

### Regular Tasks
- Update Docker images with security patches
- Monitor and rotate API keys
- Review CloudWatch logs for errors
- Update SSL certificates before expiration
- Backup critical data regularly

### Updates
1. Test changes in staging environment
2. Use blue-green deployment for zero downtime
3. Monitor application metrics after deployment
4. Have rollback plan ready