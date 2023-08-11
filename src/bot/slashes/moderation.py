import io

from discord import File
from discord import Interaction

from ..bot import EYESBot, SlashCommand


class EvaluateCommand(SlashCommand, name="eval"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.result = None

    async def callback(self, ictx: Interaction, command: str):  # noqa
        """Evaluate"""
        if ictx.user.id not in [330509305663193091, 475440146221760512]:
            await ictx.response.send_message("What do you think you're doing?", ephemeral=True)
            return

        ephemeral = (command[0] == "&")
        if ephemeral:
            command = command[1:]

        if command[0] == command[-1] == '`':
            command = command[1:-1]

        if command.startswith("await "):
            command = command[6:]
            self.result = str(await eval(command))
        else:
            self.result = str(eval(command))

        if len(self.result) > 2000:
            fp = io.BytesIO(self.result.encode('utf-8'))
            await ictx.response.send_message(file=File(fp, "output.txt"))
        else:
            await ictx.response.send_message(self.result, ephemeral=ephemeral)
