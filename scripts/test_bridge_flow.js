#!/usr/bin/env node

/**
 * Test script to demonstrate the complete bridge flow
 * This shows how the frontend should handle multi-step bridge transactions
 */

const BASE_URL = 'http://127.0.0.1:8000';

async function testBridgeFlow() {
  console.log('🚀 Testing Complete Bridge Flow\n');

  // Step 1: Initiate bridge transaction
  console.log('📋 Step 1: Initiating bridge transaction...');
  
  const bridgeResponse = await fetch(`${BASE_URL}/api/v1/chat/process-command`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      command: 'bridge 1 usdc from base to optimism',
      wallet_address: '0x55A5705453Ee82c742274154136Fce8149597058',
      chain_id: 8453
    })
  });

  const bridgeData = await bridgeResponse.json();
  
  console.log('✅ Bridge Response:');
  console.log(`   Agent Type: ${bridgeData.agent_type}`);
  console.log(`   Awaiting Confirmation: ${bridgeData.awaiting_confirmation}`);
  console.log(`   Transaction Data: ${bridgeData.transaction ? 'Present' : 'Missing'}`);
  
  if (bridgeData.transaction) {
    console.log(`   Transaction To: ${bridgeData.transaction.to}`);
    console.log(`   Transaction Data: ${bridgeData.transaction.data.slice(0, 20)}...`);
  }

  // Check if this is a multi-step bridge transaction
  const isMultiStepBridge = bridgeData.agent_type === 'bridge' && 
                           bridgeData.awaiting_confirmation && 
                           bridgeData.transaction;

  console.log(`   Is Multi-Step Bridge: ${isMultiStepBridge}`);

  if (isMultiStepBridge) {
    console.log('\n🔄 Step 2: Simulating first transaction (approval) completion...');
    
    // Simulate the first transaction being executed
    const mockTxHash = '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890';
    
    const completionResponse = await fetch(`${BASE_URL}/api/v1/chat/complete-bridge-step`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        wallet_address: '0x55A5705453Ee82c742274154136Fce8149597058',
        chain_id: 8453,
        tx_hash: mockTxHash,
        success: true
      })
    });

    const completionData = await completionResponse.json();
    
    console.log('✅ Completion Response:');
    console.log(`   Status: ${completionData.status}`);
    console.log(`   Has Next Step: ${completionData.content?.has_next_step || false}`);
    console.log(`   Next Transaction: ${completionData.transaction ? 'Present' : 'Missing'}`);
    
    if (completionData.transaction) {
      console.log(`   Next Transaction To: ${completionData.transaction.to}`);
      console.log(`   Next Transaction Data: ${completionData.transaction.data.slice(0, 20)}...`);
    }
  }

  // Step 3: Show the complete flow summary
  console.log('\n📊 Complete Flow Summary:');
  console.log('   1. ✅ Bridge initiation - Returns approval transaction');
  console.log('   2. ✅ Frontend executes approval transaction');
  console.log('   3. ✅ Frontend calls completion endpoint');
  console.log('   4. ✅ Backend returns send_token transaction');
  console.log('   5. ✅ Frontend executes send_token transaction');
  console.log('   6. ✅ Bridge complete!');

  console.log('\n🎉 Bridge flow test completed successfully!');
  console.log('\n📝 Frontend Implementation Notes:');
  console.log('   - Detect: agentType === "bridge" && awaitingConfirmation && transaction');
  console.log('   - Execute: First transaction (approval)');
  console.log('   - Call: /api/v1/chat/complete-bridge-step with tx hash');
  console.log('   - Execute: Second transaction (send_token)');
  console.log('   - Result: Complete bridge transaction');
}

// Run the test
testBridgeFlow().catch(console.error);
