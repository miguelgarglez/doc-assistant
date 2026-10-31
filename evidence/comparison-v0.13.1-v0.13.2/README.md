# v0.13.1 frente a v0.13.2

Vista previa de una cita en la última respuesta de un hilo largo, con el backend simulado de `apps/web/e2e/mocks.ts` (fuente ACME-DEMO-DS, cita de cuatro líneas) y el mismo guion en las dos versiones: `apps/web/e2e/capture-cita-final.mjs`. «Antes» es el árbol de v0.13.1; «después», v0.13.2. Los otros tamaños y temas están en `evidence/screenshots/cita-final-hilo-*.png`.

| Tamaño y tema | Antes | Después |
| --- | --- | --- |
| 1440x900 industrial claro | `antes-v0.13.1-cita-final-hilo-1440x900-industrial-light.png` | `despues-v0.13.2-cita-final-hilo-1440x900-industrial-light.png` |
| 1280x720 neutral oscuro | `antes-v0.13.1-cita-final-hilo-1280x720-neutral-dark.png` | `despues-v0.13.2-cita-final-hilo-1280x720-neutral-dark.png` |
| 390x844 industrial claro | `antes-v0.13.1-cita-final-hilo-390x844-industrial-light.png` | `despues-v0.13.2-cita-final-hilo-390x844-industrial-light.png` |

Qué cambió a la vista: la tarjeta calculaba las colisiones contra la ventana, y el composer queda fuera del hilo pero dentro de la ventana, así que la tarjeta lo tapaba (46 o 47 px en los 12 tamaños y temas). Ahora el límite es el elemento de scroll del hilo: la tarjeta se abre hacia arriba, sigue centrada en el marcador y termina antes del composer (0 px en los 12).
