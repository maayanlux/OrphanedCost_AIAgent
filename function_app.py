import azure.functions as func
import logging
import json
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.advisor import AdvisorManagementClient
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.monitor.query import LogsQueryClient
import os

app = func.FunctionApp()

# Initialize clients globally
credential = DefaultAzureCredential()

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    Decorator for implementing exponential backoff retry logic for Azure API calls
    Handles 429 (Too Many Requests) and transient errors
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except HttpResponseError as e:
                    last_exception = e
                    
                    # Handle rate limiting (429) and server errors (5xx)
                    if e.status_code in [429, 500, 502, 503, 504]:
                        if attempt < max_retries:
                            # Calculate exponential backoff with jitter
                            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                            
                            logging.warning(
                                f"API call failed (attempt {attempt + 1}/{max_retries + 1}): "
                                f"HTTP {e.status_code} - {e.message}. Retrying in {delay:.2f}s"
                            )
                            
                            time.sleep(delay)
                            continue
                        else:
                            logging.error(
                                f"Max retries ({max_retries}) exceeded for API call. "
                                f"Final error: HTTP {e.status_code} - {e.message}"
                            )
                    else:
                        # Non-retryable error, fail immediately
                        logging.error(f"Non-retryable error: HTTP {e.status_code} - {e.message}")
                        break
                        
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logging.warning(f"Unexpected error (attempt {attempt + 1}): {e}. Retrying in {delay:.2f}s")
                        time.sleep(delay)
                    else:
                        logging.error(f"Max retries exceeded. Final error: {e}")
                        break
            
            # Re-raise the last exception if all retries failed
            raise last_exception
            
        return wrapper
    return decorator

class OrphanedResourceAnalyzer:
    """Analyzes orphaned resources across Azure subscriptions (single or tenant-wide)"""
    
    def __init__(self, subscription_id: Optional[str] = None):
        self.subscription_id = subscription_id
        self.credential = credential
        self.subscription_client = SubscriptionClient(credential)
        
        # Initialize subscription-specific clients only if subscription_id is provided
        if subscription_id:
            self.compute_client = ComputeManagementClient(credential, subscription_id)
            self.network_client = NetworkManagementClient(credential, subscription_id)
            self.advisor_client = AdvisorManagementClient(credential, subscription_id)
            self.resource_client = ResourceManagementClient(credential, subscription_id)
        else:
            # These will be initialized per subscription during tenant-wide analysis
            self.compute_client = None
            self.network_client = None
            self.advisor_client = None
            self.resource_client = None
    
    def get_accessible_subscriptions(self) -> List[Dict[str, str]]:
        """Get all subscriptions accessible to the current credential"""
        subscriptions = []
        try:
            for subscription in self.subscription_client.subscriptions.list():
                subscriptions.append({
                    'subscription_id': subscription.subscription_id,
                    'display_name': subscription.display_name,
                    'state': subscription.state,
                    'tenant_id': subscription.tenant_id if hasattr(subscription, 'tenant_id') else 'Unknown'
                })
            logging.info(f"Found {len(subscriptions)} accessible subscriptions")
        except Exception as e:
            logging.error(f"Error fetching subscriptions: {str(e)}")
        
        return subscriptions
    
    def _initialize_clients_for_subscription(self, subscription_id: str):
        """Initialize Azure clients for a specific subscription"""
        try:
            self.compute_client = ComputeManagementClient(self.credential, subscription_id)
            self.network_client = NetworkManagementClient(self.credential, subscription_id)
            self.advisor_client = AdvisorManagementClient(self.credential, subscription_id)
            self.resource_client = ResourceManagementClient(self.credential, subscription_id)
            return True
        except Exception as e:
            logging.error(f"Error initializing clients for subscription {subscription_id}: {str(e)}")
            return False
        
    def get_orphaned_public_ips(self, subscription_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find unattached public IP addresses"""
        orphaned_ips = []
        
        # Use the provided subscription_id or fall back to instance subscription_id
        current_subscription_id = subscription_id or self.subscription_id
        
        for ip in self.network_client.public_ip_addresses.list_all():
            # Check all possible attachment types
            is_attached = (
                ip.ip_configuration is not None or  # Attached to Network Interface
                (hasattr(ip, 'nat_gateway') and ip.nat_gateway is not None) or  # Attached to NAT Gateway
                (hasattr(ip, 'load_balancer_frontend_ip_configurations') and 
                 ip.load_balancer_frontend_ip_configurations)  # Attached to Load Balancer
            )
            
            if not is_attached:
                orphaned_ips.append({
                    'resource_type': 'Public IP',
                    'resource_id': ip.id,
                    'name': ip.name,
                    'location': ip.location,
                    'resource_group': ip.id.split('/')[4],
                    'subscription_id': current_subscription_id,
                    'sku': ip.sku.name if ip.sku else 'Basic',
                    'allocation_method': ip.public_ip_allocation_method,
                    'tags': ip.tags or {}
                })
        
        return orphaned_ips
    
    def get_orphaned_disks(self, subscription_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find unattached managed disks"""
        orphaned_disks = []
        
        # Use the provided subscription_id or fall back to instance subscription_id
        current_subscription_id = subscription_id or self.subscription_id
        
        for disk in self.compute_client.disks.list():
            if disk.disk_state == 'Unattached':
                orphaned_disks.append({
                    'resource_type': 'Managed Disk',
                    'resource_id': disk.id,
                    'name': disk.name,
                    'location': disk.location,
                    'resource_group': disk.id.split('/')[4],
                    'subscription_id': current_subscription_id,
                    'disk_size_gb': disk.disk_size_gb,
                    'sku': disk.sku.name if disk.sku else 'Unknown',
                    'tags': disk.tags or {}
                })
        
        return orphaned_disks
    
    def get_orphaned_snapshots(self, subscription_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find old snapshots (older than specified days)"""
        snapshots = []
        
        # Use the provided subscription_id or fall back to instance subscription_id
        current_subscription_id = subscription_id or self.subscription_id
        
        for snapshot in self.compute_client.snapshots.list():
            age_days = (datetime.now(snapshot.time_created.tzinfo) - snapshot.time_created).days
            snapshots.append({
                'resource_type': 'Snapshot',
                'resource_id': snapshot.id,
                'name': snapshot.name,
                'location': snapshot.location,
                'resource_group': snapshot.id.split('/')[4],
                'subscription_id': current_subscription_id,
                'disk_size_gb': snapshot.disk_size_gb,
                'age_days': age_days,
                'created_date': snapshot.time_created.isoformat(),
                'tags': snapshot.tags or {}
            })
        
        return snapshots
    
    def get_orphaned_nics(self, subscription_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find unattached network interfaces"""
        orphaned_nics = []
        
        # Use the provided subscription_id or fall back to instance subscription_id
        current_subscription_id = subscription_id or self.subscription_id
        
        for nic in self.network_client.network_interfaces.list_all():
            if nic.virtual_machine is None:
                orphaned_nics.append({
                    'resource_type': 'Network Interface',
                    'resource_id': nic.id,
                    'name': nic.name,
                    'location': nic.location,
                    'resource_group': nic.id.split('/')[4],
                    'subscription_id': current_subscription_id,
                    'tags': nic.tags or {}
                })
        
        return orphaned_nics
    
    def get_vms_without_ahb(self, subscription_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find VMs not using Azure Hybrid Benefit for eligible OS types only"""
        vms_without_ahb = []
        
        # Use the provided subscription_id or fall back to instance subscription_id
        current_subscription_id = subscription_id or self.subscription_id
        
        for vm in self.compute_client.virtual_machines.list_all():
            # Check if VM is eligible for Azure Hybrid Benefit
            if not self._is_ahb_eligible(vm):
                continue
                
            license_type = vm.license_type
            if license_type is None or license_type == '':
                # Get OS details for better reporting
                os_info = self._get_vm_os_info(vm)
                
                vms_without_ahb.append({
                    'resource_type': 'VM without AHB',
                    'resource_id': vm.id,
                    'name': vm.name,
                    'location': vm.location,
                    'resource_group': vm.id.split('/')[4],
                    'subscription_id': current_subscription_id,
                    'vm_size': vm.hardware_profile.vm_size,
                    'os_type': vm.storage_profile.os_disk.os_type,
                    'os_info': os_info,
                    'tags': vm.tags or {}
                })
        
        return vms_without_ahb
    
    def _is_ahb_eligible(self, vm) -> bool:
        """Check if VM is eligible for Azure Hybrid Benefit"""
        try:
            # Get OS information
            if not vm.storage_profile or not vm.storage_profile.os_disk:
                return False
            
            os_type = vm.storage_profile.os_disk.os_type
            
            # Check Windows Server eligibility
            if os_type and os_type.lower() == 'windows':
                # Check if it's Windows Server (not client OS)
                if vm.storage_profile.image_reference:
                    offer = getattr(vm.storage_profile.image_reference, 'offer', '').lower()
                    sku = getattr(vm.storage_profile.image_reference, 'sku', '').lower()
                    
                    # Windows Server offers
                    windows_server_offers = [
                        'windowsserver', 'windows-server', 'windowsserver-gen2',
                        'windows_server', 'microsoftwindowsserver'
                    ]
                    
                    # Exclude Windows client SKUs
                    windows_client_skus = [
                        'windows-10', 'windows-11', 'win10', 'win11',
                        'rs5-pro', 'rs5-ent', '19h1-pro', '19h1-ent',
                        '20h1-pro', '20h2-pro', '21h1-pro'
                    ]
                    
                    # Check if it's Windows Server
                    is_server = any(server_offer in offer for server_offer in windows_server_offers)
                    is_client = any(client_sku in sku for client_sku in windows_client_skus)
                    
                    return is_server and not is_client
                else:
                    # If no image reference, assume it might be eligible (custom images)
                    return True
            
            # Check Linux eligibility (RHEL and SLES only)
            elif os_type and os_type.lower() == 'linux':
                if vm.storage_profile.image_reference:
                    offer = getattr(vm.storage_profile.image_reference, 'offer', '').lower()
                    publisher = getattr(vm.storage_profile.image_reference, 'publisher', '').lower()
                    
                    # RHEL eligibility
                    rhel_offers = ['rhel', 'rhel-byos', 'rhel-ha', 'rhel-sap-ha']
                    rhel_publishers = ['redhat', 'red-hat']
                    
                    # SLES eligibility  
                    sles_offers = ['sles', 'sles-byos', 'sles-sap', 'sles-for-sap']
                    sles_publishers = ['suse', 'suse-byos']
                    
                    is_rhel = (any(rhel_offer in offer for rhel_offer in rhel_offers) or 
                              any(rhel_pub in publisher for rhel_pub in rhel_publishers))
                    
                    is_sles = (any(sles_offer in offer for sles_offer in sles_offers) or
                              any(sles_pub in publisher for sles_pub in sles_publishers))
                    
                    return is_rhel or is_sles
            
            return False
            
        except Exception as e:
            logging.warning(f"Error checking AHB eligibility for VM {vm.name}: {str(e)}")
            return False
    
    def _get_vm_os_info(self, vm) -> str:
        """Get detailed OS information for reporting"""
        try:
            if vm.storage_profile and vm.storage_profile.image_reference:
                publisher = getattr(vm.storage_profile.image_reference, 'publisher', 'Unknown')
                offer = getattr(vm.storage_profile.image_reference, 'offer', 'Unknown')
                sku = getattr(vm.storage_profile.image_reference, 'sku', 'Unknown')
                return f"{publisher}/{offer}/{sku}"
            else:
                return "Custom/Unknown Image"
        except Exception:
            return "Unknown"
    
    def get_advisor_cost_recommendations(self, subscription_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get Azure Advisor cost optimization recommendations"""
        recommendations = []
        
        # Use the provided subscription_id or fall back to instance subscription_id
        current_subscription_id = subscription_id or self.subscription_id
        
        try:
            advisor_recs = self.advisor_client.recommendations.list(
                filter="Category eq 'Cost'"
            )
            
            for rec in advisor_recs:
                recommendations.append({
                    'resource_type': 'Advisor Recommendation',
                    'recommendation_id': rec.id,
                    'name': rec.name,
                    'category': rec.category,
                    'impact': rec.impact,
                    'risk': rec.risk,
                    'short_description': rec.short_description.problem if rec.short_description else '',
                    'solution': rec.short_description.solution if rec.short_description else '',
                    'impacted_resource': rec.impacted_value,
                    'resource_id': rec.resource_metadata.resource_id if rec.resource_metadata else '',
                    'subscription_id': current_subscription_id,
                    'potential_savings': self._extract_savings(rec.extended_properties) if rec.extended_properties else 0,
                    'last_updated': rec.last_updated.isoformat() if rec.last_updated else ''
                })
        except Exception as e:
            logging.error(f"Error fetching Advisor recommendations for subscription {current_subscription_id}: {str(e)}")
        
        return recommendations
    
    def _extract_savings(self, extended_properties: Dict) -> float:
        """Extract potential savings from extended properties"""
        if not extended_properties:
            return 0.0
        
        # Different recommendation types have different fields
        savings_keys = ['annualSavingsAmount', 'savingsAmount', 'estimatedSavings']
        for key in savings_keys:
            if key in extended_properties:
                try:
                    return float(extended_properties[key])
                except (ValueError, TypeError):
                    pass
        return 0.0
    

    
    def analyze_all(self) -> Dict[str, Any]:
        """Analyze and identify all orphaned resources (single subscription or tenant-wide)"""
        
        results = {
            'analysis_date': datetime.now().isoformat(),
            'resources': [],
            'subscriptions_analyzed': []
        }
        
        if self.subscription_id:
            # Single subscription analysis
            results['subscription_id'] = self.subscription_id
            results['analysis_scope'] = 'single_subscription'
            
            # Collect all orphaned resources for the specific subscription
            all_resources = []
            all_resources.extend(self.get_orphaned_public_ips())
            all_resources.extend(self.get_orphaned_disks())
            all_resources.extend(self.get_orphaned_snapshots())
            all_resources.extend(self.get_orphaned_nics())
            all_resources.extend(self.get_vms_without_ahb())
            all_resources.extend(self.get_advisor_cost_recommendations())
            
            results['resources'] = all_resources
            results['subscriptions_analyzed'] = [self.subscription_id]
            
        else:
            # Tenant-wide analysis across all accessible subscriptions
            results['analysis_scope'] = 'tenant_wide'
            
            subscriptions = self.get_accessible_subscriptions()
            all_resources = []
            successful_subscriptions = []
            
            logging.info(f"Starting tenant-wide analysis across {len(subscriptions)} subscriptions")
            
            for sub_info in subscriptions:
                subscription_id = sub_info['subscription_id']
                subscription_name = sub_info['display_name']
                
                logging.info(f"Analyzing subscription: {subscription_name} ({subscription_id})")
                
                try:
                    # Initialize clients for this subscription
                    if self._initialize_clients_for_subscription(subscription_id):
                        # Collect orphaned resources for this subscription
                        sub_resources = []
                        sub_resources.extend(self.get_orphaned_public_ips(subscription_id))
                        sub_resources.extend(self.get_orphaned_disks(subscription_id))
                        sub_resources.extend(self.get_orphaned_snapshots(subscription_id))
                        sub_resources.extend(self.get_orphaned_nics(subscription_id))
                        sub_resources.extend(self.get_vms_without_ahb(subscription_id))
                        sub_resources.extend(self.get_advisor_cost_recommendations(subscription_id))
                        
                        # Add subscription display name to each resource
                        for resource in sub_resources:
                            resource['subscription_name'] = subscription_name
                        
                        all_resources.extend(sub_resources)
                        successful_subscriptions.append({
                            'subscription_id': subscription_id,
                            'subscription_name': subscription_name,
                            'resources_found': len(sub_resources)
                        })
                        
                        logging.info(f"Found {len(sub_resources)} orphaned resources in {subscription_name}")
                    else:
                        logging.warning(f"Failed to initialize clients for subscription {subscription_id}")
                        
                except Exception as e:
                    logging.error(f"Error analyzing subscription {subscription_id} ({subscription_name}): {str(e)}")
            
            results['resources'] = all_resources
            results['subscriptions_analyzed'] = successful_subscriptions
            results['total_subscriptions'] = len(subscriptions)
            results['successful_subscriptions'] = len(successful_subscriptions)
            
            logging.info(f"Tenant-wide analysis completed: {len(all_resources)} total resources across {len(successful_subscriptions)} subscriptions")
        
        results['summary'] = self._generate_summary(results['resources'])
        
        return results
    
    def _generate_summary(self, resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for orphaned resources"""
        summary = {
            'total_resources': len(resources),
            'by_type': {},
            'total_potential_savings': 0.0
        }
        
        for resource in resources:
            res_type = resource.get('resource_type', 'Unknown')
            summary['by_type'][res_type] = summary['by_type'].get(res_type, 0) + 1
            
            # Only include potential savings from advisor recommendations
            if res_type == 'Advisor Recommendation':
                summary['total_potential_savings'] += resource.get('potential_savings', 0.0)
        
        return summary


def query_resources(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main query function for identifying orphaned resources (no cost analysis)
    
    Parameters:
    - subscription_id: Azure subscription ID (optional - if not provided, analyzes all subscriptions in tenant)
    - resource_types: List of resource types to query (optional)
    - resource_group: Filter by resource group (optional)
    - location: Filter by location (optional)
    - subscription_name: Filter by subscription name (optional, only for tenant-wide analysis)
    """
    
    subscription_id = query_params.get('subscription_id')
    
    # Initialize analyzer - if no subscription_id provided, it will analyze all subscriptions
    analyzer = OrphanedResourceAnalyzer(subscription_id)
    
    # Get all orphaned resources (single subscription or tenant-wide)
    results = analyzer.analyze_all()
    
    # Apply filters
    filtered_resources = results['resources']
    
    if query_params.get('resource_types'):
        resource_types = query_params['resource_types']
        filtered_resources = [r for r in filtered_resources if r['resource_type'] in resource_types]
    
    if query_params.get('resource_group'):
        rg = query_params['resource_group'].lower()
        filtered_resources = [r for r in filtered_resources if r.get('resource_group', '').lower() == rg]
    
    if query_params.get('location'):
        loc = query_params['location'].lower()
        filtered_resources = [r for r in filtered_resources if r.get('location', '').lower() == loc]
    
    if query_params.get('subscription_name'):
        sub_name = query_params['subscription_name'].lower()
        filtered_resources = [r for r in filtered_resources if r.get('subscription_name', '').lower() == sub_name]
    
    results['resources'] = filtered_resources
    results['summary'] = analyzer._generate_summary(filtered_resources)
    
    return results


@app.function_name(name="OrphanedResourcesAnalyzer")
@app.route(route="analyze", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def analyze_orphaned_resources(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger function for AI Foundry Agent
    """
    logging.info('Orphaned Resources Analyzer function triggered')
    
    try:
        req_body = req.get_json()
        logging.info(f"Request body: {json.dumps(req_body)}")
        
        results = query_resources(req_body)
        
        return func.HttpResponse(
            body=json.dumps(results, indent=2),
            mimetype="application/json",
            status_code=200
        )
        
    except ValueError as e:
        logging.error(f"Invalid request: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({'error': f'Invalid request: {str(e)}'}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({'error': str(e)}),
            mimetype="application/json",
            status_code=500
        )


# Example query for testing
@app.function_name(name="GetOrphanedResourcesExample")
@app.route(route="example", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def example_query(req: func.HttpRequest) -> func.HttpResponse:
    """Example endpoint showing orphaned resources query structure"""
    
    examples = {
        "single_subscription_analysis": {
            "subscription_id": "your-subscription-id",
            "resource_types": ["Public IP", "Managed Disk", "Snapshot", "Network Interface"],
            "resource_group": "my-resource-group",
            "location": "eastus"
        },
        "tenant_wide_analysis": {
            "resource_types": ["Public IP", "Managed Disk"],
            "location": "eastus",
            "subscription_name": "Production Subscription"
        },
        "all_resources_all_subscriptions": {
            "description": "Analyze all resource types across all subscriptions in the tenant"
        }
    }
    
    return func.HttpResponse(
        body=json.dumps(examples, indent=2),
        mimetype="application/json",
        status_code=200
    )


##########Cost#########

@app.function_name(name="CostAnalysisDirectQuery")
@app.route(route="cost-analysis", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def cost_analysis_direct_query(req: func.HttpRequest) -> func.HttpResponse:
    """
    Direct Azure Cost Management and Billing API query function
    Provides detailed cost analysis for resources, resource groups, and subscriptions
    """
    logging.info('Cost Analysis Direct Query function triggered')
    
    try:
        req_body = req.get_json()
        logging.info(f"Request body: {json.dumps(req_body)}")
        
        results = query_cost_management_direct(req_body)
        
        return func.HttpResponse(
            body=json.dumps(results, indent=2),
            mimetype="application/json",
            status_code=200
        )
        
    except ValueError as e:
        logging.error(f"Invalid request: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({'error': f'Invalid request: {str(e)}'}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({'error': str(e)}),
            mimetype="application/json",
            status_code=500
        )


class CostManagementAnalyzer:
    """Direct Azure Cost Management and Billing API analyzer"""
    
    def __init__(self, subscription_id: str):
        self.subscription_id = subscription_id
        self.credential = credential
        
        # Initialize Cost Management Client with custom headers to avoid 429 rate limiting
        self.cost_client = CostManagementClient(credential)
        
        # Add custom ClientType header to bypass rate limiting (as per Microsoft documentation)
        # https://learn.microsoft.com/en-us/answers/questions/1340993/exception-429-too-many-requests-for-azure-cost-man
        if hasattr(self.cost_client, '_client') and hasattr(self.cost_client._client, '_config'):
            # Add custom header to all requests
            custom_headers = getattr(self.cost_client._client._config, 'headers', {})
            custom_headers['ClientType'] = 'AwesomeType'
            self.cost_client._client._config.headers = custom_headers
            logging.info("Added ClientType header to Cost Management client to avoid rate limiting")
        
        self.resource_client = ResourceManagementClient(credential, subscription_id)
    
    def get_subscription_costs(self, start_date: datetime, end_date: datetime, 
                             granularity: str = "Daily") -> Dict[str, Any]:
        """Get total subscription costs with breakdown"""
        try:
            scope = f"/subscriptions/{self.subscription_id}"
            
            query_body = {
                "type": "ActualCost",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat()
                },
                "dataset": {
                    "granularity": granularity,
                    "aggregation": {
                        "totalCost": {
                            "name": "Cost",
                            "function": "Sum"
                        },
                        "totalCostUSD": {
                            "name": "CostUSD", 
                            "function": "Sum"
                        }
                    },
                    "grouping": [
                        {
                            "type": "Dimension",
                            "name": "ServiceName"
                        },
                        {
                            "type": "Dimension", 
                            "name": "ResourceLocation"
                        }
                    ]
                }
            }
            
            result = self.cost_client.query.usage(scope, query_body)
            
            return self._process_cost_result(result, "subscription")
            
        except Exception as e:
            logging.error(f"Error fetching subscription costs: {str(e)}")
            return {"error": str(e)}
    
    def get_resource_group_costs(self, resource_group: str, start_date: datetime, 
                               end_date: datetime, granularity: str = "Daily") -> Dict[str, Any]:
        """Get costs for a specific resource group"""
        try:
            scope = f"/subscriptions/{self.subscription_id}/resourceGroups/{resource_group}"
            
            query_body = {
                "type": "ActualCost",
                "timeframe": "Custom", 
                "timePeriod": {
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat()
                },
                "dataset": {
                    "granularity": granularity,
                    "aggregation": {
                        "totalCost": {
                            "name": "Cost",
                            "function": "Sum"
                        }
                    },
                    "grouping": [
                        {
                            "type": "Dimension",
                            "name": "ResourceId"
                        },
                        {
                            "type": "Dimension",
                            "name": "ServiceName"
                        }
                    ]
                }
            }
            
            result = self.cost_client.query.usage(scope, query_body)
            
            return self._process_cost_result(result, "resource_group", resource_group)
            
        except Exception as e:
            logging.error(f"Error fetching resource group costs: {str(e)}")
            return {"error": str(e)}
    
    def get_resource_costs_by_service(self, service_names: List[str], start_date: datetime,
                                    end_date: datetime) -> Dict[str, Any]:
        """Get costs filtered by Azure service names"""
        try:
            scope = f"/subscriptions/{self.subscription_id}"
            
            query_body = {
                "type": "ActualCost",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat()
                },
                "dataset": {
                    "granularity": "Daily",
                    "aggregation": {
                        "totalCost": {
                            "name": "Cost",
                            "function": "Sum"
                        }
                    },
                    "filter": {
                        "dimensions": {
                            "name": "ServiceName",
                            "operator": "In",
                            "values": service_names
                        }
                    },
                    "grouping": [
                        {
                            "type": "Dimension",
                            "name": "ResourceId"
                        },
                        {
                            "type": "Dimension",
                            "name": "ServiceName"
                        },
                        {
                            "type": "Dimension",
                            "name": "ResourceLocation"
                        }
                    ]
                }
            }
            
            result = self.cost_client.query.usage(scope, query_body)
            
            return self._process_cost_result(result, "service_filter", service_names)
            
        except Exception as e:
            logging.error(f"Error fetching service costs: {str(e)}")
            return {"error": str(e)}
    
    def get_top_cost_resources(self, start_date: datetime, end_date: datetime, 
                             top_n: int = 10) -> Dict[str, Any]:
        """Get top N most expensive resources"""
        try:
            scope = f"/subscriptions/{self.subscription_id}"
            
            query_body = {
                "type": "ActualCost",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat()
                },
                "dataset": {
                    "granularity": "None",
                    "aggregation": {
                        "totalCost": {
                            "name": "Cost",
                            "function": "Sum"
                        }
                    },
                    "grouping": [
                        {
                            "type": "Dimension",
                            "name": "ResourceId"
                        },
                        {
                            "type": "Dimension",
                            "name": "ServiceName"
                        }
                    ],
                    "sorting": [
                        {
                            "direction": "Descending",
                            "name": "Cost"
                        }
                    ]
                },
                "top": top_n
            }
            
            result = self.cost_client.query.usage(scope, query_body)
            
            return self._process_cost_result(result, "top_resources", top_n)
            
        except Exception as e:
            logging.error(f"Error fetching top cost resources: {str(e)}")
            return {"error": str(e)}
    
    def get_budget_analysis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get budget vs actual spending analysis"""
        try:
            # Get actual costs
            actual_costs = self.get_subscription_costs(start_date, end_date, "Monthly")
            
            # Get budgets (if any are configured)
            budgets = []
            try:
                scope = f"/subscriptions/{self.subscription_id}"
                budget_list = list(self.cost_client.budgets.list(scope))
                
                for budget in budget_list:
                    budgets.append({
                        "name": budget.name,
                        "amount": budget.amount,
                        "current_spend": budget.current_spend.amount if budget.current_spend else 0,
                        "forecasted_spend": budget.forecasted_spend.amount if budget.forecasted_spend else 0,
                        "time_grain": budget.time_grain,
                        "category": budget.category
                    })
            except Exception as e:
                logging.warning(f"Could not fetch budgets: {str(e)}")
            
            return {
                "subscription_id": self.subscription_id,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "actual_costs": actual_costs,
                "budgets": budgets,
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error in budget analysis: {str(e)}")
            return {"error": str(e)}
    
    def get_cost_by_location(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get costs broken down by Azure regions"""
        try:
            scope = f"/subscriptions/{self.subscription_id}"
            
            query_body = {
                "type": "ActualCost",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat()
                },
                "dataset": {
                    "granularity": "None",
                    "aggregation": {
                        "totalCost": {
                            "name": "Cost",
                            "function": "Sum"
                        }
                    },
                    "grouping": [
                        {
                            "type": "Dimension",
                            "name": "ResourceLocation"
                        },
                        {
                            "type": "Dimension",
                            "name": "ServiceName"
                        }
                    ],
                    "sorting": [
                        {
                            "direction": "Descending",
                            "name": "Cost"
                        }
                    ]
                }
            }
            
            result = self.cost_client.query.usage(scope, query_body)
            
            return self._process_cost_result(result, "by_location")
            
        except Exception as e:
            logging.error(f"Error fetching costs by location: {str(e)}")
            return {"error": str(e)}
    
    def _process_cost_result(self, result, analysis_type: str, metadata: Any = None) -> Dict[str, Any]:
        """Process cost query results into structured format"""
        processed_result = {
            "subscription_id": self.subscription_id,
            "analysis_type": analysis_type,
            "metadata": metadata,
            "total_cost": 0.0,
            "currency": "USD",
            "rows": [],
            "columns": []
        }
        
        if hasattr(result, 'columns') and result.columns:
            processed_result["columns"] = [col.name for col in result.columns]
        
        if hasattr(result, 'rows') and result.rows:
            total_cost = 0.0
            
            for row in result.rows:
                if row and len(row) > 0:
                    # First column is usually the cost
                    cost = float(row[0]) if row[0] else 0.0
                    total_cost += cost
                    
                    processed_row = {
                        "cost": cost,
                        "data": row[1:] if len(row) > 1 else []
                    }
                    processed_result["rows"].append(processed_row)
            
            processed_result["total_cost"] = total_cost
        
        return processed_result
    
    def get_specific_resources_cost(self, resource_ids: List[str], start_date: datetime,
                                  end_date: datetime) -> Dict[str, Any]:
        """Get costs for specific resource IDs using individual queries with rate limiting"""
        results = {
            "subscription_id": self.subscription_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "resources": [],
            "total_cost": 0.0
        }
        
        logging.info(f"Querying costs for {len(resource_ids)} resources individually to ensure accuracy")
        
        return self._get_individual_resource_costs(resource_ids, start_date, end_date, results)
    
    def _get_individual_resource_costs(self, resource_ids: List[str], start_date: datetime,
                                     end_date: datetime, results: Dict[str, Any]) -> Dict[str, Any]:
        """Primary method: Query each resource individually with aggressive rate limiting and retry logic"""
        logging.warning("Falling back to individual resource queries due to batch query failure")
        
        import time
        
        # Split large resource lists into smaller batches to reduce rate limiting
        batch_size = 3  # Process max 3 resources at a time
        if len(resource_ids) > batch_size:
            logging.info(f"Processing {len(resource_ids)} resources in batches of {batch_size} to avoid rate limits")
        
        # Circuit breaker for consecutive rate limit failures
        consecutive_rate_limits = 0
        max_consecutive_rate_limits = 3
        
        for i, resource_id in enumerate(resource_ids):
            # Add modest delay with ClientType header fix - much reduced delays
            if i > 0:
                # Modest rate limiting with ClientType header: 2s base + 0.5s per resource, max 10s
                delay = min(2.0 + (i * 0.5), 10.0)  
                logging.info(f"Rate limiting delay: {delay:.1f}s before querying resource {i+1}/{len(resource_ids)}")
                time.sleep(delay)
            
            # Retry logic for each individual resource with extended retries for 429
            max_retries = 5  # Increased from 3 to 5
            for attempt in range(max_retries):
                try:
                    scope = f"/subscriptions/{self.subscription_id}"
                    
                    # Use the same QueryDefinition format that works in our tests
                    from azure.mgmt.costmanagement.models import (
                        QueryDefinition, QueryTimePeriod, QueryDataset, 
                        QueryAggregation, QueryFilter, QueryComparisonExpression
                    )
                    
                    query_definition = QueryDefinition(
                        type="ActualCost",
                        timeframe="Custom",
                        time_period=QueryTimePeriod(
                            from_property=start_date,
                            to=end_date
                        ),
                        dataset=QueryDataset(
                            granularity="Daily",
                            aggregation={
                                "totalCost": QueryAggregation(name="Cost", function="Sum")
                            },
                            filter=QueryFilter(
                                dimensions=QueryComparisonExpression(
                                    name="ResourceId",
                                    operator="In",
                                    values=[resource_id]
                                )
                            )
                        )
                    )
                    
                    result = self.cost_client.query.usage(scope, query_definition)
                    
                    resource_cost = 0.0
                    daily_costs = []
                    
                    if hasattr(result, 'rows') and result.rows:
                        for row in result.rows:
                            if row and len(row) > 0:
                                cost = float(row[0]) if row[0] else 0.0
                                resource_cost += cost
                                # Parse date from the second column
                                date_value = row[1] if len(row) > 1 else ""
                                date_str = str(date_value) if date_value else ""
                                daily_costs.append({
                                    "date": date_str,
                                    "cost": cost
                                })
                    
                    results["resources"].append({
                        "resource_id": resource_id,
                        "total_cost": resource_cost,
                        "daily_costs": daily_costs
                    })
                    
                    results["total_cost"] += resource_cost
                    
                    resource_name = resource_id.split('/')[-1] if '/' in resource_id else resource_id
                    if resource_cost > 0:
                        logging.info(f"✅ Resource {i+1}/{len(resource_ids)} ({resource_name}): ${resource_cost:.2f}")
                    else:
                        logging.info(f"⚪ Resource {i+1}/{len(resource_ids)} ({resource_name}): $0.00")
                    
                    # Reset consecutive rate limit counter on success
                    consecutive_rate_limits = 0
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        # Special handling for 429 rate limit errors
                        if "429" in str(e) or "Too many requests" in str(e):
                            consecutive_rate_limits += 1
                            # Much longer delays for rate limit errors
                            retry_delay = min(15.0 * (2 ** attempt), 120.0)  # 15s, 30s, 60s, 120s
                            logging.warning(f"Rate limit hit for {resource_id} (attempt {attempt + 1}/{max_retries}). Waiting {retry_delay:.1f}s before retry...")
                            
                            # Circuit breaker: if too many consecutive rate limits, give up early
                            if consecutive_rate_limits >= max_consecutive_rate_limits:
                                logging.error(f"Circuit breaker activated: {consecutive_rate_limits} consecutive rate limits. Skipping remaining resources to avoid further API throttling.")
                                # Add remaining resources as failed
                                for remaining_resource in resource_ids[i:]:
                                    results["resources"].append({
                                        "resource_id": remaining_resource,
                                        "error": "Skipped due to rate limiting circuit breaker"
                                    })
                                return results
                        else:
                            # Standard exponential backoff for other errors
                            retry_delay = min(5.0 * (2 ** attempt), 30.0)
                            logging.warning(f"Attempt {attempt + 1} failed for {resource_id}: {str(e)}. Retrying in {retry_delay:.1f}s")
                        
                        time.sleep(retry_delay)
                    else:
                        # All retries failed
                        if "429" in str(e) or "Too many requests" in str(e):
                            consecutive_rate_limits += 1
                        
                        logging.error(f"All {max_retries} attempts failed for resource {resource_id}: {str(e)}")
                        results["resources"].append({
                            "resource_id": resource_id,
                            "error": str(e)
                        })
        
        return results


def query_cost_management_direct(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for direct Cost Management API queries
    
    Parameters:
    - subscription_id: Azure subscription ID (required)
    - query_type: Type of query (subscription, resource_group, service, top_resources, budget, location, specific_resources)
    - start_date: Start date in ISO format (required)
    - end_date: End date in ISO format (required)
    - resource_group: Resource group name (for resource_group query)
    - service_names: List of service names (for service query)
    - resource_ids: List of resource IDs (for specific_resources query)
    - top_n: Number of top resources (for top_resources query, default: 10)
    - granularity: Data granularity (Daily, Monthly, None - default: Daily)
    """
    
    subscription_id = query_params.get('subscription_id')
    if not subscription_id:
        return {'error': 'subscription_id is required'}
    
    # Auto-detect query_type if not provided based on parameters
    query_type = query_params.get('query_type')
    if not query_type:
        if query_params.get('resource_ids'):
            query_type = 'specific_resources'
        elif query_params.get('resource_group'):
            query_type = 'resource_group'
        elif query_params.get('service_names'):
            query_type = 'service'
        elif query_params.get('top_n'):
            query_type = 'top_resources'
        else:
            query_type = 'subscription'
    
    # Parse dates - handle automatic "last 30 days" calculation
    try:
        # Check if dates are provided
        if 'start_date' in query_params and 'end_date' in query_params:
            start_date_str = query_params['start_date']
            end_date_str = query_params['end_date']
            
            # Handle different date formats
            if 'T' not in start_date_str:
                # Format: YYYY-MM-DD -> add time component
                start_date = datetime.fromisoformat(start_date_str + 'T00:00:00')
                end_date = datetime.fromisoformat(end_date_str + 'T23:59:59')
            else:
                # Format: YYYY-MM-DDTHH:MM:SS[Z]
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        else:
            # Auto-calculate "last 30 days" from current date
            from datetime import timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            logging.info(f"Auto-calculated date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
    except (KeyError, ValueError) as e:
        return {'error': f'Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS): {str(e)}'}
    
    # Initialize analyzer
    analyzer = CostManagementAnalyzer(subscription_id)
    
    # Execute query based on type
    try:
        if query_type == 'subscription':
            granularity = query_params.get('granularity', 'Daily')
            return analyzer.get_subscription_costs(start_date, end_date, granularity)
        
        elif query_type == 'resource_group':
            resource_group = query_params.get('resource_group')
            if not resource_group:
                return {'error': 'resource_group is required for resource_group query'}
            granularity = query_params.get('granularity', 'Daily')
            return analyzer.get_resource_group_costs(resource_group, start_date, end_date, granularity)
        
        elif query_type == 'service':
            service_names = query_params.get('service_names')
            if not service_names:
                return {'error': 'service_names list is required for service query'}
            return analyzer.get_resource_costs_by_service(service_names, start_date, end_date)
        
        elif query_type == 'top_resources':
            top_n = query_params.get('top_n', 10)
            return analyzer.get_top_cost_resources(start_date, end_date, top_n)
        
        elif query_type == 'budget':
            return analyzer.get_budget_analysis(start_date, end_date)
        
        elif query_type == 'location':
            return analyzer.get_cost_by_location(start_date, end_date)
        
        elif query_type == 'specific_resources':
            resource_ids = query_params.get('resource_ids')
            if not resource_ids:
                return {'error': 'resource_ids list is required for specific_resources query'}
            logging.info(f"Executing specific_resources cost query for {len(resource_ids)} resources")
            return analyzer.get_specific_resources_cost(resource_ids, start_date, end_date)
        
        else:
            return {'error': f'Invalid query_type: {query_type}. Valid types: subscription, resource_group, service, top_resources, budget, location, specific_resources'}
    
    except Exception as e:
        logging.error(f"Error executing cost query: {str(e)}")
        return {'error': str(e)}


@app.function_name(name="CostManagementExample")
@app.route(route="cost-example", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def cost_management_example(req: func.HttpRequest) -> func.HttpResponse:
    """Example endpoint showing different cost query structures"""
    
    examples = {
        "subscription_costs": {
            "subscription_id": "your-subscription-id",
            "query_type": "subscription",
            "start_date": "2025-09-01T00:00:00Z",
            "end_date": "2025-09-30T23:59:59Z",
            "granularity": "Daily"
        },
        "resource_group_costs": {
            "subscription_id": "your-subscription-id",
            "query_type": "resource_group",
            "resource_group": "my-resource-group",
            "start_date": "2025-09-01T00:00:00Z",
            "end_date": "2025-09-30T23:59:59Z"
        },
        "service_costs": {
            "subscription_id": "your-subscription-id",
            "query_type": "service",
            "service_names": ["Virtual Machines", "Storage", "Networking"],
            "start_date": "2025-09-01T00:00:00Z",
            "end_date": "2025-09-30T23:59:59Z"
        },
        "top_resources": {
            "subscription_id": "your-subscription-id",
            "query_type": "top_resources",
            "top_n": 10,
            "start_date": "2025-09-01T00:00:00Z",
            "end_date": "2025-09-30T23:59:59Z"
        },
        "specific_resources": {
            "subscription_id": "your-subscription-id",
            "query_type": "specific_resources",
            "resource_ids": [
                "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1",
                "/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/storage1"
            ],
            "start_date": "2025-09-01T00:00:00Z",
            "end_date": "2025-09-30T23:59:59Z"
        },
        "budget_analysis": {
            "subscription_id": "your-subscription-id",
            "query_type": "budget",
            "start_date": "2025-09-01T00:00:00Z",
            "end_date": "2025-09-30T23:59:59Z"
        },
        "location_costs": {
            "subscription_id": "your-subscription-id",
            "query_type": "location",
            "start_date": "2025-09-01T00:00:00Z",
            "end_date": "2025-09-30T23:59:59Z"
        }
    }
    
    return func.HttpResponse(
        body=json.dumps(examples, indent=2),
        mimetype="application/json",
        status_code=200
    )
