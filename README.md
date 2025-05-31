# EchoMind - AI Memory Layer para Home Assistant

EchoMind es una capa de memoria personal para aplicaciones de IA que se integra con Home Assistant. Todos los datos se mantienen locales.

## Características

- Integración completa con Home Assistant
- Almacenamiento local de memorias
- API REST para interacción con otros servicios
- Interfaz web para gestión de memorias
- Soporte para múltiples arquitecturas

## Instalación

1. Añade este repositorio a tu instalación de Home Assistant:
   ```
   https://github.com/mercuryin/EchoMind_ha
   ```
2. Instala el addon "EchoMind - AI Memory Layer" desde la sección de addons
3. Configura las opciones según tus necesidades
4. Inicia el addon

## Configuración

El addon se puede configurar a través de la interfaz de Home Assistant con las siguientes opciones:

- `encryption_enabled`: Habilita el cifrado de datos (por defecto: true)
- `local_only`: Restringe el acceso solo a la red local (por defecto: true)
- `api_key`: Clave API opcional para acceso externo
- `log_level`: Nivel de registro (trace|debug|info|notice|warning|error|fatal)
- `max_memories`: Número máximo de memorias almacenadas (100-50000)
- `cleanup_days`: Días antes de limpiar memorias antiguas (1-365)

## Integración con Home Assistant

Este addon incluye una integración personalizada para Home Assistant que permite:
- Almacenar y recuperar memorias
- Buscar en el historial de conversaciones
- Obtener estadísticas de uso
- Integración con el agente de conversación de Home Assistant

## Soporte

Si encuentras algún problema o tienes sugerencias, por favor:
1. Revisa los logs del addon
2. Verifica la documentación
3. Abre un issue en GitHub

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles. 