# Model Context Protocol (MCP) Setup Guide

This folder contains comprehensive documentation for setting up **Model Context Protocol (MCP)** integration with your Azure Cost Management & Orphaned Resources Analyzer solution.

## 📚 Documentation Structure

| File | Description |
|------|-------------|
| [`overview.md`](overview.md) | What is MCP and why use it with cost analysis agents |
| [`prerequisites.md`](prerequisites.md) | Requirements and pre-setup checklist |
| [`app-registration.md`](app-registration.md) | Step-by-step app registration for MCP authentication |
| [`logic-app-setup.md`](logic-app-setup.md) | Configure Standard Logic App as MCP server |
| [`workflows/`](workflows/) | Ready-to-deploy Logic App workflow templates |
| [`ai-foundry-integration.md`](ai-foundry-integration.md) | Connect agents with automated triggering |
| [`testing.md`](testing.md) | Validation and testing procedures |
| [`troubleshooting.md`](troubleshooting.md) | Common issues and solutions |

## 🚀 Quick Start

1. **Check Prerequisites**: Review [`prerequisites.md`](prerequisites.md)
2. **App Registration**: Follow [`app-registration.md`](app-registration.md)
3. **Setup Logic App**: Configure using [`logic-app-setup.md`](logic-app-setup.md)
4. **Deploy Workflows**: Use templates from [`workflows/`](workflows/)
5. **Connect AI Foundry**: Configure agents via [`ai-foundry-integration.md`](ai-foundry-integration.md)
6. **Test Setup**: Validate using [`testing.md`](testing.md)

## 📖 Official Microsoft Documentation

These comprehensive Microsoft Learn articles provide detailed technical guidance:

- **[Set up Standard logic apps as remote MCP servers](https://learn.microsoft.com/en-us/azure/logic-apps/set-up-model-context-protocol-server-standard)**  
  Complete technical reference for configuring Logic Apps as MCP servers, including authentication setup, endpoint configuration, and security best practices.

- **[Trigger an agent by using Logic Apps](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/triggers)**  
  Step-by-step guide for integrating AI Foundry agents with Logic Apps workflows, covering thread management, run execution, and response handling.

---

💡 **Tip**: Start with the overview to understand MCP benefits, then follow the setup guides sequentially for best results. Refer to the Microsoft documentation for advanced scenarios and troubleshooting.