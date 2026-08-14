import asyncio
import io
import logging
import os
import sqlite3
from urllib.parse import urlsplit

import aiohttp
import discord
from discord import app_commands

import config
import db
from crawlers.base import Post
from scheduler import Scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "riceminer.db"

SITE_LABELS = {"arca": "아카라이브", "quasarzone": "퀘이사존", "fmkorea": "FM코리아"}

# 일부 이미지 CDN이 기본 HTTP 클라이언트 UA를 차단해서 브라우저처럼 보이도록 지정한다.
THUMBNAIL_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

intents = discord.Intents.default()


class RiceminerClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.conn = sqlite3.connect(DB_PATH)
        db.init_db(self.conn)
        self.queue: asyncio.Queue[Post] = asyncio.Queue()
        self.scheduler = Scheduler(self.conn, self.queue, on_error=self._on_crawl_error)
        self._synced_guilds = False

    async def setup_hook(self) -> None:
        await self.tree.sync()
        self.loop.create_task(self.scheduler.run_forever())
        self.loop.create_task(self._consume_posts())

    async def on_ready(self) -> None:
        # 글로벌 동기화는 전파에 최대 1시간 걸린다. 가입된 서버에는 즉시 반영되도록 길드 단위로도 동기화.
        if not self._synced_guilds:
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            self._synced_guilds = True
        logger.info("로그인 완료: %s (길드 %d개)", self.user, len(self.guilds))

    async def _on_crawl_error(self, site_code: str, message: str) -> None:
        settings = db.get_settings(self.conn)
        if not settings or not settings["log_channel_id"]:
            return
        channel = self.get_channel(settings["log_channel_id"])
        if channel is None:
            return
        await channel.send(f"⚠️ [{site_code}] {message}")

    async def _consume_posts(self) -> None:
        await self.wait_until_ready()
        async with aiohttp.ClientSession() as session:
            while True:
                post = await self.queue.get()
                settings = db.get_settings(self.conn)
                channel_id = settings["post_channel_id"] if settings else None
                channel = self.get_channel(channel_id) if channel_id else None
                if channel is None:
                    logger.warning("알림 채널 미설정 — 게시글 스킵: %s", post.url)
                    continue

                embed = format_embed(post)
                file = await fetch_thumbnail_file(session, post.thumbnail)
                if file:
                    embed.set_thumbnail(url=f"attachment://{file.filename}")
                try:
                    if file:
                        await channel.send(embed=embed, file=file)
                    else:
                        await channel.send(embed=embed)
                except Exception:
                    logger.exception("게시글 전송 실패: %s", post.url)


def format_embed(post: Post) -> discord.Embed:
    embed = discord.Embed(
        title=post.title[:256],
        url=post.url,
        color=discord.Color.orange(),
    )
    embed.set_author(name=SITE_LABELS.get(post.site, post.site))
    if post.price:
        embed.add_field(name="가격", value=post.price, inline=True)
    if post.shipping:
        embed.add_field(name="배송", value=post.shipping, inline=True)
    return embed


async def fetch_thumbnail_file(
    session: aiohttp.ClientSession, url: str | None
) -> discord.File | None:
    """썸네일을 직접 받아 첨부파일로 올린다.

    일부 CDN이 Discord의 외부 이미지 요청을 막아서, URL만 걸면 임베드에 안 뜨는 경우가 있다.
    """
    if not url:
        return None
    parts = urlsplit(url)
    headers = {
        "User-Agent": THUMBNAIL_USER_AGENT,
        "Referer": f"{parts.scheme}://{parts.netloc}/",
    }
    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status != 200:
                return None
            data = await response.read()
    except Exception:
        logger.warning("썸네일 다운로드 실패: %s", url)
        return None
    ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    return discord.File(io.BytesIO(data), filename=f"thumb{ext}")


def _site_choices() -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=SITE_LABELS.get(c, c), value=c) for c in config.SITE_CODES]


client = RiceminerClient()

site_group = app_commands.Group(name="site", description="사이트 크롤링 제어")
interval_group = app_commands.Group(name="interval", description="사이트별 크롤링 주기 설정")
channel_group = app_commands.Group(name="channel", description="알림/로그 채널 설정")


@site_group.command(name="on", description="사이트 크롤링을 켭니다")
@app_commands.choices(code=_site_choices())
async def site_on(interaction: discord.Interaction, code: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    db.set_enabled(client.conn, code.value, True)
    await interaction.followup.send(f"✅ {code.name} 크롤링 켜짐", ephemeral=True)


@site_group.command(name="off", description="사이트 크롤링을 끕니다")
@app_commands.choices(code=_site_choices())
async def site_off(interaction: discord.Interaction, code: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    db.set_enabled(client.conn, code.value, False)
    await interaction.followup.send(f"🛑 {code.name} 크롤링 꺼짐", ephemeral=True)


@site_group.command(name="list", description="사이트별 상태를 확인합니다")
async def site_list(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    rows = db.list_sites(client.conn)
    lines = [
        f"`{row['code']}` {SITE_LABELS.get(row['code'], row['code'])} — "
        f"{'ON' if row['enabled'] else 'OFF'}, {row['interval_sec']}초 간격"
        for row in rows
    ]
    await interaction.followup.send(
        "\n".join(lines) or "등록된 사이트가 없습니다", ephemeral=True
    )


@interval_group.command(name="set", description="사이트 크롤링 주기를 설정합니다 (최소 60초)")
@app_commands.choices(code=_site_choices())
async def interval_set(
    interaction: discord.Interaction, code: app_commands.Choice[str], seconds: int
):
    await interaction.response.defer(ephemeral=True)
    try:
        db.set_interval(client.conn, code.value, seconds)
    except ValueError as exc:
        await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        return
    await interaction.followup.send(f"✅ {code.name} 주기를 {seconds}초로 설정", ephemeral=True)


@interval_group.command(name="get", description="사이트 크롤링 주기를 확인합니다")
@app_commands.choices(code=_site_choices())
async def interval_get(interaction: discord.Interaction, code: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    site = db.get_site(client.conn, code.value)
    if site is None:
        await interaction.followup.send("❌ 알 수 없는 사이트입니다", ephemeral=True)
        return
    await interaction.followup.send(f"{code.name}: {site['interval_sec']}초", ephemeral=True)


@channel_group.command(name="set-post", description="새 글 알림을 받을 채널을 이 채널로 설정합니다")
async def channel_set_post(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    db.set_post_channel(client.conn, interaction.channel_id)
    await interaction.followup.send("✅ 이 채널로 알림을 보냅니다", ephemeral=True)


@channel_group.command(name="set-log", description="에러 로그를 받을 채널을 이 채널로 설정합니다")
async def channel_set_log(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    db.set_log_channel(client.conn, interaction.channel_id)
    await interaction.followup.send("✅ 이 채널로 로그를 보냅니다", ephemeral=True)


@client.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    command = interaction.command.name if interaction.command else "?"
    logger.error("명령 처리 실패: %s", command, exc_info=error)
    message = f"❌ 명령 처리 중 오류가 발생했습니다: {error}"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        # 응답 시간이 지나 상호작용이 만료된 경우 — 로그만 남기고 넘어간다.
        logger.warning("오류 메시지 전달 실패: %s", command)


client.tree.add_command(site_group)
client.tree.add_command(interval_group)
client.tree.add_command(channel_group)


if __name__ == "__main__":
    client.run(config.DISCORD_TOKEN)
