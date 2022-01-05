class ConfigManager:
    _db = None
    _global = {}
    _guild = {}

    @classmethod
    def init_db(cls, db):
        cls._db = db
        cls.update()

    @classmethod
    def update(cls):
        if not cls._db:
            raise ValueError("db has not been initialised")

        data = cls._db.child('config').get().val()
        cls._global = data.get('global', {})
        cls._guild = data.get('guild', {})

        print(cls._global)

    @classmethod
    def get(cls, path, key, guild_id=None, user_id=None):
        print(cls._global)
        # TODO: Implement paths of depth >1 (containing /)
        if not cls._db:
            raise ValueError("db has not been initialised")

        if result := cls._global.get(path, {}).get(key):
            return result

        # Global not found, we search guilds
        if guild_id is not None:
            if result := cls._guild.get(guild_id, {}).get(path, {}).get(key):
                return result

        # Finally we try users
        if user_id is not None:
            user_dict = cls._db.child("config").child("user").child(user_id).child(path).get().val()
            return user_dict.get(key)

        # Not found
        return None
