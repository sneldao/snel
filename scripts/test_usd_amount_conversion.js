#!/usr/bin/env node

/**
 * Test script to demonstrate USD amount conversion for swaps
 * This shows how the system should handle "swap $1 of ETH for USDC"
 */

const BASE_URL = 'http://127.0.0.1:8000';

async function testUSDAmountConversion() {
  console.log('🚀 Testing USD Amount Conversion for Swaps\n');

  // Test Case 1: USD amount with "of" syntax
  console.log('📋 Test Case 1: "swap $1 of ETH for USDC"');
  
  const swapResponse1 = await fetch(`${BASE_URL}/api/v1/chat/process-command`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      command: 'swap $1 of ETH for USDC',
      wallet_address: '0x55A5705453Ee82c742274154136Fce8149597058',
      chain_id: 1
    })
  });

  const swapData1 = await swapResponse1.json();
  
  console.log('✅ Response:');
  console.log(`   Agent Type: ${swapData1.agent_type}`);
  console.log(`   Message: ${swapData1.content?.message || swapData1.content}`);
  console.log(`   Amount: ${swapData1.content?.amount}`);
  console.log(`   Token In: ${swapData1.content?.token_in}`);
  console.log(`   Token Out: ${swapData1.content?.token_out}`);

  // Test Case 2: USD amount with "worth of" syntax
  console.log('\n📋 Test Case 2: "swap $100 worth of USDC for ETH"');
  
  const swapResponse2 = await fetch(`${BASE_URL}/api/v1/chat/process-command`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      command: 'swap $100 worth of USDC for ETH',
      wallet_address: '0x55A5705453Ee82c742274154136Fce8149597058',
      chain_id: 1
    })
  });

  const swapData2 = await swapResponse2.json();
  
  console.log('✅ Response:');
  console.log(`   Agent Type: ${swapData2.agent_type}`);
  console.log(`   Message: ${swapData2.content?.message || swapData2.content}`);
  console.log(`   Amount: ${swapData2.content?.amount}`);
  console.log(`   Token In: ${swapData2.content?.token_in}`);
  console.log(`   Token Out: ${swapData2.content?.token_out}`);

  // Test Case 3: Regular token amount (should work as before)
  console.log('\n📋 Test Case 3: "swap 0.01 ETH for USDC"');
  
  const swapResponse3 = await fetch(`${BASE_URL}/api/v1/chat/process-command`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      command: 'swap 0.01 ETH for USDC',
      wallet_address: '0x55A5705453Ee82c742274154136Fce8149597058',
      chain_id: 1
    })
  });

  const swapData3 = await swapResponse3.json();
  
  console.log('✅ Response:');
  console.log(`   Agent Type: ${swapData3.agent_type}`);
  console.log(`   Message: ${swapData3.content?.message || swapData3.content}`);
  console.log(`   Amount: ${swapData3.content?.amount}`);
  console.log(`   Token In: ${swapData3.content?.token_in}`);
  console.log(`   Token Out: ${swapData3.content?.token_out}`);

  console.log('\n🎉 USD amount conversion test completed!');
  console.log('\n📝 Expected behavior:');
  console.log('   - Test Case 1 & 2: Should convert USD amounts to token amounts');
  console.log('   - Test Case 3: Should use the specified token amount directly');
  console.log('   - All cases: Should successfully prepare swap transactions');
}

// Run the test
testUSDAmountConversion().catch(console.error);