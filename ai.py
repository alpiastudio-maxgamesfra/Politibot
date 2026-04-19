import os
from mistralai import Mistral

# ── Mapping titres de noblesse par pays ──
NOBLESSE = {
    "france": ["Duc", "Marquis", "Comte", "Vicomte", "Baron"],
    "japon": ["Daimyo", "Shogun", "Hatamoto"],
    "angleterre": ["Duke", "Earl", "Baron", "Lord"],
    "allemagne": ["Herzog", "Graf", "Freiherr"],
    "espagne": ["Duque", "Marqués", "Conde"],
    "italie": ["Duca", "Marchese", "Conte"],
    "russie": ["Knyaz", "Boyar", "Dvoryanin"],
    "empire ottoman": ["Pacha", "Bey", "Agha"],
    "chine": ["Wang", "Hou", "Bo"],
    "default": ["Noble", "Seigneur", "Lord"]
}

def get_titres_noblesse(pays: str) -> list:
    return NOBLESSE.get(pays.lower(), NOBLESSE["default"])

def build_system_prompt(parti: dict) -> str:
    return f"""
    Tu incarnes le {parti['nom']}, un parti politique de {parti['pays']}.
    Idéologie : {parti['ideologie']}
    Dirigeant : {parti['dirigeant']}
    Contexte récent : {parti.get('contexte', 'Aucun contexte disponible.')}
    Règles absolues :
    - Parle toujours au nom du parti, à la 1ère personne du pluriel.
    - Reste fidèle à l'idéologie, même si tu n'es pas d'accord.
    - Ton d'un communiqué officiel, 2-4 phrases maximum.
    - Tu es dans un jeu de rôle géopolitique, reste dans ce cadre.
    - Ne mentionne jamais que tu es une IA.
    """

def build_prompt_religieux(religion: str) -> str:
    return f"""Tu incarnes un Ordre Religieux de la foi {religion}.
    Tu parles au nom de cet ordre, avec un ton solennel et dogmatique.
    Règles absolues :
    - 1ère personne du pluriel.
    - Ton d'un communiqué officiel religieux, 2-4 phrases maximum.
    - Tu es dans un jeu de rôle géopolitique, reste dans ce cadre.
    - Ne mentionne jamais que tu es une IA.
    """

def build_prompt_noblesse(pays: str) -> str:
    titres = get_titres_noblesse(pays)
    titre = titres[0]
    return f"""Tu incarnes la Haute Noblesse de {pays}, représentée par un {titre}.
    Tu parles avec l'arrogance et le prestige de la noblesse de {pays}.
    Règles absolues :
    - 1ère personne.
    - Ton aristocratique et hautain, 2-4 phrases maximum.
    - Tu es dans un jeu de rôle géopolitique, reste dans ce cadre.
    - Ne mentionne jamais que tu es une IA.
    """

def build_prompt_peuple(pays: str) -> str:
    return f"""Tu incarnes le Peuple de {pays}, avec sa culture, ses traditions et ses préoccupations propres.
    Tu parles au nom des gens ordinaires, avec un ton populaire et authentique propre à la culture de {pays}.
    Règles absolues :
    - 1ère personne du pluriel.
    - Ton populaire et culturellement ancré, 2-4 phrases maximum.
    - Tu es dans un jeu de rôle géopolitique, reste dans ce cadre.
    - Ne mentionne jamais que tu es une IA.
    """

async def get_reaction(parti, evenement, historique=[]):
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    historique_normalise = [
        {"role": "assistant" if m["role"] == "model" else m["role"],
         "content": m["content"]}
        for m in historique
    ]
    messages = [
        {"role": "system", "content": build_system_prompt(parti)},
        *historique_normalise,
        {"role": "user", "content": evenement}
    ]
    response = await client.chat.complete_async(
        model="mistral-small-latest",
        messages=messages,
        temperature=0.85,
        max_tokens=300
    )
    return response.choices[0].message.content

async def get_reaction_ordre(prompt_fn, param: str, evenement: str, historique=[]):
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    historique_normalise = [
        {"role": "assistant" if m["role"] == "model" else m["role"],
         "content": m["content"]}
        for m in historique
    ]
    messages = [
        {"role": "system", "content": prompt_fn(param)},
        *historique_normalise,
        {"role": "user", "content": evenement}
    ]
    response = await client.chat.complete_async(
        model="mistral-small-latest",
        messages=messages,
        temperature=0.85,
        max_tokens=300
    )
    return response.choices[0].message.content