# v0.13.2 frente a v0.13.3

Tarjeta de rechazo con el mismo guion y el backend simulado de `apps/web/e2e/mocks.ts`: `apps/web/e2e/capture-respuestas.mjs`. «Antes» es la captura de v0.13.2 (`chat-rechazo-*` de ese tag); «después», la misma escena en v0.13.3. Los otros tamaños y temas están en `evidence/screenshots/chat-rechazo-*.png`; las respuestas de factura con importe es-ES, en `chat-factura-*.png`.

| Tamaño y tema | Antes | Después |
| --- | --- | --- |
| 1440x900 industrial claro | `antes-v0.13.2-rechazo-1440x900-industrial-light.png` | `despues-v0.13.3-rechazo-1440x900-industrial-light.png` |
| 390x844 neutral oscuro | `antes-v0.13.2-rechazo-390x844-neutral-dark.png` | `despues-v0.13.3-rechazo-390x844-neutral-dark.png` |

Qué cambió a la vista: el rechazo enseñaba «Sin evidencia suficiente», una frase repetida y `motivo: llm_unanswerable`. Ahora titula lo que pasó («No lo encuentro en tus fuentes»), dice qué hacer y deja los apartados relacionados. El código interno solo está en Sistema.
