import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import app
from backend.database import Database
from calligraphy.text.converter import ConversionUnavailableError, convert_text


class ScriptConversionTests(unittest.TestCase):
    def test_declared_engine_converts_both_directions_and_aliases(self):
        for target in ("trad", "zh-hant"):
            with self.subTest(target=target):
                self.assertEqual(convert_text("春眠不觉晓，处处闻啼鸟", target), "春眠不覺曉，處處聞啼鳥")
        for target in ("simp", "zh-hans"):
            with self.subTest(target=target):
                self.assertEqual(convert_text("明月松間照，清泉石上流", target), "明月松间照，清泉石上流")
        self.assertEqual(convert_text(""), "")
        self.assertEqual(convert_text("永"), "永")

    def test_qianli_and_polysemic_li_preserved_appropriately(self):
        # 「千里」依然是「千里」，不应误转为「千裏」；「万里」->「萬里」；「屋里」->「屋裏」
        self.assertEqual(convert_text("欲穷千里目，更上一层楼", "trad"), "欲窮千里目，更上一層樓")
        self.assertEqual(convert_text("千里之行，始于足下", "trad"), "千里之行，始於足下")
        self.assertEqual(convert_text("万里长征人未还", "trad"), "萬里長征人未還")
        self.assertEqual(convert_text("屋里有人", "trad"), "屋裏有人")

    def test_missing_dependency_is_not_a_successful_noop(self):
        with patch("calligraphy.text.converter.opencc", None):
            with self.assertRaisesRegex(ConversionUnavailableError, "opencc"):
                convert_text("春眠不觉晓", "trad")

    def test_invalid_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            convert_text("鸟", "invalid")

    def test_api_returns_explicit_unavailable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(f"sqlite:///{Path(directory) / 'test.db'}")
            with patch("backend.database._DB_INSTANCE", database), patch("calligraphy.text.converter.opencc", None):
                client = TestClient(app)
                response = client.post("/api/convert-script", json={"text": "鸟", "target": "trad"})
                self.assertEqual(response.status_code, 503)
                self.assertIn("opencc", response.json()["detail"])
                self.assertNotIn("text", response.json())

    def test_api_validates_target_and_accepts_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(f"sqlite:///{Path(directory) / 'test.db'}")
            with patch("backend.database._DB_INSTANCE", database):
                client = TestClient(app)
                for target in ("trad", "zh-hant"):
                    response = client.post("/api/convert-script", json={"text": "鸟", "target": target})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), {"text": "鳥", "target": target})
                response = client.post("/api/convert-script", json={"text": "鸟", "target": "invalid"})
                self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
