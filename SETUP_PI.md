# Guía para desplegar la interfaz GNSS en la Raspberry Pi Zero 2W

Este documento describe cómo organizar los archivos del proyecto en la Raspberry Pi Zero 2W para que la interfaz web funcione correctamente. A partir de esta versión todo el CSS y el JavaScript se incluyen directamente dentro de `index.html`, por lo que ya no es necesario copiar archivos adicionales a la carpeta de estáticos.

## 1. Preparar las carpetas

Ejecuta los siguientes comandos para crear la estructura de directorios necesaria (los comandos se pueden pegar tal cual en la terminal):

```bash
mkdir -p ~/gnssai/templates
```

* `mkdir -p` crea la carpeta requerida y no marca error si ya existe.
* Asegúrate de que el usuario con el que trabajas tenga permisos sobre la ruta `~/gnssai`.

## 2. Copiar los archivos del proyecto

1. **Plantilla HTML**
   - **Opción recomendada (descarga directa):**
     ```bash
     curl -L https://raw.githubusercontent.com/<TU_REPO>/index.html -o ~/gnssai/templates/index.html
     ```
     Sustituye `<TU_REPO>` por la ruta real del repositorio (por ejemplo `usuario/proyecto/main/index.html`). El parámetro `-L` permite que `curl` siga redirecciones y descargue el contenido exacto del archivo.
   - **Opción manual (copiar/pegar):**
     - Abre el archivo con tu editor preferido (por ejemplo `nano`):
       ```bash
       nano ~/gnssai/templates/index.html
       ```
     - Sustituye todo el contenido por el HTML del proyecto.
     - Si descargas el archivo desde GitHub, haz clic en **Raw** antes de copiar para evitar incluir prefijos como `diff --git` o símbolos `+`/`-` de un parche.
     - Tras pegar, verifica que las primeras líneas sean:
       ```html
       <!DOCTYPE html>
       <html lang="es">
       <head>
       ```
       Si aparecen textos como `diff --git` o cada línea comienza con `+`, borra el archivo y repite la copia porque se pegó un parche en lugar del HTML final.

2. **Archivos estáticos**
   - Ya no es necesario copiar `styles.css` ni `app.js` porque todo el código se incrustó en la plantilla.
   - Si antes habías creado `~/gnssai/static/assets/`, puedes dejarlo vacío o reutilizarlo para otros recursos opcionales (imágenes, iconos, etc.).

## 3. Verificar los archivos

Comprueba que los ficheros se copiaron correctamente:

```bash
ls ~/gnssai/templates
```

Deberías ver el archivo `index.html` en la lista.

## 4. Reiniciar el servicio web (si aplica)

Si usas `gunicorn`, `systemd` u otro servicio para servir la aplicación, reinícialo para recargar los cambios. Por ejemplo:

```bash
sudo systemctl restart gnssai.service
```

Ajusta el nombre del servicio según tu configuración.

## 5. Comprobación final

Abre el navegador apuntando a la dirección de tu Pi (por ejemplo `http://<IP_DE_LA_PI>:5000`) y verifica que la interfaz cargue correctamente.

Si observas errores 404 relacionados con archivos antiguos (`styles.css` o `app.js`), limpia la caché del navegador o reinicia el servicio para forzar la carga del nuevo HTML incrustado.
