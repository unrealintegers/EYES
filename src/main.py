from bot import EYESBot

import os
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    # Import all slash commands and tasks so they get recognised as subclasses
    from bot.slashes import *  # noqa
    from bot.slashes.shortcuts import *  # noqa
    from bot.tasks import *  # noqa

    bot = EYESBot(',')

    bot.run(os.getenv("TOKEN"))
