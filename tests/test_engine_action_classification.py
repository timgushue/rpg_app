import sys
import types

sys.modules.setdefault("anthropic", types.SimpleNamespace(Anthropic=lambda api_key=None: None))

from ai.engine import Engine, _scene_title_from_resolution


class FakeDB:
    pass


class FakeResponse:
    def __init__(self, text):
        self.content = [type("Part", (), {"text": text})()]


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return FakeResponse(response)


def test_classify_action_skill_uses_model_output():
    engine = Engine(FakeDB())
    engine.client = FakeClient(['{"skill": "Perception"}'])
    campaign = {"hero_name": "Pip", "hero_sheet": {"level": 1, "ancestry": "Elf", "class": "Wizard"}}

    skill = engine._classify_action_skill(campaign, [], "I inspect the altar for hidden switches.")

    assert skill == "Perception"
    assert engine.client.calls[0]["model"] == "claude-3-5-haiku-latest"


def test_classify_action_skill_falls_back_to_keywords_on_invalid_output():
    engine = Engine(FakeDB())
    engine.client = FakeClient(['{"skill": "Banana"}'])
    campaign = {"hero_name": "Pip", "hero_sheet": {"level": 1, "ancestry": "Elf", "class": "Wizard"}}

    skill = engine._classify_action_skill(campaign, [], "I climb the wall.")

    assert skill == "Athletics"


def test_classify_action_skill_falls_back_to_keywords_on_error():
    engine = Engine(FakeDB())
    engine.client = FakeClient([RuntimeError("boom")])
    campaign = {"hero_name": "Pip", "hero_sheet": {"level": 1, "ancestry": "Elf", "class": "Wizard"}}

    skill = engine._classify_action_skill(campaign, [], "I sneak past the guard.")

    assert skill == "Stealth"


def test_get_action_dc_uses_classifier_model():
    engine = Engine(FakeDB())
    engine.client = FakeClient(["14"])
    campaign = {
        "hero_name": "Pip",
        "hero_sheet": {"level": 1, "ancestry": "Elf", "class": "Wizard"},
        "story_state": {},
    }

    dc = engine._get_action_dc(campaign, [], "I search the room.")

    assert dc == 14
    assert engine.client.calls[0]["model"] == "claude-3-5-haiku-latest"


def test_narrate_turn_uses_narrator_model_and_prompt():
    engine = Engine(FakeDB())
    engine.client = FakeClient(["Pip slips past the guard and reaches the old door."])

    result = engine._narrate_turn(
        "Context",
        "I sneak past the guard.",
        {"dc": 15, "degree": "success"},
        {"narration_cue": "Pip slips past the guard.", "state_delta": {"xp_change": 10}},
    )

    assert result.startswith("Pip slips")
    assert engine.client.calls[0]["model"] == "claude-sonnet-4-5"
    assert "system" in engine.client.calls[0]


def test_scene_title_from_resolution_is_short_and_prefers_structured_title():
    assert _scene_title_from_resolution({"scene_title": "The Harbor Escape With Extra Words"}, "Long text") == "The Harbor Escape With Extra Words"
    assert _scene_title_from_resolution({}, "You leap into the dark harbor water. The guards shout.") == "You leap into the dark harbor"
