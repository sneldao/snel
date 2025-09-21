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
    platform,
    timestamp: new Date().toISOString(),
    ...config,
    ...properties,
  };
  
  // Implementation will be added based on your analytics setup
  console.log('[Platform Analytics]', eventData);
};
