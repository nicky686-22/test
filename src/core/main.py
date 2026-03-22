#!/usr/bin/env python3
"""
SwarmIA Main Entry Point
Enhanced AI Assistant System - "Brutal in Every Sense"
"""

import os
import sys
import logging
import asyncio
import signal
import time
from pathlib import Path
from datetime import datetime
from typing import Dict
import uvicorn

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.core.supervisor import Supervisor
from src.core.updater import create_update_checker, check_and_notify_updates
from src.agents.chat import create_chat_agent
from src.agents.aggressive import create_aggressive_agent
from src.gateway.communication import setup_communication_gateway
from src.ui.server import create_app

class SwarmIA:
    """
    Main SwarmIA application class
    Orchestrates all components of the enhanced AI assistant system
    """
    
    def __init__(self):
        self.config = Config()
        self.logger = self._setup_logger()
        
        # Core components
        self.supervisor = None
        self.chat_agent = None
        self.aggressive_agent = None
        self.gateway = None
        self.web_app = None
        self.updater = None
        
        # State
        self.running = False
        self.start_time = None
        
        # Statistics
        self.stats = {
            "start_time": None,
            "uptime": None,
            "requests_processed": 0,
            "messages_handled": 0,
            "errors": 0
        }
        
        self.logger.info("SwarmIA initialized")
    
    def _setup_logger(self):
        """Setup main application logger"""
        logger = logging.getLogger("swarmia.main")
        logger.setLevel(logging.INFO)
        
        # File handler
        log_file = self.config.LOGS_DIR / "swarmia.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def initialize_components(self):
        """Initialize all SwarmIA components"""
        self.logger.info("Initializing SwarmIA components...")
        
        try:
            # 1. Initialize Supervisor
            self.supervisor = Supervisor()
            self.logger.info("✓ Supervisor initialized")
            
            # 2. Initialize Chat Agent
            self.chat_agent = create_chat_agent(self.supervisor, self.config)
            self.logger.info("✓ Chat Agent initialized")
            
            # 3. Initialize Aggressive Agent
            self.aggressive_agent = create_aggressive_agent(self.supervisor, self.config)
            self.logger.info("✓ Aggressive Agent initialized")
            
            # 4. Initialize Update Checker
            self.updater = create_update_checker(self.config)
            self.logger.info("✓ Update Checker initialized")
            
            # 5. Initialize Communication Gateway
            self.gateway = setup_communication_gateway(self.config)
            self.logger.info("✓ Communication Gateway initialized")
            
            # 6. Initialize Web Application
            self.web_app = create_app(self.config, self.supervisor, self.chat_agent, self.aggressive_agent, self.gateway, self.updater)
            self.logger.info("✓ Web Application initialized")
            
            # Register signal handlers
            self._register_signal_handlers()
            
            self.logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            return False
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self.logger.debug("Signal handlers registered")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.stop()
    
    def start(self):
        """Start the SwarmIA system"""
        if self.running:
            self.logger.warning("SwarmIA is already running")
            return False
        
        self.logger.info("🚀 Starting SwarmIA Enhanced AI Assistant...")
        self.start_time = datetime.now()
        self.stats["start_time"] = self.start_time
        
        try:
            # Initialize components
            if not self.initialize_components():
                raise RuntimeError("Component initialization failed")
            
            # Start components in order
            self.logger.info("Starting components...")
            
            # 1. Start Supervisor
            self.supervisor.start()
            self.logger.info("✓ Supervisor started")
            
            # 2. Start Chat Agent
            self.chat_agent.start()
            self.logger.info("✓ Chat Agent started")
            
            # 3. Start Aggressive Agent
            self.aggressive_agent.start()
            self.logger.info("✓ Aggressive Agent started")
            
            # 4. Start Communication Gateway
            self.gateway.start()
            self.logger.info("✓ Communication Gateway started")
            
            # 5. Check for updates
            self._check_updates_on_start()
            
            # Mark as running
            self.running = True
            
            # Display startup banner
            self._display_startup_banner()
            
            # Start web server in background thread
            self._start_web_server()
            
            self.logger.info("🎉 SwarmIA started successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start SwarmIA: {e}")
            self.stats["errors"] += 1
            return False
    
    def _display_startup_banner(self):
        """Display startup banner with system information"""
        local_ip = self.config.get_local_ip()
        port = self.config.SERVER_PORT
        
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                   🚀 SwarmIA is Running!                    ║
║          Enhanced AI Assistant - 'Brutal in Every Sense'    ║
╚══════════════════════════════════════════════════════════════╝

📡 ACCESS INFORMATION:
  Local URL:    http://{local_ip}:{port}
  Dashboard:    http://{local_ip}:{port}/dashboard
  API Docs:     http://{local_ip}:{port}/docs

🔐 DEFAULT CREDENTIALS:
  Username:     admin
  Password:     admin
  ⚠️  CHANGE PASSWORD ON FIRST LOGIN!

⚙️  SYSTEM STATUS:
  Supervisor:   ✓ Running
  Chat Agent:   ✓ Running  
  Gateway:      ✓ Running
  Web Server:   ✓ Running on port {port}

📊 COMPONENTS:
  • Priority-based task processing
  • WhatsApp/Telegram integration
  • DeepSeek API & Llama local support
  • Agents that complete tasks fully
  • Elegant dashboard for monitoring

💡 Quick Start:
  1. Open dashboard in browser
  2. Login with admin/admin
  3. Change password immediately
  4. Configure AI provider
  5. Setup communication channels

Need help? Check: {self.config.BASE_DIR}/docs/
══════════════════════════════════════════════════════════════
"""
        print(banner)
        
        # Also log to file
        self.logger.info(f"SwarmIA accessible at http://{local_ip}:{port}")
    
    def _start_web_server(self):
        """Start the web server in a background thread"""
        import threading
        
        def run_server():
            uvicorn.run(
                self.web_app,
                host=self.config.SERVER_HOST,
                port=self.config.SERVER_PORT,
                log_level="info",
                access_log=True
            )
        
        # Start server in background thread
        server_thread = threading.Thread(
            target=run_server,
            daemon=True,
            name="web-server"
        )
        server_thread.start()
        
        self.logger.info(f"Web server started on {self.config.SERVER_HOST}:{self.config.SERVER_PORT}")
    
    def _check_updates_on_start(self):
        """Check for updates on startup"""
        try:
            update_available, update_info = self.updater.check_for_updates(force=True)
            if update_available:
                self.logger.warning(f"Update available: {update_info['current_version']} -> {update_info['latest_version']}")
                
                # Notify via gateway if configured
                if self.gateway and self.updater.settings.get("notify_on_update", True):
                    self._notify_about_update(update_info)
        except Exception as e:
            self.logger.error(f"Failed to check updates on startup: {e}")
    
    def _start_periodic_updates(self):
        """Start periodic update checks"""
        import threading
        
        def periodic_check():
            while self.running:
                try:
                    # Check every 6 hours
                    time.sleep(6 * 3600)
                    
                    if self.running and self.updater.should_check():
                        update_available, update_info = self.updater.check_for_updates()
                        if update_available and self.updater.settings.get("notify_on_update", True):
                            self._notify_about_update(update_info)
                except Exception as e:
                    self.logger.error(f"Periodic update check failed: {e}")
        
        update_thread = threading.Thread(
            target=periodic_check,
            daemon=True,
            name="periodic-update-checker"
        )
        update_thread.start()
        self.logger.info("Periodic update checks started")
    
    def _notify_about_update(self, update_info: Dict):
        """Notify about available update"""
        try:
            message = (
                f"🚀 *SwarmIA Update Available!*\n\n"
                f"*Current:* v{update_info['current_version']}\n"
                f"*Latest:* v{update_info['latest_version']}\n\n"
                f"*Release:* {update_info['release_name']}\n\n"
                f"Update from dashboard or run:\n"
                f"`sudo swarmia --update`"
            )
            
            # This would send to configured admin users
            # For now, just log
            self.logger.info(f"Update notification: {message}")
            
            # Mark as notified
            self.updater.mark_notified()
            
        except Exception as e:
            self.logger.error(f"Failed to send update notification: {e}")
    
    def stop(self):
        """Stop the SwarmIA system gracefully"""
        if not self.running:
            self.logger.warning("SwarmIA is not running")
            return
        
        self.logger.info("🛑 Stopping SwarmIA...")
        
        try:
            # Stop components in reverse order
            if self.gateway:
                self.gateway.stop()
                self.logger.info("✓ Communication Gateway stopped")
            
            if self.aggressive_agent:
                self.aggressive_agent.stop()
                self.logger.info("✓ Aggressive Agent stopped")
            
            if self.chat_agent:
                self.chat_agent.stop()
                self.logger.info("✓ Chat Agent stopped")
            
            if self.supervisor:
                self.supervisor.stop()
                self.logger.info("✓ Supervisor stopped")
            
            # Update statistics
            if self.start_time:
                uptime = datetime.now() - self.start_time
                self.stats["uptime"] = str(uptime)
            
            self.running = False
            self.logger.info("✅ SwarmIA stopped gracefully")
            
            # Display shutdown message
            print("\n" + "="*60)
            print("🛑 SwarmIA has been stopped")
            print(f"⏱️  Uptime: {self.stats['uptime']}")
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            self.stats["errors"] += 1
            return False
    
    def get_status(self):
        """Get system status"""
        if not self.running:
            return {"status": "stopped", "message": "SwarmIA is not running"}
        
        # Calculate uptime
        uptime = datetime.now() - self.start_time
        
        # Get component statuses
        components = {
            "supervisor": self.supervisor is not None,
            "chat_agent": self.chat_agent is not None,
            "gateway": self.gateway is not None,
            "web_app": self.web_app is not None
        }
        
        # Get statistics from components
        stats = {
            **self.stats,
            "uptime": str(uptime),
            "components": components,
            "supervisor_stats": self.supervisor.get_stats() if self.supervisor else {},
            "chat_agent_stats": self.chat_agent.get_stats() if self.chat_agent else {},
            "gateway_stats": self.gateway.get_stats() if self.gateway else {},
            "config": {
                "server_host": self.config.SERVER_HOST,
                "server_port": self.config.SERVER_PORT,
                "base_dir": str(self.config.BASE_DIR)
            }
        }
        
        return {
            "status": "running",
            "start_time": self.start_time.isoformat(),
            "uptime": str(uptime),
            "stats": stats
        }
    
    def run_forever(self):
        """Run SwarmIA forever (blocking)"""
        if not self.start():
            self.logger.error("Failed to start SwarmIA")
            return 1
        
        try:
            # Keep the main thread alive
            while self.running:
                # Update uptime
                if self.start_time:
                    self.stats["uptime"] = str(datetime.now() - self.start_time)
                
                # Sleep to prevent busy waiting
                import time
                time.sleep(1)
                
                # Check for shutdown conditions
                # (In a real implementation, you might check for specific conditions)
                
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        finally:
            self.stop()
        
        return 0


def main():
    """Main entry point"""
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="SwarmIA Enhanced AI Assistant")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--stop", action="store_true", help="Stop running instance")
    parser.add_argument("--config", help="Path to config file")
    
    args = parser.parse_args()
    
    # Show version
    if args.version:
        print("SwarmIA v1.0.0 - Enhanced AI Assistant")
        print("'Brutal in Every Sense' compared to OpenClaw")
        return 0
    
    # Create and run SwarmIA
    swarmia = SwarmIA()
    
    # Handle stop command
    if args.stop:
        # This would need to communicate with a running instance
        print("Stop functionality requires service management")
        return 0
    
    # Handle status command
    if args.status:
        status = swarmia.get_status()
        print(json.dumps(status, indent=2, default=str))
        return 0
    
    # Run normally
    return swarmia.run_forever()


if __name__ == "__main__":
    import json
    sys.exit(main())