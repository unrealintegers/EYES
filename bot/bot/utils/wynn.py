from __future__ import annotations

from datetime import datetime as dt

from dateutil import parser as dtparser

RANKS = [
    'RECRUIT',
    'RECRUITER',
    'CAPTAIN',
    'STRATEGIST',
    'CHIEF',
    'OWNER'
]


class GuildMember:
    def __init__(self,
                 uuid: str,
                 name: str,
                 rank: int,
                 joined: float | dt,
                 contributed: int,
                 **_):
        self.uuid = uuid
        self.name = name
        self.rank = rank
        if isinstance(joined, dt):
            self.joined = joined
        else:
            self.joined = dt.utcfromtimestamp(joined)
        self.contributed = contributed

    @classmethod
    def from_data(cls, data):
        if data['rank']:
            data['rank'] = RANKS.index(data['rank'])
        if data['joined']:
            data['joined'] = dtparser.parse(data['joined'])
        return cls(**data)

    # uuid -> { name, rank: int, joined: float (timestamp), contributed: int }
    def to_dict_item(self):
        k = self.uuid
        v = vars(self)
        del v['uuid']
        v['joined'] = v['joined'].timestamp()
        return k, v
