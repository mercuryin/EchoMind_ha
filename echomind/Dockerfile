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

# Instalar dependencias básicas y de compilación
RUN apk add --no-cache \
    bash \
    curl \
    git \
    jq \
    python3 \
    py3-pip \
    build-base \
    python3-dev \
    gcc \
    musl-dev \
    linux-headers \
    rust \
    cargo \
    openssl-dev \
    libffi-dev \
    py3-setuptools \
    ca-certificates && \
    update-ca-certificates

# Instalar Poetry usando el instalador oficial
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Configurar poetry
RUN poetry config virtualenvs.create false && \
    poetry config installer.max-workers 10

# Crear directorio de trabajo
WORKDIR /app

# Clonar el repositorio original de your-memory
RUN git clone https://github.com/jonathan-politzki/your-memory.git .

# Instalar dependencias de Python con más verbosidad
RUN poetry install --no-dev --no-interaction --no-ansi -vv

# Limpiar herramientas de compilación
RUN apk del build-base python3-dev gcc musl-dev linux-headers rust cargo openssl-dev libffi-dev py3-setuptools

# Copiar archivos de configuración y scripts específicos del addon
COPY rootfs/ / 

# Hacer ejecutables los scripts importantes
RUN chmod +x /run.sh && \
    chmod +x /usr/bin/echomind-ha-setup

# Exponer los puertos que la aplicación utilizará
EXPOSE 8765 3000

# Comando por defecto para iniciar el addon
CMD [ "/run.sh" ]
