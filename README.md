# 📚 Bot de Estudio (Discord + Gemini)

Bot de Discord gratis que lee imágenes y ayuda a estudiar: explica contenido, resuelve ejercicios, traduce textos y transcribe (OCR). Funciona 24/7 en Render (plan gratis).

---

## 1. Crear el bot en Discord

1. Ve a **https://discord.com/developers/applications**
2. Clic en **"New Application"** → ponle un nombre → **Create**
3. En el menú lateral, entra a **Bot**
4. Clic en **"Reset Token"** → **Copy** (guardalo, es tu `DISCORD_TOKEN`)
5. Desactiva **"Public Bot"** si quieres que sea privado
6. En **Privileged Gateway Intents**, activa **"Message Content Intent"** y guárdalo

### Invitar el bot a tu servidor
1. En el menú lateral entra a **OAuth2 → URL Generator**
2. Marca **bot** en "Scopes"
3. Marca estos permisos en "Bot Permissions":
   - ✅ Send Messages
   - ✅ Read Messages / View Channels
   - ✅ Attach Files
4. Copia la URL generada y ábrela en el navegador → elige tu servidor → **Authorize**

---

## 2. Obtener la API Key de Gemini (gratis)

1. Ve a **https://aistudio.google.com/apikey**
2. Inicia sesión con tu cuenta de Google
3. Clic en **"Create API key"** → copia la clave (guardala, es tu `GEMINI_API_KEY`)

---

## 3. Desplegar en Render (24/7 gratis)

1. Ve a **https://render.com** y crea una cuenta gratuita
2. Clic en **"New" → "Blueprint"** (o "Web Service")
3. Conecta tu repositorio de GitHub con este proyecto, o usa "Public Git Repository" y pega la URL de tu repo
4. Cuando te pida el archivo `render.yaml`, confírmalo
5. Durante la creación te pedirá las **variables de entorno**:
   - `DISCORD_TOKEN` = el token que guardaste
   - `GEMINI_API_KEY` = la API key que guardaste
6. Despliega. Cuando el servicio muestre "Live", tu bot está conectado.

> ⚠️ El bot debe estar en un **repositorio de GitHub** para que Render lo despliegue. Sube la carpeta `estudio-bot` a un repo (puedes excluir archivos con `.gitignore`).

---

## 4. Usar el bot

En cualquier canal donde esté el bot, sube un archivo junto con uno de estos comandos:

| Comando | Función |
|---------|---------|
| `!explica` | Explica el contenido del archivo |
| `!resuelve` | Resuelve ejercicios paso a paso |
| `!traduce` | Traduce el texto al español |
| `!leo` | Transcribe el texto (OCR) |
| `!resumen` | Resumen con los puntos más importantes (docs) |
| `!temario` | Temario/índice de temas (docs) |
| `!ayuda` | Muestra el menú de ayuda |

**Archivos soportados:**
- 📷 Imágenes: PNG, JPG, GIF, WEBP, BMP
- 📕 PDF
- 📄 Word (.doc, .docx)
- 📊 PowerPoint (.ppt, .pptx)
- 📝 Texto (.txt)

**Ejemplos:**
- Sube una foto de un apunte y escribe `!explica`
- Sube un PDF y escribe `!resumen`
- Sube un ejercicio foto y escribe `!resuelve`

---

## Límites gratis de Gemini
- ~1,500 peticiones/día (se restablece cada 24h)
- Suficiente para una persona estudiando todo el día.

## ⚠️ Importante: modelo usado
El bot usa el modelo `gemini-3.6-flash` (el más reciente compatible con cuentas nuevas).
Los modelos antiguos como `gemini-1.5-flash` ya **no están disponibles para cuentas nuevas**.
