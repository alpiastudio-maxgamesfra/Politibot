import discord
import os
import logging
from dotenv import load_dotenv
from discord.ext import commands
import json
import io
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("politibot")
from ai import get_reaction, get_reaction_ordre, get_reaction_ordre_religieux, get_titres_noblesse, build_prompt_noblesse, build_prompt_peuple
import ctypes
import subprocess
from updater import setup_updater

VERSION = "1.1.4"

# Renommer la fenêtre PowerShell
def set_window_title(title: str):
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    except Exception:
        pass

set_window_title(f"Politibot v{VERSION}")

load_dotenv()

print("Lancement de Politibot...")

# Seuls les intents réellement utilisés par le bot : lecture des serveurs,
# des messages (pour /reagir, /recuperer_messages) et du contenu des messages.
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# ══════════════════════════════════════════════════════════════
#  BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════

def load_db():
    with open("database.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    # Écriture atomique : on écrit dans un fichier temporaire puis on
    # remplace l'ancien d'un coup (os.replace est atomique sur la plupart
    # des OS). Si le process crash pendant l'écriture, database.json
    # original n'est jamais laissé à moitié écrit / corrompu.
    tmp_path = "database.json.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, "database.json")

def get_partis(db, guild_id: str, user_id: str):
    db.setdefault(guild_id, {})
    db[guild_id].setdefault(user_id, {"partis": {}})
    db[guild_id][user_id].setdefault("partis", {})
    return db[guild_id][user_id]["partis"]

def get_ordres_religieux(db, guild_id: str, user_id: str):
    db.setdefault(guild_id, {})
    db[guild_id].setdefault(user_id, {"partis": {}})
    db[guild_id][user_id].setdefault("ordres_religieux", {})
    return db[guild_id][user_id]["ordres_religieux"]

def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator or \
           any(r.name == "Modérateur" for r in interaction.user.roles)

# ══════════════════════════════════════════════════════════════
#  EVENTS
# ══════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    print(f'Politibot est en ligne ! Connecté en tant que {bot.user}')
    print('---')
    try:
        synced = await bot.tree.sync()
        print(f"Commandes Synchronisées: {len(synced)}")
    except Exception as e:
        print(e)
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=f"v{VERSION}"
        )
    )
    setup_updater(bot)

# ══════════════════════════════════════════════════════════════
#  COMMANDES INFO
# ══════════════════════════════════════════════════════════════

@bot.tree.command(name="cgu", description="Afficher les CGU")
async def cgu(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Voici les CGU: https://docs.google.com/document/d/1C9z97KnXOKczYeQu6pQnIWLGUS1o-9BUorh5vUiGUjU/edit?usp=sharing"
    )

@bot.tree.command(name="pdc", description="Afficher la politique de confidentialité")
async def pdc(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Voici la politique de confidentialité: https://docs.google.com/document/d/1JAO541YtrDSuQAWueNtiq6I9ohfpHj0GLrEIG3Xs9UM/edit?usp=sharing"
    )

@bot.tree.command(name="apropos", description="Afficher l'à propos")
async def apropos(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Voici l'à propos du bot: https://docs.google.com/document/d/1DS5IH0m6JiYUe9-xY6S9nXez85Q1YB34cmN6M66ExLI/edit?usp=sharing"
    )

@bot.tree.command(name="liste_commandes", description="Afficher toutes les commandes disponibles")
async def liste_commandes(interaction: discord.Interaction):
    embed = discord.Embed(title="📋 Commandes Politibot", color=discord.Color.blurple())
    embed.set_footer(text=f"Politibot v{VERSION}")
    embed.add_field(name="/reagir", value="Faire réagir un parti à un message", inline=False)
    embed.add_field(name="/reagir_tous", value="Faire réagir tous les partis", inline=False)
    embed.add_field(name="/reagir_religieux", value="Faire réagir un Ordre Religieux", inline=False)
    embed.add_field(name="/reagir_noblesse", value="Réaction de la Noblesse d'un pays", inline=False)
    embed.add_field(name="/reagir_peuple", value="Réaction du Peuple d'un pays", inline=False)
    embed.add_field(name="/ajout_parti", value="Ajouter un parti à la base", inline=False)
    embed.add_field(name="/supprimer_parti", value="Supprimer un parti de la base", inline=False)
    embed.add_field(name="/liste_partis", value="Lister tous les partis", inline=False)
    embed.add_field(name="/ajout_ordre_religieux", value="Créer un Ordre Religieux", inline=False)
    embed.add_field(name="/supprimer_ordre_religieux", value="Supprimer un Ordre Religieux", inline=False)
    embed.add_field(name="/liste_ordres_religieux", value="Lister tous les Ordres Religieux", inline=False)
    embed.add_field(name="/recuperer_messages", value="Récupérer les 25 derniers messages du salon", inline=False)
    embed.add_field(name="/annee", value="Afficher l'année RP actuelle", inline=False)
    embed.add_field(name="/set_annee", value="[ADMIN] Définir l'année RP", inline=False)
    embed.add_field(name="/cgu", value="Afficher les CGU", inline=False)
    embed.add_field(name="/pdc", value="Politique de confidentialité", inline=False)
    embed.add_field(name="/apropos", value="À propos du bot", inline=False)
    await interaction.response.send_message(embed=embed)

# ══════════════════════════════════════════════════════════════
#  COMMANDES PARTIS
# ══════════════════════════════════════════════════════════════

@bot.tree.command(name="ajout_parti", description="Ajouter un parti politique à la base de données")
@discord.app_commands.describe(
    parti_id="Identifiant unique (ex: france_rn)",
    nom="Nom du parti",
    pays="Pays du parti",
    ideologie="Idéologie principale",
    dirigeant="Nom du dirigeant",
    couleur="Couleur hex (ex: #003189)",
    contexte="Contexte politique actuel"
)
async def ajout_parti(interaction: discord.Interaction, parti_id: str, nom: str, pays: str,
                      ideologie: str, dirigeant: str, couleur: str = "#5865F2", contexte: str = ""):
    db = load_db()
    guild_id = str(interaction.guild_id)
    user_id  = str(interaction.user.id)
    partis   = get_partis(db, guild_id, user_id)

    if parti_id in partis:
        await interaction.response.send_message(f"❌ Le parti `{parti_id}` existe déjà.")
        return

    partis[parti_id] = {
        "nom": nom,
        "pays": pays,
        "ideologie": ideologie,
        "dirigeant": dirigeant,
        "couleur": couleur,
        "contexte": contexte,
        "historique": []
    }
    save_db(db)
    await interaction.response.send_message(f"✅ Parti `{nom}` ajouté avec l'ID `{parti_id}` !")

@bot.tree.command(name="supprimer_parti", description="Supprimer un parti de la base de données")
@discord.app_commands.describe(
    parti_id="Identifiant du parti à supprimer (ex: france_rn)"
)
async def supprimer_parti(interaction: discord.Interaction, parti_id: str):
    db = load_db()
    guild_id = str(interaction.guild_id)
    user_id  = str(interaction.user.id)
    partis   = get_partis(db, guild_id, user_id)

    if parti_id not in partis:
        await interaction.response.send_message(f"❌ Le parti `{parti_id}` n'existe pas.")
        return

    nom = partis[parti_id]["nom"]
    del partis[parti_id]
    save_db(db)
    await interaction.response.send_message(f"✅ Parti `{nom}` (`{parti_id}`) supprimé.")

@bot.tree.command(name="liste_partis", description="Lister tous les partis enregistrés")
async def liste_partis(interaction: discord.Interaction):
    db       = load_db()
    guild_id = str(interaction.guild_id)
    user_id  = str(interaction.user.id)
    partis   = get_partis(db, guild_id, user_id)

    if not partis:
        await interaction.response.send_message("❌ Aucun parti enregistré.")
        return

    embed = discord.Embed(title="🌍 Mes partis enregistrés", color=discord.Color.green())
    for parti_id, parti in partis.items():
        embed.add_field(
            name=f"{parti['nom']} (`{parti_id}`)",
            value=f"🗺️ {parti['pays']} • 👤 {parti['dirigeant']}\n📜 {parti['ideologie']}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

# ══════════════════════════════════════════════════════════════
#  COMMANDES ORDRES RELIGIEUX
# ══════════════════════════════════════════════════════════════

@bot.tree.command(name="ajout_ordre_religieux", description="Créer un Ordre Religieux pour le roleplay")
@discord.app_commands.describe(
    ordre_id="Identifiant unique (ex: france_eglise)",
    nom="Nom de l'Ordre (ex: L'Église de la Lumière)",
    religion="Foi représentée (ex: Catholicisme, Islam, Shintoïsme...)",
    chef="Nom/titre du chef de l'Ordre (ex: Grand Prêtre Aldric)",
    couleur="Couleur hex (ex: #8B4513)",
    contexte="Contexte religieux actuel"
)
async def ajout_ordre_religieux(interaction: discord.Interaction, ordre_id: str, nom: str, religion: str,
                                chef: str, couleur: str = "#8B4513", contexte: str = ""):
    db = load_db()
    guild_id = str(interaction.guild_id)
    user_id  = str(interaction.user.id)
    ordres   = get_ordres_religieux(db, guild_id, user_id)

    if ordre_id in ordres:
        await interaction.response.send_message(f"❌ L'Ordre `{ordre_id}` existe déjà.")
        return

    ordres[ordre_id] = {
        "nom": nom,
        "religion": religion,
        "chef": chef,
        "couleur": couleur,
        "contexte": contexte,
        "historique": []
    }
    save_db(db)
    await interaction.response.send_message(f"✅ Ordre Religieux `{nom}` ajouté avec l'ID `{ordre_id}` !")

@bot.tree.command(name="supprimer_ordre_religieux", description="Supprimer un Ordre Religieux de la base de données")
@discord.app_commands.describe(
    ordre_id="Identifiant de l'Ordre à supprimer (ex: france_eglise)"
)
async def supprimer_ordre_religieux(interaction: discord.Interaction, ordre_id: str):
    db = load_db()
    guild_id = str(interaction.guild_id)
    user_id  = str(interaction.user.id)
    ordres   = get_ordres_religieux(db, guild_id, user_id)

    if ordre_id not in ordres:
        await interaction.response.send_message(f"❌ L'Ordre `{ordre_id}` n'existe pas.")
        return

    nom = ordres[ordre_id]["nom"]
    del ordres[ordre_id]
    save_db(db)
    await interaction.response.send_message(f"✅ Ordre Religieux `{nom}` (`{ordre_id}`) supprimé.")

@bot.tree.command(name="liste_ordres_religieux", description="Lister tous les Ordres Religieux enregistrés")
async def liste_ordres_religieux(interaction: discord.Interaction):
    db       = load_db()
    guild_id = str(interaction.guild_id)
    user_id  = str(interaction.user.id)
    ordres   = get_ordres_religieux(db, guild_id, user_id)

    if not ordres:
        await interaction.response.send_message("❌ Aucun Ordre Religieux enregistré.")
        return

    embed = discord.Embed(title="✝️ Mes Ordres Religieux enregistrés", color=0x8B4513)
    for ordre_id, ordre in ordres.items():
        embed.add_field(
            name=f"{ordre['nom']} (`{ordre_id}`)",
            value=f"🙏 {ordre['religion']} • 👤 {ordre['chef']}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="reagir", description="Faire réagir un parti politique à un événement")
@discord.app_commands.describe(
    parti_id="Identifiant du parti (ex: france_rn)",
    message_lien="Lien du message auquel réagir (clic droit > Copier le lien)"
)
async def reagir(interaction: discord.Interaction, parti_id: str, message_lien: str):
    await interaction.response.defer()

    try:
        parties    = message_lien.strip().split("/")
        channel_id = int(parties[-2])
        message_id = int(parties[-1])
    except (ValueError, IndexError):
        await interaction.followup.send("❌ Lien de message invalide.")
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        await interaction.followup.send("❌ Channel introuvable.")
        return

    try:
        message_cible = await channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.followup.send("❌ Message introuvable.")
        return

    db       = load_db()
    guild_id = str(interaction.guild_id)
    user_id  = str(interaction.user.id)
    partis   = get_partis(db, guild_id, user_id)
    parti    = partis.get(parti_id)

    if not parti:
        await interaction.followup.send(f"❌ Parti `{parti_id}` introuvable.")
        return

    try:
        historique = parti.get("historique", [])
        reaction = await get_reaction(parti, message_cible.content, historique)

        parti.setdefault("historique", [])
        parti["historique"].append({"role": "user",      "content": message_cible.content})
        parti["historique"].append({"role": "assistant", "content": reaction})
        parti["historique"] = parti["historique"][-20:]
        save_db(db)

        embed = discord.Embed(
            title=f"🏛️ {parti['nom']} réagit :",
            description=reaction,
            color=discord.Color.from_str(parti.get("couleur", "#5865F2"))
        )
        embed.set_footer(text=f"Dirigeant : {parti['dirigeant']} • {parti['pays']}")
        await channel.send(embed=embed, reference=message_cible)
        await interaction.followup.send("✅ Réaction envoyée !")

    except Exception as e:
        logger.exception(f"Erreur /reagir (parti={parti_id})")
        if "429" in str(e):
            await interaction.followup.send("⏳ L'IA est temporairement surchargée, réessaie dans une minute.")
        else:
            await interaction.followup.send("❌ Une erreur est survenue pendant la génération de la réaction.")

@bot.tree.command(name="reagir_tous", description="Faire réagir tous les partis à un événement")
@discord.app_commands.describe(
    message_lien="Lien du message auquel réagir"
)
async def reagir_tous(interaction: discord.Interaction, message_lien: str):
    await interaction.response.defer()

    try:
        parties    = message_lien.strip().split("/")
        channel_id = int(parties[-2])
        message_id = int(parties[-1])
    except (ValueError, IndexError):
        await interaction.followup.send("❌ Lien invalide.")
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        await interaction.followup.send("❌ Channel introuvable.")
        return

    try:
        message_cible = await channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.followup.send("❌ Message introuvable.")
        return

    db       = load_db()
    guild_id = str(interaction.guild_id)
    user_id  = str(interaction.user.id)
    partis   = get_partis(db, guild_id, user_id)

    if not partis:
        await interaction.followup.send("❌ Aucun parti dans la base.")
        return

    for parti_id, parti in partis.items():
        try:
            historique = parti.get("historique", [])
            reaction = await get_reaction(parti, message_cible.content, historique)

            parti.setdefault("historique", [])
            parti["historique"].append({"role": "user",      "content": message_cible.content})
            parti["historique"].append({"role": "assistant", "content": reaction})
            parti["historique"] = parti["historique"][-20:]

            embed = discord.Embed(
                title=f"🏛️ {parti['nom']} réagit :",
                description=reaction,
                color=discord.Color.from_str(parti.get("couleur", "#5865F2"))
            )
            embed.set_footer(text=f"Dirigeant : {parti['dirigeant']} • {parti['pays']}")
            await channel.send(embed=embed, reference=message_cible)

        except Exception:
            logger.exception(f"Erreur /reagir_tous (parti={parti_id})")
            await channel.send(f"❌ Une erreur est survenue pour le parti `{parti_id}`.")

    save_db(db)
    await interaction.followup.send("✅ Tous les partis ont réagi !")

@bot.tree.command(name="reagir_religieux", description="Faire réagir un Ordre Religieux à un événement")
@discord.app_commands.describe(
    ordre_id="Identifiant de l'Ordre Religieux (ex: france_eglise)",
    message_lien="Lien du message auquel réagir (clic droit > Copier le lien)"
)
async def reagir_religieux(interaction: discord.Interaction, ordre_id: str, message_lien: str):
    await interaction.response.defer()

    try:
        parties    = message_lien.strip().split("/")
        channel_id = int(parties[-2])
        message_id = int(parties[-1])
    except (ValueError, IndexError):
        await interaction.followup.send("❌ Lien de message invalide.")
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        await interaction.followup.send("❌ Channel introuvable.")
        return

    try:
        message_cible = await channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.followup.send("❌ Message introuvable.")
        return

    db       = load_db()
    guild_id = str(interaction.guild_id)
    user_id  = str(interaction.user.id)
    ordres   = get_ordres_religieux(db, guild_id, user_id)
    ordre    = ordres.get(ordre_id)

    if not ordre:
        await interaction.followup.send(f"❌ Ordre Religieux `{ordre_id}` introuvable.")
        return

    try:
        historique = ordre.get("historique", [])
        reaction = await get_reaction_ordre_religieux(ordre, message_cible.content, historique)

        ordre.setdefault("historique", [])
        ordre["historique"].append({"role": "user",      "content": message_cible.content})
        ordre["historique"].append({"role": "assistant", "content": reaction})
        ordre["historique"] = ordre["historique"][-20:]
        save_db(db)

        embed = discord.Embed(
            title=f"✝️ {ordre['nom']} réagit :",
            description=reaction,
            color=discord.Color.from_str(ordre.get("couleur", "#8B4513"))
        )
        embed.set_footer(text=f"Chef de l'Ordre : {ordre['chef']} • {ordre['religion']}")
        await channel.send(embed=embed, reference=message_cible)
        await interaction.followup.send("✅ Réaction envoyée !")

    except Exception:
        logger.exception(f"Erreur /reagir_religieux (ordre={ordre_id})")
        await interaction.followup.send("❌ Une erreur est survenue pendant la génération de la réaction.")

@bot.tree.command(name="reagir_noblesse", description="Réaction de la Noblesse d'un pays à un événement RP")
@discord.app_commands.describe(
    pays="Le pays dont la noblesse réagit (ex: France, Japon...)",
    message_lien="Lien du message auquel réagir"
)
async def reagir_noblesse(interaction: discord.Interaction, pays: str, message_lien: str):
    await interaction.response.defer()
    try:
        parties    = message_lien.strip().split("/")
        channel_id = int(parties[-2])
        message_id = int(parties[-1])
        channel = bot.get_channel(channel_id)
        if not channel:
            await interaction.followup.send("❌ Channel introuvable.")
            return
        message_cible = await channel.fetch_message(message_id)
        titres = get_titres_noblesse(pays)
        reaction = await get_reaction_ordre(build_prompt_noblesse, pays, message_cible.content)
        embed = discord.Embed(
            title=f"👑 Noblesse de {pays} — {titres[0]}",
            description=reaction,
            color=0xFFD700
        )
        embed.add_field(name="Titres de noblesse", value=", ".join(titres), inline=False)
        embed.set_footer(text=f"En réponse à : {message_cible.content[:100]}")
        await channel.send(embed=embed, reference=message_cible)
        await interaction.followup.send("✅ Réaction envoyée !")
    except Exception:
        logger.exception("Erreur /reagir_noblesse")
        await interaction.followup.send("❌ Une erreur est survenue pendant la génération de la réaction.")

@bot.tree.command(name="reagir_peuple", description="Réaction du Peuple d'un pays à un événement RP")
@discord.app_commands.describe(
    pays="Le pays dont le peuple réagit (ex: France, Chine...)",
    message_lien="Lien du message auquel réagir"
)
async def reagir_peuple(interaction: discord.Interaction, pays: str, message_lien: str):
    await interaction.response.defer()
    try:
        parties    = message_lien.strip().split("/")
        channel_id = int(parties[-2])
        message_id = int(parties[-1])
        channel = bot.get_channel(channel_id)
        if not channel:
            await interaction.followup.send("❌ Channel introuvable.")
            return
        message_cible = await channel.fetch_message(message_id)
        reaction = await get_reaction_ordre(build_prompt_peuple, pays, message_cible.content)
        embed = discord.Embed(
            title=f"👥 Peuple de {pays}",
            description=reaction,
            color=0x3498DB
        )
        embed.set_footer(text=f"En réponse à : {message_cible.content[:100]}")
        await channel.send(embed=embed, reference=message_cible)
        await interaction.followup.send("✅ Réaction envoyée !")
    except Exception:
        logger.exception("Erreur /reagir_peuple")
        await interaction.followup.send("❌ Une erreur est survenue pendant la génération de la réaction.")

# ══════════════════════════════════════════════════════════════
#  COMMANDES RÉCUPÉRATION
# ══════════════════════════════════════════════════════════════

@bot.tree.command(name="recuperer_messages", description="Récupérer les 25 derniers messages du salon")
async def recuperer_messages(interaction: discord.Interaction):
    await interaction.response.defer()
    channel = interaction.channel
    messages = []
    async for msg in channel.history(limit=25, oldest_first=False):
        messages.append(
            f"[{msg.created_at.strftime('%d/%m/%Y %H:%M')}] {msg.author.display_name} : {msg.content}"
        )
    if not messages:
        await interaction.followup.send("❌ Aucun message trouvé.")
        return
    contenu = "\n".join(messages)
    fichier = io.BytesIO(contenu.encode("utf-8"))
    await interaction.followup.send(
        f"✅ {len(messages)} messages récupérés :",
        file=discord.File(fichier, filename="messages.txt")
    )

# ══════════════════════════════════════════════════════════════
#  COMMANDES CALENDRIER RP
# ══════════════════════════════════════════════════════════════

from discord.ext import tasks
from datetime import datetime, timedelta

# ── Helpers config ────────────────────────────────────────────

def get_config(guild_id: str) -> dict:
    data = load_db()
    return data.get("_config", {}).get(guild_id, {
        "annee_rp": 1,
        "mois_rp": 1,
        "jour_rp": 1,
        "debut_irl": None,
        "ratio_jours": 1,      # 1 jour IRL = X jours RP
        "statut": "arrete",    # "actif", "pause", "arrete"
        "channel_calendrier": None,
        "derniere_maj": None
    })

def save_config(guild_id: str, config: dict):
    data = load_db()
    if "_config" not in data:
        data["_config"] = {}
    data["_config"][guild_id] = config
    save_db(data)

def get_date_rp(guild_id: str) -> dict:
    config = get_config(guild_id)
    if config["statut"] != "actif" or not config.get("debut_irl"):
        return {
            "jour": config.get("jour_rp", 1),
            "mois": config.get("mois_rp", 1),
            "annee": config.get("annee_rp", 1)
        }
    debut = datetime.fromisoformat(config["debut_irl"])
    maintenant = datetime.now()
    jours_ecoules = (maintenant - debut).days
    ratio = config.get("ratio_jours", 1)
    jours_rp_total = (config.get("jour_rp", 1) - 1) + (jours_ecoules * ratio)
    annee_depart = config.get("annee_rp", 1)
    mois_depart = config.get("mois_rp", 1)

    # Calcul date RP
    total_mois = (mois_depart - 1) + (jours_rp_total // 30)
    jour = (jours_rp_total % 30) + 1
    annee = annee_depart + (total_mois // 12)
    mois = (total_mois % 12) + 1

    return {"jour": jour, "mois": mois, "annee": annee}

MOIS_NOMS = [
    "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

SAISON_IMAGES = {
    "printemps": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Spring_forest_mount_tai.jpg/1280px-Spring_forest_mount_tai.jpg",
    "ete":       "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/24701-nature-natural-beauty.jpg/1280px-24701-nature-natural-beauty.jpg",
    "automne":   "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Camponotus_flavomarginatus_ant.jpg/1280px-Camponotus_flavomarginatus_ant.jpg",
    "hiver":     "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Fresh_snow.JPG/1280px-Fresh_snow.JPG"
}


def get_saison(mois: int) -> str:
    if mois in [3, 4, 5]:   return "printemps"
    if mois in [6, 7, 8]:   return "ete"
    if mois in [9, 10, 11]: return "automne"
    return "hiver"

SAISON_EMOJI = {
    "printemps": "🌸", "ete": "☀️", "automne": "🍂", "hiver": "❄️"
}

def build_embed_calendrier(date: dict, guild_id: str) -> discord.Embed:
    saison = get_saison(date["mois"])
    emoji = SAISON_EMOJI[saison]
    mois_nom = MOIS_NOMS[date["mois"]]
    config = get_config(guild_id)
    statut = {"actif": "▶️ En cours", "pause": "⏸️ En pause", "arrete": "⏹️ Arrêté"}.get(config["statut"], "")

    embed = discord.Embed(
        title=f"{emoji} Calendrier du Royaume",
        description=f"## 📅 {date['jour']} {mois_nom} {date['annee']}",
        color={"printemps": 0x2ECC71, "ete": 0xF1C40F, "automne": 0xE67E22, "hiver": 0x3498DB}[saison]
    )
    embed.add_field(name="Saison", value=f"{emoji} {saison.capitalize()}", inline=True)
    embed.add_field(name="Statut RP", value=statut, inline=True)
    embed.add_field(name="Ratio", value=f"1 jour IRL = {config.get('ratio_jours', 1)} jour(s) RP", inline=True)
    embed.set_image(url=SAISON_IMAGES[saison])
    embed.set_footer(text="Politibot • Calendrier RP")
    return embed

# ── Tâche automatique quotidienne ─────────────────────────────

@tasks.loop(hours=24)
async def tick_calendrier():
    db = load_db()
    configs = db.get("_config", {})
    for guild_id, config in configs.items():
        if config.get("statut") != "actif":
            continue
        channel_id = config.get("channel_calendrier")
        if not channel_id:
            continue
        channel = bot.get_channel(int(channel_id))
        if not channel:
            continue
        date = get_date_rp(guild_id)
        embed = build_embed_calendrier(date, guild_id)
        await channel.send(embed=embed)

@tick_calendrier.before_loop
async def before_tick():
    await bot.wait_until_ready()

# ── Commandes ─────────────────────────────────────────────────

@bot.tree.command(name="set_annee", description="[ADMIN] Configurer le calendrier RP")
@discord.app_commands.describe(
    annee="Année RP de départ (ex: 1336)",
    mois="Mois RP de départ (1-12)",
    jour="Jour RP de départ (1-30)",
    ratio_jours="Nb de jours RP par jour IRL (ex: 7)",
    channel="Salon où afficher le calendrier chaque jour",
    demarrer="Démarre le RP immédiatement"
)
async def set_annee(interaction: discord.Interaction,
                    annee: int,
                    mois: int = 1,
                    jour: int = 1,
                    ratio_jours: int = 1,
                    channel: discord.TextChannel = None,
                    demarrer: bool = True):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Commande réservée aux administrateurs.", ephemeral=True)
        return

    config = {
        "annee_rp": annee,
        "mois_rp": mois,
        "jour_rp": jour,
        "ratio_jours": ratio_jours,
        "debut_irl": datetime.now().isoformat() if demarrer else None,
        "statut": "actif" if demarrer else "arrete",
        "channel_calendrier": str(channel.id) if channel else get_config(str(interaction.guild_id)).get("channel_calendrier"),
        "derniere_maj": datetime.now().isoformat()
    }
    save_config(str(interaction.guild_id), config)

    if demarrer and not tick_calendrier.is_running():
        tick_calendrier.start()

    embed = discord.Embed(title="📅 Calendrier RP configuré", color=0x2ECC71)
    embed.add_field(name="Date de départ", value=f"{jour} {MOIS_NOMS[mois]} {annee}", inline=True)
    embed.add_field(name="Ratio", value=f"1 jour IRL = {ratio_jours} jour(s) RP", inline=True)
    embed.add_field(name="Statut", value="▶️ Démarré" if demarrer else "⏹️ En attente", inline=True)
    if channel:
        embed.add_field(name="Salon calendrier", value=channel.mention, inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="annee", description="Afficher la date RP actuelle")
async def annee(interaction: discord.Interaction):
    date = get_date_rp(str(interaction.guild_id))
    embed = build_embed_calendrier(date, str(interaction.guild_id))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="rp_statut", description="[ADMIN] Gérer le statut du RP (pause/resume/stop)")
@discord.app_commands.describe(
    action="Action à effectuer"
)
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name="▶️ Reprendre", value="resume"),
    discord.app_commands.Choice(name="⏸️ Mettre en pause", value="pause"),
    discord.app_commands.Choice(name="⏹️ Arrêter", value="stop"),
])
async def rp_statut(interaction: discord.Interaction, action: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Commande réservée aux administrateurs.", ephemeral=True)
        return

    guild_id = str(interaction.guild_id)
    config = get_config(guild_id)

    if action == "pause":
        # Sauvegarde la date actuelle avant de pauser
        date = get_date_rp(guild_id)
        config["statut"] = "pause"
        config["jour_rp"] = date["jour"]
        config["mois_rp"] = date["mois"]
        config["annee_rp"] = date["annee"]
        config["debut_irl"] = None
        msg = "⏸️ RP mis en pause. La date est sauvegardée."

    elif action == "resume":
        config["statut"] = "actif"
        config["debut_irl"] = datetime.now().isoformat()
        if not tick_calendrier.is_running():
            tick_calendrier.start()
        msg = "▶️ RP repris !"

    elif action == "stop":
        config["statut"] = "arrete"
        config["debut_irl"] = None
        if tick_calendrier.is_running():
            tick_calendrier.cancel()
        msg = "⏹️ RP arrêté. Utilisez `/set_annee` pour en démarrer un nouveau."

    save_config(guild_id, config)
    await interaction.response.send_message(msg)
bot.run(os.getenv('DISCORD_TOKEN'))