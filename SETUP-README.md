# 🚀 Quick Setup Guide

This folder contains everything you need to deploy the Azure Cost Management & Orphaned Resources Analyzer solution.

## 📁 Files Overview

| File | Purpose |
|------|---------|
| `INSTRUCTIONS.md` | **Complete step-by-step manual setup guide** |
| `setup.ps1` | **Automated PowerShell deployment script** |
| `README.md` | This quick setup guide |

## ⚡ Quick Start (Automated)

### Prerequisites
- Azure CLI installed and logged in
- PowerShell 5.1 or PowerShell Core
- Python 3.11 installed
- Azure Functions Core Tools v4

### Run Automated Setup
```powershell
# Clone and navigate to repository
git clone https://github.com/iditbnaya_microsoft/CostAgents.git
cd CostAgents

# Run automated setup (replace with your resource group name)
.\setup.ps1 -ResourceGroupName "rg-cost-analyzer-prod"

# Optional: Specify location
.\setup.ps1 -ResourceGroupName "rg-cost-analyzer-prod" -Location "eastus2"
```

### What the Script Does
- ✅ Validates all prerequisites
- ✅ Creates Azure Resource Group
- ✅ Creates Storage Account
- ✅ Creates Premium Function App with Python 3.11
- ✅ Configures Managed Identity
- ✅ Assigns all required permissions
- ✅ Deploys function code (if available)
- ✅ Sets up Application Insights
- ✅ Retrieves function keys
- ✅ Provides next steps guidance

## 📖 Manual Setup

For detailed control or troubleshooting, use the comprehensive manual guide:

👉 **[Open INSTRUCTIONS.md](INSTRUCTIONS.md)** for complete step-by-step instructions

The manual guide includes:
- Detailed prerequisites validation
- Security configuration setup
- Step-by-step Azure resource creation
- AI Foundry configuration
- Testing and validation procedures
- Monitoring setup
- Troubleshooting guide
- Best practices

## 🔒 Security Setup

**Important**: After infrastructure deployment, set up the security pipeline:

```powershell
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Test security pipeline
pre-commit run --all-files
```

Configure GitHub branch protection rules to require security checks.

## 🤖 AI Foundry Configuration

After deployment, update the agent configuration files:

1. **Update `Agents/Agent-OrphanedResources.txt`**:
   - Replace `YOUR-FUNCTION-APP-NAME` with your function app name
   - Replace `YOUR-FUNCTION-KEY` with your master key

2. **Update `Agents/Agent-Orphaned-Cost.txt`**:
   - Replace `YOUR-FUNCTION-APP-NAME` with your function app name
   - Replace `YOUR-FUNCTION-KEY` with your master key

3. **Deploy agents in Azure AI Foundry Studio**

## 🧪 Testing Your Deployment

```powershell
# Test example endpoints (no authentication)
$functionAppName = "your-function-app-name"
Invoke-RestMethod -Uri "https://$functionAppName.azurewebsites.net/api/orphaned-resources-example"
Invoke-RestMethod -Uri "https://$functionAppName.azurewebsites.net/api/cost-example"

# Test authenticated endpoints
$masterKey = "your-master-key"
$subscriptionId = "your-subscription-id"

$payload = @{
    subscription_id = $subscriptionId
    resource_types = @("PublicIPAddresses", "NetworkInterfaces")
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://$functionAppName.azurewebsites.net/api/orphaned-resources?code=$masterKey" -Method POST -Body $payload -ContentType "application/json"
```

## 🆘 Need Help?

- **Automated Setup Issues**: Check PowerShell execution policy and Azure permissions
- **Manual Setup**: Follow the detailed INSTRUCTIONS.md guide
- **Security Pipeline**: Review `.github/workflows/secret-scan.yml` configuration
- **AI Foundry**: Ensure agent configurations match your deployment details

## 📊 What You Get

After successful deployment:

- **Secure Function App** with 7-tool security pipeline
- **Four API endpoints** for cost analysis and orphaned resource detection
- **Managed Identity** with least-privilege permissions
- **Application Insights** monitoring and logging
- **AI Foundry agents** for intelligent cost optimization
- **Complete documentation** and best practices

## 🎯 Next Steps

1. **Test all endpoints** to verify functionality
2. **Configure AI Foundry agents** with your deployment details
3. **Set up monitoring alerts** in Azure Monitor
4. **Train your team** on using the solution
5. **Implement regular maintenance** procedures

---

**Choose Your Path**:
- 🚀 **Quick & Automated**: Run `setup.ps1`
- 📖 **Detailed & Manual**: Follow `INSTRUCTIONS.md`

Both paths lead to the same fully functional solution! 🎉