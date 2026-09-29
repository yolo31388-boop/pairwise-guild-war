"""帮派宣战与停战系统"""
from dataclasses import dataclass, field

# 战争消耗
WAR_FUNDS_COST = 500
WAR_TOKEN_COST = 1
# 战争持续时间：48 小时（时间单位：天）
WAR_DURATION_DAYS = 2.0
# 停战后冷却：7 天内不能再宣同一帮派
WAR_COOLDOWN_DAYS = 7.0
# 积分权重：击杀 + 占领 + 资源
SCORE_KILL = 10
SCORE_CAPTURE = 50
SCORE_RESOURCE = 2
# 投降条件：积分差距超过该值可单方面投降结束战争
SURRENDER_SCORE_GAP = 1000

SAFE_ZONES = {"main_city", "safe_zone", "sanctuary", "town"}
BLOCKED_RELATIONS = {"ally", "friendly"}


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
        self.war_cooldown: dict = {}  # (g1,g2) -> 停战时间
        self.peace_requests: dict = {}  # (g1,g2) -> set of requester gids
        self.war_scores: dict = {}  # (g1,g2) -> {gid: score}

    def _find_war_key(self, g1: str, g2: str):
        for key in ((g1, g2), (g2, g1)):
            if key in self.active_wars:
                return key
        return (g1, g2)

    def declare_war(self, attacker: str, defender: str,
                    current_time: float = 0.0) -> tuple[bool, str]:
        # bug6: 同盟/友好禁止宣战，仅敌对可宣
        if not self.can_war_ally(attacker, defender):
            return False, "cannot declare war: relation is not hostile"
        # bug5: 冷却检查
        if not self.can_declare_again(attacker, current_time):
            return False, "cannot declare war: cooldown active"
        atk = self.guilds.get(attacker)
        dfn = self.guilds.get(defender)
        if atk is None or dfn is None:
            return False, "guild not found"
        # bug1: 消耗帮派资金和战争令
        if atk.funds < WAR_FUNDS_COST:
            return False, "insufficient funds"
        if atk.war_tokens < WAR_TOKEN_COST:
            return False, "insufficient war tokens"
        atk.funds -= WAR_FUNDS_COST
        atk.war_tokens -= WAR_TOKEN_COST
        # bug2: 战争有持续时间，到期自动停战
        self.active_wars[(attacker, defender)] = {
            "start_time": current_time,
            "duration": WAR_DURATION_DAYS,
        }
        self.war_scores[(attacker, defender)] = {attacker: 0, defender: 0}
        return True, "war declared"

    def get_war_duration(self) -> float:
        # bug2: 默认 48 小时
        return WAR_DURATION_DAYS

    def check_war_expiry(self, current_time: float) -> list:
        """到期自动停战，返回本次结束的战争列表。"""
        expired = []
        for key, war in list(self.active_wars.items()):
            if current_time - war["start_time"] >= war.get("duration", WAR_DURATION_DAYS):
                self._end_war(key, current_time)
                expired.append(key)
        return expired

    def _end_war(self, key: tuple, current_time: float) -> None:
        self.active_wars.pop(key, None)
        self.peace_requests.pop(key, None)
        self.war_scores.pop(key, None)
        self.war_cooldown[key] = current_time

    def request_peace(self, requester: str, other: str,
                      current_time: float = 0.0) -> tuple[bool, str]:
        # bug3: 停战需双方同意，或一方满足投降条件
        key = self._find_war_key(requester, other)
        if key not in self.active_wars:
            return False, "no active war"
        # 投降条件：积分差距过大，劣势方可单方面投降
        scores = self.war_scores.get(key, {})
        if len(scores) == 2:
            values = list(scores.values())
            if abs(values[0] - values[1]) >= SURRENDER_SCORE_GAP:
                self._end_war(key, current_time)
                return True, "surrender accepted"
        pending = self.peace_requests.setdefault(key, set())
        pending.add(requester)
        parties = set(key)
        if pending >= parties:
            self._end_war(key, current_time)
            return True, "peace agreed by both sides"
        return False, "peace pending other side's approval"

    def calculate_war_score(self, kills: int, captures: int, resources: int) -> int:
        # bug4: 击杀 + 占领 + 资源综合计算
        return kills * SCORE_KILL + captures * SCORE_CAPTURE + resources * SCORE_RESOURCE

    def can_declare_again(self, gid: str, current_time: float) -> bool:
        # bug5: 停战后 7 天冷却
        for (g1, g2), peace_time in self.war_cooldown.items():
            if gid in (g1, g2) and current_time - peace_time < WAR_COOLDOWN_DAYS:
                return False
        return True

    def can_war_ally(self, g1: str, g2: str) -> bool:
        # bug6: 同盟/友好禁止宣战，关系为敌对才能宣
        guild = self.guilds.get(g1)
        if guild is None:
            return False
        relation = guild.relation.get(g2, "neutral")
        if relation in BLOCKED_RELATIONS:
            return False
        return relation == "enemy"

    def is_safe_zone(self, location: str) -> bool:
        # bug7: 主城和安全区受保护
        return location in SAFE_ZONES
