import os
from io import BytesIO
from collections import defaultdict
import re
import discord
from discord.ext import commands
import google.generativeai as genai

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SYSTEM_PROMPT = (
    "Eres IA Pro, un asistente virtual en Discord, amigable y conversacional. "
    "Ayudas a estudiar y respondes cualquier pregunta. "
    "Cuando el usuario adjunte una imagen o documento (PDF, Word, PowerPoint, texto), "
    "analízalo y ayúdalo: explícalo, resúmelo, resuelve ejercicios, traduce o transcribe el texto. "
    "Responde SIEMPRE en español, de forma clara, amable y educada. "
    "Si te escriben sin archivo, mantén una conversación normal y útil."
)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    "gemini-3.6-flash",
    system_instruction=SYSTEM_PROMPT,
)

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Guarda una ChatSession por canal para tener memoria
sesiones = defaultdict(lambda: model.start_chat(history=[]))

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
    # Limpiar etiquetas de pensamiento de algunos modelos
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

    # Comandos especiales
    if contenido in ("!nuevo", "!reset", "!limpiar"):
        sesiones[canal_id] = model.start_chat(history=[])
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

    # Solo responder si hay texto o archivo
    if not tiene_archivo and not texto:
        return

    async with message.channel.typing():
        try:
            chat = sesiones[canal_id]

            if tiene_archivo:
                partes = []
                for attachment in message.attachments:
                    mime, tipo = await obtener_mime(attachment)
                    if mime:
                        file_bytes = await attachment.read()
                        if tipo == "imagen":
                            partes.append({"mime_type": mime, "data": file_bytes})
                        else:
                            archivo = genai.upload_file(
                                BytesIO(file_bytes),
                                display_name=attachment.filename or "documento",
                                mime_type=mime,
                            )
                            partes.append(archivo)
                if texto:
                    partes.append(texto)
                if not partes:
                    return

                response = chat.send_message(partes)
            else:
                response = chat.send_message(texto)

            respuesta = response.text

            # Si el historial crece demasiado, reiniciarlo para evitar errores de tokens
            if len(chat.history) > 24:
                sesiones[canal_id] = model.start_chat(history=[])

            await enviar_respuesta(message, respuesta)

        except Exception as e:
            await message.reply(f"❌ Ocurrió un error: {str(e)}")


if __name__ == "__main__":
    if not DISCORD_TOKEN or not GEMINI_API_KEY:
        raise RuntimeError("Faltan las variables de entorno DISCORD_TOKEN y GEMINI_API_KEY")
    bot.run(DISCORD_TOKEN)
