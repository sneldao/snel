# Coral Protocol v1 Setup Guide

## 🔄 Updated Deployment Strategy

Based on the actual Coral Protocol architecture, we need to create proper v1 configuration files and deploy to a Coral Server (not marketplace).

## 📁 Required File Structure

```
snel-coral-agents/
│   registry.toml
│
└───snel-defi/
    │   coral-agent.toml
    │   requirements.txt
    │   main.py (our coral_agent_v2.py)
```

## 🛠️ Next Steps

1. **Create registry.toml** - Define our agent in the registry
2. **Create coral-agent.toml** - Agent-specific configuration 
3. **Adapt our Python agent** - Make it compatible with Coral Server
4. **Test with Coral Studio** - Debug multi-agent interactions
5. **Deploy to Coral Server** - Self-hosted or cloud deployment

## 💡 Business Model Adjustment

Instead of marketplace revenue sharing:
- **Direct client deployment** - Host Coral Server for clients
- **SaaS model** - Monthly/usage-based pricing for access
- **Enterprise licensing** - License our agent to other developers
- **Consulting services** - Help others build similar agents

## 🎯 Advantages of This Approach

- **Full control** over pricing and deployment
- **Direct client relationships** 
- **Higher profit margins** (no platform fees)
- **Custom integrations** possible
- **Enterprise-ready** architecture

The technical work we've done is still 100% valuable - we just need to package it differently for the actual Coral Protocol deployment model.
