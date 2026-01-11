# Azure Deployment Guide

This guide covers deploying the Kenya LMS to Azure.

## Quick Deploy

```bash
# Set variables
RESOURCE_GROUP="lms-rg"
LOCATION="southafricanorth"
APP_NAME="kenya-lms"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Deploy using template (see main.bicep)
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters appName=$APP_NAME
```

## Required Azure Services

1. App Service (Container) - Django application
2. PostgreSQL Flexible Server - Database
3. Azure Cache for Redis - Celery broker
4. Storage Account - Media/documents
5. Key Vault - Secrets
6. Communication Services - Email/SMS
7. Application Insights - Monitoring

See detailed setup instructions in the main README.md file.
