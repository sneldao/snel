# Coinbase CDP Integration

This document explains how to set up and use Coinbase Developer Platform (CDP) for secure wallet management in production.

## Overview

Dowse Pointless uses the Coinbase Developer Platform (CDP) to provide secure wallet management for users. In production, we use Coinbase-Managed (2-of-2) wallets, which provide enhanced security through Multi-Party Computation (MPC).

Key benefits:

- **Enterprise-grade security**: Private keys are split between Coinbase and your application
- **Account abstraction**: ERC-4337 compatible smart wallets
- **Gas sponsorship**: Built-in Paymaster support for sponsoring gas fees
- **Multi-network support**: Same wallet address works across all supported networks

## Setup

### 1. Create a Coinbase CDP Account

1. Visit the [Coinbase Developer Platform](https://www.coinbase.com/cloud/products/developer-platform) and sign up for an account
2. Create a new API key with the necessary permissions
3. Save your API key name and private key securely

### 2. Configure Environment Variables

Add the following to your `.env.local` file:

```
CDP_API_KEY_NAME=your_coinbase_cdp_api_key_name
CDP_API_KEY_PRIVATE_KEY=your_coinbase_cdp_private_key
USE_CDP_SDK=true
CDP_USE_MANAGED_WALLET=true  # Use Coinbase-Managed (2-of-2) wallet for production
CDP_VERIFY_SSL=true
```

For development, you may want to disable SSL verification:

```
DISABLE_SSL_VERIFY=true  # Development only - REMOVE in production
```

### 3. Test Your Configuration

Run the test script to verify your CDP SDK integration works:

```bash
./test_cdp.py
```

This script will:

- Verify your API key configuration
- Create a test wallet
- Request ETH from the faucet (on testnet)
- Display the wallet address

## SSL Verification

### SSL Certificate Configuration

The Coinbase CDP SDK requires proper SSL certificate verification for secure communication. If you encounter SSL certificate errors, follow these steps:

1. **Install certifi**: Ensure the `certifi` package is installed in your environment. This package provides a curated collection of Root Certificates for validating SSL certificates.

   ```bash
   pip install certifi
   ```

2. **Configure SSL in your application**: The `SmartWalletService` in our application handles this automatically by setting the appropriate environment variables:

   ```python
   def _configure_ssl(self):
       """Configure SSL certificates to ensure secure connections."""
       try:
           # Set the SSL certificate path to the certifi bundle
           os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
           os.environ['SSL_CERT_FILE'] = certifi.where()

           # Make sure the SSL context is using the proper certificates
           ssl_context = ssl.create_default_context(cafile=certifi.where())

           logger.info(f"SSL certificates properly configured using: {certifi.where()}")
       except Exception as e:
           logger.error(f"Failed to configure SSL certificates: {e}")
           raise
   ```

### Troubleshooting SSL Issues

If you experience SSL verification errors:

1. **Check cert bundle path**: Verify that the path to your certificate bundle is correct. The error "Could not find a suitable TLS CA certificate bundle" indicates an issue with certificate path.

2. **Update certifi**: Ensure you have the latest version with `pip install --upgrade certifi`

3. **Test connectivity**: Use the `test_requests.py` script in the `cdp-test` directory to verify basic connectivity to the Coinbase API endpoints.

4. **MacOS-specific issue**: On Mac M1/M2 machines, architecture mismatches with the `coincurve` package can cause SSL issues. Try reinstalling with:
   ```bash
   pip uninstall -y coincurve
   pip install coincurve==20.0.0
   ```

## How It Works

### Wallet Types

Dowse Pointless supports two wallet types using Coinbase CDP:

1. **Developer-Managed (1-of-1) Wallets**:

   - Similar to traditional wallets, where the private key is managed entirely by the application
   - Suitable for testing and development
   - Set `CDP_USE_MANAGED_WALLET=false` to use this type

2. **Coinbase-Managed (2-of-2) Wallets**:
   - Uses MPC to split the private key between Coinbase and your application
   - Enhanced security - even if one share is compromised, assets remain secure
   - Recommended for production use
   - Set `CDP_USE_MANAGED_WALLET=true` to use this type

### Smart Wallet Features

The `SmartWalletService` provides these key methods:

- `create_smart_wallet(user_id, platform)`: Create a new smart wallet for a user
- `get_wallet_balance(user_id, platform)`: Get balance for a user's wallet
- `send_transaction(user_id, platform, to_address, amount)`: Send ETH from a user's wallet
- `fund_wallet_from_faucet(user_id, platform)`: Request ETH from faucet (testnet only)

### Networks

Currently supported networks:

- Base Sepolia (testnet)
- Base Mainnet (planned)

## Security Considerations

### Key Storage

For production, ensure that:

1. Your CDP API keys are stored securely and not exposed in client-side code
2. Access to the CDP Portal is protected with strong credentials and MFA
3. Redis data is encrypted and access-controlled
4. You follow least-privilege principles for all API keys and accounts

### Private Key Management

In our implementation, we store wallet private keys in Redis. For a production environment:

1. Consider encrypting the private keys before storing them
2. Use a more secure key management solution like AWS KMS or HashiCorp Vault
3. Implement key rotation and backup procedures

## Troubleshooting

### Common Issues

1. **"CDP API keys not found"**:

   - Check that `CDP_API_KEY_NAME` and `CDP_API_KEY_PRIVATE_KEY` are set correctly in your environment
   - Verify the keys have the necessary permissions in the CDP Portal

2. **SSL Certificate Errors**:

   - For development, you can set `DISABLE_SSL_VERIFY=true`
   - For production, ensure you have valid SSL certificates

3. **Redis Connection Issues**:
   - Check your Redis URL is correct and Redis server is running
   - Verify network connectivity between your application and Redis server

## Resources

- [Coinbase CDP Documentation](https://docs.cdp.coinbase.com/wallet-api/docs/welcome)
- [CDP Python SDK Documentation](https://github.com/coinbase/cdp-sdk-python)
- [ERC-4337 Smart Wallets](https://docs.cdp.coinbase.com/wallet-api/docs/wallets)
- [Securing a Wallet](https://docs.cdp.coinbase.com/wallet-api/docs/securing-a-wallet)
