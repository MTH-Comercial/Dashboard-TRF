"""Teste de inicialização real do app, além dos testes de sintaxe e funções."""
import os
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class StreamlitStartupTest(unittest.TestCase):
    def test_app_starts_and_shows_demo_login_without_exceptions(self):
        # O ambiente de testes jamais usa a conta Google ou as senhas reais.
        previous = os.environ.get("TRANSFORMA_DEMO")
        os.environ["TRANSFORMA_DEMO"] = "1"
        try:
            app = AppTest.from_file(
                str(Path(__file__).resolve().parents[1] / "app.py"),
                default_timeout=30,
            ).run()
            self.assertEqual(
                len(app.exception), 0,
                "Erro no startup Streamlit: " + "; ".join(
                    str(e.message) for e in app.exception
                ),
            )
        finally:
            if previous is None:
                os.environ.pop("TRANSFORMA_DEMO", None)
            else:
                os.environ["TRANSFORMA_DEMO"] = previous


if __name__ == "__main__":
    unittest.main()
