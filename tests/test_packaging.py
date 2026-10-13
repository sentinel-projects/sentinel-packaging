import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("packaging_tools", ROOT / "tools/packaging.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PackagingContract(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads((ROOT / "upstream.lock.json").read_text())

    def test_independent_source_recipes(self):
        outputs = module.recipes(self.lock)
        self.assertEqual(len(outputs), 3)
        manifest = json.loads(outputs[Path("flatpak/dev.sentinel.Sentinel.json")])
        source = manifest["modules"][0]["sources"][0]
        self.assertEqual(source["type"], "archive")
        self.assertEqual(source["sha256"], self.lock["source"]["sha256"])
        self.assertNotIn("../..", "".join(outputs.values()))

    def test_mutable_source_rejected(self):
        self.lock["source"]["url"] = self.lock["source"]["url"].rsplit("/", 1)[0] + "/main"
        with self.assertRaises(ValueError):
            module.validate(self.lock)

    def test_identity_and_version_guard(self):
        for key, value in (("numeric_version", "2.0.0"), ("app_id", "org.sentinel.Sentinel")):
            lock = copy.deepcopy(self.lock)
            lock[key] = value
            with self.assertRaises(ValueError):
                module.validate(lock)

    def test_binary_missing_has_no_partial_output(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "new"
            with self.assertRaises(ValueError):
                module.render(self.lock, out, True)
            self.assertFalse(out.exists())

    def test_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            marker = Path(root) / "keep"
            marker.write_text("preserve")
            with self.assertRaises(FileExistsError):
                module.render(self.lock, root)
            self.assertEqual(marker.read_text(), "preserve")

    def test_zero_checksum_rejected(self):
        self.lock["source"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            module.validate(self.lock)

    def test_corrupt_archive_rejected(self):
        with tempfile.NamedTemporaryFile() as archive:
            archive.write(b"corrupt")
            archive.flush()
            with self.assertRaises(ValueError):
                module.verify_source(self.lock, archive.name)

    def test_binary_contract_and_render(self):
        # Synthetic fixtures test rendering only; they are not verified release artifacts.
        for kind in ("dmg", "exe", "msi"):
            self.lock["binary_artifacts"][kind] = dict(
                url="https://github.com/sentinel-projects/sentinel/releases/download/v1.0.0-rc.8/Test." + kind,
                sha256="ab" * 32, version="1.0.0-rc.8", upstream_commit=self.lock["commit"])
        self.assertEqual(len(module.recipes(self.lock, True)), 7)
        self.lock["binary_artifacts"]["dmg"]["url"] = "https://github.com/sentinel-projects/sentinel/releases/latest/Test.dmg"
        with self.assertRaises(ValueError):
            module.recipes(self.lock, True)

if __name__ == "__main__":
    unittest.main()
