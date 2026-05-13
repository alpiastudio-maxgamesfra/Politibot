import subprocess
import os
import sys
import datetime
from discord.ext import tasks
import discord

def setup_updater(bot):

    @tasks.loop(time=datetime.time(hour=0, minute=0))
    async def auto_update():
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd="C:\\Politibot",
                capture_output=True,
                text=True
            )
            print(f"[AUTO-UPDATE] {result.stdout.strip()}")

            if "Already up to date" in result.stdout:
                return

            print("[AUTO-UPDATE] Mise à jour détectée, installation des dépendances...")
            subprocess.run(
                ["C:\\Politibot\\politibotenv\\Scripts\\pip.exe",
                 "install", "-r", "requirements.txt"],
                cwd="C:\\Politibot",
                capture_output=True
            )

            print("[AUTO-UPDATE] Redémarrage du bot...")
            os.execv(sys.executable, [sys.executable] + sys.argv)

        except Exception as e:
            print(f"[AUTO-UPDATE] Erreur : {e}")

    @auto_update.before_loop
    async def before():
        await bot.wait_until_ready()

    auto_update.start()