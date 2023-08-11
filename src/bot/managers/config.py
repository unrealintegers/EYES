import json
import os.path


class ConfigManager:
    @staticmethod
    def get_from_path(mapping, path):
        for ext in path.split('/'):
            mapping = mapping.get(ext, {})
        return mapping

    @staticmethod
    def set_to_path(mapping, path, value):
        *path, last = path.split('/')
        for ext in path:
            mapping = mapping.setdefault(ext, {})

        mapping[last] = value

    _global = {}
    _guild = {}
    _user = {}

    @classmethod
    def update(cls):
        with open('config/global.json', 'r') as f:
            cls._global = json.loads(f.read())

        with open('config/guild.json', 'r') as f:
            cls._guild = json.loads(f.read())

        with open('config/user.json', 'r') as f:
            cls._user = json.loads(f.read())

        print(cls._global)

    @classmethod
    def get_dynamic(cls, path, guild_id=None, user_id=None):
        # TODO: Reconsider the logic of this function
        if result := cls.get_from_path(cls._global, path):
            return result

        # Global not found, we search guilds
        if guild_id is not None:
            if result := cls.get_from_path(cls._guild.get(guild_id, {}), path):
                return result

        # Finally we try users
        if user_id is not None:
            if result := cls.get_from_path(cls._user.get(user_id, {}), path):
                return result

        # Not found
        return None

    @classmethod
    def get_static(cls, fp):
        with open(os.path.join('config', fp + '.json'), 'r') as f:
            return json.loads(f.read())

    @classmethod
    def set_global(cls, path, value):
        cls.set_to_path(cls._global, path, value)
        with open('config/global.json', 'w') as f:
            f.write(json.dumps(cls._global, indent=4))

    @classmethod
    def set_guild(cls, guild_id, path, value):
        cls.set_to_path(cls._guild.setdefault(guild_id, {}), path, value)
        with open('config/guild.json', 'w') as f:
            f.write(json.dumps(cls._guild, indent=4))

    @classmethod
    def set_user(cls, user_id, path, value):
        cls.set_to_path(cls._user.setdefault(user_id, {}), path, value)
        with open('config/user.json', 'w') as f:
            f.write(json.dumps(cls._user, indent=4))

    @classmethod
    def set_static(cls, fp, content):
        with open(os.path.join('config', fp + '.json'), 'w') as f:
            f.write(json.dumps(content, indent=4))
