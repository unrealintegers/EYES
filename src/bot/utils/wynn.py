from __future__ import annotations

import base64
import uuid as uuid_
import zlib
from ast import literal_eval as ieval
from datetime import datetime as dt

from dateutil import parser as dtparser

RANKS = [
    'recruit',
    'recruiter',
    'captain',
    'strategist',
    'chief',
    'owner'
]


class GuildMember:
    def __init__(self,
                 name: str,
                 uuid: uuid_.UUID,
                 rank: int,
                 joined: float | dt,
                 contributed: int,
                 **_):
        self.name = name
        self.uuid = uuid
        self.rank = rank
        if isinstance(joined, dt) or joined is None:
            self.joined = joined
        else:
            self.joined = dt.utcfromtimestamp(joined)
        self.contributed = contributed

    def __repr__(self):
        return f"<GuildMember name={self.name}>"

    def __str__(self):
        return f"<GuildMember name={self.name}>"

    @classmethod
    def from_data(cls, key, data):
        data['name'] = data.pop('username')
        if data['rank']:
            data['rank'] = RANKS.index(data['rank'])
        if data['joined']:
            data['joined'] = dtparser.parse(data['joined'])
        return cls(uuid=uuid_.UUID(key), **data)

    # { name, uuid: str, rank: int, joined: float (timestamp), contributed: int }
    def to_dict(self):
        return vars(self)


def parse_map_string(ms):
    return ieval(zlib.decompress(base64.b85decode(ms)).decode('ascii'))
