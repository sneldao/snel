/**
 * LINE Mini-dApp Layout
 * ENHANCEMENT: Extends existing layout pattern for LINE platform
 * CLEAN: Separated LINE-specific layout concerns
 */

import { Metadata } from 'next';
import { ChakraProvider } from '@chakra-ui/react';
import { Providers } from '../providers';
import { LINEProvider } from '../../providers/LINEProvider';

export const metadata: Metadata = {
  title: 'SNEL - AI DeFi Assistant | LINE Mini-dApp',
  description: 'Chat with your crypto portfolio and execute DeFi operations through LINE',
  keywords: ['DeFi', 'LINE', 'AI', 'Crypto', 'USDT', 'Kaia', 'Mini-dApp'],
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no',
  themeColor: '#00C73C', // LINE brand green
  
  // LINE Mini-dApp specific meta tags
  other: {
    'line:card': 'summary_large_image',
    'line:site': '@SNEL_DeFi',
    'line:creator': '@SNEL_DeFi',
  },

  // Open Graph for LINE sharing
  openGraph: {
    title: 'SNEL - AI DeFi Assistant for LINE',
    description: 'Execute DeFi operations with natural language commands in LINE',
    url: 'https://snel-app.netlify.app/line',
    siteName: 'SNEL',
    images: [
      {
        url: 'https://snel-app.netlify.app/line-og-image.png',
        width: 1200,
        height: 630,
        alt: 'SNEL LINE Mini-dApp',
      },
    ],
    locale: 'en_US',
    type: 'website',
  },
};

/**
 * LINE-specific layout wrapper
 * MODULAR: Composable layout that wraps existing providers
 */
export default function LINELayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* LINE Mini-dApp SDK */}
        <script 
          src="https://static.line-scdn.net/liff/edge/2/sdk.js"
          async
        />
        
        {/* LINE-specific meta tags for optimal mobile experience */}
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="SNEL" />
        
        {/* Preload critical LINE resources */}
        <link 
          rel="preconnect" 
          href="https://static.line-scdn.net"
          crossOrigin="anonymous"
        />
      </head>
      
      <body className="line-platform">
        {/* ENHANCEMENT: Reuse existing providers with LINE additions */}
        <Providers>
          <LINEProvider>
            <ChakraProvider>
              {/* LINE-optimized container */}
              <div className="line-container">
                {children}
              </div>
            </ChakraProvider>
          </LINEProvider>
        </Providers>
        
        {/* LINE-specific initialization script */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              // Initialize LINE Mini-dApp
              if (typeof liff !== 'undefined') {
                liff.init({
                  liffId: process.env.NEXT_PUBLIC_LIFF_ID || ''
                }).then(() => {
                  console.log('LIFF initialized successfully');
                }).catch((err) => {
                  console.error('LIFF initialization failed:', err);
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
