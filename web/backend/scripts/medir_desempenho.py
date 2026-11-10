"""Mede carga, memória e latência da API com entradas sintéticas (sem dados de 2025)."""
import json
from pathlib import Path
import statistics
import sys
import time

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT = Path(__file__).resolve().parents[3]


def main():
    processo = psutil.Process()
    mem = lambda: round(processo.memory_info().rss/1024**2)
    inicio_mem = mem()
    t0 = time.perf_counter()
    from fastapi.testclient import TestClient
    from app.config import Settings
    from app.main import create_app
    t1 = time.perf_counter()
    app = create_app(Settings(rate_limit_per_minute=1_000_000))
    with TestClient(app) as c:
        carga = time.perf_counter()-t1
        corpo = {'mes': 5, 'dia_semana': 2, 'tipo_local': 'VIA PÚBLICA', 'bairro': 'BELA VISTA'}
        c.post('/api/classify', json=corpo)  # primeira chamada traça o grafo
        duracoes = []
        for i in range(300):
            antes = time.perf_counter()
            r = c.post('/api/classify', json=corpo | {'mes': i % 12+1, 'dia_semana': i % 7})
            duracoes.append((time.perf_counter()-antes)*1000)
            assert r.status_code == 200
        tamanhos = {rota: len(c.get(rota, headers={'Accept-Encoding': 'gzip'}).content)
                    for rota in ['/api/options', '/api/statistics', '/api/methodology']}
        duracoes.sort()
        saida = {
            'observacao': 'Medido localmente em CPU, no processo da aplicação, sem rede; valores variam por máquina.',
            'importacao_api_s': round(t1-t0, 2), 'carga_modelo_e_inicializacao_s': round(carga, 2),
            'memoria_inicial_mb': inicio_mem, 'memoria_apos_carga_e_300_classificacoes_mb': mem(),
            'classificacao_ms': {'n': 300, 'mediana': round(statistics.median(duracoes), 1),
                                 'p95': round(duracoes[int(.95*len(duracoes))], 1), 'max': round(duracoes[-1], 1)},
            'corpo_descomprimido_bytes': tamanhos,
        }
    destino = ROOT/'reports/etapa6/desempenho.json'
    destino.write_text(json.dumps(saida, ensure_ascii=False, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(saida, ensure_ascii=False))


if __name__ == '__main__':
    main()
