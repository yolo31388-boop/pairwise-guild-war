"""帮派宣战与停战系统"""
from dataclasses import dataclass, field

WAR_DECLARATION_COST_FUNDS = 500      # 宣战消耗帮派资金
WAR_DECLARATION_COST_TOKENS = 1       # 宣战消耗战争令
WAR_DURATION_SECONDS = 48 * 3600      # bug2: 战争默认持续48小时
WAR_COOLDOWN_SECONDS = 7 * 24 * 3600  # bug5: 停战后7天冷却
SCORE_PER_KILL = 1
SCORE_PER_CAPTURE = 10
SCORE_PER_RESOURCE = 2
SCORE_PER_DESTROY = 15
SURRENDER_SCORE_RATIO = 0.3           # 积分低于对方30%可投降
SAFE_ZONES = frozenset({"main_city", "safe_zone", "sanctuary"})  # bug7: 安全区


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
        self.active_wars: dict = {}   # (g1,g2) -> {start_time, duration, scores}
        self.war_cooldown: dict = {}  # (g1,g2) -> 冷却截止时刻
        self.peace_requests: dict = {}  # (g1,g2) -> set of gid 已请求停战方

    def _find_war_key(self, g1: str, g2: str):
        for key in ((g1, g2), (g2, g1)):
            if key in self.active_wars:
                return key
        return None

    def _relation(self, g1: str, g2: str) -> str:
        guild = self.guilds.get(g1)
        if guild is None:
            return "neutral"
        return guild.relation.get(g2, "neutral")

    def declare_war(self, attacker: str, defender: str,
                    current_time: float = 0.0) -> tuple[bool, str]:
        # bug6: 同盟/友好禁止宣战，只有敌对关系才能宣战
        if not self.can_war_ally(attacker, defender):
            return False, "cannot declare war: relation is not hostile"
        if self._find_war_key(attacker, defender) is not None:
            return False, "war already active"
        # bug5: 冷却期内不能再次宣战
        if not self.can_declare_again(attacker, current_time, defender):
            return False, "war declaration is on cooldown"
        atk = self.guilds.get(attacker)
        if atk is None:
            return False, "attacker guild not found"
        # bug1: 宣战消耗帮派资金和战争令
        if atk.funds < WAR_DECLARATION_COST_FUNDS:
            return False, "insufficient funds to declare war"
        if atk.war_tokens < WAR_DECLARATION_COST_TOKENS:
            return False, "insufficient war tokens to declare war"
        atk.funds -= WAR_DECLARATION_COST_FUNDS
        atk.war_tokens -= WAR_DECLARATION_COST_TOKENS
        self.active_wars[(attacker, defender)] = {
            "start_time": current_time,
            "duration": WAR_DURATION_SECONDS,
            "scores": {attacker: 0, defender: 0},
        }
        return True, "war declared"

    def get_war_duration(self) -> float:
        # bug2: 战争有持续时间（默认48小时）
        return float(WAR_DURATION_SECONDS)

    def check_war_expiry(self, current_time: float) -> list:
        """bug2: 到期的战争自动停战，返回自动停战的战争键列表。"""
        expired = []
        for key, war in list(self.active_wars.items()):
            if current_time >= war["start_time"] + war["duration"]:
                expired.append(key)
        for key in expired:
            self._end_war(key, current_time)
        return expired

    def _end_war(self, key: tuple, current_time: float) -> None:
        self.active_wars.pop(key, None)
        self.peace_requests.pop(key, None)
        # bug5: 停战后进入7天冷却，记录冷却截止时刻
        self.war_cooldown[key] = current_time + WAR_COOLDOWN_SECONDS

    def request_peace(self, requester: str, other: str,
                      current_time: float = 0.0) -> tuple[bool, str]:
        key = self._find_war_key(requester, other)
        if key is None:
            return False, "no active war"
        # bug3: 投降条件——积分远低于对方时可单方面投降结束战争
        scores = self.active_wars[key].get("scores", {})
        my_score = scores.get(requester, 0)
        enemy_score = scores.get(other, 0)
        if enemy_score > 0 and my_score <= enemy_score * SURRENDER_SCORE_RATIO:
            self._end_war(key, current_time)
            return True, "surrender accepted"
        # bug3: 停战需要双方同意，单方请求进入 pending
        pending = self.peace_requests.setdefault(key, set())
        pending.add(requester)
        g1, g2 = key
        if {g1, g2} <= pending:
            self._end_war(key, current_time)
            return True, "peace agreed by both sides"
        return False, "peace pending: waiting for the other side"

    def calculate_war_score(self, kills: int, captures: int, resources: int,
                            destroys: int = 0) -> int:
        # bug4: 击杀+占领+资源+摧毁综合计算
        return (kills * SCORE_PER_KILL
                + captures * SCORE_PER_CAPTURE
                + resources * SCORE_PER_RESOURCE
                + destroys * SCORE_PER_DESTROY)

    def can_declare_again(self, gid: str, current_time: float,
                          other: str = None) -> bool:
        # bug5: 冷却截止时刻之前不能再次宣战
        if other is not None:
            keys = [(gid, other), (other, gid)]
        else:
            keys = [key for key in self.war_cooldown if gid in key]
        for key in keys:
            cooldown_until = self.war_cooldown.get(key)
            if cooldown_until is not None and current_time < cooldown_until:
                return False
        return True

    def can_war_ally(self, g1: str, g2: str) -> bool:
        # bug6: 同盟和友好帮派禁止宣战，关系为敌对才能宣
        return (self._relation(g1, g2) == "enemy"
                and self._relation(g2, g1) == "enemy")

    def is_safe_zone(self, location: str) -> bool:
        # bug7: 主城和安全区受保护，出城才是PVP区域
        return location in SAFE_ZONES

    def can_pvp(self, location: str) -> bool:
        """战争期间只有非安全区才能PVP。"""
        return not self.is_safe_zone(location)
