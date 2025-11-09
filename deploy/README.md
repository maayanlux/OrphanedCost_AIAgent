# Azure Cost Management Functions - Infrastructure Deployment

This folder contains ARM JSON templates to deploy the complete Azure infrastructure needed for the Azure Cost Management solution.


## 🚀 **Deployment Options**

### Option 1: Basic Infrastructure Only

Deploy just the Function App infrastructure for cost analysis functions.

<a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FIditbnaya%2FAzure-CostA-Agantic-AI%2Fmain%2Fdeploy%2Fsimple.json" target="_blank">
<img src="https://aka.ms/deploytoazurebutton" alt="Deploy to Azure"/>
</a>

**Includes:** Function App + Storage + App Service Plan + Application Insights + Log Analytics

### Option 2: Complete AI Agent Infrastructure

Deploy Function App infrastructure plus Azure AI Foundry for agent development.

<a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FIditbnaya%2FAzure-CostA-Agantic-AI%2Fmain%2Fdeploy%2Fsimple-with-foundry.json" target="_blank">
<img src="https://aka.ms/deploytoazurebutton" alt="Deploy to Azure"/>
</a>

**Includes:** All Basic Infrastructure + AI Foundry Hub + AI Project

--

## 📋 **Prerequisites**

### Required Parameters
Before deployment, you must provide names for all resources. The templates do not include default values to ensure you can customize resource names according to your organization's naming conventions.

**Required Resource Names:**

### Basic Template (simple.json):
- **Function App Name**: Must be globally unique (e.g., `func-costanalysis-yourorg-01`)
- **Hosting Plan Name**: Can be regional unique (e.g., `plan-costanalysis-prod`)
- **Storage Account Name**: Auto-generated (e.g., `sacostprodabc123def`)

### AI Foundry Template (simple-with-foundry.json):
- **Function App Name**: Must be globally unique (e.g., `func-costanalysis-yourorg-01`)
- **Hosting Plan Name**: Can be regional unique (e.g., `plan-costanalysis-prod`)  
- **Storage Account Name**: Auto-generated (e.g., `sacostprodabc123def`)
- **AI Hub Name**: Must be globally unique (e.g., `aihub-costanalysis-yourorg`)
- **AI Project Name**: Must be unique within the hub (e.g., `aiproj-costanalysis-yourorg`)


### Naming Convention Guidelines
- **Function App**: Use format `func-<solution>-<environment>-<instance>` (e.g., `func-costanalysis-prod-01`)
- **Storage Account**: Use format `sa<solution><environment><instance>` (e.g., `sacostanalysisprod01`)
- **AI Services**: Use format `<prefix>-<solution>-<environment>` (e.g., `aihub-costanalysis-prod`)

### Parameter Files

This repository includes example parameter files:
- `simple.parameters.json` - Example values for basic infrastructure
- `simple-with-foundry.parameters.json` - Example values for AI Foundry infrastructure

### Azure Subscription Requirements
- Azure subscription with appropriate permissions
- Resource group (will be created if it doesn't exist)
- Owner or Contributor access to the subscription for RBAC assignments

## ⚙️ **Template Parameters**

### Basic Deployment (`simple.json`)

These parameters align with the current ARM template. Empty default values (`""`) mean you must supply a value in the parameter file or portal UI. The storage account name is auto-generated using an ARM expression; you can override it by providing a value if desired.

| Parameter | Default (Template) | Description |
|-----------|--------------------|-------------|
| `functionAppName` | `` (required) | Globally unique Function App name |
| `hostingPlanName` | `` (required) | App Service Plan name |
| `storageAccountName` | `sacost{env}{unique}` (auto) | Storage account (auto-generated if left blank) |
| `environment` | `prod` | Environment label (dev, test, prod) |
| `location` | `<resource group location>` | Region (inherits the resource group location) |
| `runtime` | `python` | Function runtime language |
| `runtimeVersion` | `3.11` | Python version for Functions |
| `skuName` | `Y1` | Plan SKU (Y1 for Consumption; EP1/EP2/EP3 for Premium) |
| `tags` | object (sample provided) | Resource tagging object |

Tag object example:

```json
{
   "Environment": "PROD",
   "Application": "Azure Cost Management",
   "Project": "Cost Optimization",
   "Owner": "FinOps Team",
   "CostCenter": "IT-Operations"
}
```

### AI Foundry Deployment (`simple-with-foundry.json`)

Includes all basic parameters plus AI Foundry Hub & Project and optional model deployment settings.

| Parameter | Default (Template) | Description |
|-----------|--------------------|-------------|
| `aiHubName` | `` (required) | Azure AI Foundry Hub name (globally unique) |
| `aiProjectName` | `` (required) | Azure AI Foundry Project name (unique within Hub) |
| `deployModel` | `true` | Whether to deploy a model artifact placeholder |
| `modelName` | `gpt-41-mini` | Allowed: `gpt-41-mini`, `gpt-4o-mini`, `o1-mini` |
| `functionAppName` | `` (required) | Function App name |
| `hostingPlanName` | `` (required) | App Service Plan name |
| `storageAccountName` | `sacost{env}{unique}` (auto) | Auto-generated storage account name |
| `environment` | `prod` | Environment label |
| `location` | `<resource group location>` | Region (inherits RG location) |
| `runtime` | `python` | Runtime language |
| `runtimeVersion` | `3.11` | Python version |
| `skuName` | `Y1` | Plan SKU |
| `tags` | object | Resource tags |

Notes:
- To change the model later, update application logic or redeploy with a different `modelName`.
- If you set `deployModel` to `false`, no model deployment step is executed; you can attach an existing model manually in AI Foundry Studio.

## 🛠️ **Manual Deployment via Azure CLI**

### Basic Infrastructure

```bash
# Login to Azure
az login

# Create resource group
az group create --name "rg-costanalysis-prod" --location "East US"

# Deploy template
az deployment group create \
  --resource-group "rg-costanalysis-prod" \
  --template-file "simple.json" \
  --parameters "simple.parameters.json"
```

### AI Foundry Infrastructure

```bash
# Deploy enhanced template
az deployment group create \
  --resource-group "rg-costanalysis-prod" \
  --template-file "simple-with-foundry.json" \
  --parameters "simple-with-foundry.parameters.json"
```

## 🔧 **Customization**

1. **Copy parameter files:**

   ```bash
   cp simple.parameters.json my-custom.parameters.json
   ```

2. **Edit parameters:**
   - Modify resource names
   - Change SKUs and configurations
   - Adjust environment settings

3. **Deploy with custom parameters:**

    ```bash
    az deployment group create \
       --resource-group "your-rg" \
       --template-file "simple.json" \
       --parameters "@my-custom.parameters.json"
    ```

## 📁 **Files in This Folder**

- `simple.json` - Basic ARM template for Function App infrastructure
- `simple.parameters.json` - Parameters for basic deployment
- `simple-with-foundry.json` - Enhanced template with AI Foundry
- `simple-with-foundry.parameters.json` - Parameters for AI Foundry deployment
- `README.md` - This documentation

## 🎯 **Next Steps After Deployment**

1. **Basic Infrastructure:**
   - Deploy Function App code from `/function_app.py`
   - Configure environment variables in Function App settings
   - Test cost analysis endpoints

2. **AI Foundry Infrastructure:**
    - Access AI Foundry Studio via Azure portal
    - (Optional) If `deployModel` was true, verify the model placeholder and configure it as needed
    - Configure agent connections between Function App endpoints and AI Project
    - Get Function App Managed Identity ID (if needed):

       ```bash
       az functionapp identity show --name [FUNCTION-APP-NAME] --resource-group [RESOURCE-GROUP] --query principalId -o tsv
       ```

