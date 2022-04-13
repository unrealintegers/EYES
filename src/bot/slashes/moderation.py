import io

from discord import ApplicationContext, Option
from discord import File

from ..bot import EYESBot, SlashCommand


class EvaluateCommand(SlashCommand, name="evaluate"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.result = None

        self.register(self._eval, name="eval")

    async def _eval(
            self, ctx: ApplicationContext,
            command: Option(str, "&h")
    ):
        if ctx.user.id not in [330509305663193091, 475440146221760512]:
            await ctx.respond("What do you think you're doing?",
                              ephemeral=True)
            return
        """evaluate"""
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
            await ctx.respond(file=File(fp, "output.txt"))
        else:
            await ctx.respond(self.result, ephemeral=ephemeral)
