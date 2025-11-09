# Logic Apps Workflow Templates for MCP Integration

This folder contains ready-to-deploy Logic Apps workflows that integrate your Azure Cost Management solution with AI Foundry agents through the Model Context Protocol (MCP).

## 📁 Available Workflows

### 1. Orphaned Resources Agent Trigger
**File**: [`orphaned-resources-agent-trigger.json`](orphaned-resources-agent-trigger.json)

**Purpose**: Complete workflow that triggers AI Foundry agents to analyze orphaned resources and return cost analysis.

**Features**:
- ✅ **HTTP Trigger**: Accepts REST API calls with resource analysis parameters
- 🤖 **Agent Integration**: Creates thread and runs AI Foundry agent 
- ⏳ **Polling Logic**: Waits for agent completion with timeout protection
- 📊 **Response Handling**: Returns structured cost analysis results
- 🔄 **Resource Type Support**: Public IPs, Disks, Network Interfaces, VMs

**Flexible Input Schema** - All fields are optional with intelligent defaults:

**Example 1 - Basic Orphaned Resources Analysis**:
```json
{
  "analysis_type": "orphaned_resources",
  "resource_types": ["Microsoft.Network/publicIPAddresses", "Microsoft.Compute/disks"],
  "start_date": "2024-10-01", 
  "end_date": "2024-11-01",
  "subscription_id": "12345678-1234-1234-1234-123456789012"
}
```

**Example 2 - Custom Analysis with Prompt**:
```json
{
  "custom_prompt": "Find all virtual machines that haven't been accessed in 30 days and calculate potential savings",
  "subscription_id": "12345678-1234-1234-1234-123456789012",
  "include_recommendations": true,
  "output_format": "detailed"
}
```

**Example 3 - Multi-Subscription Cost Review**:
```json
{
  "analysis_type": "cost_optimization",
  "start_date": "2024-11-01",
  "end_date": "2024-11-09",
  "output_format": "summary"
}
```

**Supported Analysis Types**:
- `orphaned_resources` - Find unused/unattached resources (default)
- `cost_optimization` - Identify cost savings opportunities
- `security_review` - Security configuration analysis
- `compliance_check` - Compliance and governance review

**Common Resource Types**:
- `Microsoft.Network/publicIPAddresses` - Public IP addresses
- `Microsoft.Compute/disks` - Managed disks and snapshots
- `Microsoft.Network/networkInterfaces` - Network interfaces
- `Microsoft.Compute/virtualMachines` - Virtual machines
- `Microsoft.Storage/storageAccounts` - Storage accounts
- `Microsoft.Network/networkSecurityGroups` - Network security groups

## 🚀 Quick Deployment Guide

### Step 1: Prepare Your Environment

```powershell
# Set your deployment variables
$resourceGroup = "YOUR-RESOURCE-GROUP"
$logicAppName = "logicapp-mcp-costanalyzer"
$aiFoundryEndpoint = "YOUR-AI-FOUNDRY-ENDPOINT.services.ai.azure.com"
$aiProjectName = "YOUR-PROJECT-NAME"
$agentId = "YOUR-AGENT-ID"

# Verify AI Foundry agent ID
az rest --method GET \
  --url "https://$aiFoundryEndpoint/api/projects/$aiProjectName/assistants?api-version=2025-05-01" \
  --headers "Content-Type=application/json" \
  --resource "https://ai.azure.com"
```

### Step 2: Customize the Workflow Template

1. **Download the template**: Save `orphaned-resources-agent-trigger.json` locally
2. **Replace placeholders**:
   - `YOUR-AGENT-ID-HERE` → Your actual AI Foundry agent ID
   - `YOUR-AI-FOUNDRY-ENDPOINT` → Your AI Foundry service endpoint  
   - `YOUR-PROJECT-NAME` → Your AI Foundry project name

```powershell
# Use PowerShell to replace placeholders
$template = Get-Content "orphaned-resources-agent-trigger.json" -Raw
$template = $template.Replace("YOUR-AGENT-ID-HERE", $agentId)
$template = $template.Replace("YOUR-AI-FOUNDRY-ENDPOINT", $aiFoundryEndpoint.Split('.')[0])
$template = $template.Replace("YOUR-PROJECT-NAME", $aiProjectName)
$template | Set-Content "orphaned-resources-configured.json"
```

### Step 3: Deploy to Logic Apps

```powershell
# Create the Logic App workflow
az logicapp workflow create \
  --resource-group $resourceGroup \
  --name $logicAppName \
  --workflow-name "orphaned-resources-analyzer" \
  --definition @orphaned-resources-configured.json

# Get the trigger URL
$triggerUrl = az logicapp workflow show \
  --resource-group $resourceGroup \
  --name $logicAppName \
  --workflow-name "orphaned-resources-analyzer" \
  --query "accessEndpoint" -o tsv

Write-Host "Workflow deployed successfully!"
Write-Host "Trigger URL: $triggerUrl"
```

### Step 4: Configure Azure Agent Service Connection

The workflow uses the `azureagentservice` connection. You need to create this API connection:

```powershell
# Create Azure Agent Service connection
az resource create \
  --resource-group $resourceGroup \
  --resource-type "Microsoft.Web/connections" \
  --name "azureagentservice" \
  --properties '{
    "displayName": "Azure Agent Service",
    "api": {
      "id": "/subscriptions/YOUR-SUBSCRIPTION-ID/providers/Microsoft.Web/locations/YOUR-LOCATION/managedApis/azureagentservice"
    },
    "parameterValues": {
      "endpoint": "https://YOUR-AI-FOUNDRY-ENDPOINT"
    }
  }'
```

## 🧪 Testing Your Deployment

### Test 1: Orphaned Resources Analysis

```powershell
# Test with specific resource types and date range
$body = @{
    analysis_type = "orphaned_resources"
    resource_types = @("Microsoft.Network/publicIPAddresses", "Microsoft.Compute/disks")
    start_date = "2024-11-01"
    end_date = "2024-11-09" 
    subscription_id = "12345678-1234-1234-1234-123456789012"
    output_format = "detailed"
} | ConvertTo-Json -Depth 3

$response = Invoke-RestMethod -Uri $triggerUrl -Method POST -Body $body -ContentType "application/json"
Write-Host "Analysis Results:"
$response | ConvertTo-Json -Depth 5
```

**Expected Response Structure**:
```json
{
  "request_id": "08585728936810297538968489619CU00",
  "timestamp": "2024-11-09T10:30:00Z",
  "analysis_type": "orphaned_resources",
  "subscription_analyzed": "12345678-1234-1234-1234-123456789012",
  "date_range": {
    "start": "2024-11-01",
    "end": "2024-11-09"
  },
  "agent_response": "Found 3 orphaned public IP addresses costing $15.40/month and 7 unattached disks with $87.50/month potential savings...",
  "execution_time_seconds": 45
}
```

### Test 2: Custom Analysis with Prompt

```powershell
# Test with custom prompt for specific analysis
$body = @{
    custom_prompt = "Find all virtual machines that haven't been accessed in 30+ days and calculate the potential monthly savings from deallocation or deletion. Include rightsizing recommendations."
    subscription_id = "12345678-1234-1234-1234-123456789012"
    include_recommendations = $true
    output_format = "detailed"
} | ConvertTo-Json

Write-Host "Testing custom analysis prompt..."
$response = Invoke-RestMethod -Uri $triggerUrl -Method POST -Body $body -ContentType "application/json"
Write-Host "Custom Analysis Results:"
$response | ConvertTo-Json -Depth 5
```

### Test 3: Multi-Subscription Cost Optimization

```powershell
# Test cross-subscription analysis (no subscription_id = analyze all accessible)
$body = @{
    analysis_type = "cost_optimization"
    start_date = "2024-11-01"
    end_date = "2024-11-09"
    include_recommendations = $true
    output_format = "summary"
} | ConvertTo-Json

Write-Host "Testing multi-subscription cost optimization..."
$response = Invoke-RestMethod -Uri $triggerUrl -Method POST -Body $body -ContentType "application/json"
Write-Host "Multi-Subscription Results:"
$response | ConvertTo-Json -Depth 5
```

### Test 4: Security and Compliance Review

```powershell
# Test security-focused analysis
$body = @{
    analysis_type = "security_review"
    resource_types = @("Microsoft.Network/networkSecurityGroups", "Microsoft.Storage/storageAccounts")
    subscription_id = "12345678-1234-1234-1234-123456789012"
    output_format = "detailed"
} | ConvertTo-Json -Depth 3

Write-Host "Testing security review..."
$response = Invoke-RestMethod -Uri $triggerUrl -Method POST -Body $body -ContentType "application/json"
Write-Host "Security Analysis Results:"
$response | ConvertTo-Json -Depth 5
```

## 🔧 Customization Options

### Modify Analysis Prompt
Edit the `BuildAnalyzeBody` action to customize how the agent analyzes resources:

```javascript
// Current logic builds dynamic prompts based on resource type
// Customize the concat() function to change analysis focus
concat(
  'Analyze my orphaned ', 
  [resource-type-logic],
  ' and provide detailed cost savings recommendations including:',
  ' 1. Total cost impact',
  ' 2. Cleanup recommendations', 
  ' 3. Prevention strategies'
)
```

### Add Response Formatting
Modify the `Response` action to format agent responses:

```json
{
  "type": "Response",
  "kind": "Http", 
  "inputs": {
    "statusCode": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "analysis_date": "@utcNow()",
      "resource_type": "@triggerBody()?['resource_types']",
      "agent_response": "@outputs('Compose')",
      "execution_time": "@formatDateTime(utcNow(), 'yyyy-MM-dd HH:mm:ss')"
    }
  }
}
```

### Add Error Handling
Insert error handling actions after key steps:

```json
{
  "Scope_TryCatch": {
    "type": "Scope",
    "actions": {
      // ... existing actions
    },
    "runAfter": {},
    "trackedProperties": {
      "operation": "orphaned-resources-analysis"
    }
  },
  "Catch_Errors": {
    "type": "Scope", 
    "actions": {
      "Error_Response": {
        "type": "Response",
        "inputs": {
          "statusCode": 500,
          "body": {
            "error": "Analysis failed",
            "details": "@result('Scope_TryCatch')"
          }
        }
      }
    },
    "runAfter": {
      "Scope_TryCatch": ["Failed", "Skipped", "TimedOut"]
    }
  }
}
```

## 📋 Workflow Architecture

```
HTTP Request → Build Query → Create Thread → Create Agent Run → Poll Status → Get Messages → Return Response
                    ↓              ↓              ↓              ↓             ↓             ↓
              Dynamic Prompt   AI Foundry    Start Analysis   Wait Loop    Extract Result  Format Output
```

**Key Components**:
1. **BuildAnalyzeBody**: Creates dynamic prompts based on resource type
2. **BuildThreadBody**: Formats message for AI agent thread
3. **Create_Thread**: Initializes new conversation thread  
4. **Create_Run**: Starts agent execution with your assistant
5. **Until Loop**: Polls agent status until completion (max 5 minutes)
6. **List_Messages**: Retrieves agent response
7. **Compose**: Extracts text response from agent output

## 🛡️ Security Considerations

- **Managed Identity**: Workflow uses MSI for AI Foundry authentication
- **RBAC**: Ensure Logic App has `Azure AI Project Manager` role
- **API Versions**: Uses latest stable API version (2025-05-01)
- **Timeout Protection**: 5-minute timeout prevents indefinite runs
- **Input Validation**: Schema validation on trigger inputs

## 📚 Next Steps

1. **Deploy the workflow** using the steps above
2. **Test with sample data** to verify functionality  
3. **Integrate with monitoring** using Azure Monitor
4. **Add to automation** by calling from other systems
5. **Scale horizontally** by deploying multiple resource-specific workflows

## 📖 Additional Resources

- **[Main MCP Setup Guide](../README.md)** - Complete configuration including authentication and Logic App setup
- **[Set up Standard logic apps as remote MCP servers](https://learn.microsoft.com/en-us/azure/logic-apps/set-up-model-context-protocol-server-standard)** - Official Microsoft documentation for MCP server configuration
- **[Trigger an agent by using Logic Apps](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/triggers)** - Microsoft guide for AI Foundry agent integration with Logic Apps