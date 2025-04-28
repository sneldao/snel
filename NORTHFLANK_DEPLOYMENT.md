# Deploying Stable Snel to Northflank

This guide will walk you through deploying the Stable Snel backend to Northflank.

## Prerequisites

- A Northflank account
- Git repository with your Stable Snel code
- Required API keys and environment variables

## Step 1: Create a New Project in Northflank

1. Log in to your Northflank account at [app.northflank.com](https://app.northflank.com)
2. Click on "Create Project"
3. Name your project "stable-snel" or "stable-station"
4. Select the appropriate region for your deployment
5. Click "Create Project"

## Step 2: Set Up Environment Variables

1. In your project, go to the "Secrets" section
2. Create a new secret group called "stable-snel-env"
3. Add the following environment variables:

```
API_V1_STR=/api/v1
PROJECT_NAME=Stable Snel API
REDIS_URL=your_redis_url
BRIAN_API_KEY=your_brian_api_key
BRIAN_API_URL=https://api.brianknows.org/api/v0
DISABLE_SSL_VERIFY=false
ZEROX_API_KEY=your_zerox_api_key
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
COINGECKO_API_KEY=your_coingecko_api_key
MORALIS_API_KEY=your_moralis_api_key
ALCHEMY_KEY=your_alchemy_key
```

## Step 3: Create a Redis Add-on

1. Go to the "Add-ons" section in your project
2. Click "Create Add-on"
3. Select "Redis"
4. Choose the appropriate plan for your needs
5. Name it "stable-snel-redis"
6. Click "Create Add-on"
7. Once created, go to the add-on details and copy the connection URL
8. Update the `REDIS_URL` in your environment variables with this URL

## Step 4: Deploy the Backend Service

### Option 1: Deploy from Git Repository

1. Go to the "Services" section in your project
2. Click "Create Service"
3. Select "From Git Repository"
4. Connect your Git repository if not already connected
5. Select the repository containing your Stable Snel code
6. Configure the service:
   - Name: stable-snel-backend
   - Build settings:
     - Dockerfile path: backend/Dockerfile
     - Context directory: backend
   - Port: 8000
   - Environment variables: Select the "stable-snel-env" secret group
   - Resources: 
     - CPU: 0.5 vCPU
     - Memory: 1 GB
   - Scaling:
     - Min instances: 1
     - Max instances: 3
   - Health check:
     - Path: /health
     - Port: 8000
7. Click "Create Service"

### Option 2: Deploy Using Northflank CLI

1. Install the Northflank CLI:
   ```bash
   npm install -g @northflank/cli
   ```

2. Log in to Northflank:
   ```bash
   northflank login
   ```

3. Deploy using the northflank.yml file:
   ```bash
   northflank apply -f northflank.yml
   ```

## Step 5: Configure Networking

1. Go to the "Networking" section in your project
2. Click "Create Public Domain"
3. Configure your domain:
   - If you have a custom domain, enter it here
   - Otherwise, use the Northflank subdomain
4. Select the backend service and port 8000
5. Click "Create Domain"

## Step 6: Update Frontend Configuration

Update your frontend configuration to point to your new backend URL:

1. In your Vercel project for the frontend, update the environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-northflank-domain.com
   ```

2. Redeploy your frontend on Vercel

## Step 7: Verify Deployment

1. Visit your backend URL to check if the service is running:
   ```
   https://your-northflank-domain.com/health
   ```

2. Test the frontend integration by visiting your Vercel app:
   ```
   https://stable-snel.vercel.app
   ```

## Troubleshooting

If you encounter any issues:

1. Check the logs in the Northflank dashboard
2. Verify that all environment variables are set correctly
3. Ensure the Redis add-on is properly connected
4. Check that CORS settings allow requests from your frontend domain

## Scaling and Monitoring

Northflank provides built-in monitoring and scaling capabilities:

1. Go to the "Metrics" section to view performance data
2. Adjust the scaling settings in your service configuration as needed
3. Set up alerts for important metrics

## Continuous Deployment

To set up continuous deployment:

1. Configure your Git repository to trigger deployments on push
2. Set up branch rules to deploy specific branches to different environments
3. Configure preview environments for pull requests if needed
