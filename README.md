# Kenya-First LMS - Online Learning Management System

A production-ready Learning Management System built specifically for the Kenyan market, featuring integrated M-Pesa and Airtel Money payments, multi-tenancy, and Azure cloud deployment.

## 🌍 Overview

This LMS is designed for B2C learners in Kenya with:
- **Kenya Payment Integration**: M-Pesa Daraja API (STK Push, C2B) and Airtel Money
- **Subscriptions with Dunning**: Monthly/annual renewals with automatic retry schedule
- **Multi-tenancy**: Support multiple institutions on a single deployment
- **Azure Cloud**: Blob Storage, Key Vault, Communication Services, Application Insights
- **Production-Ready**: Docker, CI/CD with GitHub Actions, comprehensive monitoring

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (for local development)
- Azure subscription (for production deployment)

### Local Development with Docker

1. **Clone the repository**
```bash
git clone https://github.com/ONDAR-025/online-cyber-services.git
cd online-cyber-services
```

2. **Create environment file**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start services with Docker Compose**
```bash
docker-compose up -d
```

4. **Access the application**
- Web: http://localhost:8000
- Admin: http://localhost:8000/admin

### Manual Setup (Without Docker)

1. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure database**
```bash
# Create PostgreSQL database
createdb lms

# Set DATABASE_URL in .env
DATABASE_URL=postgres://username:password@localhost:5432/lms
```

4. **Run migrations**
```bash
python manage.py migrate
```

5. **Create superuser**
```bash
python manage.py createsuperuser
```

6. **Start development server**
```bash
python manage.py runserver
```

7. **Start Celery worker (in separate terminal)**
```bash
celery -A lms_config worker -l info
```

8. **Start Celery beat (in separate terminal)**
```bash
celery -A lms_config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## 💳 Kenya Payment Setup

### M-Pesa Daraja API

1. **Register for Daraja API**
   - Go to https://developer.safaricom.co.ke
   - Create an account and create a new app
   - Get your Consumer Key and Consumer Secret
   - For production, apply for API credentials through Safaricom

2. **Configure M-Pesa in .env**
```env
MPESA_ENVIRONMENT=sandbox  # or production
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_SHORTCODE=174379  # Sandbox shortcode
MPESA_PASSKEY=your_passkey
MPESA_CALLBACK_URL=https://yourdomain.com/webhooks/mpesa
```

3. **Register C2B URLs**
```bash
python manage.py register_mpesa_urls
```

### Airtel Money API

1. **Register for Airtel Money API**
   - Contact Airtel Kenya Business team
   - Apply for Airtel Money API access
   - Get Client ID and Client Secret

2. **Configure Airtel Money in .env**
```env
AIRTEL_ENVIRONMENT=sandbox  # or production
AIRTEL_CLIENT_ID=your_client_id
AIRTEL_CLIENT_SECRET=your_client_secret
AIRTEL_CALLBACK_URL=https://yourdomain.com/webhooks/airtel
```

### Testing Payments

For M-Pesa sandbox:
- Test phone number: 254708374149
- PIN: Use any 4-digit PIN in sandbox

For Airtel sandbox:
- Contact Airtel for test credentials

## ☁️ Azure Services Setup

### 1. Azure Blob Storage

```bash
# Create storage account
az storage account create \
  --name lmsstorage \
  --resource-group lms-rg \
  --location southafricanorth \
  --sku Standard_LRS

# Get connection string
az storage account show-connection-string \
  --name lmsstorage \
  --resource-group lms-rg
```

Add to .env:
```env
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
```

### 2. Azure Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name lms-keyvault \
  --resource-group lms-rg \
  --location southafricanorth

# Add secrets
az keyvault secret set --vault-name lms-keyvault --name "DjangoSecretKey" --value "your-secret-key"
az keyvault secret set --vault-name lms-keyvault --name "MPesaConsumerKey" --value "your-mpesa-key"
```

Add to .env:
```env
AZURE_KEY_VAULT_URL=https://lms-keyvault.vault.azure.net/
```

### 3. Azure Communication Services

```bash
# Create ACS resource
az communication create \
  --name lms-acs \
  --resource-group lms-rg \
  --location global

# Get connection string
az communication show-connection-string \
  --name lms-acs \
  --resource-group lms-rg
```

Add to .env:
```env
ACS_CONNECTION_STRING=your_acs_connection_string
ACS_EMAIL_FROM=noreply@lms.co.ke
ACS_SMS_FROM=+254712345678
```

### 4. Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app lms-insights \
  --resource-group lms-rg \
  --location southafricanorth

# Get connection string
az monitor app-insights component show \
  --app lms-insights \
  --resource-group lms-rg
```

Add to .env:
```env
APPLICATIONINSIGHTS_CONNECTION_STRING=your_insights_connection_string
```

## 🏗️ Architecture

### Technology Stack

- **Backend**: Django 5.0, Django REST Framework
- **Database**: PostgreSQL (with django-tenants for multi-tenancy)
- **Cache/Queue**: Redis, Celery
- **Storage**: Azure Blob Storage
- **Secrets**: Azure Key Vault
- **Notifications**: Azure Communication Services (Email + SMS)
- **Monitoring**: Azure Application Insights
- **Deployment**: Docker, Azure App Service

### Key Features

1. **Course Management**
   - Courses with sections and lessons
   - Video (HLS), documents, quizzes
   - Prerequisites and access gating
   - Progress tracking

2. **Assessments**
   - Multiple choice, true/false, short answer questions
   - Grading and pass/fail logic
   - Certificate issuance (PDF in Azure Blob)

3. **Commerce**
   - Products and pricing (one-time, monthly, yearly)
   - Orders and invoices
   - VAT calculation (16% Kenya)
   - Coupons and refunds

4. **Payments**
   - M-Pesa STK Push and C2B
   - Airtel Money Collect
   - Webhook handling with idempotency
   - Double-entry ledger
   - Nightly reconciliation

5. **Subscriptions**
   - Recurring billing (monthly/yearly)
   - Dunning schedule: T+0, +1, +3 days, grace until T+7
   - Auto-renewal with STK/Collect
   - Downgrade rules

6. **Notifications**
   - Email and SMS via Azure Communication Services
   - Multi-language templates (English, Swahili)
   - Quiet hours support
   - Retry logic

## 📊 Admin Features

### Instructor Dashboard
- Course CRUD operations
- Content upload and management
- Student grading
- Revenue tracking
- Reconciliation reports

### Admin Tools
- Provider credentials management per tenant
- Webhook event viewer
- Payment reconciliation
- Subscription management
- User management

## 🔒 Security

- CSRF protection enabled
- HTTPS enforcement in production
- Rate limiting on sensitive endpoints
- Idempotency for payment operations
- Webhook signature verification
- Secure credential storage (Azure Key Vault)

## 🧪 Testing

Run tests:
```bash
pytest
```

With coverage:
```bash
pytest --cov=. --cov-report=html
```

## 📦 Deployment

### Azure App Service

See `deployment/azure/README.md` for detailed deployment instructions.

Quick deploy:
```bash
# Build and push Docker image
docker build -t lms:latest .
docker tag lms:latest youracr.azurecr.io/lms:latest
docker push youracr.azurecr.io/lms:latest

# Deploy to Azure App Service
az webapp config container set \
  --name lms-webapp \
  --resource-group lms-rg \
  --docker-custom-image-name youracr.azurecr.io/lms:latest
```

### Environment Variables

All required environment variables are documented in `.env.example`.

Critical settings for production:
```env
DEBUG=False
DJANGO_SECRET_KEY=use-a-strong-random-key
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
ALLOWED_HOSTS=yourdomain.com,.azurewebsites.net
```

## 🔄 CI/CD

GitHub Actions workflows are configured for:
- Linting and code quality checks
- Automated testing
- Docker image building
- Deployment to Azure staging
- Production deployment with approval

## 📖 API Documentation

### Payment Endpoints

```
POST /api/payments/intents - Create payment intent
POST /api/payments/mpesa/stk-push - Initiate M-Pesa STK Push
POST /api/payments/airtel/collect - Initiate Airtel Money collection
POST /webhooks/mpesa - M-Pesa callback
POST /webhooks/airtel - Airtel callback
```

### Subscription Endpoints

```
POST /api/subscriptions - Create subscription
GET /api/subscriptions/{id} - Get subscription details
POST /api/subscriptions/{id}/renew - Manually trigger renewal
POST /api/subscriptions/{id}/cancel - Cancel subscription
```

### Course Endpoints

```
GET /api/courses - List courses
GET /api/courses/{id} - Course details
POST /api/enrollments - Enroll in course
GET /api/enrollments/{id}/progress - Get progress
POST /api/progress/{lesson_id} - Update lesson progress
```

## 🌐 Multi-Language Support

The system supports English and Swahili:
- UI templates available in both languages
- Notification templates in English and Swahili
- User language preference setting

## 🆘 Support

For issues and questions:
- GitHub Issues: https://github.com/ONDAR-025/online-cyber-services/issues
- Email: support@lms.co.ke

## 📄 License

Copyright © 2024-2026 ONDAR-025. All rights reserved.

---

**Built for Kenya 🇰🇪 | Powered by Azure ☁️**
 
