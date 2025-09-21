/**
 * LINE Provider
 * ENHANCEMENT: Extends existing provider pattern for LINE platform
 * DRY: Reuses existing provider structure and patterns
 */

'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { usePlatform } from '../utils/platformDetection';

// LINE SDK types (will be replaced with actual SDK types)
interface LIFFContext {
  type: 'utou' | 'room' | 'group' | 'square_chat';
  groupId?: string;
  roomId?: string;
  userId?: string;
  utouId?: string;
}

interface LIFFProfile {
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
        if (typeof window !== 'undefined' && window.liff) {
          const liffId = process.env.NEXT_PUBLIC_LIFF_ID;
          if (!liffId) {
            throw new Error('LIFF ID not configured');
          }

          await window.liff.init({ liffId });
          
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
        }
      } catch (error) {
        console.error('LIFF initialization failed:', error);
        setState(prev => ({
          ...prev,
          isInitialized: true,
          error: error instanceof Error ? error.message : 'LIFF initialization failed',
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
    // Implementation will use LINE Mini-dApp SDK wallet features
    // This maintains compatibility with existing Web3 patterns
    console.log('LINE wallet connection to be implemented');
  };

  /**
   * Get wallet address from LINE
   */
  const getWalletAddress = async (): Promise<string | null> => {
    // Implementation will use LINE Mini-dApp SDK
    console.log('Get LINE wallet address to be implemented');
    return null;
  };

  /**
   * Sign message with LINE wallet
   */
  const signMessage = async (message: string): Promise<string> => {
    // Implementation will use LINE Mini-dApp SDK
    console.log('LINE message signing to be implemented');
    return '';
  };

  /**
   * Execute transaction through LINE
   * DRY: Reuses existing transaction service logic
   */
  const executeTransaction = async (txData: any): Promise<string> => {
    // Implementation will bridge to existing transaction services
    console.log('LINE transaction execution to be implemented');
    return '';
  };

  /**
   * Get balance from LINE wallet
   * PERFORMANT: Can reuse existing caching mechanisms
   */
  const getBalance = async (address: string, token?: string): Promise<string> => {
    // Implementation will reuse existing balance services
    console.log('LINE balance query to be implemented');
    return '0';
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
