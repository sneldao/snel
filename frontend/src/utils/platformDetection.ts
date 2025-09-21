/**
 * Platform Detection System
 * Detects whether SNEL is running on web or LINE environment
 * Following CLEAN principle: Single responsibility for platform awareness
 */

export enum Platform {
  WEB = 'web',
  LINE = 'line'
}

export interface PlatformConfig {
  platform: Platform;
  isLIFF: boolean;
  isMobile: boolean;
  walletType: 'wagmi' | 'line' | 'hybrid';
  features: {
    socialLogin: boolean;
    directWallet: boolean;
    chatInterface: boolean;
    notifications: boolean;
  };
}

/**
 * Detects current platform based on environment
 * ENHANCEMENT: Extends existing functionality without breaking changes
 */
export const detectPlatform = (): Platform => {
  // Check if running in LIFF (LINE Front-end Framework) environment
  if (typeof window !== 'undefined') {
    // LINE Mini-dApp specific detection
    if (window.location.hostname.includes('liff-') || 
        window.location.search.includes('liff.state') ||
        // @ts-ignore - LIFF object check
        window.liff) {
      return Platform.LINE;
    }
  }
  
  return Platform.WEB;
};

/**
 * Checks if the current domain is whitelisted for LINE SDK usage
 * SECURITY: Ensures SDK only works on pre-registered domains
 */
export const isDomainWhitelisted = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  const whitelistedDomains = [
    'localhost:3000', // Local development
    'localhost',      // Local development
    // Add any other whitelisted domains here
  ];
  
  const currentDomain = window.location.host;
  
  // Check if current domain is in the whitelisted domains
  return whitelistedDomains.some(domain => currentDomain.includes(domain));
};

/**
 * Validates if LINE SDK can be initialized safely
 * SECURITY: Combines platform detection with domain validation
 */
export const canInitializeLINE = (): boolean => {
  return detectPlatform() === Platform.LINE && isDomainWhitelisted();
};

/**
 * Gets platform-specific configuration
 * DRY: Single source of truth for platform capabilities
 */
export const getPlatformConfig = (platform: Platform = detectPlatform()): PlatformConfig => {
  const baseConfig = {
    platform,
    isMobile: typeof window !== 'undefined' ? window.innerWidth < 768 : false,
  };

  switch (platform) {
    case Platform.LINE:
      return {
        ...baseConfig,
        isLIFF: true,
        walletType: 'line',
        features: {
          socialLogin: true,      // LINE account integration
          directWallet: false,    // Wallet connect on demand
          chatInterface: true,    // Chat-based interactions
          notifications: true,    // LINE notifications
        }
      };

    case Platform.WEB:
    default:
      return {
        ...baseConfig,
        isLIFF: false,
        walletType: 'wagmi',
        features: {
          socialLogin: false,     // Direct wallet connection
          directWallet: true,     // Immediate wallet connect
          chatInterface: false,   // Traditional UI
          notifications: false,   // Web notifications only
        }
      };
  }
};

/**
 * Platform-aware hook for components
 * MODULAR: Composable platform awareness
 */
export const usePlatform = () => {
  const platform = detectPlatform();
  const config = getPlatformConfig(platform);
  
  return {
    platform,
    config,
    isLINE: platform === Platform.LINE,
    isWeb: platform === Platform.WEB,
    isMobile: config.isMobile,
    features: config.features,
  };
};

/**
 * Platform-specific URL handling
 * CLEAN: Separated URL concerns by platform
 */
export const getPlatformURL = (path: string, platform: Platform = detectPlatform()): string => {
  const baseURL = process.env.NEXT_PUBLIC_API_URL || 'https://snel-app.netlify.app';
  
  switch (platform) {
    case Platform.LINE:
      // LINE Mini-dApp URLs might have different routing
      return `${baseURL}/line${path}`;
    
    case Platform.WEB:
    default:
      return `${baseURL}${path}`;
  }
};

/**
 * Platform-aware analytics tracking
 * ORGANIZED: Consistent tracking across platforms
 */
export const trackPlatformEvent = (event: string, properties?: Record<string, any>) => {
  const platform = detectPlatform();
  const config = getPlatformConfig(platform);
  
  // Platform-specific analytics
  const eventData = {
    event,
    timestamp: new Date().toISOString(),
    platform: config.platform,
    features: config.features,
    ...properties,
  };
  
  // Implementation will be added based on your analytics setup
  console.log('[Platform Analytics]', eventData);
};

/**
 * LINE-specific configuration validation
 * SECURITY: Ensures all required LINE configurations are present
 */
export const validateLINEConfig = (): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];
  
  // Check required environment variables
  if (!process.env.NEXT_PUBLIC_LIFF_ID) {
    errors.push('NEXT_PUBLIC_LIFF_ID is required for LINE integration');
  }
  
  if (!process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID) {
    errors.push('NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID is required for Bitget Wallet integration');
  }
  
  // Check domain whitelisting
  if (!isDomainWhitelisted()) {
    errors.push('Current domain is not whitelisted for LINE SDK usage');
  }
  
  // Check if running in secure context (required for wallet operations)
  if (typeof window !== 'undefined' && !window.isSecureContext) {
    errors.push('Secure context (HTTPS) required for wallet operations');
  }
  
  return {
    isValid: errors.length === 0,
    errors,
  };
};

/**
 * Check if Reown/WalletConnect is properly configured
 * SECURITY: Validates domain verification requirements
 */
export const validateReownConfig = (): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];
  
  const projectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID;
  if (!projectId) {
    errors.push('WalletConnect Project ID is required for Reown integration');
  }
  
  // Check if domain is likely to be verified with Reown
  if (typeof window !== 'undefined') {
    const domain = window.location.host;
    if (domain.includes('localhost') && !domain.includes('localhost:3000')) {
      errors.push('For local testing, use localhost:3000 or register your domain with Reown');
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors,
  };
};

/**
 * Get LINE test mode configuration
 * SECURITY: Ensures testMode is properly set based on environment
 */
export const getLINETestMode = (): boolean => {
  // Always use test mode in development
  if (process.env.NODE_ENV === 'development') {
    return true;
  }
  
  // Check for explicit test mode override
  if (process.env.NEXT_PUBLIC_LINE_TEST_MODE === 'true') {
    return true;
  }
  
  // Production should use live mode (false) unless explicitly overridden
  return false;
};
