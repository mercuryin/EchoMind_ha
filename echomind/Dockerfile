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

# Crear directorio de trabajo
WORKDIR /app

# Clonar el repositorio original de your-memory
RUN git clone https://github.com/jonathan-politzki/your-memory.git .

# Actualizar pip y wheel
RUN pip3 install --no-cache-dir --upgrade pip wheel setuptools

# Instalar dependencias de Python una por una con verbosidad
RUN pip3 install --no-cache-dir -v qdrant-client==1.9.1 && \
    pip3 install --no-cache-dir -v pydantic==2.7.3 && \
    pip3 install --no-cache-dir -v openai==1.33.0 && \
    pip3 install --no-cache-dir -v posthog==3.5.0 && \
    pip3 install --no-cache-dir -v pytz==2024.1 && \
    pip3 install --no-cache-dir -v sqlalchemy==2.0.31 && \
    pip3 install --no-cache-dir -v langchain-neo4j==0.4.0 && \
    pip3 install --no-cache-dir -v neo4j==5.23.1 && \
    pip3 install --no-cache-dir -v rank-bm25==0.2.2

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
