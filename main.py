import discord
from discord.ext import commands
from discord import opus
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv


if not opus.is_loaded():
    opus_paths = [
        '/opt/homebrew/lib/libopus.dylib',
        '/usr/local/lib/libopus.dylib',
        'libopus.dylib'
    ]
    for path in opus_paths:
        if os.path.exists(path):
            try:
                opus.load_opus(path)
                print(f"Opus 로드 성공: {path}")
                break
            except Exception as e:
                print(f"{path} 로드 실패: {e}")


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

queue = []
current_volume = 0.5 
current_song_title = "없음"

YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

def play_next(ctx):
    global current_song_title
    if len(queue) > 0:
        next_song = queue.pop(0)
        current_song_title = next_song['title']
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(next_song['url'], **FFMPEG_OPTIONS), 
            volume=current_volume
        )
        ctx.voice_client.play(source, after=lambda e: play_next(ctx))
        asyncio.run_coroutine_threadsafe(ctx.send(f"🎶 다음 곡 재생: **{current_song_title}**"), bot.loop)
    else:
        current_song_title = "없음"

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!도움말 입력"))
    print(f'{bot.user.name} 봇 온라인!')



@bot.command()
async def 도움말(ctx):
    embed = discord.Embed(title="🎵 음악 봇 명령어 안내", color=discord.Color.blue())
    embed.add_field(name="입장/퇴장", value="`!들어와`, `!나가`", inline=False)
    embed.add_field(name="재생", value="`!틀어 [제목]`, `!패스`", inline=False)
    embed.add_field(name="제어", value="`!멈춰`, `!다시`", inline=False)
    embed.add_field(name="설정", value="`!볼륨 [0~100]`, `!가사`, `!목록`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def 들어와(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
    else:
        await ctx.send("음성 채널에 먼저 들어가 주세요!")

@bot.command()
async def 틀어(ctx, *, search):
    global current_song_title
    if not ctx.voice_client:
        await ctx.invoke(들어와)
    async with ctx.typing():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
            song_data = {'url': info['url'], 'title': info['title']}
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            queue.append(song_data)
            await ctx.send(f"예약됨: **{info['title']}**")
        else:
            current_song_title = info['title']
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song_data['url'], **FFMPEG_OPTIONS), volume=current_volume)
            ctx.voice_client.play(source, after=lambda e: play_next(ctx))
            await ctx.send(f" 재생 중: **{current_song_title}**")

@bot.command()
async def 멈춰(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸잠시 멈춤!")

@bot.command()
async def 다시(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶다시 재생!")

@bot.command()
async def 볼륨(ctx, volume: float): 
    global current_volume
    
    if 0 <= volume <= 1:
        current_volume = volume
    elif 1 < volume <= 100:
        current_volume = volume / 100
    else:
        await ctx.send("볼륨은 0~100 사이 숫자로 입력해 주세요!")
        return

    if ctx.voice_client and ctx.voice_client.source:
        ctx.voice_client.source.volume = current_volume
    await ctx.send(f"🔊 볼륨이 {int(current_volume * 100)}%로 설정되었습니다.")

@bot.command()
async def 가사(ctx):
    if current_song_title != "없음":
        url = f"https://www.google.com/search?q={current_song_title.replace(' ', '+')}+lyrics"
        await ctx.send(f"가사 링크: {url}")

@bot.command()
async def 패스(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("다음 곡!")

@bot.command()
async def 목록(ctx):
    if not queue:
        await ctx.send("대기열이 비어 있습니다.")
    else:
        msg = "**대기열**\n" + "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(queue)])
        await ctx.send(msg)

@bot.command()
async def 나가(ctx):
    if ctx.voice_client:
        queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("안녕!")

if TOKEN:
    bot.run(TOKEN)
