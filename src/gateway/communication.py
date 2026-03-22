                # Use polling
                self.application.run_polling(allowed_updates=Update.ALL_TYPES)
                self.logger.info("Telegram bot started with polling")
            
            self.logger.info("Telegram handler started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Telegram handler: {e}")
            raise
    
    def stop(self):
        """Stop the Telegram bot"""
        if self.application:
            self.application.stop()
            self.application = None
        self.logger.info("Telegram handler stopped")
    
    async def _handle_start(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        user_id = str(update.effective_user.id)
        
        # Check if user is allowed
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text(
                "⚠️ You are not authorized to use this bot.\n"
                "Please contact the administrator."
            )
            return
        
        welcome_text = (
            "🤖 *Welcome to SwarmIA!*\n\n"
            "I'm your enhanced AI assistant, independent from OpenClaw.\n\n"
            "✨ *Features:*\n"
            "• Priority-based task processing\n"
            "• WhatsApp & Telegram integration\n"
            "• DeepSeek API & Llama local support\n"
            "• Agents that complete tasks fully\n"
            "• Elegant dashboard for monitoring\n\n"
            "Type /help to see available commands."
        )
        
        await update.message.reply_text(welcome_text, parse_mode="Markdown")
    
    async def _handle_help(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        help_text = (
            "🆘 *SwarmIA Help*\n\n"
            "*Available Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/status - Check system status\n"
            "/tasks - List recent tasks\n"
            "/agents - List available agents\n\n"
            "*Just send a message* to interact with the AI assistant.\n"
            "Your messages get *CRITICAL priority* and are never queued!"
        )
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def _handle_message(self, update: Update, context: CallbackContext):
        """Handle incoming messages"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name
        text = update.message.text
        
        # Check if user is allowed
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text(
                "⚠️ You are not authorized to use this bot.\n"
                "Please contact the administrator."
            )
            return
        
        # Forward to gateway
        self.gateway.receive_message(
            platform="telegram",
            sender=user_id,
            text=text,
            message_id=update.message.message_id,
            username=username,
            chat_id=update.effective_chat.id
        )
        
        # Send acknowledgment
        await update.message.reply_text(
            "✅ Message received and queued for processing with *CRITICAL priority*.\n"
            "An agent will respond shortly...",
            parse_mode="Markdown"
        )
    
    def send_message(self, recipient: str, text: str) -> bool:
        """Send Telegram message"""
        try:
            asyncio.run(self._async_send_message(recipient, text))
            return True
        except Exception as e:
            self.logger.error(f"Telegram send error: {e}")
            return False
    
    async def _async_send_message(self, chat_id: str, text: str):
        """Async method to send Telegram message"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            self.logger.error(f"Async Telegram send error: {e}")
            raise


class MockWhatsAppHandler(WhatsAppHandler):
    """Mock WhatsApp handler for development"""
    
    def send_message(self, recipient: str, text: str) -> bool:
        """Mock send - just log"""
        self.logger.info(f"[MOCK] Would send WhatsApp to {recipient}: {text[:50]}...")
        return True
    
    def handle_webhook(self, request_data: Dict):
        """Mock webhook handler"""
        self.logger.info(f"[MOCK] Webhook received: {request_data}")
        return True


class MockTelegramHandler(TelegramHandler):
    """Mock Telegram handler for development"""
    
    def start(self):
        self.logger.info("[MOCK] Telegram handler started (mock mode)")
    
    def send_message(self, recipient: str, text: str) -> bool:
        """Mock send - just log"""
        self.logger.info(f"[MOCK] Would send Telegram to {recipient}: {text[:50]}...")
        return True


# Utility functions
def setup_communication_gateway(config: Config) -> CommunicationGateway:
    """Factory function to create and setup communication gateway"""
    gateway = CommunicationGateway(config)
    
    # Example: Register a default message handler
    def default_message_handler(message: Dict):
        """Default handler that logs messages"""
        gateway.logger.info(f"Default handler: {message.get('sender')} said: {message.get('text', '')[:100]}")
    
    gateway.register_message_handler(default_message_handler)
    
    return gateway


def main():
    """Main function for testing"""
    from core.config import Config
    
    print("🚀 Testing SwarmIA Communication Gateway")
    
    config = Config()
    gateway = setup_communication_gateway(config)
    
    # Start gateway
    if gateway.start():
        print("✅ Gateway started successfully")
        
        # Example: Send a test message
        gateway.send_message(
            platform="telegram",
            recipient="123456789",
            text="Test message from SwarmIA Gateway"
        )
        
        # Keep running
        try:
            while True:
                stats = gateway.get_stats()
                print(f"\n📊 Gateway Stats:")
                print(f"  Messages received: {stats['messages_received']}")
                print(f"  Messages sent: {stats['messages_sent']}")
                print(f"  Uptime: {stats['uptime']}")
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n🛑 Stopping gateway...")
            gateway.stop()
    
    else:
        print("❌ Failed to start gateway")


if __name__ == "__main__":
    import sys
    import time
    main()