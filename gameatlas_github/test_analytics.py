import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import analytics as a


class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.steam = a.load_platform("steam")
        cls.ps = a.load_platform("playstation")
        cls.before = {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for platform in a.PLATFORMS
            for p in a.paths(platform)
        }

    @classmethod
    def tearDownClass(cls):
        for name, sha in cls.before.items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != sha:
                raise AssertionError("Application modified a dataset or manifest")

    def test_real_counts_and_metric_denominators(self):
        steam = a.summary(self.steam)
        ps = a.summary(self.ps)
        self.assertEqual(
            (
                steam["games"],
                steam["free"],
                steam["unknown_price"],
                steam["usd_price_n"],
                steam["rated"],
            ),
            (6100, 365, 20, 5715, 6067),
        )
        self.assertEqual(
            (
                ps["games"],
                ps["free"],
                ps["unknown_price"],
                ps["usd_price_n"],
                ps["rated"],
            ),
            (1500, 111, 67, 1433, 1477),
        )
        self.assertEqual(ps["median_price_n"], 1322)
        self.assertEqual(int(self.ps["rating"].isna().sum()), 23)

    def test_unknowns_are_retained_and_numeric_filters_exclude_them(self):
        unknown = a.filter_games(self.steam, statuses=["unknown"])
        self.assertEqual(len(unknown), 20)
        self.assertIsNone(a.summary(unknown)["median_paid_price"])
        self.assertTrue(a.price_rows(unknown).empty)
        currencyless_free = self.steam[self.steam["status"].eq("free")]
        self.assertEqual(len(currencyless_free), 365)
        self.assertTrue(a.filter_games(currencyless_free, price_range=(0, 100)).empty)
        self.assertTrue(
            a.filter_games(
                self.ps[self.ps["rating_status"].eq("unrated")], minimum_rating=0
            ).empty
        )

    def test_genres_never_duplicate_main_rows(self):
        selected = a.filter_games(self.steam, genres=["action", "rpg"])
        self.assertTrue(selected["id"].is_unique)
        self.assertEqual(
            len(selected),
            int(
                self.steam["categories"]
                .map(lambda tags: bool({"action", "rpg"}.intersection(tags)))
                .sum()
            ),
        )
        stats = a.genre_stats(self.steam)
        self.assertEqual(int(stats["games"].sum()), 24078)
        ps_stats = a.genre_stats(self.ps)
        self.assertEqual(int(ps_stats["games"].sum()), 2367)
        self.assertEqual(int((~self.ps["categories"].map(bool)).sum()), 16)

    def test_filters_literal_search_support_and_empty_state(self):
        self.assertTrue(
            a.filter_games(
                self.steam, query="[no game has this literal substring]"
            ).empty
        )
        both = a.filter_games(self.ps, support="PS4 və PS5", platform="playstation")
        self.assertEqual(len(both), 439)
        sample = pd.DataFrame([dict(self.ps.iloc[0]), dict(self.ps.iloc[1])])
        sample.loc[sample.index[0], "votes"] = 0
        sample.loc[sample.index[0], "rating_eligible"] = False
        sample.loc[sample.index[0], "rating"] = None
        self.assertEqual(len(a.filter_games(sample, minimum_votes=1)), 1)
        self.assertIsNone(a.summary(self.steam.iloc[0:0])["median_rating"])

    def test_corrupted_data_cannot_be_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, manifest = a.paths("steam", root)
            data.parent.mkdir(parents=True)
            data.write_text("[]", encoding="utf-8")
            manifest.write_text(
                '{"platform":"steam","files_sha256":{"games_clean.json":"wrong"},"games":0}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "fayl izi"):
                a.load_platform("steam", root)
        with self.assertRaises(ValueError):
            a.strict_json('{"a":1,"a":2}')
        with self.assertRaises(ValueError):
            a.strict_json("[NaN]")

    def test_streamlit_platforms_filters_empty_and_quality_pages(self):
        app = AppTest.from_file(
            str(Path(__file__).with_name("app.py")), default_timeout=30
        ).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(any("6,100" in m.value for m in app.markdown))
        app.switch_page("views/detail.py").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "6,100")
        self.assertEqual(len(app.get("plotly_chart")), 10)
        self.assertEqual(len(app.sidebar.text_input), 0)
        self.assertTrue(any(x.label == "Oyunları filtrlə" and x.proto.expanded for x in app.expander))
        app.multiselect(key="statuses_steam").set_value(["Naməlum"]).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "20")
        self.assertEqual(app.metric[1].value, "—")
        app.text_input(key="query_steam").set_value("NO_SUCH_GAME_987654321").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0")
        self.assertTrue(any("tapılmadı" in x.value for x in app.info))
        app.button(key="reset_steam").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "6,100")
        self.assertEqual(app.text_input(key="query_steam").value, "")
        self.assertEqual(app.multiselect(key="statuses_steam").value, [])
        self.assertFalse(app.warning)
        app.checkbox(key="price_active_steam").check().run()
        app.slider(key="price_steam").set_value((0.0, 10.0)).run()
        app.checkbox(key="year_active_steam").check().run()
        app.checkbox(key="rating_active_steam").check().run()
        self.assertFalse(app.exception)
        self.assertLess(int(app.metric[0].value.replace(",", "")), 6100)
        app.button(key="reset_steam").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "6,100")
        for prefix in ("price_active", "rating_active", "year_active"):
            self.assertFalse(app.checkbox(key=prefix + "_steam").value)
        self.assertFalse(app.warning)
        app.selectbox(key="detail_platform").set_value("PS Store").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "1,500")
        app.checkbox(key="rating_active_playstation").check().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "1,477")
        for kind in (
            "Janrlara görə qiymətlər",
            "İl və janr üzrə oyun sayı",
            "Cihazlara görə oyun sayı",
            "Nəşriyyatlara görə oyunlar",
        ):
            app.selectbox(key="chart_builder").set_value(kind).run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
        app.switch_page("views/quality.py").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe), 2)
        with patch.dict(
            "os.environ",
            {
                "GAME_ANALYTICS_PROJECT": str(
                    Path(tempfile.gettempdir()) / "game_atlas_missing_987654321"
                )
            },
        ):
            missing = AppTest.from_file(
                str(Path(__file__).with_name("app.py")), default_timeout=30
            ).run()
            self.assertFalse(missing.exception)
            self.assertEqual(len(missing.error), 1)


if __name__ == "__main__":
    unittest.main()
