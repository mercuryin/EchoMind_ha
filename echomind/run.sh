#!/usr/bin/with-contenv bashio
# shellcheck shell=bash

# ==============================================================================
# Script de inicio para el Addon EchoMind
# ==============================================================================

# Configuración de Bash Strict Mode (opcional pero recomendado)
set -o errexit  # Salir inmediatamente si un comando falla
set -o nounset  # Salir si se usa una variable no definida
set -o pipefail # El código de salida de una pipeline es el del último comando que falló
# IFS=$'\n\t' # Configurar Internal Field Separator para evitar problemas con espacios (opcional)

# Variables de Configuración del Addon (leídas desde options.json)
# Usar bashio::config para leer las opciones de forma segura
CONFIG_PATH=/data/options.json

BASHIO_LOG_LEVEL=$(bashio::config 'log_level' 'info') # Nivel de log para bashio y scripts
ENCRYPTION_ENABLED=$(bashio::config 'encryption_enabled' true)
LOCAL_ONLY=$(bashio::config 'local_only' true)
API_KEY=$(bashio::config 'api_key' '')
MAX_MEMORIES=$(bashio::config 'max_memories' 10000)
CLEANUP_DAYS=$(bashio::config 'cleanup_days' 30)

# Configurar el nivel de log de bashio
if bashio::log.level_exists "${BASHIO_LOG_LEVEL}"; then
    bashio::log.level "${BASHIO_LOG_LEVEL}"
else
    bashio::log.level "info" # Fallback a info si el nivel no es válido
fi

bashio::log.info "---------------------------------------------------------"
bashio::log.info "             Iniciando Addon EchoMind v$(bashio::addon.version)            "
bashio::log.info "---------------------------------------------------------"
bashio::log.info "Repositorio del Addon: https://github.com/mercuryin/EchoMind_ha"
bashio::log.info "Aplicación base EchoMind (fork): https://github.com/mercuryin/your-memory"
bashio::log.info "Por favor, informa de cualquier problema o sugerencia."

bashio::log.debug "Leyendo configuración del addon..."
bashio::log.debug "CONFIG_PATH: ${CONFIG_PATH}"
bashio::log.debug "Log Level: ${BASHIO_LOG_LEVEL}"
bashio::log.debug "Encryption Enabled: ${ENCRYPTION_ENABLED}"
bashio::log.debug "Local Only: ${LOCAL_ONLY}"
bashio::log.debug "API Key (longitud): ${#API_KEY}" # No mostrar la API Key directamente
bashio::log.debug "Max Memories: ${MAX_MEMORIES}"
bashio::log.debug "Cleanup Days: ${CLEANUP_DAYS}"

# Exportar variables de entorno para la aplicación Node.js
# La aplicación Node.js debería estar preparada para leer estas variables
export NODE_ENV="production" # Entorno de Node.js
export LOG_LEVEL="${BASHIO_LOG_LEVEL}" # Pasar el nivel de log a la app
export ENCRYPTION_ENABLED="${ENCRYPTION_ENABLED}"
export LOCAL_ONLY="${LOCAL_ONLY}"
export API_KEY="${API_KEY}"
export MAX_MEMORIES="${MAX_MEMORIES}"
export CLEANUP_DAYS="${CLEANUP_DAYS}"
export DATA_DIR="/data" # Directorio persistente para datos del addon
export ECHOMIND_API_PORT="8765" # Puerto para la API de EchoMind
export ECHOMIND_WEB_PORT="3000" # Puerto para la Web UI de EchoMind

# Crear directorios necesarios si no existen
# /data es el directorio persistente para el addon
bashio::log.info "Asegurando que los directorios de datos existen..."
mkdir -p /data/echomind_db # Para la base de datos vectorial (ChromaDB)
mkdir -p /data/backups     # Para backups de la aplicación
mkdir -p /data/config      # Para cualquier configuración adicional de la app Node.js

# Ejecutar el script de configuración de EchoMind para Home Assistant
# Este script puede configurar la aplicación Node.js para que funcione con HA
bashio::log.info "Ejecutando script de configuración de EchoMind (echomind-ha-setup)..."
if [ -f /usr/bin/echomind-ha-setup ]; then
    chmod +x /usr/bin/echomind-ha-setup # Asegurar permisos
    /usr/bin/echomind-ha-setup
    bashio::log.info "Script echomind-ha-setup ejecutado."
else
    bashio::log.warning "Script echomind-ha-setup no encontrado en /usr/bin. Omitiendo."
fi

# Navegar al directorio de la aplicación
cd /app || bashio::exit.nok "No se pudo cambiar al directorio /app"

# Iniciar la aplicación Node.js (EchoMind)
bashio::log.info "Iniciando la aplicación EchoMind (Node.js)..."
# Usar `exec` para reemplazar el proceso de shell con el proceso de Node
# o ejecutar en segundo plano si necesitas que el script continúe (por ejemplo, para health checks)

# Opción 1: Ejecutar en segundo plano y esperar (como en tu script original)
# Esto permite que bashio maneje señales y que el script siga si Node.js no las maneja bien
# npm start &
# APP_PID=$!
# bashio::log.info "Aplicación EchoMind iniciada con PID: ${APP_PID}"
# wait "${APP_PID}"

# Opción 2: Usar exec para reemplazar el proceso actual (más limpio si Node maneja señales SIGTERM/SIGINT)
# Asegúrate de que tu app Node.js maneje correctamente SIGTERM para un apagado limpio.
exec npm start

# Si npm start no funciona directamente, podría ser necesario llamar a node explícitamente:
# exec node server.js # o el entrypoint de tu aplicación

bashio::log.info "Aplicación EchoMind detenida."
# Código de salida (opcional, bashio::exit.ok o bashio::exit.nok)
