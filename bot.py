import os
from io import BytesIO
import discord
from discord.ext import commands
import google.generativeai as genai

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3.6-flash")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

SYSTEM_PROMPT = (
    "Eres un asistente de estudio en español, amable y detallado. "
    "Cuando recibas una imagen o un documento, tu tarea es ayudar a la persona a estudiar. "
    "Puedes: explicar el contenido, resolver ejercicios paso a paso, transcribir el texto (OCR), "
    "resumir documentos, o traducirlo. Responde siempre en español, claro y educativo."
)

INSTRUCCIONES = {
    "explica": "Explica claramente el contenido de este archivo como material de estudio.",
    "resuelve": "Resuelve el ejercicio mostrado paso a paso y explica el razonamiento.",
    "traduce": "Traduce todo el texto visible al español.",
    "leo": "Transcribe todo el texto visible de forma fiel (OCR).",
    "resumen": "Haz un resumen claro y organizado con los puntos más importantes del documento.",
    "temario": "Extrae y organiza un temario/índice con los temas principales del documento.",
}

# Tipos de archivo soportados
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

# Algunos adjuntos traen el mimetype vacío, así que también usamos la extensión
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
    print(f"Bot conectado como {bot.user}")


@bot.command(name="ayuda")
async def ayuda(ctx):
    embed = discord.Embed(
        title="📚 Bot de Estudio",
        description=(
            "¡Hola! Soy tu asistente de estudio.\n\n"
            "Sube un archivo (📷 imagen, 📄 Word, 📕 PDF o 📊 PowerPoint) "
            "y escribe uno de estos comandos en el mismo mensaje:\n\n"
            "• `!explica` - Explica el contenido\n"
            "• `!resuelve` - Resuelve ejercicios paso a paso\n"
            "• `!traduce` - Traduce el texto al español\n"
            "• `!leo` - Transcribe el texto (OCR)\n"
            "• `!resumen` - Resumen del documento\n"
            "• `!temario` - Temario/índice de temas\n\n"
            "**Ejemplo:** sube un PDF y escribe `!resumen`.\n\n"
            "También escribe **!ayuda** para ver este menú."
        ),
        color=0x00FF00,
    )
    await ctx.send(embed=embed)


async def analizar_archivo(ctx, tarea):
    if not ctx.message.attachments:
        await ctx.send(f"Adjunta un archivo en el mismo mensaje con `!{tarea}`.")
        return

    attachment = ctx.message.attachments[0]

    # Determinar el mimetype
    mime = attachment.content_type
    if not mime or mime not in MIME_MAP:
        ext = os.path.splitext(attachment.filename or "")[1].lower()
        mime = EXTENSION_MIME.get(ext)

    if not mime or mime not in MIME_MAP:
        await ctx.send(
            "❌ No reconozco ese tipo de archivo. "
            "Sirve para: imágenes (PNG/JPG/GIF/WEBP/BMP), PDF, Word (.doc/.docx), "
            "PowerPoint (.ppt/.pptx) y texto (.txt)."
        )
        return

    tipo = MIME_MAP[mime]
    procesando = await ctx.send(f"⏳ Analizando el archivo...")

    try:
        file_bytes = await attachment.read()
        instruccion = INSTRUCCIONES.get(tarea, "Analiza este archivo.")

        partes = [SYSTEM_PROMPT, instruccion]
        if tipo == "imagen":
            partes.append({"mime_type": mime, "data": file_bytes})
        else:
            # Sube el archivo de documento al cliente de Gemini
            archivo = genai.upload_file(
                BytesIO(file_bytes),
                display_name=attachment.filename or "documento",
                mime_type=mime,
            )
            partes.append(archivo)

        response = model.generate_content(partes)

        respuesta = response.text
        if not respuesta or respuesta.strip() == "":
            respuesta = "No pude extraer información de ese archivo. Intenta con otro."

        if len(respuesta) > 1800:
            bloques = [respuesta[i : i + 1800] for i in range(0, len(respuesta), 1800)]
            for i, bloque in enumerate(bloques):
                if i == 0:
                    await procesando.edit(content=bloque)
                else:
                    await ctx.send(bloque)
        else:
            await procesando.edit(content=respuesta)

    except Exception as e:
        await procesando.edit(content=f"❌ Ocurrió un error: {str(e)}")


def crear_comando(nombre):
    @bot.command(name=nombre)
    async def _cmd(ctx):
        await analizar_archivo(ctx, nombre)
    return _cmd


for comando in INSTRUCCIONES:
    crear_comando(comando)


if __name__ == "__main__":
    if not DISCORD_TOKEN or not GEMINI_API_KEY:
        raise RuntimeError("Faltan las variables de entorno DISCORD_TOKEN y GEMINI_API_KEY")
    bot.run(DISCORD_TOKEN)
