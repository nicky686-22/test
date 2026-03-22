                self.deepseek_handler = create_deepseek_handler(self.config, sync=True)
            
            if "api_key" in config:
                self.deepseek_handler.update_config(**config)
                self.active_ai = "deepseek"
                self.logger.info("DeepSeek configuration updated")
        
        elif ai_type == "llama":
            if not self.llama_handler:
                self.llama_handler = create_llama_handler(self.config)
            
            if "model_path" in config:
                self.llama_handler.update_config(**config)
                self.active_ai = "llama"
                self.logger.info("Llama configuration updated")


# Factory function
def create_chat_agent(supervisor: Supervisor, config: Config) -> ChatAgent:
    """
    Create chat agent instance
    
    Args:
        supervisor: Supervisor instance
        config: Configuration object
    
    Returns:
        Chat agent instance
    """
    return ChatAgent(supervisor, config)


# Example usage
def example_usage():
    """Example of using chat agent"""
    from core.config import Config
    from core.supervisor import Supervisor
    
    print("💬 Chat Agent Example")
    
    config = Config()
    supervisor = Supervisor()
    agent = create_chat_agent(supervisor, config)
    
    # Start agent
    if agent.start():
        print("✅ Chat agent started")
        
        # Example task
        task = {
            "task_id": "test_123",
            "type": "process_message",
            "data": {
                "platform": "telegram",
                "sender": "user123",
                "text": "Hello, can you help me with a task?",
                "message_id": "msg_001"
            }
        }
        
        agent.queue_task(task)
        print("📨 Task queued for processing")
        
        # Wait a bit
        import time
        time.sleep(2)
        
        # Get stats
        stats = agent.get_stats()
        print(f"\n📊 Chat Agent Stats:")
        print(f"  Messages processed: {stats['messages_processed']}")
        print(f"  Active conversations: {stats['active_conversations']}")
        print(f"  AI handler: {stats['ai_handler'] or 'None'}")
        
        # Stop agent
        agent.stop()
        print("\n🛑 Chat agent stopped")
    
    else:
        print("❌ Failed to start chat agent")


if __name__ == "__main__":
    import sys
    example_usage()