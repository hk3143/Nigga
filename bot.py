import os
import re
import time
import base64
from collections import defaultdict
import discord
from discord.ext import commands
import aiohttp

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODELO = "gemini-3.6-flash"
URL_GEMINI = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent"

SYSTEM_PROMPT = (
    "Eres IA Pro, un asistente virtual en Discord, amigable y conversacional. "
    "Ayudas a estudiar y respondes cualquier pregunta. "
    "Cuando el usuario adjunte una imagen o documento (PDF, Word, PowerPoint, texto), "
    "analízalo y ayúdalo: explícalo, resúmelo, resuelve ejercicios, traduce o transcribe el texto. "
    "Responde SIEMPRE en español, de forma clara, amable y educada. "
    "Si te escriben sin archivo, mantén una conversación normal y útil. "
    "IMPORTANTE PARA MATEMÁTICAS: Cuando resuelvas ejercicios o muestres operaciones, "
    "usa SIEMPRE signos y símbolos matemáticos claros y legibles en lugar de texto plano. "
    "Usa el símbolo ÷ para dividir, × para multiplicar, √ para raíz cuadrada, "
    "² para al cuadrado, ³ para al cubo, y escribe las fracciones en forma de barra "
    "como a/b o con el formato visual equivalente. Usa signos de puntuación correctos "
    "(igual =, más +, menos −) y presenta cada paso de forma ordenada y fácil de leer. "
    "Si el chat soporta LaTeX/fórmulas, puedes usarlas con el formato $...$ o $$...$$, "
    "pero siempre incluye también los símbolos matemáticos directamente visibles "
    "para que se entiendan sin necesidad de plugins."
)

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Guarda el historial por canal: lista de dicts {"role":..., "parts":[...]}
sesiones = defaultdict(list)

# Registro del último mensaje por usuario+canal para saltar duplicados
ultimo_mensaje = defaultdict(lambda: {"texto": "", "tiempo": 0.0})

MIME_MAP = {
    "image/png": "imagen",
    "image/jpeg": "imagen",
    "image/jpg": "imagen",
    "image/gif": "imagen",
    "image/webp": "imagen",
    "image/bmp": "imagen",
    "application/pdf": "pdf",
    "application/msword": "word",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "word",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "ppt",
    "text/plain": "texto",
}

EXTENSION_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
}


async def llamar_gemini(client, historia):
    """Envía la historia a Gemini por HTTP directo y devuelve el texto de respuesta."""
    contenido = []
    for turno in historia:
        contenido.append({"role": turno["role"], "parts": turno["parts"]})

    cuerpo = {
        "contents": contenido,
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
    }

    cabeceras = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    async with client.post(URL_GEMINI, headers=cabeceras, json=cuerpo) as resp:
        datos = await resp.json()
        if resp.status != 200:
            msg = datos.get("error", {}).get("message", f"HTTP {resp.status}")
            raise RuntimeError(msg)
        try:
            return datos["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return None


@bot.event
async def on_ready():
    print(f"IA Pro conectado como {bot.user}")


async def obtener_mime(attachment):
    mime = attachment.content_type
    if not mime or mime not in MIME_MAP:
        ext = os.path.splitext(attachment.filename or "")[1].lower()
        mime = EXTENSION_MIME.get(ext)
    if mime and mime in MIME_MAP:
        return mime, MIME_MAP[mime]
    return None, None


async def enviar_respuesta(message, texto):
    if not texto or texto.strip() == "":
        texto = "No pude generar una respuesta. Intenta reformular tu pregunta."
    texto = re.sub(r"<thought>.*?</thought>", "", texto, flags=re.DOTALL).strip()
    if len(texto) > 1800:
        bloques = [texto[i : i + 1800] for i in range(0, len(texto), 1800)]
        for i, bloque in enumerate(bloques):
            if i == 0:
                await message.reply(bloque)
            else:
                await message.channel.send(bloque)
    else:
        await message.reply(texto)


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    canal_id = message.channel.id
    contenido = message.content.strip().lower()
    tiene_archivo = bool(message.attachments)
    texto = message.content.strip()

    if contenido in ("!nuevo", "!reset", "!limpiar"):
        sesiones[canal_id] = []
        await message.reply("🧹 Conversación reiniciada. ¡Pregúntame lo que quieras!")
        return

    if contenido in ("!ayuda", "!help"):
        await message.reply(
            "¡Hola! Soy **IA Pro** 🤖.\n\n"
            "Háblame como a un chat normal: pregúntame lo que sea y te respondo.\n\n"
            "**📷📄 Sube archivos** (imágenes, PDF, Word, PowerPoint) y los analizo automáticamente: "
            "los explico, resumo, resuelvo ejercicios o traduzco.\n\n"
            "Comandos:\n"
            "• `!nuevo` - Reinicia la conversación\n"
            "• `!ayuda` - Este menú\n\n"
            "¡Empecemos! 😊"
        )
        return

    if not tiene_archivo and not texto:
        return

    # Saltar mensajes duplicados o casi idénticos del mismo usuario
    clave = (message.author.id, canal_id)
    ahora = time.time()
    ultimo = ultimo_mensaje[clave]
    iguales = texto == ultimo["texto"].strip()
    texto_normalizado = re.sub(r"\s+", " ", texto).strip().lower()
    ultimo_normalizado = re.sub(r"\s+", " ", ultimo["texto"].strip()).lower()
    casi_iguales = (
        texto_normalizado and
        texto_normalizado == ultimo_normalizado
    )
    if (iguales or casi_iguales) and (ahora - ultimo["tiempo"] <= 10):
        return

    ultimo_mensaje[clave] = {"texto": texto, "tiempo": ahora}

    async with message.channel.typing():
        try:
            partes_usuario = []

            if tiene_archivo:
                for attachment in message.attachments:
                    mime, tipo = await obtener_mime(attachment)
                    if not mime:
                        continue
                    file_bytes = await attachment.read()
                    b64 = base64.b64encode(file_bytes).decode("utf-8")
                    partes_usuario.append({
                        "inline_data": {"mime_type": mime, "data": b64},
                    })

            if texto:
                partes_usuario.append({"text": texto})
            if not partes_usuario:
                return

            sesiones[canal_id].append({"role": "user", "parts": partes_usuario})

            async with aiohttp.ClientSession() as client:
                respuesta = await llamar_gemini(client, sesiones[canal_id])

            if respuesta:
                sesiones[canal_id].append({"role": "model", "parts": [{"text": respuesta}]})

            # Limitar el historial para no exceder tokens
            if len(sesiones[canal_id]) > 30:
                sesiones[canal_id] = sesiones[canal_id][-20:]

            await enviar_respuesta(message, respuesta)

        except Exception as e:
            await message.reply(f"❌ Ocurrió un error: {str(e)}")


if __name__ == "__main__":
    if not DISCORD_TOKEN or not GEMINI_API_KEY:
        raise RuntimeError("Faltan las variables de entorno DISCORD_TOKEN y GEMINI_API_KEY")
    bot.run(DISCORD_TOKEN)
