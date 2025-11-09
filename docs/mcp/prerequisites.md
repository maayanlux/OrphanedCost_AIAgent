# MCP Setup Prerequisites

## 🔍 Environment Requirements

### Azure Resources Required
- ✅ **Azure Logic Apps Standard tier** (required for MCP server functionality)
- ✅ **Azure AI Foundry project** with agent configurations
- ✅ **Your deployed Azure Functions** from the Cost Analyzer solution
- ✅ **Azure subscription** with appropriate permissions

### Permissions Needed
- **Application Administrator** (for app registration)
- **Contributor** on resource groups (for Logic Apps deployment)
- **Azure AI Project Manager** (for AI Foundry integration)
- **Cost Management Reader** (for cost analysis permissions)

### Tools & Access
- **PowerShell** with Azure CLI installed
- **VS Code** (optional, for MCP client testing)
- **Microsoft Entra ID** tenant access
- **GitHub Copilot** (optional, for agent testing)

## 📋 Pre-Setup Checklist

### 1. Verify Azure Functions Deployment
Ensure your cost analyzer functions are deployed and working:

```powershell
# Test your existing functions
$functionAppName = "YOUR-FUNCTION-APP-NAME"
$resourceGroup = "YOUR-RESOURCE-GROUP"

# Check function app status
az functionapp show --name $functionAppName --resource-group $resourceGroup --query "state"

# List available functions
az functionapp function list --name $functionAppName --resource-group $resourceGroup --query "[].name"
```

Expected functions:
- `orphaned-resources` 
- `cost-analysis`
- Any custom cost optimization functions

### 2. Verify AI Foundry Project
Check your AI Foundry setup:

```powershell
# List AI Foundry projects
az cognitiveservices account list --query "[?kind=='AIServices'].[name,resourceGroup,location]" -o table

# Get project details
$aiProjectName = "YOUR-AI-PROJECT-NAME"
az cognitiveservices account show --name $aiProjectName --resource-group $resourceGroup
```

### 3. Check Required Azure CLI Extensions

```powershell
# Install/update required extensions
az extension add --name logic
az extension add --name cognitiveservices
az extension add --name webapp

# Verify extensions
az extension list --query "[?name=='logic' || name=='cognitiveservices' || name=='webapp'].name" -o table
```

### 4. Validate Permissions

```powershell
# Check your current role assignments
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --all --query "[].{Role:roleDefinitionName,Scope:scope}" -o table

# Required roles should include:
# - Application Administrator (Entra ID level)
# - Contributor (Subscription/Resource Group level)  
# - Azure AI Project Manager (AI Foundry resource level)
```

## 🔑 Information to Gather

Before starting MCP setup, collect these values:

```powershell
# Subscription and tenant info
$subscriptionId = az account show --query id -o tsv
$tenantId = az account show --query tenantId -o tsv

# Resource group and function app details
$resourceGroup = "YOUR-RESOURCE-GROUP"
$functionAppName = "YOUR-FUNCTION-APP-NAME"
$functionAppUrl = "https://$functionAppName.azurewebsites.net"

# AI Foundry project details
$aiProjectName = "YOUR-AI-PROJECT-NAME"
$aiResourceGroup = "YOUR-AI-RESOURCE-GROUP"

# Storage account (for Logic Apps)
$storageAccount = "YOUR-STORAGE-ACCOUNT"

Write-Host "Subscription ID: $subscriptionId"
Write-Host "Tenant ID: $tenantId" 
Write-Host "Function App URL: $functionAppUrl"
Write-Host "AI Project: $aiProjectName"
```

## ⚠️ Important Notes

### Security Considerations
- **Never commit secrets** to version control
- **Use managed identities** where possible
- **Follow least privilege** principle for role assignments
- **Enable audit logging** for all MCP operations

### Naming Conventions
Use consistent naming for MCP resources:
- **App Registration**: `{ProjectName}-MCP-Server`
- **Logic App**: `logicapp-mcp-{projectname}`
- **Managed Identity**: `mi-mcp-{projectname}`

### Testing Environment
Consider setting up MCP in a development environment first:
- Separate resource group for MCP testing
- Development AI Foundry project
- Test function app with sample data

---

**Next Step**: Once all prerequisites are met, proceed to [app-registration.md](app-registration.md) for authentication setup.