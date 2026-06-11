import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    def test_registry_metadata_declares_comfy_constraints(self):
        tool_comfy = self.pyproject["tool"]["comfy"]

        self.assertEqual(tool_comfy["PublisherId"], "oshtz")
        self.assertIn("requires-comfyui", tool_comfy)

    def test_dependencies_do_not_install_comfy_runtime_stack(self):
        dependencies = set(self.pyproject["project"]["dependencies"])

        self.assertNotIn("torch", dependencies)
        self.assertFalse(any(dep.startswith("boto3") for dep in dependencies))

    def test_comfyignore_excludes_nested_release_artifact(self):
        comfyignore = (ROOT / ".comfyignore").read_text(encoding="utf-8").splitlines()

        self.assertIn("node.zip", comfyignore)


if __name__ == "__main__":
    unittest.main()
