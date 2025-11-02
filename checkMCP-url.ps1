# Simple Azure POST Request

$uri = "https://management.azure.com/subscriptions/a3e5fcf7-ef49-45ae-ba82-6e490fe388af/resourceGroups/rg-ai/providers/Microsoft.Web/sites/lamcpserver/hostruntime/runtime/webhooks/workflow/api/management/listMcpServerUrl?api-version=2021-02-01"

# Get Azure token and make POST request
$token = [Microsoft.Azure.Commands.Common.Authentication.AzureSession]::Instance.AuthenticationFactory.Authenticate((Get-AzContext).Account, (Get-AzContext).Environment, (Get-AzContext).Tenant.Id, $null, "Never", $null, "https://management.azure.com/").AccessToken

$headers = @{ "Authorization" = "Bearer $token" }

$response = Invoke-RestMethod -Uri $uri -Method POST -Headers $headers

$response