ARG BUILD_FROM
FROM ${BUILD_FROM}

# Addon metadata
LABEL io.hass.name="EchoMind - AI Memory Layer"
LABEL io.hass.description="Personal Memory Layer for AI Applications with Home Assistant Integration. All memory remains local."
LABEL io.hass.version="1.0.0"
LABEL io.hass.slug="echomind"
LABEL io.hass.arch="$BUILD_ARCH"
LABEL maintainer="mercuryin <[tu_email_o_contacto_aqui]>" 
LABEL io.hass.url="https://github.com/mercuryin/EchoMind_ha"

# Instalar dependencias del sistema y herramientas base
RUN apk add --no-cache \
    bash \
    curl \
    git \
    jq \
    nodejs \
    npm \
    python3 \
    py3-pip

# Instalar uv para gestión de paquetes Python y luego las dependencias de Python
# Esto permite un build más rápido de las dependencias de Python
RUN pip3 install uv && \
    uv pip install --system \
    chromadb \
    sentence-transformers

# Crear directorio de trabajo para la aplicación Node.js
WORKDIR /app

# Clonar tu fork de EchoMind
RUN git clone https://github.com/mercuryin/your-memory.git . 
# Si tienes una rama específica para el addon, clónala:
# RUN git clone -b ha-addon --single-branch https://github.com/mercuryin/your-memory.git .

# Instalar dependencias de Node.js
# Usar --legacy-peer-deps si hay problemas con dependencias de pares, común en algunos proyectos Node
RUN npm install --production --legacy-peer-deps

# Copiar archivos de configuración y scripts específicos del addon
# Esto incluye el script de inicio y cualquier script de setup
COPY rootfs/ / 

# Hacer ejecutables los scripts importantes
RUN chmod +x /run.sh && \
    chmod +x /usr/bin/echomind-ha-setup

# Exponer los puertos que la aplicación utilizará
EXPOSE 8765 3000

# Comando por defecto para iniciar el addon
CMD [ "/run.sh" ]
