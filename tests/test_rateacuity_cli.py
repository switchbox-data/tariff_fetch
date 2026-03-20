from tariff_fetch._cli.rateacuity import _match_rateacuity_choice, _match_rateacuity_choices


def test_match_rateacuity_choice_compares_case_insensitively():
    assert (
        _match_rateacuity_choice(
            query="con ed",
            choices=[
                "Pacific Gas and Electric Company",
                "Consolidated Edison Company of New York",
            ],
            category="Utility",
        )
        == "Consolidated Edison Company of New York"
    )


def test_match_rateacuity_choices_deduplicates_repeated_matches():
    assert _match_rateacuity_choices(
        queries=["residential service", "RESIDENTIAL"],
        choices=[
            "General Service Demand",
            "Residential Service",
        ],
        category="Tariff",
    ) == ["Residential Service"]
