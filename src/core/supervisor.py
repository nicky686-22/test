            return {
                **self.stats,
                "uptime": str(uptime),
                "tasks_by_status": tasks_by_status,
                "agents_by_type": agents_by_type,
                "total_tasks": len(self.tasks),
                "total_agents": len(self.agents),
                "queue_size": self.task_queue.qsize(),
                "capabilities": list(self.agent_capabilities.keys())
            }
    
    def cancel_task(self, task_id: str, reason: str = "Cancelled by user"):
        """Cancel a task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            task.status = TaskStatus.CANCELLED
            task.error = reason
            task.completed_at = datetime.now()
            
            # Remove from agent if assigned
            if task.assigned_agent:
                agent = self.agents.get(task.assigned_agent)
                if agent and task_id in agent.current_tasks:
                    agent.current_tasks.remove(task_id)
            
            self.logger.info(f"Task cancelled: {task_id} - {reason}")
            return True
    
    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status != TaskStatus.FAILED:
                return False
            
            # Reset task for retry
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.completed_at = None
            task.assigned_agent = None
            task.error = None
            task.retry_count += 1
            
            # Requeue
            priority_value = 5 - task.priority.value
            self.task_queue.put((priority_value, time.time(), task_id))
            
            self.logger.info(f"Task retry scheduled: {task_id} (attempt {task.retry_count})")
            return True
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed/failed tasks"""
        with self.lock:
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if task.completed_at and task.completed_at.timestamp() < cutoff_time:
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            if tasks_to_remove:
                self.logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
    
    def emergency_stop(self):
        """Emergency stop - cancel all running tasks"""
        with self.lock:
            running_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]
            
            for task in running_tasks:
                task.status = TaskStatus.CANCELLED
                task.error = "Emergency stop"
                task.completed_at = datetime.now()
                
                if task.assigned_agent:
                    agent = self.agents.get(task.assigned_agent)
                    if agent and task.id in agent.current_tasks:
                        agent.current_tasks.remove(task.id)
            
            self.logger.warning(f"Emergency stop: cancelled {len(running_tasks)} tasks")


# Factory function
def create_supervisor(config: Optional[Config] = None) -> Supervisor:
    """
    Create supervisor instance
    
    Args:
        config: Configuration object (optional)
    
    Returns:
        Supervisor instance
    """
    return Supervisor(config)


# Example usage
def example_usage():
    """Example of using supervisor"""
    from core.config import Config
    
    print("👨‍💼 Supervisor Example")
    
    config = Config()
    supervisor = create_supervisor(config)
    
    # Start supervisor
    if supervisor.start():
        print("✅ Supervisor started")
        
        # Create some example tasks
        task1_id = supervisor.create_task(
            task_type="process_message",
            data={"platform": "telegram", "sender": "user123", "text": "Hello"},
            priority=TaskPriority.CRITICAL,
            source="gateway"
        )
        
        task2_id = supervisor.create_task(
            task_type="complete_conversation",
            data={"conversation_id": "conv_123"},
            priority=TaskPriority.NORMAL,
            source="dashboard"
        )
        
        print(f"📨 Created tasks: {task1_id}, {task2_id}")
        
        # Wait a bit
        import time
        time.sleep(2)
        
        # Get stats
        stats = supervisor.get_stats()
        print(f"\n📊 Supervisor Stats:")
        print(f"  Tasks created: {stats['tasks_created']}")
        print(f"  Tasks completed: {stats['tasks_completed']}")
        print(f"  Agents registered: {stats['agents_registered']}")
        print(f"  Queue size: {stats['queue_size']}")
        
        # Get tasks
        tasks = supervisor.get_tasks()
        print(f"\n📋 Tasks ({len(tasks)} total):")
        for task in tasks[:3]:  # Show first 3
            print(f"  - {task.id}: {task.type} ({task.status.value})")
        
        # Stop supervisor
        supervisor.stop()
        print("\n🛑 Supervisor stopped")
    
    else:
        print("❌ Failed to start supervisor")


if __name__ == "__main__":
    import sys
    example_usage()