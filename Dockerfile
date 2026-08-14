FROM pyd4vinci/scrapling

RUN uv pip install --python /app/.venv/bin/python3 discord.py python-dotenv

WORKDIR /app
COPY bot.py config.py db.py scheduler.py ./
COPY crawlers ./crawlers

ENTRYPOINT []
CMD ["uv", "run", "python3", "bot.py"]
