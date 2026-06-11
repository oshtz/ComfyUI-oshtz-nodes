import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "oshtz_nodes_testpkg"


def load_llm_module():
    sys.modules.setdefault("torch", types.SimpleNamespace(Tensor=object))

    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE_NAME] = package

    utils_spec = importlib.util.spec_from_file_location(f"{PACKAGE_NAME}.utils", ROOT / "utils.py")
    utils_module = importlib.util.module_from_spec(utils_spec)
    sys.modules[utils_spec.name] = utils_module
    utils_spec.loader.exec_module(utils_module)

    nodes_package = types.ModuleType(f"{PACKAGE_NAME}.nodes")
    nodes_package.__path__ = [str(ROOT / "nodes")]
    sys.modules[f"{PACKAGE_NAME}.nodes"] = nodes_package

    llm_spec = importlib.util.spec_from_file_location(
        f"{PACKAGE_NAME}.nodes.llm_aio",
        ROOT / "nodes" / "llm_aio.py",
    )
    llm_module = importlib.util.module_from_spec(llm_spec)
    sys.modules[llm_spec.name] = llm_module
    llm_spec.loader.exec_module(llm_module)
    return llm_module


class LLMAIONodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.llm = load_llm_module()

    def test_input_types_does_not_fetch_openrouter(self):
        with mock.patch.object(self.llm.requests, "get", side_effect=AssertionError("network call")):
            input_types = self.llm.LLMAIONode.INPUT_TYPES()

        model_options = input_types["required"]["model"][0]
        self.assertIn("gpt-4o", model_options)
        self.assertIn("openai/gpt-4o", model_options)

    def test_secret_resolution_prefers_widget_value(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            self.assertEqual(self.llm._resolve_secret(" widget-key ", "OPENAI_API_KEY"), "widget-key")

    def test_secret_resolution_uses_environment_fallback(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-openrouter"}):
            self.assertEqual(self.llm._resolve_secret("", "OPENROUTER_API_KEY"), "env-openrouter")

    def test_model_override_selects_typed_model(self):
        node = self.llm.LLMAIONode()
        with mock.patch.object(self.llm, "OpenAIApi") as api_cls:
            api_cls.return_value.chat.return_value = "ok"
            result = node.process(
                api_type="openai",
                model="gpt-4o",
                max_token=8,
                temperature=0,
                prompt="hello",
                seed=0,
                model_override="custom-model",
                openai_api_key="key",
            )

        self.assertEqual(result, ("ok",))
        config = api_cls.return_value.chat.call_args.args[1]
        self.assertEqual(config.model, "custom-model")


if __name__ == "__main__":
    unittest.main()
