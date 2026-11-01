# Error del modelo en chat y Sistema

Las capturas usan una respuesta SSE simulada con el código `model_busy`. El antes usa el build de v0.15.0; el después usa el build con la corrección de la traza. Ambas vistas se capturaron a 1280 × 800.

- [Chat antes](antes/chat.png) y [después](despues/chat.png): el mensaje propone reintentar y no muestra el código.
- [Sistema antes](antes/sistema.png) y [después](despues/sistema.png): ahora muestra la pregunta y el código aunque el fallo ocurra antes del primer paso. Reproducir queda desactivado si no hay pasos.
