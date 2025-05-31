"""The EchoMind Assist integration."""
import logging
from typing import Any, Dict

import async_timeout
import asyncio
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    APP_NAME,
    CONF_ECHOMIND_ADDON_URL,
    CONF_ENABLE_DEBUG_LOGGING,
    DEFAULT_ECHOMIND_ADDON_URL,
    DEFAULT_ENABLE_DEBUG_LOGGING,
    SERVICE_ADD_MEMORY,
    SERVICE_SEARCH_MEMORY,
    SERVICE_CLEAR_MEMORY,
    SERVICE_GET_MEMORY_STATS,
    ATTR_TEXT,
    ATTR_CONTEXT,
    ATTR_USER_ID,
    ATTR_QUERY,
    ATTR_LIMIT,
    ATTR_DAYS_OLD,
    ATTR_RESULTS,
    ATTR_MEMORY_ID,
    ATTR_TOTAL_MEMORIES,
    ATTR_LAST_UPDATED,
    EVENT_ECHOMIND_MEMORY_ADDED,
    EVENT_ECHOMIND_SEARCH_RESULTS,
    EVENT_ECHOMIND_STATS_UPDATED
)

_LOGGER = logging.getLogger(__name__)

# Define las plataformas que tu integración usará (por ejemplo, sensor, conversation)
PLATFORMS: list[Platform] = [Platform.CONVERSATION] # Solo conversation por ahora

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the EchoMind Assist integration (yaml config not supported)."""
    # Este componente se configura solo a través de la UI (ConfigFlow)
    # Si alguna vez soportas YAML, la lógica iría aquí.
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EchoMind Assist from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    config = entry.data
    options = entry.options

    # Configurar el nivel de log basado en la opción del config flow
    # Esto permite cambiar el nivel de log dinámicamente si se implementa un OptionsFlow
    debug_logging_enabled = options.get(CONF_ENABLE_DEBUG_LOGGING, 
                                       config.get(CONF_ENABLE_DEBUG_LOGGING, DEFAULT_ENABLE_DEBUG_LOGGING))
    current_log_level = _LOGGER.getEffectiveLevel()
    if debug_logging_enabled:
        if current_log_level > logging.DEBUG:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.info("Debug logging enabled for EchoMind Assist.")
    else:
        if current_log_level == logging.DEBUG:
             _LOGGER.setLevel(logging.INFO) # O el nivel por defecto que uses
             _LOGGER.info("Debug logging disabled for EchoMind Assist.")

    addon_url = config.get(CONF_ECHOMIND_ADDON_URL, DEFAULT_ECHOMIND_ADDON_URL).rstrip('/')
    
    # Guardar la URL del addon para que los servicios y el agente de conversación puedan usarla
    # También podrías crear un "coordinator" o un "client" si la lógica es más compleja
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_ECHOMIND_ADDON_URL: addon_url,
        "config": config, # Guardar toda la config por si es útil en otros lados
        "options": options # Guardar opciones si hay un options flow
    }
    _LOGGER.info(f"EchoMind Assist configured with addon URL: {addon_url}")

    # Verificar conexión con el addon (opcional, pero bueno para early feedback)
    try:
        session = async_get_clientsession(hass)
        async with async_timeout.timeout(10):
            # Usar el endpoint /api/health si existe
            response = await session.get(f"{addon_url}/api/health")
            if response.status != 200:
                _LOGGER.warning(
                    f"Failed to connect to EchoMind addon at {addon_url}/api/health (status: {response.status}). "
                    f"Integration might not work correctly."
                )
                # Podrías levantar ConfigEntryNotReady aquí si la conexión es crítica al inicio
                # raise ConfigEntryNotReady(f"Cannot connect to EchoMind addon at {addon_url}")
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        _LOGGER.warning(f"Connection to EchoMind addon failed: {err}. Integration might not work.")
        # raise ConfigEntryNotReady(f"Cannot connect to EchoMind addon: {err}")

    # Cargar las plataformas (ej. conversation agent)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Registrar servicios
    await async_register_services(hass, entry)

    # Escuchar por cambios en las opciones si se implementa OptionsFlow
    entry.async_on_unload(entry.add_update_listener(async_update_options_listener))

    return True

async def async_update_options_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug(f"EchoMind Assist options updated: {entry.options}")
    # Aquí puedes recargar la entrada o actualizar datos si es necesario por cambio de opciones
    # Por ejemplo, cambiar el nivel de log o reconfigurar partes del componente.
    # await hass.config_entries.async_reload(entry.entry_id)
    
    # Actualizar el nivel de log basado en la nueva opción
    debug_logging_enabled = entry.options.get(CONF_ENABLE_DEBUG_LOGGING, DEFAULT_ENABLE_DEBUG_LOGGING)
    current_log_level = _LOGGER.getEffectiveLevel()
    if debug_logging_enabled:
        if current_log_level > logging.DEBUG:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.info("Debug logging enabled for EchoMind Assist via options update.")
    else:
        if current_log_level == logging.DEBUG:
             _LOGGER.setLevel(logging.INFO)
             _LOGGER.info("Debug logging disabled for EchoMind Assist via options update.")

    # Guardar las nuevas opciones en hass.data[DOMAIN][entry.entry_id]
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN][entry.entry_id]["options"] = entry.options
    else:
        _LOGGER.warning("Could not find EchoMind Assist entry data to update options.")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading EchoMind Assist integration.")
    # Descargar plataformas (conversation agent)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Eliminar servicios
    async_remove_services(hass)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]: # Si no quedan más entries, limpiar el dominio
            hass.data.pop(DOMAIN)

    return unload_ok

async def _call_echomind_api(
    hass: HomeAssistant, 
    entry_id: str, 
    method: str, 
    endpoint: str, 
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper function to call the EchoMind addon API."""
    if DOMAIN not in hass.data or entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("EchoMind Assist client not configured.")
        raise HomeAssistantError("EchoMind Assist client not configured.")

    base_url = hass.data[DOMAIN][entry_id][CONF_ECHOMIND_ADDON_URL]
    url = f"{base_url}/api/{endpoint}"
    session = async_get_clientsession(hass)

    _LOGGER.debug(f"Calling EchoMind API: {method} {url} with data: {data}")

    try:
        async with async_timeout.timeout(15): # Timeout un poco más largo para llamadas API
            if method.upper() == "GET":
                response = await session.get(url, params=data)
            elif method.upper() == "POST":
                response = await session.post(url, json=data)
            elif method.upper() == "DELETE":
                response = await session.delete(url, json=data) # DELETE con cuerpo JSON
            else:
                _LOGGER.error(f"Unsupported HTTP method: {method}")
                raise HomeAssistantError(f"Unsupported HTTP method: {method}")

            if response.status == 200 or response.status == 201:
                try:
                    result = await response.json()
                    _LOGGER.debug(f"EchoMind API response from {url}: {result}")
                    return result
                except aiohttp.ContentTypeError:
                     _LOGGER.debug(f"EchoMind API response from {url} was not JSON (status: {response.status}). Assuming success for non-JSON 200/201.")
                     return {"status": "success", "message": "Operation successful, no JSON response."}
            elif response.status == 204: # No Content, éxito
                _LOGGER.debug(f"EchoMind API response from {url}: Success (204 No Content)")
                return {"status": "success", "message": "Operation successful (204 No Content)."}
            else:
                error_text = await response.text()
                _LOGGER.error(
                    f"Error calling EchoMind API {url} (status: {response.status}): {error_text}"
                )
                raise HomeAssistantError(
                    f"EchoMind API error (status {response.status}): {error_text[:200]}..."
                )
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        _LOGGER.error(f"Error calling EchoMind API {url}: {e}")
        raise HomeAssistantError(f"EchoMind API communication error: {e}")
    except Exception as e:
        _LOGGER.exception(f"Unexpected error calling EchoMind API {url}: {e}")
        raise HomeAssistantError(f"Unexpected EchoMind API error: {e}")

async def async_register_services(hass: HomeAssistant, entry: ConfigEntry):
    """Register the EchoMind Assist services."""
    _LOGGER.info("Registering EchoMind Assist services.")

    async def add_memory_service(call: ServiceCall):
        """Service to add a new memory to EchoMind."""
        text = call.data.get(ATTR_TEXT)
        context = call.data.get(ATTR_CONTEXT, {})
        user_id = call.data.get(ATTR_USER_ID, "default") # Ejemplo, podrías tomarlo del contexto de HA

        if not text:
            _LOGGER.error("Add memory service called without 'text'.")
            raise ValueError("The 'text' field is required to add a memory.")

        # Enriquecer el contexto si es necesario
        context["source"] = "home_assistant_service"
        context["timestamp"] = hass.helpers.dt.utcnow().isoformat()
        context["user_id"] = user_id # Asegurar que user_id esté en el contexto

        payload = {"text": text, "context": context}
        try:
            result = await _call_echomind_api(hass, entry.entry_id, "POST", "memories", payload)
            memory_id = result.get("id", "unknown")
            _LOGGER.info(f"Memory '{text[:50]}...' added to EchoMind with ID: {memory_id}")
            hass.bus.async_fire(EVENT_ECHOMIND_MEMORY_ADDED, {ATTR_MEMORY_ID: memory_id, ATTR_TEXT: text})
        except HomeAssistantError as e:
            _LOGGER.error(f"Failed to add memory via service: {e}")
            # No relanzar para no matar la automatización, pero el error ya está logueado.

    async def search_memory_service(call: ServiceCall) -> Dict[str, Any]: # O SupportsResponse. მხოლოდ
        """Service to search memories in EchoMind."""
        query = call.data.get(ATTR_QUERY)
        limit = call.data.get(ATTR_LIMIT, 5)
        # user_id = call.data.get(ATTR_USER_ID) # Si tu API de búsqueda soporta filtrar por user_id

        if not query:
            _LOGGER.error("Search memory service called without 'query'.")
            raise ValueError("The 'query' field is required to search memories.")
        
        payload = {"query": query, "limit": limit}
        # if user_id: payload["user_id"] = user_id

        try:
            results = await _call_echomind_api(hass, entry.entry_id, "POST", "search", payload) # Asumiendo POST para búsqueda
            _LOGGER.info(f"Search for '{query}' returned {len(results)} memories from EchoMind.")
            hass.bus.async_fire(EVENT_ECHOMIND_SEARCH_RESULTS, {ATTR_QUERY: query, ATTR_RESULTS: results})
            # Para servicios que devuelven datos directamente (SupportsResponse.ONLY):
            return {ATTR_RESULTS: results}
        except HomeAssistantError as e:
            _LOGGER.error(f"Failed to search memory via service: {e}")
            return {ATTR_RESULTS: []} # Devolver vacío en caso de error

    async def clear_memory_service(call: ServiceCall):
        """Service to clear memories from EchoMind."""
        user_id = call.data.get(ATTR_USER_ID)
        days_old = call.data.get(ATTR_DAYS_OLD)
        payload = {}
        if user_id: payload["user_id"] = user_id
        if days_old: payload["days_old"] = days_old
        
        if not payload:
            _LOGGER.warning("Clear memory service called without any filters (user_id or days_old). This might clear all memories.")
            # Podrías requerir un filtro o una confirmación explícita si no hay filtros

        try:
            await _call_echomind_api(hass, entry.entry_id, "DELETE", "memories", payload)
            _LOGGER.info(f"Clear memory request sent to EchoMind with filters: {payload}")
        except HomeAssistantError as e:
            _LOGGER.error(f"Failed to clear memory via service: {e}")

    async def get_memory_stats_service(call: ServiceCall) -> Dict[str, Any]:
        """Service to get memory statistics from EchoMind."""
        try:
            stats = await _call_echomind_api(hass, entry.entry_id, "GET", "stats")
            _LOGGER.info(f"Memory stats received from EchoMind: {stats}")
            hass.bus.async_fire(EVENT_ECHOMIND_STATS_UPDATED, stats)
            return stats
        except HomeAssistantError as e:
            _LOGGER.error(f"Failed to get memory stats via service: {e}")
            return {} # Devolver vacío o error

    # Registrar los servicios
    hass.services.async_register(DOMAIN, SERVICE_ADD_MEMORY, add_memory_service)
    
    # El servicio de búsqueda puede devolver datos, así que usa supports_response
    hass.services.async_register(
        DOMAIN, 
        SERVICE_SEARCH_MEMORY, 
        search_memory_service, 
        supports_response=SupportsResponse.ONLY # O .OPTIONAL si a veces no devuelve
    )
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_MEMORY, clear_memory_service)
    hass.services.async_register(
        DOMAIN, 
        SERVICE_GET_MEMORY_STATS, 
        get_memory_stats_service,
        supports_response=SupportsResponse.ONLY
    )

def async_remove_services(hass: HomeAssistant):
    """Remove the EchoMind Assist services."""
    _LOGGER.info("Removing EchoMind Assist services.")
    hass.services.async_remove(DOMAIN, SERVICE_ADD_MEMORY)
    hass.services.async_remove(DOMAIN, SERVICE_SEARCH_MEMORY)
    hass.services.async_remove(DOMAIN, SERVICE_CLEAR_MEMORY)
    hass.services.async_remove(DOMAIN, SERVICE_GET_MEMORY_STATS)

