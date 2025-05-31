"""Config flow for EchoMind Assist integration."""
import logging
from typing import Any, Dict, Optional

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    APP_NAME,
    CONF_ECHOMIND_ADDON_URL,
    CONF_BASE_CONVERSATION_AGENT,
    CONF_MEMORY_CONTEXT_LIMIT,
    CONF_AUTO_STORE_CONVERSATIONS,
    CONF_ENABLE_DEBUG_LOGGING,
    DEFAULT_ECHOMIND_ADDON_URL,
    DEFAULT_MEMORY_CONTEXT_LIMIT,
    DEFAULT_AUTO_STORE_CONVERSATIONS,
    DEFAULT_ENABLE_DEBUG_LOGGING,
    NO_BASE_AGENT_SELECTED
)

_LOGGER = logging.getLogger(__name__)

async def validate_addon_connection(hass: HomeAssistant, url: str) -> Dict[str, Any]:
    """Validate that we can connect to the EchoMind addon."""
    session = async_get_clientsession(hass)
    errors: Dict[str, str] = {}
    try:
        # Prefer a dedicated health check endpoint if the addon provides one
        async with session.get(f"{url.rstrip('/')}/api/health", timeout=10) as response:
            if response.status == 200:
                # Optionally, you could check the response content for a specific value
                # data = await response.json()
                # if data.get("status") == "ok":
                #     return errors
                _LOGGER.info(f"Successfully connected to EchoMind addon at {url}")
                return errors # Success
            elif response.status == 404:
                _LOGGER.warning(f"Health check endpoint not found on EchoMind addon at {url}/api/health. Assuming OK if base URL is reachable.")
                # Fallback: try base URL if /api/health is not found (for simpler addons)
                async with session.get(url, timeout=10) as base_response:
                    if base_response.status == 200 or base_response.status == 403: # 403 might mean Ingress is working
                         _LOGGER.info(f"Fallback connection to EchoMind addon at {url} successful (status: {base_response.status})")
                         return errors
                    errors["base"] = "cannot_connect_fallback"
                    _LOGGER.error(f"Fallback connection failed to EchoMind addon at {url}, status: {base_response.status}")
                    return errors
            else:
                errors["base"] = "cannot_connect"
                _LOGGER.error(f"Connection failed to EchoMind addon health check at {url}/api/health, status: {response.status}")
                return errors
    except aiohttp.ClientConnectorError:
        _LOGGER.error(f"ClientConnectorError connecting to EchoMind addon at {url}")
        errors["base"] = "cannot_connect_client_connector"
    except TimeoutError:
        _LOGGER.error(f"Timeout connecting to EchoMind addon at {url}")
        errors["base"] = "timeout_connect"
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception connecting to EchoMind addon at {url}: {e}")
        errors["base"] = "unknown"
    return errors

class EchoMindAssistConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EchoMind Assist."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            addon_url = user_input.get(CONF_ECHOMIND_ADDON_URL, DEFAULT_ECHOMIND_ADDON_URL).rstrip('/')
            validation_errors = await validate_addon_connection(self.hass, addon_url)
            errors.update(validation_errors)

            if not errors:
                # Ensure unique instance
                await self.async_set_unique_id(f"{DOMAIN}_{addon_url}")
                self._abort_if_unique_id_configured()

                _LOGGER.info(f"Creating EchoMind Assist config entry with data: {user_input}")
                return self.async_create_entry(title=APP_NAME, data=user_input)

        # Get available conversation agents for the base_agent dropdown
        # This is a simplified way; a more robust way might involve a helper function
        # or waiting for conversation component to be fully set up.
        conv_agents = self.hass.data.get("conversation", {}).get("agents", {})
        available_agents = {agent_id: agent_id for agent_id in conv_agents.keys()}
        # Add a "None" option or a special marker if no base agent is desired
        available_agents[NO_BASE_AGENT_SELECTED] = "No specific base agent (EchoMind direct)"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ECHOMIND_ADDON_URL,
                    default=user_input.get(CONF_ECHOMIND_ADDON_URL, DEFAULT_ECHOMIND_ADDON_URL) if user_input else DEFAULT_ECHOMIND_ADDON_URL,
                ): cv.string,
                vol.Optional(
                    CONF_BASE_CONVERSATION_AGENT,
                    default=user_input.get(CONF_BASE_CONVERSATION_AGENT, NO_BASE_AGENT_SELECTED) if user_input else NO_BASE_AGENT_SELECTED,
                ): vol.In(available_agents),
                vol.Optional(
                    CONF_MEMORY_CONTEXT_LIMIT,
                    default=user_input.get(CONF_MEMORY_CONTEXT_LIMIT, DEFAULT_MEMORY_CONTEXT_LIMIT) if user_input else DEFAULT_MEMORY_CONTEXT_LIMIT,
                ): cv.positive_int,
                vol.Optional(
                    CONF_AUTO_STORE_CONVERSATIONS,
                    default=user_input.get(CONF_AUTO_STORE_CONVERSATIONS, DEFAULT_AUTO_STORE_CONVERSATIONS) if user_input else DEFAULT_AUTO_STORE_CONVERSATIONS,
                ): cv.boolean,
                vol.Optional(
                    CONF_ENABLE_DEBUG_LOGGING,
                    default=user_input.get(CONF_ENABLE_DEBUG_LOGGING, DEFAULT_ENABLE_DEBUG_LOGGING) if user_input else DEFAULT_ENABLE_DEBUG_LOGGING,
                ): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors, last_step=True
        )

    # Example of how to implement options flow if needed later
    # @staticmethod
    # @callback
    # def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlowHandler:
    #     """Get the options flow for this handler."""
    #     return EchoMindOptionsFlowHandler(config_entry)

# class EchoMindOptionsFlowHandler(config_entries.OptionsFlow):
#     """Handle an options flow for EchoMind Assist."""

#     def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
#         """Initialize options flow."""
#         self.config_entry = config_entry

#     async def async_step_init(
#         self, user_input: Optional[Dict[str, Any]] = None
#     ) -> FlowResult:
#         """Manage the options."""
#         errors: Dict[str, str] = {}
        
#         # Get current agents again, in case they changed
#         conv_agents = self.hass.data.get("conversation", {}).get("agents", {})
#         available_agents = {agent_id: agent_id for agent_id in conv_agents.keys()}
#         available_agents[NO_BASE_AGENT_SELECTED] = "No specific base agent (EchoMind direct)"

#         if user_input is not None:
#             # TODO: Add validation for options if necessary
#             _LOGGER.debug(f"Updating EchoMind Assist options with: {user_input}")
#             return self.async_create_entry(title="", data=user_input)

#         schema = vol.Schema(
#             {
#                 vol.Optional(
#                     CONF_BASE_CONVERSATION_AGENT,
#                     default=self.config_entry.options.get(CONF_BASE_CONVERSATION_AGENT, NO_BASE_AGENT_SELECTED),
#                 ): vol.In(available_agents),
#                 vol.Optional(
#                     CONF_MEMORY_CONTEXT_LIMIT,
#                     default=self.config_entry.options.get(CONF_MEMORY_CONTEXT_LIMIT, DEFAULT_MEMORY_CONTEXT_LIMIT),
#                 ): cv.positive_int,
#                 vol.Optional(
#                     CONF_AUTO_STORE_CONVERSATIONS,
#                     default=self.config_entry.options.get(CONF_AUTO_STORE_CONVERSATIONS, DEFAULT_AUTO_STORE_CONVERSATIONS),
#                 ): cv.boolean,
#                 vol.Optional(
#                     CONF_ENABLE_DEBUG_LOGGING,
#                     default=self.config_entry.options.get(CONF_ENABLE_DEBUG_LOGGING, DEFAULT_ENABLE_DEBUG_LOGGING),
#                 ): cv.boolean,
#             }
#         )

#         return self.async_show_form(
#             step_id="init", data_schema=schema, errors=errors, last_step=True
#         )
