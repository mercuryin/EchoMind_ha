"""Constants for the EchoMind Assist integration."""

# Domain for the integration
DOMAIN = "echomind_assist"

# Configuration keys
CONF_ECHOMIND_ADDON_URL = "echomind_addon_url"      # Renamed from CONF_JEAN_MEMORY_URL
CONF_BASE_CONVERSATION_AGENT = "base_conversation_agent" # Renamed for clarity
CONF_MEMORY_CONTEXT_LIMIT = "memory_context_limit"
CONF_AUTO_STORE_CONVERSATIONS = "auto_store_conversations" # Renamed for clarity
CONF_ENABLE_DEBUG_LOGGING = "enable_debug_logging" # New option for verbose logging

# Default values
DEFAULT_ECHOMIND_ADDON_URL = "http://echomind.local.hass.io:8765" # Using .local.hass.io for supervisor DNS
DEFAULT_MEMORY_CONTEXT_LIMIT = 5
DEFAULT_AUTO_STORE_CONVERSATIONS = True
DEFAULT_ENABLE_DEBUG_LOGGING = False

# Service names
SERVICE_ADD_MEMORY = "add_memory"
SERVICE_SEARCH_MEMORY = "search_memory"
SERVICE_CLEAR_MEMORY = "clear_memory"
SERVICE_GET_MEMORY_STATS = "get_memory_stats" # New service example

# Event types
EVENT_ECHOMIND_MEMORY_ADDED = f"{DOMAIN}_memory_added"
EVENT_ECHOMIND_SEARCH_RESULTS = f"{DOMAIN}_search_results"
EVENT_ECHOMIND_STATS_UPDATED = f"{DOMAIN}_stats_updated"

# Attributes
ATTR_TEXT = "text"
ATTR_CONTEXT = "context"
ATTR_USER_ID = "user_id"
ATTR_QUERY = "query"
ATTR_LIMIT = "limit"
ATTR_DAYS_OLD = "days_old"
ATTR_RESULTS = "results"
ATTR_MEMORY_ID = "memory_id"
ATTR_TOTAL_MEMORIES = "total_memories"
ATTR_LAST_UPDATED = "last_updated"

# Other constants
APP_NAME = "EchoMind Assist"

# Base agent ID if none is selected, allowing passthrough or basic functionality
NO_BASE_AGENT_SELECTED = "echomind_no_base_agent"
