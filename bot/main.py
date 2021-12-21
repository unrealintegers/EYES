from bot import EYESBot

if __name__ == "__main__":
    # Import all slash commands so they get recognised as subclasses
    from bot.slashes import *  # noqa

    bot = EYESBot(',')

    bot.run()
