            # Create new connection
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                connect_kwargs = {
                    "hostname": host,
                    "username": username,
                    "timeout": self.aggressive_config["ssh"]["timeout"],
                    "banner_timeout": self.aggressive_config["ssh"]["banner_timeout"]
                }
                
                if key_path and os.path.exists(key_path):
                    connect_kwargs["key_filename"] = key_path
                elif password:
                    connect_kwargs["password"] = password
                else:
                    # Try key from default location
                    default_key = Path.home() / ".ssh" / "id_rsa"
                    if default_key.exists():
                        connect_kwargs["key_filename"] = str(default_key)
                
                client.connect(**connect_kwargs)
                
                self.ssh_connections[connection_key] = client
                self.logger.info(f"SSH connection established: {connection_key}")
                
                return client
                
            except Exception as e:
                client.close()
                raise ConnectionError(f"Failed to connect to {host}: {e}")
    
    def _close_ssh_connection(self, connection_key: str):
        """Close SSH connection"""
        with self.ssh_lock:
            if connection_key in self.ssh_connections:
                try:
                    self.ssh_connections[connection_key].close()
                except:
                    pass
                del self.ssh_connections[connection_key]
                self.logger.info(f"SSH connection closed: {connection_key}")
    
    def _close_all_ssh_connections(self):
        """Close all SSH connections"""
        with self.ssh_lock:
            for connection_key in list(self.ssh_connections.keys()):
                self._close_ssh_connection(connection_key)
    
    def _is_command_allowed(self, command: str) -> bool:
        """Check if command is allowed"""
        if not self.aggressive_config["system_commands"]["enabled"]:
            return False
        
        # Get command name (first word)
        cmd_name = command.split()[0] if command else ""
        
        # Check against allowed commands
        allowed_commands = self.aggressive_config["system_commands"]["allowed_commands"]
        
        # Check exact match or prefix
        for allowed in allowed_commands:
            if cmd_name == allowed or cmd_name.startswith(f"{allowed} "):
                return True
        
        return False
    
    def _is_path_allowed(self, path: str) -> bool:
        """Check if path is allowed for access"""
        if not self.aggressive_config["file_access"]["enabled"]:
            return False
        
        path_obj = Path(path).resolve()
        
        # Check blocked paths first
        for blocked in self.aggressive_config["file_access"]["blocked_paths"]:
            blocked_path = Path(blocked).resolve()
            try:
                if path_obj.is_relative_to(blocked_path):
                    return False
            except:
                pass
        
        # Check allowed paths
        for allowed in self.aggressive_config["file_access"]["allowed_paths"]:
            allowed_path = Path(allowed).resolve()
            try:
                if path_obj.is_relative_to(allowed_path):
                    return True
            except:
                pass
        
        return False
    
    def _simple_network_scan(self, network: str, ports: List[int], timeout: int) -> List[Dict]:
        """Simple network scan implementation"""
        results = []
        
        # Parse network (simple implementation)
        # For production, use python-nmap or similar
        if network == "localhost" or network == "127.0.0.1":
            hosts = ["127.0.0.1"]
        elif network.endswith("/24"):
            base = network[:-3]
            hosts = [f"{base}.{i}" for i in range(1, 255)]
        else:
            hosts = [network]
        
        # Limit hosts
        max_hosts = self.aggressive_config["network"]["max_hosts"]
        hosts = hosts[:max_hosts]
        
        for host in hosts:
            host_info = {"host": host, "ports": []}
            
            for port in ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    
                    if result == 0:
                        host_info["ports"].append({
                            "port": port,
                            "status": "open",
                            "service": self._get_service_name(port)
                        })
                    else:
                        host_info["ports"].append({
                            "port": port,
                            "status": "closed"
                        })
                        
                except:
                    host_info["ports"].append({
                        "port": port,
                        "status": "error"
                    })
            
            # Only add if any ports are open
            open_ports = [p for p in host_info["ports"] if p.get("status") == "open"]
            if open_ports:
                host_info["open_ports_count"] = len(open_ports)
                results.append(host_info)
        
        return results
    
    def _get_service_name(self, port: int) -> str:
        """Get service name for port"""
        common_ports = {
            22: "SSH",
            80: "HTTP",
            443: "HTTPS",
            3000: "Node.js/Development",
            8080: "HTTP-Alt",
            9000: "Sonar/PhpMyAdmin"
        }
        return common_ports.get(port, "Unknown")
    
    def _get_cpu_info(self) -> Dict:
        """Get CPU information"""
        try:
            import psutil
            return {
                "cores": psutil.cpu_count(),
                "usage_percent": psutil.cpu_percent(interval=1),
                "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None
            }
        except:
            return {"error": "psutil not available"}
    
    def _get_memory_info(self) -> Dict:
        """Get memory information"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total_gb": mem.total / (1024**3),
                "available_gb": mem.available / (1024**3),
                "used_percent": mem.percent,
                "used_gb": mem.used / (1024**3)
            }
        except:
            return {"error": "psutil not available"}
    
    def _get_disk_info(self) -> Dict:
        """Get disk information"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            return {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
                "used_percent": disk.percent
            }
        except:
            return {"error": "psutil not available"}
    
    def _get_network_info(self) -> Dict:
        """Get network information"""
        try:
            import psutil
            net_io = psutil.net_io_counters()
            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        except:
            return {"error": "psutil not available"}
    
    def _get_processes_info(self) -> List[Dict]:
        """Get processes information"""
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except:
                    pass
            return processes[:50]  # Limit to 50 processes
        except:
            return {"error": "psutil not available"}
    
    def _audit_log_action(self, task: Dict, success: bool, result: Any):
        """Log action to audit log"""
        if not self.aggressive_config["security"]["audit_all_actions"]:
            return
        
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task.get("task_id"),
            "task_type": task.get("type"),
            "data": task.get("data", {}),
            "success": success,
            "result_summary": str(result)[:500] if result else None,
            "user": task.get("source", "unknown")
        }
        
        try:
            with open(self.audit_log, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')
        except:
            pass
    
    def queue_task(self, task: Dict):
        """Queue a task for processing"""
        self.task_queue.put(task)
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        uptime = datetime.now() - self.stats["start_time"]
        
        return {
            **self.stats,
            "uptime": str(uptime),
            "ssh_connections_active": len(self.ssh_connections),
            "queue_size": self.task_queue.qsize(),
            "config": {
                "enabled": self.aggressive_config["enabled"],
                "ssh_enabled": self.aggressive_config["ssh"]["enabled"],
                "commands_enabled": self.aggressive_config["system_commands"]["enabled"],
                "file_access_enabled": self.aggressive_config["file_access"]["enabled"]
            }
        }
    
    def update_config(self, config: Dict):
        """Update agent configuration"""
        self.aggressive_config.update(config)
        
        # Save to file
        config_file = self.config.CONFIG_DIR / "aggressive_config.json"
        try:
            with open(config_file, 'w') as f:
                json.dump(self.aggressive_config, f, indent=2)
            self.logger.info("Aggressive agent configuration updated")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")


# Factory function
def create_aggressive_agent(supervisor: Supervisor, config: Config) -> AggressiveAgent:
    """
    Create aggressive agent instance
    
    Args:
        supervisor: Supervisor instance
        config: Configuration object
    
    Returns:
        Aggressive agent instance
    """
    return AggressiveAgent(supervisor, config)


# Example usage
def example_usage():
    """Example of using aggressive agent"""
    from core.config import Config
    from core.supervisor import Supervisor
    
    print("⚡ Aggressive Agent Example")
    
    config = Config()
    supervisor = Supervisor()
    agent = create_aggressive_agent(supervisor, config)
    
    # Start agent
    if agent.start():
        print("✅ Aggressive agent started")
        
        # Example: Get system info
        task = {
            "task_id": "test_sysinfo",
            "type": "system_info",
            "data": {"type": "cpu"},
            "source": "example"
        }
        
        agent.queue_task(task)
        print("📨 System info task queued")
        
        # Wait a bit
        import time
        time.sleep(2)
        
        # Get stats
        stats = agent.get_stats()
        print(f"\n📊 Aggressive Agent Stats:")
        print(f"  Tasks completed: {stats['tasks_completed']}")
        print(f"  Commands executed: {stats['commands_executed']}")
        print(f"  SSH connections: {stats['ssh_connections_active']}")
        
        # Stop agent
        agent.stop()
        print("\n🛑 Aggressive agent stopped")
    
    else:
        print("❌ Failed to start aggressive agent")


if __name__ == "__main__":
    import sys
    example_usage()