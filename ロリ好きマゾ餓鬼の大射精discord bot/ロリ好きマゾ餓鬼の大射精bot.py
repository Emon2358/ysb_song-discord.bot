import discord
from discord.ext import commands
import asyncio
import yt_dlp
import logging
import os
from dotenv import load_dotenv

# .env ファイルから環境変数を読み込み
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# ロギングの設定
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# グローバル変数でボイスクライアントと再生キューを追跡
voice_clients = {}
queues = {}
current_track = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def play(ctx, *, url):
    try:
        if not ctx.message.author.voice:
            await ctx.send("ボイスチャンネルに接続してください。")
            return
        channel = ctx.message.author.voice.channel
        
        if ctx.guild.id in voice_clients:
            await voice_clients[ctx.guild.id].move_to(channel)
        else:
            voice_clients[ctx.guild.id] = await channel.connect()

        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []

        queues[ctx.guild.id].append(url)
        if not voice_clients[ctx.guild.id].is_playing():
            await play_next(ctx.guild)

    except Exception as e:
        logging.error(f"エラーが発生しました: {str(e)}")
        await ctx.send(f"エラーが発生しました: {str(e)}")

async def stream_youtube(guild, url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'extract_flat': True,
        'noplaylist': True,
        'force_generic_extractor': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await bot.loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
        url2 = info['url']
    
    voice_client = voice_clients[guild.id]
    voice_client.play(discord.FFmpegPCMAudio(url2), after=lambda e: bot.loop.create_task(play_next(guild)))

    current_track[guild.id] = (url, info["title"])
    await guild.text_channels[0].send(f'再生中: {info["title"]}')

async def play_next(guild):
    if queues[guild.id]:
        next_url = queues[guild.id].pop(0)
        await stream_youtube(guild, next_url)
    else:
        await guild.text_channels[0].send("再生キューが空です。")

@bot.command()
async def skip(ctx):
    if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
        voice_clients[ctx.guild.id].stop()
        await ctx.send("次の曲にスキップしました。")
    else:
        await ctx.send("現在再生中の曲がありません。")

@bot.command()
async def stop(ctx):
    if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
        voice_clients[ctx.guild.id].stop()
        queues[ctx.guild.id] = []
        await ctx.send("再生を停止し、キューをクリアしました。")
    else:
        await ctx.send("現在再生中の曲がありません。")

@bot.command()
async def leave(ctx):
    if ctx.guild.id in voice_clients:
        await voice_clients[ctx.guild.id].disconnect()
        del voice_clients[ctx.guild.id]
        if ctx.guild.id in queues:
            del queues[ctx.guild.id]
        await ctx.send("ボイスチャンネルから切断しました。")
    else:
        await ctx.send("Botはボイスチャンネルに接続していません。")

@bot.event
async def on_voice_state_update(member, before, after):
    if not member.bot and after.channel is None:
        if before.channel is not None and before.channel.guild.id in voice_clients:
            if len(before.channel.members) == 1:
                await voice_clients[before.channel.guild.id].disconnect()
                del voice_clients[before.channel.guild.id]
                if before.channel.guild.id in queues:
                    del queues[before.channel.guild.id]

bot.run(TOKEN)























