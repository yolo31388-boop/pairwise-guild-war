"""帮派宣战与停战系统 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guild.war import WarSystem, Guild

class TestWarCost:
    def test_war_requires_funds_and_tokens(self):
        ws = WarSystem()
        ws.guilds["g1"] = Guild("g1", "a", funds=0, war_tokens=0)
        ws.guilds["g2"] = Guild("g2", "b")
        ok, msg = ws.declare_war("g1", "g2")
        assert ok == False  # bug1: 不消耗也成功

class TestWarDuration:
    def test_war_has_duration(self):
        ws = WarSystem()
        d = ws.get_war_duration()
        assert d < float("inf") and d > 0  # bug2: inf

class TestPeaceRequiresBoth:
    def test_peace_needs_both_sides_agree(self):
        ws = WarSystem()
        ws.active_wars[("g1", "g2")] = {"start_time": 0}
        ok, msg = ws.request_peace("g1", "g2")
        # 应该需要对方同意
        assert "pending" in msg or ok == False  # bug3: 直接成功

class TestWarScore:
    def test_war_score_includes_more_than_kills(self):
        ws = WarSystem()
        s1 = ws.calculate_war_score(kills=10, captures=0, resources=0)
        s2 = ws.calculate_war_score(kills=0, captures=10, resources=100)
        assert s2 > 0  # bug4: 只看kills=0

class TestWarCooldown:
    def test_cannot_declare_war_right_after_peace(self):
        ws = WarSystem()
        ws.war_cooldown[("g1", "g2")] = 100.0
        assert ws.can_declare_again("g1", 50.0) == False  # bug5: True
        assert ws.can_declare_again("g1", 150.0) == True

class TestAllyProtection:
    def test_allies_cannot_declear_war(self):
        ws = WarSystem()
        ws.guilds["g1"] = Guild("g1", "a")
        ws.guilds["g2"] = Guild("g2", "b")
        ws.guilds["g1"].relation["g2"] = "ally"
        assert ws.can_war_ally("g1", "g2") == False  # bug6: True

class TestSafeZone:
    def test_main_city_is_safe_zone(self):
        ws = WarSystem()
        assert ws.is_safe_zone("main_city") == True  # bug7: False
