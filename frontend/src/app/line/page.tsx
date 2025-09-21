/**
 * LINE Mini-dApp Main Page
 * ENHANCEMENT: Extends existing MainApp for LINE platform
 * DRY: Reuses existing MainApp component with LINE-specific adaptations
 */

'use client';

import React, { useEffect } from 'react';
import { Box, Container, VStack, Alert, AlertIcon, AlertTitle, AlertDescription } from '@chakra-ui/react';
import dynamic from 'next/dynamic';

// Import platform detection
import { usePlatform } from '../../utils/platformDetection';
import { useLINE, useLINEFeatures } from '../../providers/LINEProvider';

// ENHANCEMENT: Dynamically import existing MainApp to avoid duplication
// This follows the DRY principle by reusing existing functionality
const MainApp = dynamic(() => import('../../components/MainApp'), {
  loading: () => <Box p={4}>Loading SNEL...</Box>,
  ssr: false, // LINE Mini-dApp requires client-side rendering
});

// LINE-specific wrapper component
const LINEAppWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <Box 
      className="line-app-wrapper"
      minH="100vh"
      bg="white"
      // LINE-specific styling
      sx={{
        // Remove default margins/padding that might interfere with LINE
        '& body': {
          margin: 0,
          padding: 0,
        },
        
        // Ensure proper mobile viewport
        '& .line-container': {
          maxWidth: '100vw',
          overflowX: 'hidden',
        },
        
        // LINE brand colors integration
        '& .chakra-button[data-theme="primary"]': {
          bg: '#00C73C', // LINE green
          color: 'white',
        },
      }}
    >
      {children}
    </Box>
  );
};

/**
 * LINE Mini-dApp Component
 * MODULAR: Composable wrapper around existing MainApp
 */
export default function LINEPage() {
  const { isLINE, platform, features } = usePlatform();
  const line = useLINE();
  const lineFeatures = useLINEFeatures();

  // Track LINE-specific analytics
  useEffect(() => {
    if (isLINE && line.isInitialized) {
      console.log('LINE Mini-dApp loaded', {
        platform,
        features,
        lineContext: line.context,
        userId: line.profile?.userId,
      });
    }
  }, [isLINE, line.isInitialized, platform, features, line.context, line.profile]);

  // Handle LINE initialization errors
  if (line.error) {
    return (
      <Container maxW="container.sm" py={8}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <VStack align="start" spacing={2}>
            <AlertTitle>LINE Mini-dApp Error</AlertTitle>
            <AlertDescription>
              {line.error}
              <br />
              Please try refreshing the page or contact support.
            </AlertDescription>
          </VStack>
        </Alert>
      </Container>
    );
  }

  // Show loading state while LIFF initializes
  if (isLINE && !line.isInitialized) {
    return (
      <Container maxW="container.sm" py={8}>
        <VStack spacing={4}>
          <Box>Initializing LINE Mini-dApp...</Box>
        </VStack>
      </Container>
    );
  }

  return (
    <LINEAppWrapper>
      {/* ENHANCEMENT: Wrap existing MainApp with LINE-specific features */}
      <MainApp 
        // Pass LINE-specific props to enhance existing functionality
        platform={platform}
        lineFeatures={lineFeatures}
        lineProfile={line.profile}
        isLineLoggedIn={line.isLoggedIn}
        
        // LINE-specific callbacks
        onLineLogin={line.login}
        onLineLogout={line.logout}
        onLineShare={line.shareMessage}
        onLineClose={line.closeWindow}
        
        // Wallet integration
        onLineConnectWallet={line.connectWallet}
        onLineGetAddress={line.getWalletAddress}
        onLineExecuteTransaction={line.executeTransaction}
      />
    </LINEAppWrapper>
  );
}

/**
 * Metadata moved to layout.tsx to avoid 'use client' conflict
 * CLEAN: Proper separation of server/client components
 */
