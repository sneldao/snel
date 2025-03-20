import json

async def process_brian_confirmation(brian_agent, command, redis_service):
    """
    Process a confirmation for a pending Brian operation.
    
    Args:
        brian_agent: The Brian agent instance
        command: The command object
        redis_service: The Redis service instance
        
    Returns:
        CommandResponse with transaction data
    """
    try:
        # Process the confirmation with the Brian agent
        result = await brian_agent.process_brian_confirmation(
            chain_id=command.chain_id,
            wallet_address=command.wallet_address,
            user_name=command.user_name
        )
        
        # Log the entire result for debugging
        logger.info(f"Brian confirmation result: {json.dumps(result, default=str)}")
        
        # Clear the pending command and agent type
        user_id = command.wallet_address or command.creator_id
        await redis_service.clear_pending_command(user_id)
        await redis_service.delete(f"pending_command_type:{user_id}")
        
        # Get transaction data - try multiple places where it might be
        transaction_data = None
        
        # Check for transaction data in different places
        if "transaction" in result:
            transaction_data = result["transaction"]
            logger.info(f"Found transaction in result root: {json.dumps(transaction_data, default=str)}")
        elif isinstance(result.get("content"), dict) and "transaction" in result["content"]:
            transaction_data = result["content"]["transaction"]
            logger.info(f"Found transaction in result.content: {json.dumps(transaction_data, default=str)}")
        
        # Ensure the transaction data is properly formatted
        if transaction_data:
            # Make sure chainId is present and is a number
            if "chainId" in transaction_data and isinstance(transaction_data["chainId"], str):
                transaction_data["chainId"] = int(transaction_data["chainId"])
                
            # Convert value to string if it's a number
            if "value" in transaction_data and not isinstance(transaction_data["value"], str):
                transaction_data["value"] = str(transaction_data["value"])
            
            # Ensure gasLimit is present
            if "gasLimit" not in transaction_data and "gas" in transaction_data:
                transaction_data["gasLimit"] = transaction_data["gas"]
            
            logger.info(f"Final formatted transaction data: {json.dumps(transaction_data, default=str)}")
        
        # Create a rich message with transaction details
        message = "Executing transaction..."
        if isinstance(result.get("content"), dict) and "message" in result["content"]:
            message = result["content"]["message"]
        
        # Return early with the Brian result
        response = CommandResponse(
            content={
                "type": "message",
                "message": message
            },
            error_message=result.get("error"),
            metadata=result.get("metadata", {}),
            agent_type="brian",
            transaction=transaction_data,
            awaiting_confirmation=False
        )
        
        # Log the response we're returning
        logger.info(f"Returning CommandResponse with transaction: {transaction_data is not None}")
        
        return response
    except Exception as e:
        logger.error(f"Error processing Brian confirmation: {e}")
        return CommandResponse(
            content={
                "type": "error",
                "message": "An error occurred while processing the Brian confirmation."
            },
            error_message=str(e),
            metadata={},
            agent_type="brian",
            transaction=None,
            awaiting_confirmation=False
        ) 