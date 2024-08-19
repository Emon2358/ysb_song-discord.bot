import discord
from discord.ext import commands
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

class MusicControls(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏸️ 一時停止/再開", style=discord.ButtonStyle.primary)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        if voice_clients[guild_id].is_playing():
            voice_clients[guild_id].pause()
            await interaction.response.send_message("⏸️ 再生を一時停止しました。", ephemeral=True)
        else:
            voice_clients[guild_id].resume()
            await interaction.response.send_message("▶️ 再生を再開しました。", ephemeral=True)

    @discord.ui.button(label="⏹️ 停止", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        voice_clients[guild_id].stop()
        queues[guild_id] = []
        await interaction.response.send_message("⏹️ 再生を停止し、キューをクリアしました。", ephemeral=True)

    @discord.ui.button(label="⏭️ スキップ", style=discord.ButtonStyle.success)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        voice_clients[guild_id].stop()
        await interaction.response.send_message("⏭️ 次の曲にスキップしました。", ephemeral=True)
        await play_next(interaction.guild, self.ctx)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def play(ctx, *, url):
    """URLから音楽を再生します。"""
    try:
        if not ctx.message.author.voice:
            await ctx.send("🔊 ボイスチャンネルに接続してください。")
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
            await play_next(ctx.guild, ctx)

    except Exception as e:
        logging.error(f"エラーが発生しました: {str(e)}")
        await ctx.send(f"⚠️ エラーが発生しました: {str(e)}")

async def stream_youtube(guild, url, ctx):
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
        title = info['title']
        thumbnail = info.get('thumbnail', '')

    voice_client = voice_clients[guild.id]
    voice_client.play(discord.FFmpegPCMAudio(url2), after=lambda e: bot.loop.create_task(play_next(guild, ctx)))

    current_track[guild.id] = (url, title)
    
    # 埋め込みメッセージの作成
    embed = discord.Embed(title="🎶 Now Playing", description=f"[{title}]({url})", color=discord.Color.blue())
    embed.set_thumbnail(url=thumbnail)
    
    view = MusicControls(ctx)
    await ctx.send(embed=embed, view=view)

async def play_next(guild, ctx):
    if queues[guild.id]:
        next_url = queues[guild.id].pop(0)
        await stream_youtube(guild, next_url, ctx)
    else:
        await ctx.send("再生キューが空です。")

@bot.command()
async def leave(ctx):
    """ボイスチャンネルから切断します。"""
    if ctx.guild.id in voice_clients:
        await voice_clients[ctx.guild.id].disconnect()
        del voice_clients[ctx.guild.id]
        if ctx.guild.id in queues:
            del queues[ctx.guild.id]
        await ctx.send("🚪 ボイスチャンネルから切断しました。")
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























