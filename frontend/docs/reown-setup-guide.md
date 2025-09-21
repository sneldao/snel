# WalletConnect Domain Verification Setup Guide

## Overview
This guide explains how to set up domain verification with WalletConnect for wallet integration in the LINE Mini Dapp using the existing ConnectKit infrastructure.

## Prerequisites
- WalletConnect Project ID from [WalletConnect Cloud](https://cloud.walletconnect.com/)
- Access to LINE Mini Dapp Tech Support team
- Domain registered with LINE for Mini Dapp usage

## Step 1: WalletConnect Project Setup

1. **Create WalletConnect Project**
   - Go to [WalletConnect Cloud](https://cloud.walletconnect.com/)
   - Create a new project
   - Note down your Project ID

2. **Configure Project Settings**
   - Set project name: "Snel - DeFi Assistant"
   - Add project description: "DeFi operations through LINE Mini-dApp"
   - Upload app icon: Use Snel logo

## Step 2: Domain Configuration

1. **Add Allowed Domains**
   - In WalletConnect Cloud, go to your project settings
   - Add your production domain
   - Add `localhost:3000` for local development
   - Add any staging domains

2. **Configure Redirect URIs**
   - Add your domain with `/wallet-bridge` path
   - Example: `https://yourdomain.com/wallet-bridge`
   - Add localhost: `http://localhost:3000/wallet-bridge`

## Step 3: Environment Variables

1. **Frontend Configuration**
   ```env
   NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id_here
   ```

2. **Verify Configuration**
   - Ensure the project ID is correctly set
   - Test locally with `localhost:3000`

## Step 4: LINE Tech Support Coordination

1. **Share Project ID**
   - Contact LINE Mini Dapp Tech Support team
   - Provide your WalletConnect Project ID
   - Request domain verification for Bitget Wallet integration

2. **Required Information to Share**
   - WalletConnect Project ID
   - Production domain URL
   - LIFF ID
   - Expected launch date

## Step 5: Testing

1. **Local Testing**
   ```bash
   npm run dev
   # Navigate to http://localhost:3000/line
   # Test wallet connection functionality
   ```

2. **Production Testing**
   - Deploy to staging environment
   - Test wallet connection on actual LINE app
   - Verify Bitget Wallet integration works

## Step 6: Verification Checklist

- [ ] WalletConnect project created and configured
- [ ] Project ID added to environment variables
- [ ] Domains added to WalletConnect project
- [ ] Project ID shared with LINE Tech Support
- [ ] Domain verification confirmed by LINE team
- [ ] Local testing successful
- [ ] Production testing successful

## Troubleshooting

### Common Issues

1. **"Domain not verified" error**
   - Ensure domain is added to WalletConnect project
   - Confirm LINE Tech Support has verified the domain
   - Check that HTTPS is enabled in production

2. **"Project ID not found" error**
   - Verify the project ID is correctly set in environment variables
   - Ensure the project is active in WalletConnect Cloud

3. **Wallet connection fails**
   - Check browser console for detailed error messages
   - Verify secure context (HTTPS) is available
   - Ensure Bitget Wallet is installed and updated

### Support Contacts

- **LINE Tech Support**: Contact through Mini Dapp Developer Telegram Channel
- **WalletConnect Support**: [WalletConnect Discord](https://discord.gg/walletconnect)
- **Developer Channel**: https://t.me/+Fq6bbac7NLhmNGJl

## Security Notes

- Never expose your WalletConnect Project ID in public repositories
- Always use environment variables for configuration
- Ensure testMode is enabled during development
- Verify domain whitelisting is properly implemented

## Next Steps

After completing domain verification:
1. Test the complete wallet integration flow
2. Verify transaction execution works correctly
3. Test on actual LINE Mini Dapp environment
4. Prepare demo for submission to LINE team
