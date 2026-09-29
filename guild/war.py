"""帮派宣战与停战系统 - 含7个bug"""
from dataclasses import dataclass, field

@dataclass
class Guild:
    gid: str
    name: str
    funds: int = 1000
    war_tokens: int = 0
    relation: dict = field(default_factory=dict)  # other_gid -> ally/enemy/neutral

class WarSystem:
    def __init__(self):
        self.guilds: dict[str, Guild] = {}
        self.active_wars: dict = {}  # (g1,g2) -> {start_time, duration}
        self.war_cooldown: dict = {}  # bug5: 无冷却

    def declare_war(self, attacker: str, defender: str) -> tuple[bool, str]:
        # bug1: 不消耗
        return True, "war declared"

    def get_war_duration(self) -> float:
        # bug2: 无持续时间
        return float("inf")

    def request_peace(self, requester: str, other: str) -> tuple[bool, str]:
        # bug3: 单方面即可
        return True, "peace"

    def calculate_war_score(self, kills: int, captures: int, resources: int) -> int:
        # bug4: 只看击杀
        return kills

    def can_declare_again(self, gid: str, current_time: float) -> bool:
        # bug5: 无冷却
        return True

    def can_war_ally(self, g1: str, g2: str) -> bool:
        # bug6: 同盟可宣战
        return True

    def is_safe_zone(self, location: str) -> bool:
        # bug7: 无安全区
        return False
