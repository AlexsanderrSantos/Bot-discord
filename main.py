import discord
from discord.ext import commands
import yt_dlp
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="@", intents=intents)
bot.remove_command("help")

queue = []
current_song = None
last_song = None
loop_mode = False

ytdl_opts = {
    "format": "bestaudio/best",
    "noplaylist":True,
    "quiet": True
}

ffmpeg_opts = {
    "options": "-vn"
}

@bot.event
async def on_ready():
    print(f"Bot online! {bot.user}")
    
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🎧 Comandos do Bot de Música",
        description="Use @ antes de cada comando",
        color=discord.Color.blue()
    )

    # Música
    embed.add_field(
        name="▶️ Música",
        value=(
            "`@play <nome ou link>` - Toca música\n"
            "`@skip` - Pula música atual\n"
            "`@back` - Volta música anterior\n"
            "`@stop` - Para tudo e limpa fila"
        ),
        inline=False
    )

    # Fila
    embed.add_field(
        name="📜 Fila",
        value=(
            "`@fila` - Mostra todas músicas\n"
            "`@remove <número>` - Remove da fila"
        ),
        inline=False
    )

    # Controle
    embed.add_field(
        name="⏸️ Controle",
        value=(
            "`@pause` - Pausa música\n"
            "`@continuar` - Continua música\n"
            "`@sair` - Sai da call"
        ),
        inline=False
    )

    # Extras
    embed.add_field(
        name="🔁 Extras",
        value=(
            "`@loop` - Liga/Desliga loop"
        ),
        inline=False
    )

    embed.set_footer(text="Ex: @play Eminem without me")

    await ctx.send(embed=embed)       
    
@bot.command()
async def play (ctx, *, query):
    global current_song, last_song 
    
    if not ctx.author.voice:
        await ctx.send("Você é retardado cara ? Entra na call primeiro...")
        return
    
    channel = ctx.author.voice.channel
    vc = ctx.voice_client
    
    if not vc:
        vc = await channel.connect()
    
    with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
        if not query.startswith("http"):
            query = f"ytsearch1:{query}"
            
        info = ytdl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]

        music = {
            "url": info["webpage_url"], 
            "title": info["title"]
        }

    if vc.is_playing():
        queue.append(music)
        await ctx.send(f"🎶 Adicionado: {music['title']}")
        return

    if current_song:
        last_song = current_song

    current_song = music

    source = discord.FFmpegPCMAudio(
        info["url"],
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        options="-vn"
    )

    vc.play(source, after=lambda e: bot.loop.create_task(play_next(ctx)))

    await ctx.send(f"▶️ Tocando: {music['title']}")
        
async def play_next(ctx):
    global current_song, last_song
    
    if not queue:
        if loop_mode and current_song:
            queue.append(current_song)
        else: 
            current_song = None
            return
        
    vc = ctx.voice_client
    music = queue.pop(0)
    
    if current_song:
        last_song = current_song
    current_song = music
    
    with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
        info = ytdl.extract_info(music["url"], download=False)
        audio_url = info["url"]
        
    source = discord.FFmpegPCMAudio(audio_url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", options="-vn")
    vc.play(source, after=lambda e: bot.loop.create_task(play_next(ctx)))
    
    await ctx.send(f"▶️ Tocando: {music['title']}")
    
@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        if queue:
            await ctx.send(f"Proxima: {queue[0]['title']}")
        else: 
            await ctx.send("pulando... sem proxima musica na fila!")
            
        vc.stop()
        
@bot.command()
async def back(ctx):
    global current_song, last_song
    
    vc = ctx.voice_client
    
    if not last_song:
        await ctx.send("N tem nada antes dessa porra!")
        return
    
    if vc and vc.is_playing():
        vc.stop()
        
    queue.insert(0, current_song) 
    queue.insert(0, last_song)
    await ctx.send(f"Voltando para: {last_song['title']}")
    
@bot.command()   
async def sair(ctx):
    vc = ctx.voice_client
    if vc:
        await ctx.send(f"Vou Betar, falow !")
        await vc.disconnect()

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("Parei a musica nessa porra!")
        
@bot.command()
async def continuar(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("Continuei a musica nessa porra!")

@bot.command()
async def stop(ctx):
    global queue, current_song, last_song, loop_mode
    
    vc = ctx.voice_client 
    
    if not vc:
        await ctx.send("Nem to em call, pra que parar ?")
        return
    queue.clear()
    current_song = None
    last_song = None
    loop_mode = False 
    
    if vc.is_playing() or vc.is_paused():
        vc.stop()
        await ctx.send("⛔ Parei tudo e limpei a fila!")
        
@bot.command()
async def loop(ctx):
    global loop_mode
    loop_mode = not loop_mode
    if loop_mode:
        await ctx.send("🔁 Loop ativado!")
    else:
        await ctx.send("🔁 Loop desativado!")
        
@bot.command()
async def fila(ctx):
    if not current_song and not queue:
        await ctx.send("A fila tá vazia 😢")
        return
    
    msg = ""
    
    if current_song:
        msg += f"**Tocando agora:** {current_song['title']}\n"
        
        if queue:
            msg += "📜 Próximas músicas:\n"
            
            for i, music in enumerate(queue, start=1):
                msg += f"{i}, {music['title']}\n"
                
        if len(msg) > 1900:
            msg = msg[:1900] + "\n lista muitoooo grande!"
    await ctx.send(msg)
    
@bot.command()
async def remove(ctx, index: int = None):
    if index is None:
        await ctx.send("Usa assim: @remove <número da música>\nEx: @remove 1")
        return
    if not queue:
        await ctx.send("Fila vazia, não tem nada pra remover!")
        return
    if index < 1 or index > len(queue):
        await ctx.send("Número inválido!")
        return
    removed = queue.pop(index - 1)
    await ctx.send(f"❌ Removido: {removed['title']}")     
       
        
                
TOKEN = os.getenv("DISCORD_")