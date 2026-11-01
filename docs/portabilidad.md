# Estado de portabilidad

La ruta de arranque está en [README](../README.md#arranque-igual-en-macos-linux-y-windows). Esta revisión es estática. No demuestra que el ZIP o la aplicación funcionen en los tres sistemas.

| Entorno | Evidencia y límite |
|---|---|
| macOS Apple Silicon | Hay pruebas de versiones anteriores en un M4. Falta repetir la secuencia exacta del README desde un ZIP recién creado en esta rama. |
| Linux x64 | La matriz de GitHub Actions incluye Ubuntu, pero todavía no se ha ejecutado. |
| Windows x64 | La matriz incluye Windows, pero todavía no se ha ejecutado ni se ha probado en un equipo físico. |
| Otras arquitecturas | `scripts/assets.json` enumera más binarios que `scripts/package.py`: el ZIP solo incluye macOS arm64, Ubuntu x64 y Windows CPU x64. No se acredita un ZIP autocontenido para macOS x64, Linux arm64 o Windows arm64. `sqlite-vec` tampoco ofrece wheel para Windows ARM según la limitación registrada en el README. |

## Rutas y procesos revisados

- Los scripts usan `pathlib` para las rutas del proyecto y `tempfile` para descomprimir el ZIP. El empaquetador incluye solo archivos versionados y excluye directorios de datos y dependencias.
- `setup.py` resuelve ejecutables con `shutil.which`, instala las dependencias fijadas y construye la web. Estas instalaciones necesitan acceso a Internet y permisos de escritura en el entorno local.
- `dev.py` crea grupos de procesos propios en POSIX y usa grupos de procesos y `taskkill /T` en Windows. En Windows, `taskkill /T` no encuentra descendientes si el padre ya ha terminado. La prueba en un sistema real sigue pendiente.
- `package.py` envía SIGINT al grupo propio del proceso en POSIX para su prueba en limpio. La instrucción de esta sesión exige controlar procesos solo por PID. No se ha ejecutado esa prueba y hay que resolver esa incompatibilidad antes de usarla en este Mac.
- La matriz configura puertos 3180, 8180 y 8181–8184. El backend falso no arranca OCR; comprobar que 8184 queda libre no prueba OCR.

## Pruebas pendientes

Ejecutar el camino exacto del README desde un ZIP recién empaquetado en un directorio temporal propio, con los seis puertos configurados y modelos locales, después de obtener autorización para las instalaciones. Comprobar consulta, cita, rechazo, ingesta de factura sintética y cierre de los procesos propios. Conservar los logs y mover el directorio temporal a `_trash/`. Ejecutar por separado la matriz en GitHub cuando se autorice su publicación; una revisión estática no equivale a una ejecución de Linux o Windows.
