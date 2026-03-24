import requests
import time
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests.exceptions as req_exc
import matplotlib.pyplot as plt
from datetime import datetime
import os

URL_POST = "http://localhost:30090/transactions"
URL_GET = "http://localhost:30090/transactions"

HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
}

PAYLOAD = {
    "account_id": 1,
    "type": "INCOME",
    "amount": 5000,
    "description": "string",
    "occurred_at": "2025-10-14T22:19:38.572Z",
    "category": "trabalho"
}

TIMEOUT = 20

def send_post(session):
    start = time.time()
    try:
        response = session.post(URL_POST, headers=HEADERS, json=PAYLOAD, timeout=TIMEOUT)
        elapsed = time.time() - start
        body_snippet = response.text.replace('\n', ' ')[:200]
        return {
            "method": "POST",
            "elapsed": elapsed,
            "timestamp": time.time(),
            "status": response.status_code,
            "body": body_snippet,
        }
    except req_exc.ReadTimeout as e:
        return {"method": "POST", "elapsed": None, "status": "error", "error": f"ReadTimeout: {e}"}
    except req_exc.ConnectionError as e:
        return {"method": "POST", "elapsed": None, "status": "error", "error": f"ConnectionError: {e}"}
    except Exception as e:
        return {"method": "POST", "elapsed": None, "status": "error", "error": str(e)}


def send_get(session):
    start = time.time()
    try:
        response = session.get(URL_GET, headers=HEADERS, timeout=TIMEOUT)
        elapsed = time.time() - start
        body_snippet = response.text.replace('\n', ' ')[:200]
        return {
            "method": "GET",
            "elapsed": elapsed,
            "timestamp": time.time(),
            "status": response.status_code,
            "body": body_snippet,
        }
    except req_exc.ReadTimeout as e:
        return {"method": "GET", "elapsed": None, "status": "error", "error": f"ReadTimeout: {e}"}
    except req_exc.ConnectionError as e:
        return {"method": "GET", "elapsed": None, "status": "error", "error": f"ConnectionError: {e}"}
    except Exception as e:
        return {"method": "GET", "elapsed": None, "status": "error", "error": str(e)}


def load_test(total_requests=300, duration_minutes=10, max_workers=40):
    total_seconds = int(duration_minutes * 60)
    start_time = time.time()

    base = total_requests // total_seconds
    remainder = total_requests % total_seconds

    print(f"🚀 Iniciando teste: {total_requests} requisições em {duration_minutes} minutos ({total_seconds}s) — média {total_requests/total_seconds:.2f} req/s")

    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]) 
    adapter = HTTPAdapter(max_retries=retries, pool_connections=max_workers, pool_maxsize=max_workers)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for sec in range(total_seconds):
            to_send = base + (1 if sec < remainder else 0)
            for i in range(to_send):
                if (sec + i) % 2 == 0:
                    futures.append(executor.submit(send_post, session))
                else:
                    futures.append(executor.submit(send_get, session))

            elapsed = time.time() - start_time
            print(f"{int(elapsed)}s -> sending {to_send} requests (total submitted so far: {len(futures)})")

            time_to_next = (start_time + sec + 1) - time.time()
            if time_to_next > 0:
                time.sleep(time_to_next)

    results = []
    for fut in as_completed(futures):
        try:
            res = fut.result()
        except Exception as e:
            res = {"method": "UNKNOWN", "elapsed": None, "status": "error", "error": str(e)}

        if res.get("status") == "error":
            print(f"{res.get('method')} -> error: {res.get('error')}")
        else:
            print(f"{res.get('method')} -> status={res.get('status')} time={res.get('elapsed'):.4f}s body='{res.get('body')}'")

        results.append(res)

    tempos = [r["elapsed"] for r in results if r.get("elapsed") is not None]
    timestamps = [r.get("timestamp") for r in results if r.get("timestamp") is not None]
    status = [r["status"] for r in results]

    sucesso = len([s for s in status if s == 200 or s == 201])
    falha = len([s for s in status if s != 200 and s != 201 and s != "error"]) + len([s for s in status if s == "error"])

    media = mean(tempos) if tempos else 0

    throughput = [0] * int(duration_minutes)
    latency_per_minute = [[] for _ in range(int(duration_minutes))]

    for r in results:
        ts = r.get("timestamp")
        elapsed = r.get("elapsed")
        if ts is None:
            continue
        minute_idx = int((ts - start_time) // 60)
        if 0 <= minute_idx < int(duration_minutes):
            throughput[minute_idx] += 1
            if elapsed is not None:
                latency_per_minute[minute_idx].append(elapsed)

    avg_latency_per_minute = [mean(lst) if lst else 0 for lst in latency_per_minute]

    total_responses = len(results)
    total_attempted = len(futures)
    success_count = sucesso
    failure_count = falha
    success_rate = (success_count / total_responses) * 100.0 if total_responses > 0 else 0.0
    error_rate = (failure_count / total_responses) * 100.0 if total_responses > 0 else 0.0

    total_test_seconds = int(duration_minutes * 60)
    overall_rps = (total_responses / total_test_seconds) if total_test_seconds > 0 else 0.0

    tempos_clean = [float(t) for t in tempos if t is not None]
    if tempos_clean:
        latency_stats = {
            'count': len(tempos_clean),
            'mean': float(mean(tempos_clean)),
            'min': float(min(tempos_clean)),
            'max': float(max(tempos_clean)),
            'p50': float(np.percentile(tempos_clean, 50)),
            'p90': float(np.percentile(tempos_clean, 90)),
            'p95': float(np.percentile(tempos_clean, 95)),
            'p99': float(np.percentile(tempos_clean, 99)),
        }
    else:
        latency_stats = {
            'count': 0,
            'mean': 0.0,
            'min': 0.0,
            'max': 0.0,
            'p50': 0.0,
            'p90': 0.0,
            'p95': 0.0,
            'p99': 0.0,
        }

    structured = {
        'test': {
            'total_attempted': int(total_attempted),
            'total_responses': int(total_responses),
            'duration_minutes': int(duration_minutes),
            'duration_seconds': int(total_test_seconds),
            'overall_rps': float(overall_rps),
        },
        'counts': {
            'success': int(success_count),
            'failure': int(failure_count),
            'success_rate_percent': float(success_rate),
            'error_rate_percent': float(error_rate),
        },
        'latency': latency_stats,
        'throughput_per_minute': [int(v) for v in throughput],
        'avg_latency_per_minute': [float(v) for v in avg_latency_per_minute],
    }

    try:
        with open('resultados_structured.json', 'w', encoding='utf-8') as jf:
            json.dump(structured, jf, ensure_ascii=False, indent=2)
        print("✅ Estrutura de resultados salva em 'results_structured.json'")
    except Exception as e:
        print(f"⚠️ Não foi possível salvar resultados estruturados: {e}")

        print("✅ Teste concluído. Resultados salvos em 'results_structured.json'.")

    return structured

if __name__ == "__main__":
    results_struct = load_test(total_requests=30000, duration_minutes=10, max_workers=40)
    if isinstance(results_struct, dict):
        print('\n--- Resumo Estruturado ---')
        print(f"Total respostas: {results_struct['test']['total_responses']}")
        print(f"Sucessos: {results_struct['counts']['success']} ({results_struct['counts']['success_rate_percent']:.2f}%)")
        print(f"Erros: {results_struct['counts']['failure']} ({results_struct['counts']['error_rate_percent']:.2f}%)")
        print(f"Latência p95: {results_struct['latency']['p95']:.4f} s")
