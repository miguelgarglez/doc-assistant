from invoice_battery_support import CASES


def test_battery_has_no_false_answer_and_covers_every_intent():
    kinds = {c.kind for c in CASES}
    intents = {c.plan["intent"] for c in CASES}
    assert kinds == {"answer", "clarify", "refuse"}
    assert intents == {"valor", "lista", "contar", "sumar"}
    assert len(CASES) >= 30
