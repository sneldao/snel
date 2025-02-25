# SSL Configuration Guide

This document provides guidance on handling SSL certificate verification issues in the application.

## Understanding SSL Issues

SSL certificate verification issues can occur for several reasons:

1. **Outdated CA certificates**: Your system's certificate authority (CA) store might be outdated.
2. **Proxy interference**: Corporate proxies sometimes intercept HTTPS traffic.
3. **API endpoint issues**: Some API providers might have certificate configuration problems.

## Configuration Options

The application provides several options for handling SSL issues:

### Option 1: Disable SSL Verification (Development Only)

```
DISABLE_SSL_VERIFY=true
```

**WARNING**: This option disables all SSL certificate verification, making your connections insecure.
This should NEVER be used in production environments.

### Option 2: Use Custom CA Certificates (Recommended for Local Production)

```
CA_CERT_PATH=/path/to/cacert.pem
```

This option allows you to specify a custom CA certificate bundle to use for SSL verification.
This is the recommended approach for production environments where you're experiencing SSL issues.

### Option 3: Vercel Deployment (Recommended for Vercel)

When deploying to Vercel, you should use Vercel's built-in CA certificates:

```
NODE_EXTRA_CA_CERTS=true
```

This tells Node.js to use its built-in CA certificates for SSL verification, which are kept up-to-date by Vercel.

## Obtaining Updated CA Certificates

### For macOS

macOS users can create a CA bundle with:

```bash
security export -t certs -f pemseq -k /System/Library/Keychains/SystemRootCertificates.keychain > cacert.pem
```

### For Linux

Most Linux distributions provide a package with up-to-date CA certificates:

- Debian/Ubuntu: `sudo apt-get install ca-certificates`
- CentOS/RHEL: `sudo yum install ca-certificates`

The certificates are typically stored in `/etc/ssl/certs/ca-certificates.crt`.

### Using Mozilla's CA Bundle

You can also download Mozilla's CA bundle:

```bash
curl -o cacert.pem https://curl.se/ca/cacert.pem
```

## Implementation

### For Local Development/Production

Once you have your CA certificate bundle, set the `CA_CERT_PATH` environment variable to its location:

```
CA_CERT_PATH=/path/to/cacert.pem
```

The application will then use this certificate bundle for all SSL connections.

### For Vercel Deployment

In your Vercel project settings, add the following environment variable:

```
NODE_EXTRA_CA_CERTS=true
```

This will ensure that your application uses Vercel's up-to-date CA certificates.

## QuickNode Configuration

For QuickNode, you need to set the API key:

```
QUICKNODE_API_KEY=your_quicknode_key_here
```

You can also customize the QuickNode endpoints for each chain:

```
QUICKNODE_ETH_MAINNET_URL=https://your-quicknode-eth-endpoint.quiknode.pro/your-api-key/
QUICKNODE_OPTIMISM_URL=https://your-quicknode-optimism-endpoint.quiknode.pro/your-api-key/
QUICKNODE_POLYGON_URL=https://your-quicknode-polygon-endpoint.quiknode.pro/your-api-key/
QUICKNODE_ARBITRUM_URL=https://your-quicknode-arbitrum-endpoint.quiknode.pro/your-api-key/
QUICKNODE_BASE_URL=https://your-quicknode-base-endpoint.quiknode.pro/your-api-key/
QUICKNODE_SCROLL_URL=https://your-quicknode-scroll-endpoint.quiknode.pro/your-api-key/
QUICKNODE_AVALANCHE_URL=https://your-quicknode-avalanche-endpoint.quiknode.pro/your-api-key/ext/bc/C/rpc/
```

If these environment variables are not set, the application will use the default endpoints.

## Troubleshooting

If you continue to experience SSL issues:

1. Ensure the CA bundle is up-to-date
2. Check if the API endpoint's certificate is valid (using tools like `openssl s_client`)
3. Consider using a different API endpoint if available
4. Contact the API provider's support if the issue persists
