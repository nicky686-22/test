#!/usr/bin/env python3
"""
SwarmIA Supervisor Module
Gestiona agentes, tareas y prioridades
"""

import time
import queue
import logging
import threading
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from uuid import uuid4


# ============================================================
# Enums
# ============================================================

class TaskPriority(Enum):
    """Prioridad de tareas"""
    CRITICAL = 0    # Máxima prioridad
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4  # Mínima prioridad


class TaskStatus(Enum):
    """Estado de una tarea"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(Enum):
    """Estado de un agente"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


# ============================================================
# Data Classes
# ============================================================

@dataclass
class Task:
    """Representa una tarea en el sistema"""
    id: str
    type: str
    data: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agent: Optional[str] = None
    source: str = "system"
    retry_count: int = 0
    max_retries: int = 3
    error: Optional[str] = None
    result: Optional[Any] = None


@dataclass
class Agent:
    """Representa un agente en el sistema"""
    id: str
    name: str
    type: str
    status: AgentStatus = AgentStatus.IDLE
    capabilities: List[str] = field(default_factory=list)
    current_tasks: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# Supervisor Class
# ============================================================

class Supervisor:
    """
    Supervisor central de SwarmIA
    Gestiona agentes y tareas con sistema de prioridades
    """
    
    def __init__(self, config=None):
        """
        Inicializar supervisor
        
        Args:
            config: Configuración (opcional)
        """
        self.config = config
        self.logger = self._setup_logger()
        
        # Estado
        self.running = False
        self.lock = threading.RLock()
        
        # Tareas
        self.tasks: Dict[str, Task] = {}
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.task_counter = 0
        
        # Agentes
        self.agents: Dict[str, Agent] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        
        # Estadísticas
        self.stats = {
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "agents_registered": 0,
            "agents_active": 0,
            "start_time": None
        }
        
        # Threads
        self.worker_thread = None
        self.cleanup_thread = None
        self.heartbeat_thread = None
        
        self.logger.info("Supervisor initialized")
    
    def _setup_logger(self) -> logging.Logger:
        """Configurar logger"""
        logger = logging.getLogger("swarmia.supervisor")
        logger.setLevel(logging.INFO)
        return logger
    
    # ============================================================
    # Lifecycle Methods
    # ============================================================
    
    def start(self) -> bool:
        """Iniciar supervisor"""
        if self.running:
            self.logger.warning("Supervisor already running")
            return False
        
        try:
            self.logger.info("Starting supervisor...")
            self.running = True
            self.stats["start_time"] = datetime.now()
            
            # Iniciar threads
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            
            self.worker_thread.start()
            self.cleanup_thread.start()
            self.heartbeat_thread.start()
            
            self.logger.info("Supervisor started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start supervisor: {e}")
            self.running = False
            return False
    
    def stop(self):
        """Detener supervisor"""
        if not self.running:
            return
        
        self.logger.info("Stopping supervisor...")
        self.running = False
        
        # Esperar threads
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        
        self.logger.info("Supervisor stopped")
    
    # ============================================================
    # Worker Loops
    # ============================================================
    
    def _worker_loop(self):
        """Loop principal de procesamiento de tareas"""
        while self.running:
            try:
                # Obtener tarea de la cola con timeout
                priority, timestamp, task_id = self.task_queue.get(timeout=1)
                
                with self.lock:
                    task = self.tasks.get(task_id)
                    if not task or task.status != TaskStatus.PENDING:
                        continue
                
                # Procesar tarea
                self._process_task(task)
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker loop error: {e}")
    
    def _process_task(self, task: Task):
        """Procesar una tarea"""
        try:
            # Buscar agente disponible
            agent = self._assign_agent(task)
            
            if not agent:
                # No hay agente disponible, reencolar
                self.logger.warning(f"No agent available for task {task.id}, requeuing")
                self._requeue_task(task)
                return
            
            # Marcar como running
            with self.lock:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                task.assigned_agent = agent.id
                agent.current_tasks.append(task.id)
                agent.status = AgentStatus.BUSY
            
            self.logger.info(f"Task {task.id} assigned to agent {agent.name}")
            
            # Aquí iría la ejecución real del agente
            # Por ahora simulamos ejecución
            import time
            time.sleep(0.5)
            
            # Marcar como completada
            with self.lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = {"status": "success", "message": f"Task {task.id} completed"}
                
                agent.current_tasks.remove(task.id)
                if not agent.current_tasks:
                    agent.status = AgentStatus.IDLE
            
            self.stats["tasks_completed"] += 1
            self.logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Task {task.id} failed: {e}")
            self._handle_task_failure(task, e)
    
    def _assign_agent(self, task: Task) -> Optional[Agent]:
        """Asignar agente para una tarea"""
        with self.lock:
            # Buscar agentes con capacidad para esta tarea
            available_agents = []
            for agent in self.agents.values():
                if agent.status == AgentStatus.IDLE:
                    if task.type in agent.capabilities or "*" in agent.capabilities:
                        available_agents.append(agent)
            
            if not available_agents:
                return None
            
            # Por ahora elegir el primero
            return available_agents[0]
    
    def _requeue_task(self, task: Task):
        """Reencolar tarea para reintento"""
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            priority_value = 5 - task.priority.value
            self.task_queue.put((priority_value, time.time(), task.id))
            self.logger.info(f"Task {task.id} requeued (attempt {task.retry_count}/{task.max_retries})")
        else:
            self._handle_task_failure(task, Exception("Max retries exceeded"))
    
    def _handle_task_failure(self, task: Task, error: Exception):
        """Manejar fallo de tarea"""
        with self.lock:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(error)
            
            if task.assigned_agent:
                agent = self.agents.get(task.assigned_agent)
                if agent and task.id in agent.current_tasks:
                    agent.current_tasks.remove(task.id)
                    if not agent.current_tasks:
                        agent.status = AgentStatus.IDLE
        
        self.stats["tasks_failed"] += 1
        self.logger.error(f"Task {task.id} failed: {error}")
    
    def _cleanup_loop(self):
        """Loop de limpieza de tareas antiguas"""
        while self.running:
            try:
                time.sleep(3600)  # Cada hora
                self.cleanup_old_tasks()
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
    
    def _heartbeat_loop(self):
        """Loop de heartbeat para agentes"""
        while self.running:
            try:
                time.sleep(30)  # Cada 30 segundos
                self._check_agent_heartbeats()
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
    
    def _check_agent_heartbeats(self):
        """Verificar heartbeats de agentes"""
        now = datetime.now()
        with self.lock:
            for agent_id, agent in list(self.agents.items()):
                if (now - agent.last_heartbeat).seconds > 60:
                    self.logger.warning(f"Agent {agent.name} heartbeat timeout")
                    agent.status = AgentStatus.OFFLINE
    
    # ============================================================
    # Task Management
    # ============================================================
    
    def create_task(self, task_type: str, data: Dict[str, Any],
                    priority: TaskPriority = TaskPriority.NORMAL,
                    source: str = "system") -> str:
        """
        Crear una nueva tarea
        
        Args:
            task_type: Tipo de tarea
            data: Datos de la tarea
            priority: Prioridad
            source: Origen de la tarea
        
        Returns:
            ID de la tarea creada
        """
        with self.lock:
            self.task_counter += 1
            task_id = f"task_{self.task_counter}_{uuid4().hex[:8]}"
            
            task = Task(
                id=task_id,
                type=task_type,
                data=data,
                priority=priority,
                source=source
            )
            
            self.tasks[task_id] = task
            
            # Agregar a cola con prioridad
            priority_value = 5 - priority.value
            self.task_queue.put((priority_value, time.time(), task_id))
            
            self.stats["tasks_created"] += 1
            
            self.logger.debug(f"Task created: {task_id} (priority={priority.name})")
            return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Obtener una tarea por ID"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_tasks(self, status: Optional[TaskStatus] = None, limit: int = 100) -> List[Task]:
        """Obtener lista de tareas"""
        with self.lock:
            tasks = list(self.tasks.values())
            
            if status:
                tasks = [t for t in tasks if t.status == status]
            
            # Ordenar por fecha descendente
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            
            return tasks[:limit]
    
    def cancel_task(self, task_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancelar una tarea"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            task.status = TaskStatus.CANCELLED
            task.error = reason
            task.completed_at = datetime.now()
            
            # Remover de agente si está asignada
            if task.assigned_agent:
                agent = self.agents.get(task.assigned_agent)
                if agent and task_id in agent.current_tasks:
                    agent.current_tasks.remove(task_id)
            
            self.stats["tasks_cancelled"] += 1
            self.logger.info(f"Task cancelled: {task_id} - {reason}")
            return True
    
    def retry_task(self, task_id: str) -> bool:
        """Reintentar una tarea fallida"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status != TaskStatus.FAILED:
                return False
            
            # Resetear tarea para reintento
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.completed_at = None
            task.assigned_agent = None
            task.error = None
            task.retry_count += 1
            
            # Reencolar
            priority_value = 5 - task.priority.value
            self.task_queue.put((priority_value, time.time(), task_id))
            
            self.logger.info(f"Task retry scheduled: {task_id} (attempt {task.retry_count})")
            return True
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Limpiar tareas antiguas"""
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
    
    # ============================================================
    # Agent Management
    # ============================================================
    
    def register_agent(self, agent_id: str, name: str, agent_type: str,
                       capabilities: List[str], metadata: Optional[Dict] = None) -> bool:
        """Registrar un nuevo agente"""
        with self.lock:
            if agent_id in self.agents:
                self.logger.warning(f"Agent already registered: {agent_id}")
                return False
            
            agent = Agent(
                id=agent_id,
                name=name,
                type=agent_type,
                capabilities=capabilities,
                metadata=metadata or {}
            )
            
            self.agents[agent_id] = agent
            self.agent_capabilities[agent_id] = capabilities
            
            self.stats["agents_registered"] += 1
            self.stats["agents_active"] += 1
            
            self.logger.info(f"Agent registered: {name} (type={agent_type})")
            return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Desregistrar un agente"""
        with self.lock:
            if agent_id not in self.agents:
                return False
            
            agent = self.agents[agent_id]
            
            # Cancelar tareas del agente
            for task_id in agent.current_tasks:
                self.cancel_task(task_id, f"Agent {agent.name} unregistered")
            
            del self.agents[agent_id]
            del self.agent_capabilities[agent_id]
            
            self.stats["agents_active"] -= 1
            
            self.logger.info(f"Agent unregistered: {agent.name}")
            return True
    
    def update_agent_heartbeat(self, agent_id: str) -> bool:
        """Actualizar heartbeat de un agente"""
        with self.lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return False
            
            agent.last_heartbeat = datetime.now()
            if agent.status == AgentStatus.OFFLINE:
                agent.status = AgentStatus.IDLE
            
            return True
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Obtener un agente por ID"""
        with self.lock:
            return self.agents.get(agent_id)
    
    def get_agents(self, agent_type: Optional[str] = None) -> List[Agent]:
        """Obtener lista de agentes"""
        with self.lock:
            agents = list(self.agents.values())
            if agent_type:
                agents = [a for a in agents if a.type == agent_type]
            return agents
    
    # ============================================================
    # Statistics
    # ============================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del supervisor"""
        with self.lock:
            uptime = None
            if self.stats["start_time"]:
                uptime = datetime.now() - self.stats["start_time"]
            
            # Estadísticas por estado
            tasks_by_status = {}
            for status in TaskStatus:
                tasks_by_status[status.value] = len([t for t in self.tasks.values() if t.status == status])
            
            # Estadísticas por tipo de agente
            agents_by_type = {}
            for agent in self.agents.values():
                agents_by_type[agent.type] = agents_by_type.get(agent.type, 0) + 1
            
            return {
                **self.stats,
                "uptime": str(uptime) if uptime else None,
                "tasks_by_status": tasks_by_status,
                "agents_by_type": agents_by_type,
                "total_tasks": len(self.tasks),
                "total_agents": len(self.agents),
                "queue_size": self.task_queue.qsize(),
                "capabilities": list(self.agent_capabilities.keys())
            }
    
    def emergency_stop(self):
        """Parada de emergencia - cancelar todas las tareas en ejecución"""
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


# ============================================================
# Factory Function
# ============================================================

def create_supervisor(config=None):
    """
    Create supervisor instance
    
    Args:
        config: Configuration object (optional)
    
    Returns:
        Supervisor instance
    """
    return Supervisor(config)


# ============================================================
# Example Usage
# ============================================================

def example_usage():
    """Ejemplo de uso del supervisor"""
    print("👨‍💼 Supervisor Example\n")
    
    supervisor = create_supervisor()
    
    # Registrar un agente de ejemplo
    supervisor.register_agent(
        agent_id="agent_chat_001",
        name="Chat Agent",
        agent_type="chat",
        capabilities=["process_message", "complete_conversation", "analyze_sentiment"]
    )
    
    supervisor.register_agent(
        agent_id="agent_agg_001",
        name="Aggressive Agent",
        agent_type="aggressive",
        capabilities=["execute_action", "monitor_system"]
    )
    
    # Iniciar supervisor
    if supervisor.start():
        print("✅ Supervisor started\n")
        
        # Crear tareas con diferentes prioridades
        task1 = supervisor.create_task(
            task_type="process_message",
            data={"platform": "telegram", "sender": "user123", "text": "Hello"},
            priority=TaskPriority.CRITICAL,
            source="gateway"
        )
        print(f"📨 Critical task created: {task1}")
        
        task2 = supervisor.create_task(
            task_type="complete_conversation",
            data={"conversation_id": "conv_123"},
            priority=TaskPriority.NORMAL,
            source="dashboard"
        )
        print(f"📨 Normal task created: {task2}")
        
        task3 = supervisor.create_task(
            task_type="analyze_sentiment",
            data={"text": "This is amazing!"},
            priority=TaskPriority.LOW,
            source="analytics"
        )
        print(f"📨 Low priority task created: {task3}")
        
        # Esperar procesamiento
        import time
        time.sleep(2)
        
        # Obtener estadísticas
        stats = supervisor.get_stats()
        print(f"\n📊 Supervisor Stats:")
        print(f"  Tasks created: {stats['tasks_created']}")
        print(f"  Tasks completed: {stats['tasks_completed']}")
        print(f"  Tasks failed: {stats['tasks_failed']}")
        print(f"  Agents registered: {stats['agents_registered']}")
        print(f"  Queue size: {stats['queue_size']}")
        
        # Mostrar tareas
        tasks = supervisor.get_tasks()
        print(f"\n📋 Tasks ({len(tasks)} total):")
        for task in tasks[:5]:  # Mostrar primeras 5
            status_icon = "✓" if task.status == TaskStatus.COMPLETED else "⏳"
            print(f"  {status_icon} {task.id}: {task.type} ({task.status.value})")
        
        # Detener supervisor
        supervisor.stop()
        print("\n🛑 Supervisor stopped")
    
    else:
        print("❌ Failed to start supervisor")


if __name__ == "__main__":
    example_usage()
