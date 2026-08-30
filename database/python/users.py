from pymongo import UpdateOne
from database.python.mongodb import db


players = db["Jogadores"]
mora = db["Mora"]
hunos = db["Hunos"]
inv = db["Inventários"]
mag = db["Magias"]
hab = db["Habilidades"]

def cadastro(membros):
    players_ops = []
    mora_ops = []
    hunos_ops = []
    inv_ops = []
    mag_ops = []
    hab_ops = []

    for member in membros:
        if member.bot:
            continue

        user_id = str(member.id)
        guild_id = str(member.guild.id)

        filtro = {
            "ID": user_id,
            "guild_id": guild_id
        }

        players_ops.append(
            UpdateOne(
                filtro,
                {
                    "$setOnInsert": {
                        "ID": user_id,
                        "guild_id": guild_id,
                        "Nome do Discord": member.display_name,
                        "nome de usuario do disc": member.name,
                        "Situação": "pendente",
                        "Nome": None,
                        "Raça": None,
                        "Nivel": 1,
                        "XP": 0,
                        "Vida": 100,
                        "Vida_Maxima": 100,
                        "Mana": 100,
                        "Mana Total": 100,
                        "Ma"
                        "Força": 0,
                        "Defesa": 0,
                        "Velocidade": 0,
                        "Destreza": 0,
                        "Magia": 0,
                        "Sorte": 0
                    }
                },
                upsert=True
            )
        )

        mora_ops.append(
            UpdateOne(
                filtro,
                {
                    "$setOnInsert": {
                        "Situação": "pendente",
                        "ID": user_id,
                        "guild_id": guild_id,
                        "carteira": 0,
                        "banco": 0,
                    }
                },
                upsert=True
            )
        )

        hunos_ops.append(
            UpdateOne(
                filtro,
                {
                    "$setOnInsert": {
                        "ID": user_id,
                        "guild_id": guild_id,
                        "Situação": "pendente",
                        "carteira": 0,
                        "banco": 0
                    }
                },
                upsert=True
            )
        )

        inv_ops.append(
            UpdateOne(
                filtro,
                {
                    "$setOnInsert": {
                        "ID": user_id,
                        "guild_id": guild_id,
                        "Situação": "pendente",
                        "itens": []
                    }
                },
                upsert=True
            )
        )

        mag_ops.append(
            UpdateOne(
                filtro,
                {
                    "$setOnInsert": {
                        "ID": user_id,
                        "guild_id": guild_id,
                        "Situação": "pendente",
                        "magias": []
                    }
                },
                upsert=True
            )
        )

        hab_ops.append(
            UpdateOne(
                filtro,
                {
                    "$setOnInsert": {
                        "ID": user_id,
                        "guild_id": guild_id,
                        "Situação": "pendente",
                        "habilidades": []
                    }
                },
                upsert=True
            )
        )

    if players_ops:
        players.bulk_write(players_ops)

    if mora_ops:
        mora.bulk_write(mora_ops)

    if hunos_ops:
        hunos.bulk_write(hunos_ops)

    if inv_ops:
        inv.bulk_write(inv_ops)

    if mag_ops:
        mag.bulk_write(mag_ops)

    if hab_ops:
        hab.bulk_write(hab_ops)

    return len(players_ops)

