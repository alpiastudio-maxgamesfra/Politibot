import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import json
import ssl
import io
from datetime import datetime
from ai import get_reaction, get_reaction_ordre, get_titres_noblesse, build_prompt_religieux, build_prompt_noblesse, build_prompt_peuple

ssl._create_default_https_context = ssl._create_unverified_context

VERSION = "1.1.0"

load_dotenv()

print("Lancement de Politibot...")
bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

# ══════════════════════════════════════════════════════════════
#  BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════

def load_db():
    with open("database.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open("database.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_partis(db, guild_id: str, user_id: str):
    db.setdefault(guild_id, {})
    db[guild_id].setdefault(user_id, {"partis": {}})
    db[guild_id][user_id].setdefault("partis", {})
    return db[guild_id][user_id]["partis"]

def get_config(guild_id: str) -> dict:
    data = load_db()
    return data.get("_config", {}).get(guild_id, {
        "annee_rp": 1,
        "debut_irl": None,
        "ratio": 12
    })

def save_config(guild_id: str, config: dict):
    data = load_db()
    if "_config" not in data:
        data["_config"] = {}
    data["_config"][guild_id] = config
    save_db(data)  # Partis et tout le reste intact

def get_annee_actuelle(guild_id: str) -> int:
    config = get_config(guild_id)
    if not config.get("debut_irl"):
        return config.get("annee_rp", 1)
    debut = datetime.fromisoformat(config["debut_irl"])
    maintenant = datetime.now()
    jours_ecoules = (maintenant - debut).days
    ratio = config.get("ratio", 12)
    mois_rp = jours_ecoules * ratio / 30
    return config["annee_rp"] + int(mois_rp / 12)

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
    embed.add_field(name="/reagir_religieux", value="Réaction d'un Ordre Religieux", inline=False)
    embed.add_field(name="/reagir_noblesse", value="Réaction de la Noblesse d'un pays", inline=False)
    embed.add_field(name="/reagir_peuple", value="Réaction du Peuple d'un pays", inline=False)
    embed.add_field(name="/ajout_parti", value="Ajouter un parti à la base", inline=False)
    embed.add_field(name="/supprimer_parti", value="Supprimer un parti de la base", inline=False)
    embed.add_field(name="/liste_partis", value="Lister tous les partis", inline=False)
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
#  COMMANDES RÉACTIONS
# ══════════════════════════════════════════════════════════════

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
        if "429" in str(e):
            await interaction.followup.send("⏳ L'IA est temporairement surchargée, réessaie dans une minute.")
        else:
            await interaction.followup.send(f"❌ Erreur IA : `{e}`")

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

        except Exception as e:
            await channel.send(f"❌ Erreur pour `{parti_id}` : `{e}`")

    save_db(db)
    await interaction.followup.send("✅ Tous les partis ont réagi !")

@bot.tree.command(name="reagir_religieux", description="Réaction d'un Ordre Religieux à un événement RP")
@discord.app_commands.describe(
    religion="La religion de l'ordre (ex: Catholicisme, Islam, Shintoïsme...)",
    message_lien="Lien du message auquel réagir"
)
async def reagir_religieux(interaction: discord.Interaction, religion: str, message_lien: str):
    await interaction.response.defer()
    try:
        parties    = message_lien.strip().split("/")
        channel_id = int(parties[-2])
        message_id = int(parties[-1])
        channel = bot.get_channel(channel_id)
        message_cible = await channel.fetch_message(message_id)
        reaction = await get_reaction_ordre(build_prompt_religieux, religion, message_cible.content)
        embed = discord.Embed(
            title=f"✝️ Ordre Religieux — {religion}",
            description=reaction,
            color=0x8B4513
        )
        embed.set_footer(text=f"En réponse à : {message_cible.content[:100]}")
        await channel.send(embed=embed, reference=message_cible)
        await interaction.followup.send("✅ Réaction envoyée !")
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur : `{e}`")

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
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur : `{e}`")

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
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur : `{e}`")

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

@bot.tree.command(name="set_annee", description="[ADMIN] Définir l'année RP et la correspondance IRL")
@discord.app_commands.describe(
    annee="L'année RP actuelle (ex: 1450)",
    ratio="Nb de mois RP par mois IRL (ex: 12 = 1 an RP par mois IRL)",
    demarrer="Démarre le compteur IRL maintenant"
)
async def set_annee(interaction: discord.Interaction, annee: int, ratio: int = 12, demarrer: bool = True):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Commande réservée aux administrateurs.", ephemeral=True)
        return
    config = {
        "annee_rp": annee,
        "ratio": ratio,
        "debut_irl": datetime.now().isoformat() if demarrer else None
    }
    save_config(str(interaction.guild_id), config)
    embed = discord.Embed(title="📅 Année RP configurée", color=0x2ECC71)
    embed.add_field(name="Année RP", value=str(annee), inline=True)
    embed.add_field(name="Ratio", value=f"1 mois IRL = {ratio} mois RP", inline=True)
    embed.add_field(name="Compteur", value="✅ Démarré" if demarrer else "⏸️ Manuel", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="annee", description="Affiche l'année RP actuelle")
async def annee(interaction: discord.Interaction):
    annee_actuelle = get_annee_actuelle(str(interaction.guild_id))
    config = get_config(str(interaction.guild_id))
    embed = discord.Embed(title="📅 Calendrier RP", color=0xF1C40F)
    embed.add_field(name="Année RP", value=f"**{annee_actuelle}**", inline=True)
    embed.add_field(name="Ratio", value=f"1 mois IRL = {config.get('ratio', 12)} mois RP", inline=True)
    await interaction.response.send_message(embed=embed)

# ══════════════════════════════════════════════════════════════

bot.run(os.getenv('DISCORD_TOKEN'))