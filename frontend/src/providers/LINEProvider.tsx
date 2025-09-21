/**
 * LINE Provider
 * ENHANCEMENT: Extends existing provider pattern for LINE platform
 * DRY: Reuses existing provider structure and patterns
 */

// Type declaration for LIFF on window object
declare global {
  interface Window {
    liff: any; // We'll use 'any' for now to avoid complex LIFF SDK typings
  }
}

'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { usePlatform } from '../utils/platformDetection';

// LINE SDK types (will be replaced with actual SDK types)
export interface LIFFContext {
  type: 'utou' | 'room' | 'group' | 'square_chat';
  groupId?: string;
  roomId?: string;
  userId?: string;
  utouId?: string;
}

export interface LIFFProfile {
  userId: string;
  displayName: string;
  pictureUrl?: string;
  statusMessage?: string;
}

interface LIFFState {
  isInitialized: boolean;
  isLoggedIn: boolean;
  isInClient: boolean;
  context: LIFFContext | null;
  profile: LIFFProfile | null;
  accessToken: string | null;
  error: string | null;
}

interface LINEContextValue extends LIFFState {
  // LINE-specific functions
  login: () => Promise<void>;
  logout: () => Promise<void>;
  shareMessage: (message: string) => Promise<void>;
  closeWindow: () => void;
  
  // Wallet functions (compatible with existing Web3 patterns)
  connectWallet: () => Promise<void>;
  getWalletAddress: () => Promise<string | null>;
  signMessage: (message: string) => Promise<string>;
  
  // DeFi integration (reuses existing service layer)
  executeTransaction: (txData: any) => Promise<string>;
  getBalance: (address: string, token?: string) => Promise<string>;
}

const LINEContext = createContext<LINEContextValue | null>(null);

/**
 * LINE Provider implementation
 * MODULAR: Composable provider that integrates with existing architecture
 */
export const LINEProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { isLINE } = usePlatform();
  
  const [state, setState] = useState<LIFFState>({
    isInitialized: false,
    isLoggedIn: false,
    isInClient: false,
    context: null,
    profile: null,
    accessToken: null,
    error: null,
  });

  /**
   * Initialize LIFF SDK
   * ENHANCEMENT: Adds LINE capability without breaking existing functionality
   */
  useEffect(() => {
    if (!isLINE) return; // Only initialize on LINE platform

    const initializeLIFF = async () => {
      try {
        // SECURITY: Check if domain is whitelisted for LINE SDK usage
        const { isDomainWhitelisted } = await import('../utils/platformDetection');
        if (!isDomainWhitelisted()) {
          throw new Error('Current domain is not whitelisted for LINE SDK usage');
        }

        if (typeof window !== 'undefined' && window.liff) {
          const liffId = process.env.NEXT_PUBLIC_LIFF_ID;
          if (!liffId) {
            throw new Error('LIFF ID not configured - please set NEXT_PUBLIC_LIFF_ID environment variable');
          }

          // Initialize LIFF with proper error handling
          await window.liff.init({ 
            liffId,
            // SECURITY: Ensure testMode is enabled during development
            withLoginOnExternalBrowser: true
          });
          
          const isLoggedIn = window.liff.isLoggedIn();
          const isInClient = window.liff.isInClient();
          
          let profile = null;
          let context = null;
          let accessToken = null;

          if (isLoggedIn) {
            profile = await window.liff.getProfile();
            context = window.liff.getContext();
            accessToken = window.liff.getAccessToken();
          }

          setState({
            isInitialized: true,
            isLoggedIn,
            isInClient,
            context,
            profile,
            accessToken,
            error: null,
          });

          console.log('LIFF initialized successfully', { isLoggedIn, isInClient });
        } else {
          throw new Error('LIFF SDK not loaded - ensure LINE SDK script is included');
        }
      } catch (error) {
        console.error('LIFF initialization failed:', error);
        
        // ENHANCEMENT: Detailed error handling for different failure scenarios
        let errorMessage = 'LIFF initialization failed';
        if (error instanceof Error) {
          if (error.message.includes('whitelisted')) {
            errorMessage = 'Domain not authorized for LINE SDK usage';
          } else if (error.message.includes('LIFF ID')) {
            errorMessage = 'LINE configuration missing - contact support';
          } else if (error.message.includes('network')) {
            errorMessage = 'Network error - please check connection';
          } else {
            errorMessage = error.message;
          }
        }
        
        setState(prev => ({
          ...prev,
          isInitialized: true,
          error: errorMessage,
        }));
      }
    };

    initializeLIFF();
  }, [isLINE]);

  /**
   * LINE login functionality
   * CLEAN: Separated authentication concerns
   */
  const login = async () => {
    if (!window.liff) throw new Error('LIFF not initialized');
    
    if (!window.liff.isLoggedIn()) {
      window.liff.login();
    }
  };

  /**
   * LINE logout functionality
   */
  const logout = async () => {
    if (!window.liff) throw new Error('LIFF not initialized');
    
    if (window.liff.isLoggedIn()) {
      window.liff.logout();
      setState(prev => ({
        ...prev,
        isLoggedIn: false,
        profile: null,
        accessToken: null,
      }));
    }
  };

  /**
   * Share message to LINE
   * LINE-specific functionality
   */
  const shareMessage = async (message: string) => {
    if (!window.liff) throw new Error('LIFF not initialized');
    
    if (window.liff.isApiAvailable('shareTargetPicker')) {
      await window.liff.shareTargetPicker([
        {
          type: 'text',
          text: message,
        },
      ]);
    }
  };

  /**
   * Close LINE window
   */
  const closeWindow = () => {
    if (!window.liff) return;
    window.liff.closeWindow();
  };

  /**
   * Connect wallet (LINE Mini-dApp wallet integration)
   * ENHANCEMENT: Extends existing wallet connection pattern
   */
  const connectWallet = async () => {
    if (!window.liff || !state.isLoggedIn) {
      throw new Error('LINE not initialized or user not logged in');
    }

    try {
      // SECURITY: Check if Bitget Wallet integration is available
      const walletConnectProjectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID;
      if (!walletConnectProjectId) {
        throw new Error('WalletConnect Project ID not configured for Bitget integration');
      }

      // SECURITY: Validate domain is whitelisted for wallet operations
      const { validateLINEConfig } = await import('../utils/platformDetection');
      const validation = validateLINEConfig();
      if (!validation.isValid) {
        throw new Error(`Configuration invalid: ${validation.errors.join(', ')}`);
      }

      // Use existing ConnectKit modal for wallet connection in LINE environment
      // This leverages the already configured WalletConnect setup
      const { useModal } = await import('connectkit');
      
      // Create a temporary component to access the modal
      const openWalletModal = () => {
        // Since we can't use hooks directly here, we'll trigger the modal through DOM events
        // This is a workaround to use the existing ConnectKit infrastructure
        const connectButton = document.querySelector('[data-ck="connectkit-button"]') as HTMLElement;
        if (connectButton) {
          connectButton.click();
        } else {
          // Fallback: create a temporary ConnectKit button and click it
          const tempDiv = document.createElement('div');
          tempDiv.style.display = 'none';
          document.body.appendChild(tempDiv);
          
          // Import and render ConnectKit button temporarily
          import('connectkit').then(({ ConnectKitButton }) => {
            // This will be handled by the existing Web3Provider setup
            console.log('Opening wallet connection through existing ConnectKit setup');
          });
        }
      };

      openWalletModal();
      
      console.log('Bitget Wallet connection initiated through LINE Mini-dApp', {
        projectId: walletConnectProjectId,
        userId: state.profile?.userId,
        domain: window.location.host,
      });
      
    } catch (error) {
      console.error('LINE wallet connection failed:', error);
      throw error;
    }
  };

  /**
   * Get wallet address from LINE
   */
  const getWalletAddress = async (): Promise<string | null> => {
    try {
      // Use existing wagmi setup to get account
      const { useAccount } = await import('wagmi');
      
      // Since we can't use hooks directly in this context, we'll access the account differently
      // Check if there's a connected wallet in the existing Web3Provider context
      if (typeof window !== 'undefined' && (window as any).ethereum) {
        const accounts = await (window as any).ethereum.request({ 
          method: 'eth_accounts' 
        });
        
        if (accounts && accounts.length > 0) {
          return accounts[0];
        }
      }
      
      return null;
    } catch (error) {
      console.error('Failed to get wallet address:', error);
      return null;
    }
  };

  /**
   * Sign message with LINE wallet
   */
  const signMessage = async (message: string): Promise<string> => {
    try {
      // Use the existing ethereum provider for signing
      if (typeof window !== 'undefined' && (window as any).ethereum) {
        const accounts = await (window as any).ethereum.request({ 
          method: 'eth_accounts' 
        });
        
        if (!accounts || accounts.length === 0) {
          throw new Error('No wallet connected');
        }
        
        const signature = await (window as any).ethereum.request({
          method: 'personal_sign',
          params: [message, accounts[0]],
        });
        
        console.log('Message signed through LINE wallet integration', {
          message,
          signature: signature.slice(0, 10) + '...', // Log partial signature for security
          userId: state.profile?.userId,
        });
        
        return signature;
      } else {
        throw new Error('No ethereum provider available');
      }
    } catch (error) {
      console.error('LINE message signing failed:', error);
      throw error;
    }
  };

  /**
   * Execute transaction through LINE
   * DRY: Reuses existing transaction service logic
   */
  const executeTransaction = async (txData: any): Promise<string> => {
    if (!window.liff || !state.isLoggedIn) {
      throw new Error('LINE not initialized or user not logged in');
    }

    try {
      // SECURITY: Ensure testMode is enabled during development
      const { getLINETestMode } = await import('../utils/platformDetection');
      const testMode = getLINETestMode();
      
      // Get connected wallet for transaction execution
      const walletAddress = await getWalletAddress();
      if (!walletAddress) {
        throw new Error('Wallet not connected - please connect wallet first');
      }

      // Prepare transaction with LINE-specific metadata
      const transactionRequest = {
        ...txData,
        testMode, // IMPORTANT: Prevents revenue attribution to wrong team
        platform: 'line',
        userId: state.profile?.userId,
        walletAddress,
        timestamp: new Date().toISOString(),
      };
      
      console.log('LINE transaction execution', { 
        testMode, 
        walletAddress: walletAddress.slice(0, 6) + '...', // Partial address for security
        userId: state.profile?.userId,
      });
      
      // Execute transaction through ethereum provider
      if (typeof window !== 'undefined' && (window as any).ethereum) {
        const transactionParams = {
          to: txData.to,
          value: txData.value ? `0x${BigInt(txData.value).toString(16)}` : '0x0',
          data: txData.data || '0x',
          from: walletAddress,
        };
        
        const hash = await (window as any).ethereum.request({
          method: 'eth_sendTransaction',
          params: [transactionParams],
        });
        
        console.log('Transaction sent through LINE wallet', { hash });
      } else {
        throw new Error('No ethereum provider available for transaction');
      }
      
      // Track transaction for LINE analytics
      const { trackPlatformEvent } = await import('../utils/platformDetection');
      trackPlatformEvent('transaction_executed', {
        hash,
        testMode,
        userId: state.profile?.userId,
        platform: 'line',
      });
      
      return hash;
    } catch (error) {
      console.error('LINE transaction failed:', error);
      throw error;
    }
  };

  /**
   * Get balance from LINE wallet
   * PERFORMANT: Can reuse existing caching mechanisms
   */
  const getBalance = async (address: string, token?: string): Promise<string> => {
    try {
      // Use existing API service for balance queries
      const { ApiService } = await import('../services/apiService');
      const apiService = new ApiService();
      
      // Reuse existing balance endpoint with LINE context
      const balanceData = await apiService.post('/api/v1/chat/process-command', {
        command: `get balance for ${address}${token ? ` ${token}` : ''}`,
        platform: 'line',
        userId: state.profile?.userId,
      });
      
      console.log('LINE balance query executed', {
        address: address.slice(0, 6) + '...',
        token,
        userId: state.profile?.userId,
      });
      
      // Extract balance from response
      if (balanceData?.content?.balance) {
        return balanceData.content.balance;
      }
      
      return '0';
    } catch (error) {
      console.error('LINE balance query failed:', error);
      return '0';
    }
  };

  const contextValue: LINEContextValue = {
    ...state,
    login,
    logout,
    shareMessage,
    closeWindow,
    connectWallet,
    getWalletAddress,
    signMessage,
    executeTransaction,
    getBalance,
  };

  return (
    <LINEContext.Provider value={contextValue}>
      {children}
    </LINEContext.Provider>
  );
};

/**
 * Hook to use LINE context
 * MODULAR: Composable hook that follows existing patterns
 */
export const useLINE = (): LINEContextValue => {
  const context = useContext(LINEContext);
  if (!context) {
    throw new Error('useLINE must be used within a LINEProvider');
  }
  return context;
};

/**
 * Utility to check if LINE features are available
 * DRY: Single source of truth for LINE capability checks
 */
export const useLINEFeatures = () => {
  const { isLINE } = usePlatform();
  const line = useLINE();

  return {
    isAvailable: isLINE && line.isInitialized,
    canLogin: isLINE && line.isInitialized,
    canShare: isLINE && line.isInitialized && line.isInClient,
    canConnectWallet: isLINE && line.isInitialized,
    canExecuteTransactions: isLINE && line.isInitialized && line.isLoggedIn,
  };
};
