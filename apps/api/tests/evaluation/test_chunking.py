from investigation_engine.evaluation.answers import load_northwind_questions
from investigation_engine.evaluation.chunking import CONFIGS, check_facts


def test_every_key_fact_is_in_the_northwind_corpus() -> None:
    check_facts(load_northwind_questions())


def test_configs_compare_both_strategies_at_each_size() -> None:
    pairs = {(config.strategy, config.max_words) for config in CONFIGS}

    assert pairs == {(s, n) for s in ("fixed", "structured") for n in (60, 120, 200)}
