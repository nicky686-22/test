#!/usr/bin/env python3
"""
Agente Voz - Reconocimiento y síntesis de voz
Soporta: speech_recognition, pyttsx3, whisper, gTTS
Capacidades: escuchar, hablar, comandos por voz, transcripción
"""

import os
import sys
import asyncio
import tempfile
import wave
import audioop
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import threading
import queue

# Importaciones opcionales
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    sr = None

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    pyttsx3 = None

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    gTTS = None

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgenteVoz(Agente):
    """
    Agente Voz - Reconocimiento y síntesis de voz
    Permite interacción por voz con SwarmIA
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="voz",
            nombre="Agente Voz",
            tipo=TipoAgente.VOZ,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        
        # Configuración
        self.idioma = os.getenv("VOZ_IDIOMA", "es-ES")
        self.microfono_index = int(os.getenv("VOZ_MICROFONO", "0"))
        self.escuchando = False
        self.hilo_escucha = None
        self.cola_comandos = queue.Queue()
        
        # Inicializar motores
        self.recognizer = None
        self.tts_engine = None
        self.whisper_model = None
        
        self._inicializar()
        self._registrar_capacidades()
        self.logger.info("Agente Voz iniciado")
    
    def _inicializar(self):
        """Inicializar motores de voz"""
        
        # Speech Recognition
        if SPEECH_RECOGNITION_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = int(os.getenv("VOZ_ENERGIA", "3000"))
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.pause_threshold = float(os.getenv("VOZ_PAUSA", "0.8"))
                self.logger.info("Speech Recognition inicializado")
            except Exception as e:
                self.logger.error(f"Error inicializando Speech Recognition: {e}")
        
        # Text-to-Speech
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                # Configurar voz en español si está disponible
                voices = self.tts_engine.getProperty('voices')
                for voice in voices:
                    if 'spanish' in voice.name.lower() or 'español' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.9)
                self.logger.info("TTS engine inicializado")
            except Exception as e:
                self.logger.error(f"Error inicializando TTS: {e}")
        
        # Whisper
        if WHISPER_AVAILABLE:
            try:
                modelo = os.getenv("VOZ_WHISPER_MODEL", "base")
                self.whisper_model = whisper.load_model(modelo)
                self.logger.info(f"Whisper modelo '{modelo}' cargado")
            except Exception as e:
                self.logger.error(f"Error cargando Whisper: {e}")
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        
        self.registrar_capacidad(
            nombre="escuchar",
            descripcion="Escuchar comandos de voz",
            parametros=["duracion"],
            ejemplos=["escuchar comando", "qué dice", "empezar a escuchar"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="hablar",
            descripcion="Convertir texto a voz",
            parametros=["texto"],
            ejemplos=["di hola", "habla", "responde con voz"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="transcribir",
            descripcion="Transcribir audio a texto",
            parametros=["archivo"],
            ejemplos=["transcribir audio.wav", "qué dice este archivo"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="grabar",
            descripcion="Grabar audio del micrófono",
            parametros=["duracion", "archivo"],
            ejemplos=["grabar 5 segundos", "grabar audio"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="microfonos",
            descripcion="Listar micrófonos disponibles",
            ejemplos=["listar micrófonos", "qué micrófonos hay"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="escuchar_continuo",
            descripcion="Escuchar comandos continuamente",
            ejemplos=["empezar a escuchar", "modo escucha", "siempre escuchando"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="detener_escucha",
            descripcion="Detener escucha continua",
            ejemplos=["dejar de escuchar", "detener escucha"],
            nivel_riesgo="bajo"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        if "escuchar" in tipo or "escuchar" in desc:
            if "continuo" in desc or "modo" in desc:
                return await self._escuchar_continuo(desc, parametros)
            return await self._escuchar(desc, parametros)
        
        elif "hablar" in tipo or "hablar" in desc or "di" in desc:
            return await self._hablar(desc, parametros)
        
        elif "transcribir" in tipo or "transcribir" in desc:
            return await self._transcribir(desc, parametros)
        
        elif "grabar" in tipo or "grabar" in desc:
            return await self._grabar(desc, parametros)
        
        elif "microfonos" in tipo or "listar microfonos" in desc:
            return await self._listar_microfonos()
        
        elif "detener_escucha" in tipo or "dejar de escuchar" in desc:
            return await self._detener_escucha()
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # ESCUCHAR
    # ============================================================
    
    async def _escuchar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Escuchar un comando de voz"""
        if not self.recognizer:
            return ResultadoTarea(exito=False, error="Speech Recognition no disponible")
        
        duracion = parametros.get("duracion", 5)
        self.logger.info(f"Escuchando por {duracion} segundos...")
        
        try:
            with sr.Microphone(device_index=self.microfono_index) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=duracion, phrase_time_limit=duracion)
            
            # Reconocer usando Google (requiere internet) o Whisper
            try:
                texto = self.recognizer.recognize_google(audio, language=self.idioma)
                self.logger.info(f"Reconocido: {texto}")
                
                return ResultadoTarea(
                    exito=True,
                    datos={
                        "texto": texto,
                        "metodo": "google",
                        "mensaje": f"He escuchado: {texto}"
                    }
                )
            except sr.UnknownValueError:
                return ResultadoTarea(
                    exito=False,
                    error="No entendí lo que dijiste"
                )
            except sr.RequestError as e:
                return ResultadoTarea(
                    exito=False,
                    error=f"Error con servicio de reconocimiento: {e}"
                )
                
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    async def _escuchar_continuo(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Escuchar comandos continuamente"""
        if self.escuchando:
            return ResultadoTarea(exito=False, error="Ya estoy escuchando")
        
        palabra_activacion = parametros.get("palabra", "swarmia")
        
        def loop_escucha():
            self.escuchando = True
            self.logger.info(f"Modo escucha continua activado. Palabra de activación: '{palabra_activacion}'")
            
            with sr.Microphone(device_index=self.microfono_index) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                while self.escuchando:
                    try:
                        self.logger.debug("Esperando palabra de activación...")
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                        
                        try:
                            texto = self.recognizer.recognize_google(audio, language=self.idioma)
                            texto_lower = texto.lower()
                            
                            if palabra_activacion in texto_lower:
                                self.logger.info(f"Palabra de activación detectada: {texto}")
                                # Extraer comando después de la palabra de activación
                                comando = texto_lower.replace(palabra_activacion, "").strip()
                                if comando:
                                    self.cola_comandos.put(comando)
                                    self.logger.info(f"Comando: {comando}")
                            elif self.escuchando:
                                # También detectar comandos directos
                                self.cola_comandos.put(texto_lower)
                                
                        except sr.UnknownValueError:
                            pass
                        except sr.RequestError:
                            pass
                            
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        self.logger.error(f"Error en escucha continua: {e}")
            
            self.logger.info("Modo escucha continua detenido")
        
        self.hilo_escucha = threading.Thread(target=loop_escucha, daemon=True)
        self.hilo_escucha.start()
        
        # Procesar comandos en segundo plano
        def procesar_comandos():
            while self.escuchando:
                try:
                    comando = self.cola_comandos.get(timeout=1)
                    if comando:
                        self.logger.info(f"Procesando comando de voz: {comando}")
                        # Crear tarea en supervisor
                        self.supervisor.create_task(
                            task_type="chat_message",
                            data={"message": comando},
                            source="voz"
                        )
                except queue.Empty:
                    continue
        
        threading.Thread(target=procesar_comandos, daemon=True).start()
        
        return ResultadoTarea(
            exito=True,
            datos={
                "palabra_activacion": palabra_activacion,
                "mensaje": f"Escuchando. Di '{palabra_activacion}' seguido de tu comando"
            }
        )
    
    async def _detener_escucha(self) -> ResultadoTarea:
        """Detener escucha continua"""
        if not self.escuchando:
            return ResultadoTarea(exito=False, error="No estoy escuchando")
        
        self.escuchando = False
        if self.hilo_escucha:
            self.hilo_escucha.join(timeout=2)
        
        return ResultadoTarea(
            exito=True,
            datos={"mensaje": "Modo escucha desactivado"}
        )
    
    # ============================================================
    # HABLAR (TTS)
    # ============================================================
    
    async def _hablar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Convertir texto a voz"""
        texto = parametros.get("texto") or self._extraer_texto(desc)
        
        if not texto:
            return ResultadoTarea(exito=False, error="¿Qué quieres que diga?")
        
        # Intentar con pyttsx3 (offline)
        if self.tts_engine:
            try:
                self.tts_engine.say(texto)
                self.tts_engine.runAndWait()
                return ResultadoTarea(
                    exito=True,
                    datos={"texto": texto, "metodo": "pyttsx3", "mensaje": f"He dicho: {texto[:50]}"}
                )
            except Exception as e:
                self.logger.error(f"Error en TTS: {e}")
        
        # Fallback con gTTS (online)
        if GTTS_AVAILABLE:
            try:
                tts = gTTS(text=texto, lang=self.idioma.split('-')[0])
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                    tts.save(f.name)
                    # Reproducir con sistema
                    if sys.platform == 'darwin':
                        os.system(f'afplay "{f.name}"')
                    elif sys.platform == 'linux':
                        os.system(f'ffplay -nodisp -autoexit "{f.name}"')
                    elif sys.platform == 'win32':
                        os.system(f'start "{f.name}"')
                return ResultadoTarea(
                    exito=True,
                    datos={"texto": texto, "metodo": "gTTS", "mensaje": f"He dicho: {texto[:50]}"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=f"Error con gTTS: {e}")
        
        return ResultadoTarea(
            exito=False,
            error="No hay motor TTS disponible. Instala pyttsx3 o gTTS"
        )
    
    # ============================================================
    # TRANSCRIBIR
    # ============================================================
    
    async def _transcribir(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Transcribir audio a texto"""
        archivo = parametros.get("archivo") or self._extraer_archivo(desc)
        
        if not archivo:
            return ResultadoTarea(exito=False, error="Especifica el archivo de audio")
        
        archivo_path = Path(archivo)
        if not archivo_path.exists():
            return ResultadoTarea(exito=False, error=f"Archivo no encontrado: {archivo}")
        
        # Usar Whisper si está disponible
        if WHISPER_AVAILABLE and self.whisper_model:
            try:
                resultado = self.whisper_model.transcribe(str(archivo_path))
                texto = resultado["text"]
                return ResultadoTarea(
                    exito=True,
                    datos={
                        "texto": texto,
                        "archivo": archivo,
                        "metodo": "whisper",
                        "segmentos": resultado.get("segments", [])[:5]
                    }
                )
            except Exception as e:
                self.logger.error(f"Error con Whisper: {e}")
        
        # Usar SpeechRecognition
        if SPEECH_RECOGNITION_AVAILABLE:
            try:
                with sr.AudioFile(str(archivo_path)) as source:
                    audio = self.recognizer.record(source)
                    texto = self.recognizer.recognize_google(audio, language=self.idioma)
                    return ResultadoTarea(
                        exito=True,
                        datos={"texto": texto, "archivo": archivo, "metodo": "google"}
                    )
            except Exception as e:
                return ResultadoTarea(exito=False, error=f"Error transcribiendo: {e}")
        
        return ResultadoTarea(
            exito=False,
            error="No hay motor de transcripción disponible. Instala whisper o speech_recognition"
        )
    
    # ============================================================
    # GRABAR
    # ============================================================
    
    async def _grabar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Grabar audio del micrófono"""
        if not PYAUDIO_AVAILABLE:
            return ResultadoTarea(exito=False, error="PyAudio no instalado")
        
        duracion = parametros.get("duracion", 5)
        archivo = parametros.get("archivo", f"grabacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
        
        self.logger.info(f"Grabando {duracion} segundos...")
        
        try:
            import pyaudio
            import wave
            
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 44100
            
            p = pyaudio.PyAudio()
            
            stream = p.open(format=FORMAT,
                           channels=CHANNELS,
                           rate=RATE,
                           input=True,
                           input_device_index=self.microfono_index,
                           frames_per_buffer=CHUNK)
            
            frames = []
            
            for i in range(0, int(RATE / CHUNK * duracion)):
                data = stream.read(CHUNK)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            wf = wave.open(archivo, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "archivo": archivo,
                    "duracion": duracion,
                    "tamaño": Path(archivo).stat().st_size,
                    "mensaje": f"Grabación guardada en {archivo}"
                }
            )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error grabando: {e}")
    
    # ============================================================
    # LISTAR MICRÓFONOS
    # ============================================================
    
    async def _listar_microfonos(self) -> ResultadoTarea:
        """Listar micrófonos disponibles"""
        if not PYAUDIO_AVAILABLE:
            return ResultadoTarea(exito=False, error="PyAudio no instalado")
        
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            
            microfonos = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels') > 0:
                    microfonos.append({
                        "index": i,
                        "nombre": info.get('name'),
                        "canales": info.get('maxInputChannels'),
                        "tasa": int(info.get('defaultSampleRate'))
                    })
            
            p.terminate()
            
            return ResultadoTarea(
                exito=True,
                datos={"microfonos": microfonos, "total": len(microfonos)}
            )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _extraer_texto(self, desc: str) -> Optional[str]:
        """Extraer texto para hablar"""
        import re
        patterns = [
            r"di\s+(.+)",
            r"habla\s+(.+)",
            r"di que\s+(.+)",
            r"dice\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, desc, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extraer_archivo(self, desc: str) -> Optional[str]:
        """Extraer nombre de archivo de audio"""
        import re
        match = re.search(r'([\w\-\.]+\.(?:wav|mp3|ogg|flac))', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        return None


# ============================================================
# Factory Function
# ============================================================

def crear_agente_voz(supervisor: Supervisor, config: Config) -> AgenteVoz:
    """Crea instancia del agente de voz"""
    return AgenteVoz(supervisor, config)
