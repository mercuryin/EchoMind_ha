"""Conversation agent for EchoMind Assist integration."""
import logging
from typing import Any, Dict, Optional
import dataclasses # Para dataclasses.replace

import aiohttp
import async_timeout

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from homeassistant.components.homeassistant.exposed_entities import async_should_expose

from .const import (
    DOMAIN,
    APP_NAME,
    CONF_ECHOMIND_ADDON_URL,
    CONF_BASE_CONVERSATION_AGENT,
    CONF_MEMORY_CONTEXT_LIMIT,
    CONF_AUTO_STORE_CONVERSATIONS,
    CONF_ENABLE_DEBUG_LOGGING, # Para logs del agente
    DEFAULT_ECHOMIND_ADDON_URL,
    DEFAULT_MEMORY_CONTEXT_LIMIT,
    DEFAULT_AUTO_STORE_CONVERSATIONS,
    NO_BASE_AGENT_SELECTED
)

_LOGGER = logging.getLogger(__name__)

async def async_get_agent(hass: HomeAssistant, entry: ConfigEntry) -> conversation.AbstractConversationAgent:
    """Set up and return EchoMind conversation agent."""
    # Acceder a la configuración y opciones guardadas en __init__.py
    # Esto es más limpio que pasar `entry` directamente si solo necesitas ciertos valores.
    # O puedes pasar `entry` si el agente necesita acceder a más cosas de la config entry.
    # agent_data = hass.data[DOMAIN][entry.entry_id]
    # addon_url = agent_data[CONF_ECHOMIND_ADDON_URL]
    # etc.
    
    # Crear una instancia del agente con la entrada de configuración
    agent = EchoMindConversationAgent(hass, entry)
    await agent.async_initialize() # Permitir inicialización asíncrona si es necesaria
    return agent

class EchoMindConversationAgent(conversation.AbstractConversationAgent):
    """EchoMind conversation agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry # Guardar la config entry para acceder a config y options
        self._addon_url: str = ""
        self._base_agent_id: Optional[str] = None
        self._memory_context_limit: int = DEFAULT_MEMORY_CONTEXT_LIMIT
        self._auto_store: bool = DEFAULT_AUTO_STORE_CONVERSATIONS
        self._base_agent: Optional[conversation.AbstractConversationAgent] = None
        self._debug_logging: bool = False

    async def async_initialize(self) -> None:
        """Initialize the agent asynchronously after creation."""
        config = self.entry.data
        options = self.entry.options # Usar opciones si existen (de OptionsFlow)

        self._addon_url = options.get(CONF_ECHOMIND_ADDON_URL, config.get(CONF_ECHOMIND_ADDON_URL, DEFAULT_ECHOMIND_ADDON_URL)).rstrip('/')
        self._base_agent_id = options.get(CONF_BASE_CONVERSATION_AGENT, config.get(CONF_BASE_CONVERSATION_AGENT))
        self._memory_context_limit = options.get(CONF_MEMORY_CONTEXT_LIMIT, config.get(CONF_MEMORY_CONTEXT_LIMIT, DEFAULT_MEMORY_CONTEXT_LIMIT))
        self._auto_store = options.get(CONF_AUTO_STORE_CONVERSATIONS, config.get(CONF_AUTO_STORE_CONVERSATIONS, DEFAULT_AUTO_STORE_CONVERSATIONS))
        self._debug_logging = options.get(CONF_ENABLE_DEBUG_LOGGING, config.get(CONF_ENABLE_DEBUG_LOGGING, False))

        if self._debug_logging:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug logging enabled for EchoMindConversationAgent")
        else:
            # Restablecer al nivel de log del logger principal si el debug está desactivado
            # Esto asume que el logger principal (en __init__) controla el nivel base.
            # O puedes fijarlo a logging.INFO aquí.
            parent_logger_level = logging.getLogger(f"custom_components.{DOMAIN}").getEffectiveLevel()
            _LOGGER.setLevel(parent_logger_level if parent_logger_level != logging.NOTSET else logging.INFO)

        _LOGGER.debug(
            f"EchoMind Agent Initializing: Addon URL='{self._addon_url}', Base Agent ID='{self._base_agent_id}', "
            f"Context Limit={self._memory_context_limit}, Auto Store={self._auto_store}, Debug Logging={self._debug_logging}"
        )

        if self._base_agent_id and self._base_agent_id != NO_BASE_AGENT_SELECTED:
            try:
                # Obtener el agente base real
                all_agents = await conversation.async_get_conversation_agents(self.hass)
                self._base_agent = all_agents.get(self._base_agent_id)
                if self._base_agent:
                    _LOGGER.info(f"Successfully loaded base conversation agent: {self._base_agent_id}")
                else:
                    _LOGGER.warning(f"Base conversation agent '{self._base_agent_id}' not found.")
            except Exception as e:
                _LOGGER.error(f"Error loading base conversation agent '{self._base_agent_id}': {e}")
                self._base_agent = None # Asegurar que es None si falla la carga
        else:
            _LOGGER.info("No base conversation agent selected or EchoMind direct mode.")
            self._base_agent = None

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        if self._base_agent:
            return self._base_agent.supported_languages
        # Si no hay agente base, EchoMind podría ser agnóstico al idioma o tener su propia lista
        return ["en", "es"] # Ejemplo, ajustar según sea necesario

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        if self._debug_logging:
            _LOGGER.debug(f"Input to EchoMind Agent: Text='{user_input.text}', ConvID='{user_input.conversation_id}', DeviceID='{user_input.device_id}')

        # 1. Recuperar memorias relevantes
        relevant_memories = await self._get_relevant_memories(
            user_input.text, 
            user_input.conversation_id
        )

        # 2. Enriquecer el prompt/input con el contexto de memoria
        # Esto es para el LLM del agente base. Si no hay agente base, EchoMind podría usar esto directamente.
        processed_input_text = self._enhance_text_with_memory(user_input.text, relevant_memories)
        
        # Crear una nueva instancia de ConversationInput con el texto modificado
        # Esto es importante para no modificar el objeto original si se reutiliza
        enhanced_user_input = dataclasses.replace(user_input, text=processed_input_text)

        if self._debug_logging:
            _LOGGER.debug(f"Enhanced text for LLM: {enhanced_user_input.text}")

        # 3. Procesar con el agente base (LLM) si está configurado
        if self._base_agent:
            try:
                # Pasar el input enriquecido al agente base
                result = await self._base_agent.async_process(enhanced_user_input)
            except Exception as e:
                _LOGGER.error(f"Error processing with base agent '{self._base_agent_id}': {e}")
                # Fallback a una respuesta directa de EchoMind o error
                intent_response = conversation.IntentResponse(language=user_input.language)
                intent_response.async_set_error(
                    conversation.IntentResponseErrorCode.UNKNOWN,
                    f"Error in base agent: {e}"
                )
                result = conversation.ConversationResult(
                    response=intent_response, conversation_id=user_input.conversation_id
                )
        else:
            # No hay agente base, EchoMind podría intentar responder directamente o indicar que no puede
            _LOGGER.info("No base agent, EchoMind direct response (not fully implemented in this example).")
            intent_response = conversation.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(
                f"EchoMind received: '{user_input.text}'. Memory context was considered. (Direct LLM response not implemented)"
            )
            # Aquí podrías hacer una llamada a tu addon para que un LLM procese `enhanced_user_input.text`
            # direct_llm_response = await self._call_echomind_llm(enhanced_user_input.text)
            # intent_response.async_set_speech(direct_llm_response)
            result = conversation.ConversationResult(
                response=intent_response, conversation_id=user_input.conversation_id
            )

        # 4. Almacenar nueva información en memoria (si está habilitado)
        if self._auto_store:
            assistant_response_text = ""
            if result.response.speech:
                 # Intentar obtener la parte "plain" o la primera respuesta de voz disponible
                speech_parts = result.response.speech.get("plain", result.response.speech)
                if isinstance(speech_parts, dict):
                    assistant_response_text = speech_parts.get("speech", "")
                elif isinstance(speech_parts, str): # Si es una cadena directa (menos común)
                    assistant_response_text = speech_parts
            
            if not assistant_response_text and result.response.error_code:
                assistant_response_text = f"Error from LLM: {result.response.error_code}"

            await self._store_interaction(
                user_input.text,
                assistant_response_text,
                user_input.conversation_id,
                user_input.device_id
            )
        
        if self._debug_logging:
             _LOGGER.debug(f"Output from EchoMind Agent: Response='{result.response.speech}', ConvID='{result.conversation_id}'")

        return result

    async def _call_echomind_api(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Helper function to call the EchoMind addon API."""
        # Reutilizar la función de __init__.py sería ideal si estuviera en un módulo compartido
        # Por ahora, duplicamos una versión simplificada o podríamos importarla si la estructura lo permite.
        # Esta versión es más simple y asume que la URL del addon está en self._addon_url
        
        url = f"{self._addon_url}/api/{endpoint.lstrip('/')}"
        session = async_get_clientsession(self.hass)
        
        if self._debug_logging:
            _LOGGER.debug(f"Agent calling EchoMind API: {method} {url} with data: {data}")

        try:
            async with async_timeout.timeout(10): # Timeout para llamadas API
                if method.upper() == "GET":
                    api_response = await session.get(url, params=data)
                elif method.upper() == "POST":
                    api_response = await session.post(url, json=data)
                # Añadir más métodos si es necesario (DELETE, PUT)
                else:
                    _LOGGER.error(f"Unsupported HTTP method in agent: {method}")
                    return {"error": f"Unsupported HTTP method: {method}"}

                if api_response.status == 200 or api_response.status == 201:
                    try:
                        result_json = await api_response.json()
                        if self._debug_logging:
                            _LOGGER.debug(f"API response from {url}: {result_json}")
                        return result_json
                    except aiohttp.ContentTypeError:
                        if self._debug_logging:
                            _LOGGER.debug(f"API response from {url} was not JSON (status: {api_response.status}).")
                        return {"status": "success", "message": "Operation successful, no JSON response."}
                elif api_response.status == 204:
                     if self._debug_logging:
                        _LOGGER.debug(f"API response from {url}: Success (204 No Content)")
                     return {"status": "success", "message": "Operation successful (204 No Content)."}
                else:
                    error_text = await api_response.text()
                    _LOGGER.warning(
                        f"Error from EchoMind API {url} (status: {api_response.status}): {error_text}"
                    )
                    return {"error": "api_call_failed", "status_code": api_response.status, "details": error_text[:200]}
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            _LOGGER.error(f"Error calling EchoMind API {url}: {e}")
            return {"error": "communication_error", "details": str(e)}
        except Exception as e:
            _LOGGER.exception(f"Unexpected error calling EchoMind API {url}: {e}")
            return {"error": "unexpected_error", "details": str(e)}

    async def _get_relevant_memories(self, query: str, conversation_id: Optional[str]) -> list:
        """Fetch relevant memories from EchoMind addon."""
        payload = {"query": query, "limit": self._memory_context_limit}
        if conversation_id:
            # Si tu API soporta filtrar por conversation_id, añádelo aquí
            # payload["context_filter"] = {"conversation_id": conversation_id}
            # O podrías pasar el conversation_id como un campo de primer nivel si la API lo espera así
            payload["conversation_id"] = conversation_id 

        if self._debug_logging:
            _LOGGER.debug(f"Searching memories with payload: {payload}")

        response_data = await self._call_echomind_api("POST", "search", payload) # Asumiendo POST para búsqueda
        
        if "error" in response_data:
            _LOGGER.warning(f"Failed to get relevant memories: {response_data.get('details')}")
            return []
        
        # Asumir que la respuesta es una lista de memorias si no hay error
        # o que está bajo una clave como "results" o "memories"
        memories = response_data if isinstance(response_data, list) else response_data.get("results", [])
        if self._debug_logging:
            _LOGGER.debug(f"Found {len(memories)} relevant memories.")
        return memories

    def _enhance_text_with_memory(self, text: str, memories: list) -> str:
        """Enhance the user's input text with memory context for the LLM."""
        if not memories:
            return text

        # Formato del contexto de memoria (ajustar según preferencia)
        memory_context_parts = ["# Relevant Memory Context (from EchoMind):"]
        for mem in memories:
            timestamp_str = mem.get("context", {}).get("timestamp", "")
            # Intentar parsear y formatear el timestamp si es una cadena ISO
            try:
                if timestamp_str:
                    dt_obj = dt_util.parse_datetime(timestamp_str)
                    if dt_obj:
                        # Formato más amigable, o podrías usar dt_util.as_local(dt_obj).strftime(...)
                        timestamp_str = dt_obj.strftime("%Y-%m-%d %H:%M") 
            except ValueError:
                pass # Dejar el timestamp como está si no se puede parsear
            
            memory_text = mem.get("text", "")
            if timestamp_str:
                memory_context_parts.append(f"- [{timestamp_str}] {memory_text}")
            else:
                memory_context_parts.append(f"- {memory_text}")
        
        memory_context_str = "\n".join(memory_context_parts)

        # Combinar con la consulta actual del usuario
        # Este prompt puede ser bastante largo. Considera truncar `memory_context_str`
        # o el número de memorias si excede el límite de tokens del LLM base.
        enhanced_text = f"{memory_context_str}\n\n# User's Current Query:\n{text}"
        
        # Opcional: Añadir instrucciones específicas para el LLM sobre cómo usar la memoria
        # enhanced_text += "\n\nInstruction: Use the memory context above to provide a more informed and personalized response to the user's current query. Refer to past interactions if relevant."
        return enhanced_text

    async def _store_interaction(
        self,
        user_text: str,
        assistant_response: str,
        conversation_id: Optional[str],
        device_id: Optional[str],
    ) -> None:
        """Store the current user-assistant interaction in EchoMind."""
        if not user_text and not assistant_response: # No almacenar si no hay nada que almacenar
            if self._debug_logging:
                _LOGGER.debug("Skipping storage of empty interaction.")
            return

        payload = {
            "text": f"User: {user_text}\nAssistant: {assistant_response}",
            "context": {
                "source": "home_assistant_conversation",
                "conversation_id": conversation_id or "unknown_conversation",
                "device_id": device_id or "unknown_device",
                "timestamp": dt_util.utcnow().isoformat(), # UTC timestamp
                "user_input": user_text, # Guardar user_input por separado
                "assistant_output": assistant_response # Guardar assistant_output por separado
            }
        }
        if self._debug_logging:
            _LOGGER.debug(f"Storing interaction with payload: {payload}")

        response_data = await self._call_echomind_api("POST", "memories", payload)
        
        if "error" in response_data:
            _LOGGER.warning(f"Failed to store interaction: {response_data.get('details')}")
        elif self._debug_logging:
            memory_id = response_data.get("id", "unknown")
            _LOGGER.debug(f"Interaction stored successfully. Memory ID: {memory_id}")
