import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_NAME = "oshtz_lora_test_module"


class FolderPathsStub(types.SimpleNamespace):
    def __init__(self):
        super().__init__()
        self.requested = []

    def get_path_filename(self, value):
        return value.replace("\\", "/").split("/")[-1]

    def get_full_path(self, category, name):
        self.requested.append((category, name))
        return f"/fake/{category}/{name}" if name == "style.safetensors" else None

    def get_filename_list(self, category):
        return ["style.safetensors"] if category == "loras" else []


class LoraLoaderStub:
    calls = []

    def load_lora(self, model, clip, lora_name, strength_model, strength_clip):
        self.calls.append((model, clip, lora_name, strength_model, strength_clip))
        return (f"{model}+{lora_name}", f"{clip}+{lora_name}")


def load_lora_module():
    folder_paths_stub = FolderPathsStub()
    sys.modules["folder_paths"] = folder_paths_stub
    sys.modules["nodes"] = types.SimpleNamespace(LoraLoader=LoraLoaderStub)
    sys.modules.pop("server", None)

    spec = importlib.util.spec_from_file_location(MODULE_NAME, ROOT / "nodes" / "lora_switcher_dynamic.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    module.folder_paths = folder_paths_stub
    module.LoraLoader = LoraLoaderStub
    LoraLoaderStub.calls = []
    return module


class LoraSwitcherDynamicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lora = load_lora_module()

    def setUp(self):
        self.lora.LoraLoader.calls = []

    def test_parse_lora_config_normalizes_strengths(self):
        parsed = self.lora.parse_lora_config('[{"lora":"style.safetensors","strength":"0.75"}]')

        self.assertEqual(
            parsed,
            [{"lora": "style.safetensors", "strength_model": 0.75, "strength_clip": 0.75}],
        )

    def test_parse_lora_config_ignores_invalid_entries(self):
        with mock.patch("builtins.print"):
            parsed = self.lora.parse_lora_config('[{"lora":"bad.safetensors","strength":"nope"}, 3]')

        self.assertEqual(parsed, [])

    def test_select_lora_config_uses_one_based_index(self):
        configs = [
            {"lora": "a.safetensors", "strength_model": 1.0, "strength_clip": 1.0},
            {"lora": "b.safetensors", "strength_model": 0.5, "strength_clip": 0.5},
        ]

        self.assertEqual(self.lora.select_lora_config(configs, 2)["lora"], "b.safetensors")
        self.assertIsNone(self.lora.select_lora_config(configs, 0))
        with mock.patch("builtins.print"):
            self.assertIsNone(self.lora.select_lora_config(configs, "bad"))

    def test_apply_lora_loads_selected_config(self):
        node = self.lora.LoraSwitcherDynamic()

        result = node.apply_lora(
            "model",
            "clip",
            1,
            lora_config='[{"lora":"subdir/style.safetensors","strength_model":0.8,"strength_clip":0.6}]',
        )

        self.assertEqual(result, ("model+style.safetensors", "clip+style.safetensors"))
        self.assertEqual(
            self.lora.LoraLoader.calls,
            [("model", "clip", "style.safetensors", 0.8, 0.6)],
        )


if __name__ == "__main__":
    unittest.main()
