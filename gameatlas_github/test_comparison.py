from pathlib import Path
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

import analytics as a
from comparison import exact_candidates, price_comparison


class ComparisonTests(unittest.TestCase):
    def test_ambiguous_titles_not_paired_and_editions_not_stripped(self):
        steam = pd.DataFrame(
            [
                {"id": "steam:1", "title": "Game", "title_key": "game"},
                {"id": "steam:2", "title": "Game Deluxe", "title_key": "game deluxe"},
            ]
        )
        ps = pd.DataFrame(
            [
                {"id": "ps:1", "title": "Game", "title_key": "game"},
                {"id": "ps:2", "title": "Game", "title_key": "game"},
            ]
        )
        self.assertTrue(exact_candidates(steam, ps).empty)
        ps = ps.iloc[:1]
        result = exact_candidates(steam, ps)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["id_steam"], "steam:1")
        blank = pd.DataFrame([{"id": "x", "title": "Unknown", "title_key": None}])
        self.assertTrue(exact_candidates(blank, blank).empty)

    def test_price_math_missing_currency_unknown_and_zero_base(self):
        left = {"price": 10.0, "currency": "USD", "price_eligible": True}
        right = {"price": 15.0, "currency": "USD", "price_eligible": True}
        self.assertEqual(
            price_comparison(left, right)["ps_relative_to_steam_pct"], 50.0
        )
        self.assertEqual(price_comparison(left, right)["difference_usd"], 5.0)
        for change in (
            {"price": None},
            {"currency": None},
            {"currency": "EUR"},
            {"price_eligible": False},
            {"price": float("nan")},
        ):
            self.assertIsNone(price_comparison(left, {**right, **change}))
        zero = price_comparison({**left, "price": 0}, right)
        self.assertEqual(zero["difference_usd"], 15.0)
        self.assertIsNone(zero["ps_relative_to_steam_pct"])
        self.assertEqual(price_comparison(left, left)["cheaper"], "Bərabər")

    def test_pair_confirmation_does_not_carry_to_another_candidate(self):
        steam, ps = a.load_platform("steam"), a.load_platform("playstation")
        candidates = exact_candidates(steam, ps)
        si, pi = steam.set_index("id"), ps.set_index("id")
        valid = [
            i
            for i, r in candidates.iterrows()
            if price_comparison(si.loc[r.id_steam], pi.loc[r.id_ps]) is not None
        ]
        self.assertGreater(len(valid), 1)
        self.assertFalse(candidates["title_key"].eq("resident evil 2").any())
        app = AppTest.from_file(
            str(Path(__file__).with_name("app.py")), default_timeout=30
        ).run()
        app.switch_page("views/compare.py").run()
        self.assertFalse(app.exception)
        app.selectbox(key="pair_candidate").set_value(valid[0]).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.checkbox[0].value)
        baseline_charts = len(app.get("plotly_chart"))
        self.assertGreaterEqual(baseline_charts, 7)
        app.checkbox[0].check().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), baseline_charts + 1)
        app.selectbox(key="pair_candidate").set_value(valid[1]).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.checkbox[0].value)
        self.assertEqual(len(app.get("plotly_chart")), baseline_charts)
        app.radio(key="pair_method").set_value("Əl ilə iki oyun seç").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.checkbox[0].value)


if __name__ == "__main__":
    unittest.main()
