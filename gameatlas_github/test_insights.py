from pathlib import Path
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

import analytics as a
from insights import (
    basket_summary,
    budget_distribution,
    genre_overlap,
    primary_genres,
    ranked_games,
    support_profile,
    year_profile,
)


class InsightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.steam = a.load_platform("steam")
        cls.ps = a.load_platform("playstation")

    def test_primary_groups_reconcile_without_changing_membership(self):
        counts = primary_genres(self.steam).set_index("categories")["games"]
        self.assertEqual(int(counts.sum()), 6100)
        self.assertEqual(int(counts["horror"]), 794)
        membership = a.genre_stats(self.steam).set_index("categories")["games"]
        self.assertEqual(int(membership["horror"]), 1000)
        self.assertEqual(int(membership.sum()), 24078)

    def test_budget_boundaries_unknowns_and_empty_denominator(self):
        rows = pd.DataFrame(
            {
                "price": [0, 10, 10.01, 20, 40, 60, 60.01, None, 1],
                "price_eligible": [True] * 7 + [False, True],
                "currency": ["USD"] * 8 + [None],
            }
        )
        bands = budget_distribution(rows)
        self.assertEqual(bands["games"].tolist(), [1, 1, 2, 1, 1, 1])
        self.assertAlmostEqual(bands["share"].sum(), 100)
        self.assertEqual(int(budget_distribution(self.steam)["games"].sum()), 5715)
        empty = budget_distribution(rows.iloc[0:0])
        self.assertTrue(empty["share"].isna().all())
        self.assertEqual(int(empty["games"].sum()), 0)

    def test_jaccard_uses_unique_ids_and_never_invents_empty_similarity(self):
        frame = pd.DataFrame(
            {
                "id": ["a", "a", "b", "c"],
                "categories": [["A", "B", "B"], ["A"], ["A"], ["B"]],
            }
        )
        counts, similarity = genre_overlap(frame, ["A", "B", "Empty"])
        self.assertEqual(counts.loc["A", "B"], 1)
        self.assertAlmostEqual(similarity.loc["A", "B"], 100 / 3)
        self.assertEqual(similarity.loc["A", "A"], 100)
        self.assertTrue(pd.isna(similarity.loc["Empty", "Empty"]))

    def test_small_sample_rating_is_shrunk_and_zero_strength_is_native(self):
        rows = pd.DataFrame(
            {
                "id": ["low", "high", "base", "none"],
                "rating": [100, 100, 0, None],
                "votes": [1, 1000, 200, 0],
                "rating_eligible": [True, True, True, False],
            }
        )
        ranked = ranked_games(rows, minimum_votes=0).set_index("id")
        self.assertGreater(
            ranked.loc["high", "weighted_rating"], ranked.loc["low", "weighted_rating"]
        )
        self.assertNotIn("none", ranked.index)
        native = ranked_games(rows, minimum_votes=0, strength=0)
        self.assertTrue(native["weighted_rating"].equals(native["rating"]))
        self.assertTrue(ranked_games(rows.iloc[0:0]).empty)

    def test_basket_sum_is_partial_and_platform_ids_are_distinct(self):
        rows = pd.DataFrame(
            {
                "id": ["steam:a", "steam:a", "ps:a", "unknown"],
                "price": [10, 10, 15, None],
                "price_eligible": [True, True, True, False],
                "currency": ["USD", "USD", "USD", None],
            }
        )
        self.assertEqual(
            basket_summary(rows),
            {"games": 3, "priced": 2, "unknown": 1, "observed_total": 25.0},
        )
        self.assertIsNone(basket_summary(rows.iloc[3:])["observed_total"])

    def test_support_keeps_unknown_and_years_have_separate_denominators(self):
        sample = self.steam.iloc[:3].copy()
        sample["is_windows"] = [True, False, None]
        support = support_profile(sample, "steam")
        self.assertEqual(
            support[support["support"].eq("Windows")]["games"].tolist(), [1, 1, 1]
        )
        years = year_profile(self.steam)
        self.assertEqual(
            int(years["games"].sum()), int(self.steam["year"].notna().sum())
        )
        self.assertTrue((years["price_n"] <= years["games"]).all())
        self.assertTrue((years["rating_n"] <= years["games"]).all())

    def test_discovery_minimum_price_bounds_for_both_platforms(self):
        app = AppTest.from_file(
            str(Path(__file__).with_name("app.py")), default_timeout=40
        ).run()
        app.switch_page("views/lab.py").run()
        for platform, label, frame in (
            ("steam", "Steam", self.steam),
            ("playstation", "PS Store", self.ps),
        ):
            with self.subTest(platform=platform):
                app.radio(key="lab_platform").set_value(label).run()
                self.assertEqual(app.number_input(key="lab_min_price_" + platform).value, 0)
                app.number_input(key="lab_votes_" + platform).set_value(0)
                app.slider(key="lab_rating_" + platform).set_value(0.0)
                app.number_input(key="lab_min_price_" + platform).set_value(10.0).run()
                self.assertFalse(app.exception)
                self.assertFalse(app.warning)
                prices = app.dataframe[0].value["USD"]
                self.assertFalse(prices.empty)
                self.assertTrue(prices.between(10.0, 20.0).all())
                # Equal bounds must retain games priced exactly at that amount.
                boundary = float(frame.loc[
                    frame["rating_eligible"] & frame["price_eligible"]
                    & frame["currency"].eq("USD") & frame["votes"].gt(0)
                    & frame["price"].between(10.0, 20.0), "price"
                ].iloc[0])
                app.number_input(key="lab_min_price_" + platform).set_value(boundary)
                app.number_input(key="lab_budget_" + platform).set_value(boundary).run()
                self.assertFalse(app.exception)
                self.assertFalse(app.warning)
                self.assertFalse(app.dataframe[0].value.empty)
                self.assertTrue(app.dataframe[0].value["USD"].eq(boundary).all())
                app.number_input(key="lab_min_price_" + platform).set_value(boundary + 1).run()
                self.assertFalse(app.exception)
                self.assertTrue(any("Minimum qiymət maksimum qiymətdən" in w.value for w in app.warning))
                self.assertFalse(any(x.key == "lab_picks_" + platform for x in app.multiselect))
                app.number_input(key="lab_min_price_" + platform).set_value(0.0)
                app.number_input(key="lab_budget_" + platform).set_value(20.0).run()
                self.assertFalse(app.warning)
        app.radio(key="lab_platform").set_value("Steam").run()
        app.number_input(key="lab_min_price_steam").set_value(5.0).run()
        app.radio(key="lab_platform").set_value("PS Store").run()
        self.assertEqual(app.number_input(key="lab_min_price_playstation").value, 0.0)

    def test_ui_has_only_real_genre_modes_and_collection_can_be_removed(self):
        app = AppTest.from_file(
            str(Path(__file__).with_name("app.py")), default_timeout=40
        ).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="home_genre_basis").options, [
            "Hər oyunu bir qrupda say", "Bütün janr və etiketlərdə say"
        ])
        app.selectbox(key="home_genre_basis").set_value("Bütün janr və etiketlərdə say").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.warning)
        for previous_choice in ("Demo · nümunə görünüş", "Demo dizayn · süni indeks"):
            app = AppTest.from_file(
                str(Path(__file__).with_name("app.py")), default_timeout=40
            )
            app.session_state["home_genre_basis"] = previous_choice
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox(key="home_genre_basis").value, "Hər oyunu bir qrupda say")
        app.switch_page("views/lab.py").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertGreaterEqual(len(app.get("plotly_chart")), 8)
        pick = app.multiselect(key="lab_picks_steam").options[0].rsplit(" · ", 1)[1]
        app.multiselect(key="lab_picks_steam").set_value([pick]).run()
        app.button(key="lab_add").click().run()
        self.assertFalse(app.exception)
        saved = app.session_state["atlas_wishlist"]
        self.assertEqual(len(saved), 1)
        remove = app.multiselect(key="lab_remove").options[0].rsplit(" · ", 1)[1]
        app.multiselect(key="lab_remove").set_value([remove]).run()
        app.button(key="lab_remove_button").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["atlas_wishlist"], [])
        app.radio(key="lab_platform").set_value("PS Store").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        app.number_input(key="lab_budget_playstation").set_value(0).run()
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
