# Azure Cost Management & Orphaned Resources Analyzer

A comprehensive Azure Functions application that provides cost analysis and orphaned resource detection across Azure subscriptions. This application integrates with Azure AI Foundry agents to provide intelligent resource management and cost optimization recommendations.

## ⚠️ **IMPORTANT SECURITY DISCLAIMER**

> **🚨 CRITICAL NOTICE: This solution does NOT use private endpoints and communicates over public internet with Azure APIs.**
>
> **IMPLEMENTATION RESPONSIBILITY**: Any organization or individual implementing this solution must:
> - **Review the entire codebase** to ensure it meets their security requirements
> - **Validate that the solution aligns** with their organizational security policies  
> - **Assess network security implications** of public endpoint usage
> - **Implement additional security measures** as required by their environment
> - **Take full responsibility** for the security implications of deployment
>
> **Microsoft, the solution authors, and contributors assume NO RESPONSIBILITY for security breaches, data exposure, or policy violations that may result from implementing this solution. The implementation and security review responsibility lies entirely with the implementing party.**

## 🏗️ Infrastructure Requirements

### Azure Functions
- **Service Plan**: Premium EP1 (minimum 1 instance)
- **Operating System**: Linux
- **Runtime**: Python 3.11
- **Authentication**: Managed Identity (System-assigned recommended)

### Required Azure Permissions
The Azure Functions Managed Identity requires the following role assignments:

#### Storage Account Permissions
- **Storage Blob Data Owner** - On the Function App's Storage Account

#### Subscription/Tenant Level Permissions  
Assign these roles on the scope you want to analyze (subscription or management group):
- **Reader** - For resource enumeration and details
- **Cost Management Reader** - For accessing cost data and billing information
- **Advisor Recommendations Contributor** - For assessments and reviews access

### Azure AI Foundry Requirements
- **Azure AI Foundry Resource** - Foundry resource for AI orchestration
- **Azure AI Foundry Project** - Project workspace within the Foundry
- **Connection Configuration** - Proper endpoint and authentication setup between Foundry agents and Functions

### Network Requirements
> ⚠️ **Security Note**: This solution uses **public endpoints** for all Azure service communications. No private endpoint or VNET integration is configured.

### Python Dependencies
- **Python Runtime**: 3.11 (as specified in requirements.txt)
- **Azure SDK Libraries**: For Cost Management, Resource Graph, and ARM APIs
- **Function Runtime**: Azure Functions v4

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Azure AI Foundry"
        Agent[AI Foundry Agent]
    end
    
    subgraph "Azure Functions App"
        F1[OrphanedResourcesAnalyzer]
        F2[GetOrphanedResourcesExample]
        F3[CostAnalysisDirectQuery]
        F4[CostManagementExample]
    end
    
    subgraph "Azure APIs"
        ARM[Azure Resource Manager API]
        CM[Cost Management API]
        RG[Resource Graph API]
    end
    
    Agent --> F1
    Agent --> F2
    Agent --> F3
    Agent --> F4
    
    F1 --> ARM
    F1 --> RG
    F2 --> ARM
    F3 --> CM
    F4 --> CM
```

## 🚀 Features

### Orphaned Resources Detection
- **Virtual Machines**: Identifies VMs without Azure Hybrid Benefit (AHB) eligible for Windows Server, RHEL, and SLES
- **Network Interfaces**: Detects NICs not attached to any virtual machine
- **Public IP Addresses**: Finds unattached public IPs
- **Managed Disks**: Identifies disks not attached to any VM
- **Network Security Groups**: Detects NSGs not associated with subnets or NICs

### Cost Analysis & Optimization
- **Direct Cost Management API Integration**: Real-time cost data retrieval
- **Multi-Resource Cost Analysis**: Batch processing with rate limiting optimization
- **Flexible Date Ranges**: Auto-calculation or custom date periods
- **Granular Cost Breakdown**: Daily, monthly, or aggregate cost reporting
- **Azure Hybrid Benefit Detection**: Identifies potential licensing cost savings

### Azure AI Foundry Integration
- **Agent-Triggered Analysis**: Seamless integration with AI Foundry agents
- **Intelligent Recommendations**: AI-powered cost optimization suggestions
- **Automated Reporting**: Structured data output for agent consumption

## 📋 Azure Functions API Reference

### 1. OrphanedResourcesAnalyzer
**Endpoint**: `/api/orphaned-resources`  
**Method**: POST  
**Purpose**: Comprehensive orphaned resource detection and analysis

**Request Schema**:
```json
{
  "subscription_id": "string (required)",
  "resource_types": ["VirtualMachines", "NetworkInterfaces", "PublicIPAddresses", "Disks", "NetworkSecurityGroups"],
  "resource_group": "string (optional)",
  "include_costs": true,
  "cost_period_days": 30
}
```

### 3. CostAnalysisDirectQuery
**Endpoint**: `/api/cost-analysis`  
**Method**: POST  
**Purpose**: Direct Azure Cost Management API queries with advanced filtering

**Request Schema**:
```json
{
  "subscription_id": "string (required)",
  "query_type": "specific_resources|resource_group|service|top_resources|subscription",
  "resource_ids": ["array of resource IDs"],
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "granularity": "Daily|Monthly",
  "top_n": 10
}
```

## 🤖 Azure AI Foundry Agent Integration

This application is designed to be triggered by Azure AI Foundry agents for intelligent resource management and cost optimization.

### Agent Configuration Files

All agent configurations, instructions, and schemas are located in the **`Agents/`** folder:

- **`Agent-OrphanedResources.txt`** - Instructions for the Orphaned Resources Analyzer agent
- **`Agent-Orphaned-Cost.txt`** - Instructions for the Cost Analysis agent  
- **`agents_schema.json`** - Complete OpenAPI schema for both agents
- **`connected-agents.txt`** - Connection and deployment instructions

### Agent Architecture

This application provides **two specialized agents** that work together:

1. **Agent 1: Orphaned Resources Analyzer** - Detects unused Azure resources
2. **Agent 2: Cost Analysis Agent** - Calculates financial impact of orphaned resources

**Detailed configurations and instructions for each agent are available in the `Agents/` folder.**

### Integration Benefits

- **Real-time Data**: Direct Azure API integration for accurate results
- **Cost Optimization**: Immediate identification of potential savings
- **Flexible Deployment**: Support for single subscription or tenant-wide analysis

### Quick Setup Guide

1. **Deploy your Azure Functions** to your Azure subscription
2. **Get your function keys** from Azure portal (Function App → Functions → Function Keys)
3. **Update the configuration files** in the `Agents/` folder with your deployment details:
   - Replace `YOUR-FUNCTION-APP-NAME` with your actual function app name
   - Replace `YOUR-FUNCTION-KEY` with your actual function keys
4. **Use the files in the `Agents/` folder** to configure your Azure AI Foundry agents

⚠️ **Security Note**: Never commit actual function keys to version control. Use placeholders in templates.

### 🔗 Advanced: Model Context Protocol (MCP) Setup

For enterprise scenarios requiring automated agent triggering and advanced workflow orchestration, you can configure agents to use the **Model Context Protocol (MCP)** through Azure Logic Apps.

**MCP enables**:
- 🤖 **Automated Agent Triggering** based on Azure alerts, schedules, or business events
- 🛡️ **Enterprise Security** with OAuth 2.0 and Easy Auth integration
- 🔧 **Tool Discovery** for agents to automatically find cost analysis capabilities
- 📊 **Workflow Integration** with existing Logic Apps and enterprise systems

📚 **Complete MCP Setup Guide**: [`docs/mcp/`](docs/mcp/README.md)

**Quick Links**:
- [MCP Overview & Benefits](docs/mcp/overview.md) - Understand MCP value for cost analysis
- [Prerequisites Checklist](docs/mcp/prerequisites.md) - Ensure environment readiness  
- [Step-by-Step Setup](docs/mcp/README.md) - Complete configuration guide
- [Ready-to-Deploy Workflows](docs/mcp/workflows/) - Logic App templates

**Use Cases**: Daily cost reports, alert-driven analysis, ticket integration, compliance automation


## 📁 Project Structure

```
├── function_app.py          # Main Azure Functions application
├── host.json               # Azure Functions host configuration
├── local.settings.json     # Local development settings
├── requirements.txt        # Python dependencies
├── README.md              # This documentation
├── Agents/                # Azure AI Foundry agent configurations
│   ├── Agent-OrphanedResources.txt     # Orphaned Resources agent instructions
│   ├── Agent-Orphaned-Cost.txt         # Cost Analysis agent instructions
│   ├── agents_schema.json              # Complete OpenAPI schema
│   └── connected-agents.txt            # Connection and deployment guide
└── tests/                 # Test files and debugging utilities (excluded from git)
    ├── test_*.py          # Unit and integration tests
    ├── debug_*.py         # Debugging utilities
    └── *.md               # Additional documentation
```

## 🚀 Deployment

### Prerequisites
- **Azure Subscription** with appropriate billing permissions
- **Azure Functions Core Tools v4**
- **Python 3.11** (required version)
- **Azure CLI** with permissions to create resources
- **Azure AI Foundry** access for agent configuration

### Step 1: Create Azure Function App
```bash
# Create resource group
az group create --name rg-cost-analyzer --location eastus2

# Create storage account for Function App
az storage account create \
  --name sacostanalyzer$(date +%s) \
  --resource-group rg-cost-analyzer \
  --location eastus2 \
  --sku Standard_LRS

# Create Function App with Premium EP1 plan on Linux
az functionapp plan create \
  --resource-group rg-cost-analyzer \
  --name plan-cost-analyzer \
  --location eastus2 \
  --number-of-workers 1 \
  --sku EP1 \
  --is-linux

az functionapp create \
  --resource-group rg-cost-analyzer \
  --plan plan-cost-analyzer \
  --name func-cost-analyzer-$(date +%s) \
  --storage-account sacostanalyzer \
  --runtime python \
  --runtime-version 3.11 \
  --os-type Linux \
  --assign-identity
```

### Step 2: Configure Managed Identity Permissions
```bash
# Get the Function App's Managed Identity Object ID
FUNCTION_PRINCIPAL_ID=$(az functionapp identity show \
  --name your-function-app-name \
  --resource-group rg-cost-analyzer \
  --query principalId -o tsv)

# Assign Storage Blob Data Owner on Function's Storage Account
az role assignment create \
  --assignee $FUNCTION_PRINCIPAL_ID \
  --role "Storage Blob Data Owner" \
  --scope "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/rg-cost-analyzer/providers/Microsoft.Storage/storageAccounts/YOUR_STORAGE_ACCOUNT"

# Assign Reader role (replace with your target scope)
az role assignment create \
  --assignee $FUNCTION_PRINCIPAL_ID \
  --role "Reader" \
  --scope "/subscriptions/YOUR_TARGET_SUBSCRIPTION_ID"

# Assign Cost Management Reader role
az role assignment create \
  --assignee $FUNCTION_PRINCIPAL_ID \
  --role "Cost Management Reader" \
  --scope "/subscriptions/YOUR_TARGET_SUBSCRIPTION_ID"

# Assign Advisor Recommendations Contributor role
az role assignment create \
  --assignee $FUNCTION_PRINCIPAL_ID \
  --role "Advisor Recommendations Contributor" \
  --scope "/subscriptions/YOUR_TARGET_SUBSCRIPTION_ID"
```

### Step 3: Set Up Azure AI Foundry
1. **Create Azure AI Foundry Project**:
   - Navigate to Azure portal → Create Resource → Azure AI Foundry
   - Create a new Project for agent orchestration

### Step 4: Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start local Azure Functions runtime
func host start
```

### Step 5: Deploy to Azure
```bash
# Deploy to Azure Functions
func azure functionapp publish your-function-app-name --python
```

### Step 6: Configure Application Settings
```bash
# Set any required application settings
az functionapp config appsettings set \
  --name your-function-app-name \
  --resource-group rg-cost-analyzer \
  --settings "ENVIRONMENT=production"
```

## 📖 Additional Resources

- **Azure Functions Documentation**: [docs.microsoft.com/azure/azure-functions](https://docs.microsoft.com/azure/azure-functions)
- **Azure Cost Management API**: [docs.microsoft.com/rest/api/cost-management](https://docs.microsoft.com/rest/api/cost-management)
- **Azure AI Foundry**: [docs.microsoft.com/azure/ai-foundry](https://docs.microsoft.com/azure/ai-foundry)