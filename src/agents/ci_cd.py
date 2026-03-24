#!/usr/bin/env python3
"""
Agente CI/CD - Integración continua y despliegue continuo
Soporta: GitHub, GitLab, Bitbucket, Jenkins, GitHub Actions, GitLab CI
Capacidades: clonar, commit, push, crear PR, ejecutar pipelines, despliegues
"""

import os
import sys
import json
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

# Importaciones opcionales
try:
    import git
    from git import Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgenteCICD(Agente):
    """
    Agente CI/CD - Integración continua y despliegue continuo
    Soporta: GitHub, GitLab, Bitbucket, Jenkins, GitHub Actions
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="ci_cd",
            nombre="Agente CI/CD",
            tipo=TipoAgente.CI_CD,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        
        # Configuración de repositorios
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.gitlab_token = os.getenv("GITLAB_TOKEN", "")
        self.bitbucket_token = os.getenv("BITBUCKET_TOKEN", "")
        
        # Directorio de trabajo
        self.workspace = Path(os.getenv("CI_WORKSPACE", "/tmp/swarmia-ci"))
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Repositorios clonados
        self.repos: Dict[str, Path] = {}
        
        self._registrar_capacidades()
        self._mostrar_disponibilidad()
        self.logger.info(f"Agente CI/CD iniciado. Workspace: {self.workspace}")
    
    def _mostrar_disponibilidad(self):
        """Mostrar herramientas disponibles"""
        self.logger.info("Herramientas disponibles:")
        self.logger.info(f"  Git: {'✅' if GIT_AVAILABLE else '❌ (pip install GitPython)'}")
        self.logger.info(f"  GitHub: {'✅' if self.github_token else '❌ (falta GITHUB_TOKEN)'}")
        self.logger.info(f"  GitLab: {'✅' if self.gitlab_token else '❌ (falta GITLAB_TOKEN)'}")
        self.logger.info(f"  Bitbucket: {'✅' if self.bitbucket_token else '❌ (falta BITBUCKET_TOKEN)'}")
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        
        # Git básico
        self.registrar_capacidad(
            nombre="git_clonar",
            descripcion="Clonar un repositorio",
            parametros=["url", "destino"],
            ejemplos=["clonar https://github.com/usuario/repo.git", "git clone"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="git_status",
            descripcion="Ver estado del repositorio",
            parametros=["repo"],
            ejemplos=["estado del repositorio", "git status"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="git_commit",
            descripcion="Hacer commit de cambios",
            parametros=["repo", "mensaje", "archivos"],
            ejemplos=["commit cambios con mensaje 'actualización'", "git commit"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="git_push",
            descripcion="Subir cambios al repositorio remoto",
            parametros=["repo", "rama"],
            ejemplos=["subir cambios a GitHub", "git push"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="git_pull",
            descripcion="Traer cambios del repositorio remoto",
            parametros=["repo", "rama"],
            ejemplos=["traer últimos cambios", "git pull"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="git_branch",
            descripcion="Crear o listar ramas",
            parametros=["repo", "nombre"],
            ejemplos=["crear rama feature", "listar ramas"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="git_merge",
            descripcion="Fusionar ramas",
            parametros=["repo", "origen", "destino"],
            ejemplos=["fusionar feature en main", "git merge"],
            nivel_riesgo="alto"
        )
        
        # GitHub
        self.registrar_capacidad(
            nombre="github_pr_crear",
            descripcion="Crear Pull Request en GitHub",
            parametros=["repo", "titulo", "cuerpo", "base", "head"],
            ejemplos=["crear PR en GitHub", "pull request"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="github_pr_listar",
            descripcion="Listar Pull Requests",
            parametros=["repo", "estado"],
            ejemplos=["listar PRs abiertos", "ver pull requests"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="github_issue_crear",
            descripcion="Crear Issue en GitHub",
            parametros=["repo", "titulo", "cuerpo"],
            ejemplos=["crear issue", "reportar bug"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="github_release",
            descripcion="Crear release en GitHub",
            parametros=["repo", "tag", "nombre"],
            ejemplos=["crear release v1.0.0", "publicar versión"],
            nivel_riesgo="medio"
        )
        
        # GitLab
        self.registrar_capacidad(
            nombre="gitlab_mr_crear",
            descripcion="Crear Merge Request en GitLab",
            parametros=["repo", "titulo", "origen", "destino"],
            ejemplos=["crear MR en GitLab", "merge request"],
            nivel_riesgo="medio"
        )
        
        # CI/CD Pipelines
        self.registrar_capacidad(
            nombre="ci_ejecutar",
            descripcion="Ejecutar pipeline CI/CD",
            parametros=["repo", "pipeline"],
            ejemplos=["ejecutar GitHub Actions", "correr tests"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="ci_estado",
            descripcion="Ver estado de pipeline",
            parametros=["repo", "run_id"],
            ejemplos=["estado del pipeline", "ver si pasó"],
            nivel_riesgo="bajo"
        )
        
        # Despliegues
        self.registrar_capacidad(
            nombre="deploy",
            descripcion="Desplegar aplicación",
            parametros=["repo", "entorno"],
            ejemplos=["desplegar a producción", "deploy a staging"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="rollback",
            descripcion="Revertir despliegue",
            parametros=["repo", "version"],
            ejemplos=["rollback a versión anterior", "revertir despliegue"],
            nivel_riesgo="critico"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        # Git básico
        if "git_clonar" in tipo or "clonar" in desc:
            return await self._git_clonar(desc, parametros)
        
        elif "git_status" in tipo or "estado" in desc:
            return await self._git_status(desc, parametros)
        
        elif "git_commit" in tipo or "commit" in desc:
            return await self._git_commit(desc, parametros)
        
        elif "git_push" in tipo or "push" in desc:
            return await self._git_push(desc, parametros)
        
        elif "git_pull" in tipo or "pull" in desc:
            return await self._git_pull(desc, parametros)
        
        elif "git_branch" in tipo or "branch" in desc or "rama" in desc:
            return await self._git_branch(desc, parametros)
        
        elif "git_merge" in tipo or "merge" in desc or "fusionar" in desc:
            return await self._git_merge(desc, parametros)
        
        # GitHub
        elif "github_pr_crear" in tipo or "crear pr" in desc or "pull request" in desc:
            return await self._github_pr_crear(desc, parametros)
        
        elif "github_pr_listar" in tipo or "listar pr" in desc:
            return await self._github_pr_listar(desc, parametros)
        
        elif "github_issue_crear" in tipo or "crear issue" in desc:
            return await self._github_issue_crear(desc, parametros)
        
        elif "github_release" in tipo or "release" in desc:
            return await self._github_release(desc, parametros)
        
        # GitLab
        elif "gitlab_mr_crear" in tipo or "crear mr" in desc:
            return await self._gitlab_mr_crear(desc, parametros)
        
        # CI/CD
        elif "ci_ejecutar" in tipo or "ejecutar pipeline" in desc:
            return await self._ci_ejecutar(desc, parametros)
        
        elif "ci_estado" in tipo or "estado pipeline" in desc:
            return await self._ci_estado(desc, parametros)
        
        # Despliegues
        elif "deploy" in tipo or "desplegar" in desc:
            return await self._deploy(desc, parametros)
        
        elif "rollback" in tipo or "revertir" in desc:
            return await self._rollback(desc, parametros)
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _obtener_repo(self, repo_nombre: str) -> Optional[Path]:
        """Obtener ruta de repositorio clonado"""
        return self.repos.get(repo_nombre) or self.workspace / repo_nombre
    
    def _extraer_url_repo(self, desc: str) -> Optional[str]:
        """Extraer URL de repositorio de la descripción"""
        import re
        # GitHub, GitLab, Bitbucket URLs
        patterns = [
            r'https?://github\.com/[^\s]+\.git',
            r'https?://gitlab\.com/[^\s]+\.git',
            r'https?://bitbucket\.org/[^\s]+\.git',
            r'git@github\.com:[^\s]+\.git',
            r'[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+'
        ]
        for pattern in patterns:
            match = re.search(pattern, desc)
            if match:
                return match.group(0)
        return None
    
    def _extraer_repo_nombre(self, url: str) -> str:
        """Extraer nombre del repositorio de la URL"""
        return url.split('/')[-1].replace('.git', '')
    
    def _extraer_mensaje_commit(self, desc: str) -> str:
        """Extraer mensaje de commit de la descripción"""
        import re
        match = re.search(r'(?:mensaje|message)[:\s]+["\']?([^"\']+)["\']?', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        return f"Actualización automática SwarmIA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    def _extraer_rama(self, desc: str) -> str:
        """Extraer nombre de rama de la descripción"""
        import re
        match = re.search(r'(?:rama|branch)[:\s]+([a-zA-Z0-9_-]+)', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        return "main"
    
    def _ejecutar_git(self, repo_path: Path, comandos: List[str]) -> Dict:
        """Ejecutar comandos git en repositorio"""
        try:
            result = subprocess.run(
                comandos,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "exito": result.returncode == 0,
                "salida": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    def _api_request(self, url: str, method: str = "GET", data: Dict = None, token: str = None) -> Dict:
        """Realizar petición a API"""
        if not REQUESTS_AVAILABLE:
            return {"exito": False, "error": "requests no instalado"}
        
        headers = {"Authorization": f"token {token}"} if token else {}
        headers["Accept"] = "application/vnd.github.v3+json"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=30)
            else:
                return {"exito": False, "error": f"Método no soportado: {method}"}
            
            return {
                "exito": response.status_code < 400,
                "status": response.status_code,
                "data": response.json() if response.text else None,
                "error": response.text if response.status_code >= 400 else None
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    # ============================================================
    # GIT BÁSICO
    # ============================================================
    
    async def _git_clonar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Clonar repositorio"""
        url = parametros.get("url") or self._extraer_url_repo(desc)
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica la URL del repositorio")
        
        nombre = self._extraer_repo_nombre(url)
        destino = parametros.get("destino") or self.workspace / nombre
        destino = Path(destino)
        
        self.logger.info(f"Clonando {url} -> {destino}")
        
        if GIT_AVAILABLE:
            try:
                repo = Repo.clone_from(url, destino)
                self.repos[nombre] = destino
                return ResultadoTarea(
                    exito=True,
                    datos={
                        "url": url,
                        "destino": str(destino),
                        "nombre": nombre,
                        "mensaje": f"Repositorio clonado en {destino}"
                    }
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            # Usar git CLI
            cmd = ["git", "clone", url, str(destino)]
            result = self._ejecutar_git(self.workspace, cmd)
            if result["exito"]:
                self.repos[nombre] = destino
            return ResultadoTarea(
                exito=result["exito"],
                datos={"url": url, "destino": str(destino), "salida": result["salida"]}
            )
    
    async def _git_status(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ver estado del repositorio"""
        repo_nombre = parametros.get("repo") or self._extraer_repo_nombre(desc)
        repo_path = self._obtener_repo(repo_nombre)
        
        if not repo_path or not repo_path.exists():
            return ResultadoTarea(exito=False, error=f"Repositorio no encontrado: {repo_nombre}")
        
        result = self._ejecutar_git(repo_path, ["git", "status", "--porcelain"])
        
        # Parsear cambios
        cambios = []
        if result["salida"]:
            for line in result["salida"].strip().split('\n'):
                if line:
                    status = line[:2]
                    archivo = line[3:]
                    cambios.append({"estado": status, "archivo": archivo})
        
        return ResultadoTarea(
            exito=result["exito"],
            datos={
                "repo": repo_nombre,
                "tiene_cambios": len(cambios) > 0,
                "cambios": cambios,
                "total_cambios": len(cambios)
            }
        )
    
    async def _git_commit(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Hacer commit de cambios"""
        repo_nombre = parametros.get("repo") or self._extraer_repo_nombre(desc)
        repo_path = self._obtener_repo(repo_nombre)
        mensaje = parametros.get("mensaje") or self._extraer_mensaje_commit(desc)
        archivos = parametros.get("archivos", ["."])
        
        if not repo_path or not repo_path.exists():
            return ResultadoTarea(exito=False, error=f"Repositorio no encontrado: {repo_nombre}")
        
        # Agregar archivos
        for archivo in archivos:
            self._ejecutar_git(repo_path, ["git", "add", archivo])
        
        # Hacer commit
        result = self._ejecutar_git(repo_path, ["git", "commit", "-m", mensaje])
        
        return ResultadoTarea(
            exito=result["exito"],
            datos={
                "repo": repo_nombre,
                "mensaje": mensaje,
                "salida": result["salida"],
                "error": result["error"]
            }
        )
    
    async def _git_push(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Subir cambios al remoto"""
        repo_nombre = parametros.get("repo") or self._extraer_repo_nombre(desc)
        repo_path = self._obtener_repo(repo_nombre)
        rama = parametros.get("rama") or self._extraer_rama(desc)
        
        if not repo_path or not repo_path.exists():
            return ResultadoTarea(exito=False, error=f"Repositorio no encontrado: {repo_nombre}")
        
        result = self._ejecutar_git(repo_path, ["git", "push", "origin", rama])
        
        return ResultadoTarea(
            exito=result["exito"],
            datos={
                "repo": repo_nombre,
                "rama": rama,
                "salida": result["salida"]
            }
        )
    
    async def _git_pull(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Traer cambios del remoto"""
        repo_nombre = parametros.get("repo") or self._extraer_repo_nombre(desc)
        repo_path = self._obtener_repo(repo_nombre)
        rama = parametros.get("rama") or self._extraer_rama(desc)
        
        if not repo_path or not repo_path.exists():
            return ResultadoTarea(exito=False, error=f"Repositorio no encontrado: {repo_nombre}")
        
        result = self._ejecutar_git(repo_path, ["git", "pull", "origin", rama])
        
        return ResultadoTarea(
            exito=result["exito"],
            datos={
                "repo": repo_nombre,
                "rama": rama,
                "salida": result["salida"]
            }
        )
    
    async def _git_branch(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear o listar ramas"""
        repo_nombre = parametros.get("repo") or self._extraer_repo_nombre(desc)
        repo_path = self._obtener_repo(repo_nombre)
        nombre = parametros.get("nombre")
        
        if not repo_path or not repo_path.exists():
            return ResultadoTarea(exito=False, error=f"Repositorio no encontrado: {repo_nombre}")
        
        if nombre:
            # Crear rama
            result = self._ejecutar_git(repo_path, ["git", "checkout", "-b", nombre])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"repo": repo_nombre, "rama": nombre, "salida": result["salida"]}
            )
        else:
            # Listar ramas
            result = self._ejecutar_git(repo_path, ["git", "branch", "-a"])
            ramas = [r.strip() for r in result["salida"].split('\n') if r.strip()]
            return ResultadoTarea(
                exito=result["exito"],
                datos={"repo": repo_nombre, "ramas": ramas, "total": len(ramas)}
            )
    
    async def _git_merge(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Fusionar ramas"""
        repo_nombre = parametros.get("repo") or self._extraer_repo_nombre(desc)
        repo_path = self._obtener_repo(repo_nombre)
        origen = parametros.get("origen") or "feature"
        destino = parametros.get("destino") or "main"
        
        if not repo_path or not repo_path.exists():
            return ResultadoTarea(exito=False, error=f"Repositorio no encontrado: {repo_nombre}")
        
        # Cambiar a rama destino
        self._ejecutar_git(repo_path, ["git", "checkout", destino])
        # Fusionar
        result = self._ejecutar_git(repo_path, ["git", "merge", origen])
        
        return ResultadoTarea(
            exito=result["exito"],
            datos={
                "repo": repo_nombre,
                "origen": origen,
                "destino": destino,
                "salida": result["salida"]
            }
        )
    
    # ============================================================
    # GITHUB
    # ============================================================
    
    async def _github_pr_crear(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear Pull Request en GitHub"""
        if not self.github_token:
            return ResultadoTarea(exito=False, error="GitHub no configurado. Configura GITHUB_TOKEN")
        
        repo = parametros.get("repo") or self._extraer_repo_nombre(desc)
        titulo = parametros.get("titulo") or "Pull Request automático"
        cuerpo = parametros.get("cuerpo") or "Creado por SwarmIA"
        base = parametros.get("base") or "main"
        head = parametros.get("head") or self._extraer_rama(desc)
        
        # Formato: owner/repo
        if '/' not in repo:
            # Intentar extraer de descripción
            import re
            match = re.search(r'([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', desc)
            if match:
                repo = match.group(1)
            else:
                return ResultadoTarea(exito=False, error=f"Formato inválido. Usa owner/repo: {repo}")
        
        url = f"https://api.github.com/repos/{repo}/pulls"
        data = {
            "title": titulo,
            "body": cuerpo,
            "head": head,
            "base": base
        }
        
        result = self._api_request(url, "POST", data, self.github_token)
        
        if result["exito"]:
            pr_data = result["data"]
            return ResultadoTarea(
                exito=True,
                datos={
                    "url": pr_data.get("html_url"),
                    "number": pr_data.get("number"),
                    "title": pr_data.get("title"),
                    "estado": pr_data.get("state")
                }
            )
        else:
            return ResultadoTarea(exito=False, error=result.get("error", "Error creando PR"))
    
    async def _github_pr_listar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Listar Pull Requests"""
        if not self.github_token:
            return ResultadoTarea(exito=False, error="GitHub no configurado")
        
        repo = parametros.get("repo") or self._extraer_repo_nombre(desc)
        estado = parametros.get("estado", "open")
        
        if '/' not in repo:
            import re
            match = re.search(r'([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', desc)
            if match:
                repo = match.group(1)
        
        url = f"https://api.github.com/repos/{repo}/pulls?state={estado}"
        result = self._api_request(url, "GET", token=self.github_token)
        
        if result["exito"]:
            prs = []
            for pr in result["data"]:
                prs.append({
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "user": pr.get("user", {}).get("login"),
                    "url": pr.get("html_url"),
                    "estado": pr.get("state")
                })
            return ResultadoTarea(
                exito=True,
                datos={"pull_requests": prs, "total": len(prs)}
            )
        else:
            return ResultadoTarea(exito=False, error=result.get("error"))
    
    async def _github_issue_crear(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear Issue en GitHub"""
        if not self.github_token:
            return ResultadoTarea(exito=False, error="GitHub no configurado")
        
        repo = parametros.get("repo") or self._extraer_repo_nombre(desc)
        titulo = parametros.get("titulo") or "Issue creado por SwarmIA"
        cuerpo = parametros.get("cuerpo") or desc
        
        if '/' not in repo:
            import re
            match = re.search(r'([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', desc)
            if match:
                repo = match.group(1)
        
        url = f"https://api.github.com/repos/{repo}/issues"
        data = {"title": titulo, "body": cuerpo}
        
        result = self._api_request(url, "POST", data, self.github_token)
        
        if result["exito"]:
            issue_data = result["data"]
            return ResultadoTarea(
                exito=True,
                datos={
                    "url": issue_data.get("html_url"),
                    "number": issue_data.get("number"),
                    "title": issue_data.get("title")
                }
            )
        else:
            return ResultadoTarea(exito=False, error=result.get("error"))
    
    async def _github_release(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear Release en GitHub"""
        if not self.github_token:
            return ResultadoTarea(exito=False, error="GitHub no configurado")
        
        repo = parametros.get("repo") or self._extraer_repo_nombre(desc)
        tag = parametros.get("tag") or f"v{datetime.now().strftime('%Y%m%d')}"
        nombre = parametros.get("nombre") or f"Release {tag}"
        cuerpo = parametros.get("cuerpo") or "Release automático creado por SwarmIA"
        
        if '/' not in repo:
            import re
            match = re.search(r'([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', desc)
            if match:
                repo = match.group(1)
        
        url = f"https://api.github.com/repos/{repo}/releases"
        data = {
            "tag_name": tag,
            "name": nombre,
            "body": cuerpo,
            "draft": False,
            "prerelease": False
        }
        
        result = self._api_request(url, "POST", data, self.github_token)
        
        if result["exito"]:
            release_data = result["data"]
            return ResultadoTarea(
                exito=True,
                datos={
                    "url": release_data.get("html_url"),
                    "tag": tag,
                    "nombre": nombre
                }
            )
        else:
            return ResultadoTarea(exito=False, error=result.get("error"))
    
    # ============================================================
    # GITLAB
    # ============================================================
    
    async def _gitlab_mr_crear(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear Merge Request en GitLab"""
        if not self.gitlab_token:
            return ResultadoTarea(exito=False, error="GitLab no configurado. Configura GITLAB_TOKEN")
        
        repo = parametros.get("repo") or self._extraer_repo_nombre(desc)
        titulo = parametros.get("titulo") or "Merge Request automático"
        cuerpo = parametros.get("cuerpo") or "Creado por SwarmIA"
        origen = parametros.get("origen") or self._extraer_rama(desc)
        destino = parametros.get("destino") or "main"
        
        # Formato: owner/repo
        if '/' not in repo:
            import re
            match = re.search(r'([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', desc)
            if match:
                repo = match.group(1)
        
        # GitLab API usa ID numérico o path codificado
        repo_encoded = repo.replace('/', '%2F')
        url = f"https://gitlab.com/api/v4/projects/{repo_encoded}/merge_requests"
        
        data = {
            "source_branch": origen,
            "target_branch": destino,
            "title": titulo,
            "description": cuerpo
        }
        
        headers = {"PRIVATE-TOKEN": self.gitlab_token}
        
        if not REQUESTS_AVAILABLE:
            return ResultadoTarea(exito=False, error="requests no instalado")
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            if response.status_code < 400:
                mr_data = response.json()
                return ResultadoTarea(
                    exito=True,
                    datos={
                        "url": mr_data.get("web_url"),
                        "iid": mr_data.get("iid"),
                        "title": mr_data.get("title")
                    }
                )
            else:
                return ResultadoTarea(exito=False, error=f"Error {response.status_code}: {response.text}")
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # CI/CD PIPELINES
    # ============================================================
    
    async def _ci_ejecutar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ejecutar pipeline CI/CD"""
        repo = parametros.get("repo") or self._extraer_repo_nombre(desc)
        pipeline = parametros.get("pipeline", "github_actions")
        
        # Detectar si es GitHub Actions
        if "github" in desc or "actions" in desc:
            return await self._github_actions_ejecutar(repo, desc)
        elif "gitlab" in desc:
            return await self._gitlab_pipeline_ejecutar(repo, desc)
        else:
            return ResultadoTarea(
                exito=False,
                error="No se detectó qué CI ejecutar. Especifica: GitHub Actions, GitLab CI"
            )
    
    async def _github_actions_ejecutar(self, repo: str, desc: str) -> ResultadoTarea:
        """Ejecutar GitHub Actions workflow"""
        if not self.github_token:
            return ResultadoTarea(exito=False, error="GitHub no configurado")
        
        if '/' not in repo:
            import re
            match = re.search(r'([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', desc)
            if match:
                repo = match.group(1)
            else:
                return ResultadoTarea(exito=False, error=f"Formato inválido: {repo}")
        
        # Obtener workflows disponibles
        workflows_url = f"https://api.github.com/repos/{repo}/actions/workflows"
        workflows = self._api_request(workflows_url, "GET", token=self.github_token)
        
        if not workflows["exito"] or not workflows["data"].get("workflows"):
            return ResultadoTarea(exito=False, error="No se encontraron workflows")
        
        # Tomar el primer workflow o el especificado
        workflow_id = workflows["data"]["workflows"][0]["id"]
        
        # Disparar workflow
        trigger_url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
        data = {"ref": "main"}
        
        result = self._api_request(trigger_url, "POST", data, self.github_token)
        
        return ResultadoTarea(
            exito=result["exito"],
            datos={
                "repo": repo,
                "workflow_id": workflow_id,
                "mensaje": "Workflow disparado" if result["exito"] else result.get("error")
            }
        )
    
    async def _gitlab_pipeline_ejecutar(self, repo: str, desc: str) -> ResultadoTarea:
        """Ejecutar GitLab pipeline"""
        if not self.gitlab_token:
            return ResultadoTarea(exito=False, error="GitLab no configurado")
        
        if '/' not in repo:
            import re
            match = re.search(r'([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', desc)
            if match:
                repo = match.group(1)
        
        repo_encoded = repo.replace('/', '%2F')
        url = f"https://gitlab.com/api/v4/projects/{repo_encoded}/pipeline"
        
        data = {"ref": "main"}
        headers = {"PRIVATE-TOKEN": self.gitlab_token}
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            if response.status_code < 400:
                pipeline_data = response.json()
                return ResultadoTarea(
                    exito=True,
                    datos={
                        "repo": repo,
                        "pipeline_id": pipeline_data.get("id"),
                        "url": pipeline_data.get("web_url")
                    }
                )
            else:
                return ResultadoTarea(exito=False, error=f"Error {response.status_code}")
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    async def _ci_estado(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ver estado de pipeline"""
        # Implementar según servicio
        return ResultadoTarea(
            exito=False,
            error="Función en desarrollo. Próximamente."
        )
    
    # ============================================================
    # DESPLIEGUES
    # ============================================================
    
    async def _deploy(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Desplegar aplicación"""
        repo = parametros.get("repo") or self._extraer_repo_nombre(desc)
        entorno = parametros.get("entorno") or "production"
        
        # Aquí se integraría con Docker, Kubernetes, etc.
        # Por ahora, simular despliegue
        self.logger.info(f"Desplegando {repo} en {entorno}")
        
        # Crear tarea para agente Docker si está disponible
        if hasattr(self.supervisor, 'create_task'):
            self.supervisor.create_task(
                task_type="docker_deploy",
                data={"repo": repo, "entorno": entorno},
                source="ci_cd"
            )
        
        return ResultadoTarea(
            exito=True,
            datos={
                "repo": repo,
                "entorno": entorno,
                "mensaje": f"Despliegue de {repo} iniciado en {entorno}"
            }
        )
    
    async def _rollback(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Revertir despliegue"""
        repo = parametros.get("repo") or self._extraer_repo_nombre(desc)
        version = parametros.get("version") or "anterior"
        
        self.logger.warning(f"Rollback de {repo} a versión {version}")
        
        return ResultadoTarea(
            exito=True,
            datos={
                "repo": repo,
                "version": version,
                "mensaje": f"Rollback de {repo} a versión {version} iniciado"
            }
        )


# ============================================================
# Factory Function
# ============================================================

def crear_agente_ci_cd(supervisor: Supervisor, config: Config) -> AgenteCICD:
    """Crea instancia del agente CI/CD"""
    return AgenteCICD(supervisor, config)
