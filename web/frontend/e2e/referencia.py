"""Respostas de referência da interface Python segura para o teste de integração.

Lê registros sintéticos hipotéticos em JSON pela entrada padrão. Não acessa datasets.
"""
import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'src'))

from final5.validation import SafeClassifier  # noqa: E402

classificador = SafeClassifier()
print(json.dumps([classificador.classify(r) for r in json.load(sys.stdin)], ensure_ascii=False))
