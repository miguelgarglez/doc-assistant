import os

import pytest
from invoice_battery_support import (
    CASES,
    Case,
    assert_blocks_grounded,
    assert_no_false_answer,
)

from doc_assistant.bootstrap import ask_invoices
from doc_assistant.infra.models.http import HttpLLM

LIVE = os.environ.get("DOC_ASSISTANT_LIVE_LLM")


@pytest.mark.skipif(not LIVE, reason="DOC_ASSISTANT_LIVE_LLM not set")
@pytest.mark.parametrize("case", CASES, ids=[c.question for c in CASES])
def test_battery_with_a_real_model(battery_config, case: Case):
    assert LIVE is not None
    llm = HttpLLM(LIVE.rstrip("/") + "/v1/chat/completions", "llm-local", 120)
    result = ask_invoices(battery_config, case.question, llm=llm)
    assert result is not None
    assert_no_false_answer(case.question, result)
    assert_blocks_grounded(result)
    if result["ok"]:
        assert case.kind == "answer", f"answered a {case.kind} case: {result['answer']}"
        for piece in case.want if case.live_want is None else case.live_want:
            assert piece in result["answer"], f"expected {piece!r} in {result['answer']!r}"
        for piece in case.forbid:
            assert piece not in result["answer"], f"{piece!r} in {result['answer']!r}"
