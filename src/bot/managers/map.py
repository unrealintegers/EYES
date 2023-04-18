import typing

if typing.TYPE_CHECKING:
    from ..bot import EYESBot


class MapManager:
    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

        self.claim_guilds = {}
        self.owners = {}

    def init(self):
        self.owners = self.bot.db.child('config').child('claims').get().val()
        self.claim_guilds = {}
        for t, g in self.owners.items():
            if isinstance(t, str) and isinstance(g, str):
                self.claim_guilds.setdefault(g, []).append(t)
            else:
                self.bot.logger.critical(f"Guild claims of wrong format: {g} owns {t}")
                self.claim_guilds = {}
                break

    def is_map_guild(self, guild: str):
        return guild in self.claim_guilds

    def is_ffa(self, territory: str):
        if owner := self.owners.get(territory):
            return owner == "_"
        else:
            raise ValueError(f"Invalid Name for Territory: {territory}")

    def owns(self, guild: str, territory: str):
        if owner := self.owners.get(territory):
            return owner == guild
        else:
            raise ValueError(f"Invalid Name for Territory: {territory}")
