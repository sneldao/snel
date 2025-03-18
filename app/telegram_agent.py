async def _handle_keys_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /keys command to explain key custody.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        # Create buttons for wallet management if they have a wallet
        buttons = []
        if wallet_address:
            buttons.append([
                {"text": "📱 Open Web App", "url": "https://snel-pointless.vercel.app"}
            ])
        
        # Check if we're using SmartWalletService or WalletService
        is_smart_wallet = isinstance(self.wallet_service, SmartWalletService) if SMART_WALLET_AVAILABLE else False
        
        if is_smart_wallet:
            # Coinbase CDP wallet information
            return {
                "content": "🔐 **Key Custody & Security**\n\n" +
                    "Your wallet security is our priority. Here's how it works:\n\n" +
                    "• Your wallet is powered by Coinbase Developer Platform (CDP)\n" +
                    "• CDP creates an ERC-4337 compatible smart wallet for you\n" +
                    "• Your private keys are securely managed by CDP\n" +
                    "• The wallet uses Account Abstraction technology for improved security and usability\n" +
                    "• YOU maintain full control of your wallet through your Telegram account\n" +
                    "• Our bot NEVER has access to your private keys\n\n" +
                    "For full wallet management including advanced features, please use our web interface at:\n" +
                    "https://snel-pointless.vercel.app\n\n" +
                    "There you can access the full Coinbase CDP dashboard to manage all aspects of your wallet security.",
                "metadata": {
                    "telegram_buttons": buttons
                } if buttons else None
            }
        else:
            # Legacy/simulated wallet information
            return {
                "content": "🔐 **Key Custody & Security**\n\n" +
                    "Your wallet security is our priority. Here's how it works:\n\n" +
                    "• You're currently using a simulated wallet for testing\n" +
                    "• For a real wallet with improved security, you'll need to upgrade\n" +
                    "• Real wallets use Coinbase CDP technology with ERC-4337 Account Abstraction\n" +
                    "• Simulated wallets are perfect for learning but aren't suitable for real assets\n\n" +
                    "For full wallet management including advanced features, please use our web interface at:\n" +
                    "https://snel-pointless.vercel.app",
                "metadata": {
                    "telegram_buttons": buttons
                } if buttons else None
            } 