import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict
from datetime import datetime
import os


MONOLITICO_BASE = "http://localhost:55111"

MICROSERVICES_ACCOUNTS = "http://localhost:62371"
MICROSERVICES_TRANSACTIONS = "http://localhost:30090"

TRANSACTION_PAYLOAD = {
    "account_id": 1,
    "type": "INCOME",
    "amount": 5000,
    "description": "Teste de carga gradual",
    "occurred_at": "2025-10-14T22:19:38.572Z",
    "category": "trabalho"
}


LOAD_PHASES = [
    (15000, 1)
]

MAX_WORKERS = 300  
TIMEOUT = 5 


def send_request(session, endpoint_name, endpoint_url, request_id, phase_num):
    start = time.time()
    try:
        response = session.get(endpoint_url, timeout=TIMEOUT)
        elapsed = time.time() - start
        return {
            "id": request_id,
            "phase": phase_num,
            "endpoint": endpoint_name,
            "status": response.status_code,
            "elapsed": elapsed,
            "timestamp": time.time(),
            "success": response.status_code in [200, 201],
            "error": None
        }
    except requests.exceptions.Timeout:
        return {
            "id": request_id,
            "phase": phase_num,
            "endpoint": endpoint_name,
            "status": "timeout",
            "elapsed": TIMEOUT,
            "timestamp": time.time(),
            "success": False,
            "error": "Timeout"
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "id": request_id,
            "phase": phase_num,
            "endpoint": endpoint_name,
            "status": "connection_error",
            "elapsed": None,
            "timestamp": time.time(),
            "success": False,
            "error": f"Connection Error: {str(e)[:100]}"
        }
    except Exception as e:
        return {
            "id": request_id,
            "phase": phase_num,
            "endpoint": endpoint_name,
            "status": "error",
            "elapsed": None,
            "timestamp": time.time(),
            "success": False,
            "error": str(e)[:100]
        }

def run_phase(session, phase_num, req_per_min, duration_min, endpoints):
    print(f"\n{'='*70}")
    print(f"FASE {phase_num}: {req_per_min} requisições/min por {duration_min} minuto(s)")
    print(f"{'='*70}")
    
    total_requests = req_per_min * duration_min
    total_seconds = duration_min * 60
    

    phase_start = time.time()
    results = []
    futures = []
    request_counter = 0
    endpoints_cycle = list(endpoints.keys())
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for second in range(total_seconds):
            requests_this_second = req_per_min // 60
            if second < (req_per_min % 60):
                requests_this_second += 1
            
            for i in range(requests_this_second):
                request_counter += 1
                endpoint_name = endpoints_cycle[(request_counter - 1) % len(endpoints_cycle)]
                endpoint_url = endpoints[endpoint_name]
                
                future = executor.submit(
                    send_request, 
                    session, 
                    endpoint_name, 
                    endpoint_url, 
                    request_counter,
                    phase_num
                )
                futures.append(future)
            
            elapsed = time.time() - phase_start
            next_second = (second + 1)
            time_to_wait = next_second - elapsed
            if time_to_wait > 0:
                time.sleep(time_to_wait)
        
        print(f"\n⏳ Aguardando conclusão de {len(futures)} requisições...")
        for i, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result()
                results.append(result)
                
                if i % 50 == 0 or i == len(futures):
                    success_count = sum(1 for r in results if r["success"])
                    print(f"   [{i}/{len(futures)}] Processadas | "
                          f"Sucesso: {success_count}/{len(results)} "
                          f"({(success_count/len(results)*100):.1f}%)")
            except Exception as e:
                print(f"   ✗ Erro ao processar resultado: {e}")
    
    print(f"\n📊 Resultados da Fase {phase_num}:")
    for endpoint_name in endpoints.keys():
        endpoint_results = [r for r in results if r["endpoint"] == endpoint_name]
        if endpoint_results:
            success = sum(1 for r in endpoint_results if r["success"])
            total = len(endpoint_results)
            print(f"   {endpoint_name.upper()}: {success}/{total} sucessos ({(success/total*100):.1f}%)")
    
    total_success = sum(1 for r in results if r["success"])
    print(f"   TOTAL: {total_success}/{len(results)} sucessos ({(total_success/len(results)*100):.1f}%)")
    
    return results

def run_test(test_microservices=True):
    architecture = "microsservices" if test_microservices else "monolitico"
    
    if test_microservices:
        base_url = None 
        endpoints = {
            "transactions": f"{MICROSERVICES_TRANSACTIONS}/transactions/1",
            "accounts": f"{MICROSERVICES_ACCOUNTS}/accounts"
        }
    else:
        base_url = MONOLITICO_BASE
        endpoints = {
            "transactions": f"{base_url}/transactions/1",
            "accounts": f"{base_url}/accounts"
        }
    
    print(f"\n{'='*70}")
    print(f"TESTE 3 REFORMULADO - DEGRADAÇÃO GRADUAL SOB CARGA PROGRESSIVA")
    print(f"{'='*70}")
    print(f"Arquitetura: {architecture.upper()}")
    if test_microservices:
        print(f"URLs: /accounts={MICROSERVICES_ACCOUNTS}, /transactions={MICROSERVICES_TRANSACTIONS}")
    else:
        print(f"Base URL: {base_url}")
    print(f"Endpoints: {', '.join(endpoints.keys())}")
    print(f"\nFases do teste:")
    total_requests = 0
    for i, (rpm, duration) in enumerate(LOAD_PHASES, 1):
        phase_total = rpm * duration
        total_requests += phase_total
        print(f"  Fase {i}: {rpm} req/min × {duration} min = {phase_total} requisições")
    print(f"\nTotal de requisições: {total_requests}")
    print(f"Duração total: {sum(d for _, d in LOAD_PHASES)} minutos")
    print(f"{'='*70}\n")
    
    session = requests.Session()
    all_results = []
    test_start_time = time.time()
    
    try:
        for phase_num, (req_per_min, duration) in enumerate(LOAD_PHASES, 1):
            phase_results = run_phase(session, phase_num, req_per_min, duration, endpoints)
            all_results.extend(phase_results)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    
    test_duration = time.time() - test_start_time
    
    print(f"\n{'='*70}")
    print("ANÁLISE FINAL")
    print(f"{'='*70}\n")
    
    total_requests = len(all_results)
    total_success = sum(1 for r in all_results if r["success"])
    total_failed = total_requests - total_success
    
    print(f"Duração total do teste: {test_duration/60:.2f} minutos")
    print(f"Total de requisições: {total_requests}")
    print(f"Sucessos: {total_success} ({(total_success/total_requests*100):.2f}%)")
    print(f"Falhas: {total_failed} ({(total_failed/total_requests*100):.2f}%)")
    
    print(f"\n📊 Análise por Endpoint:\n")
    for endpoint_name in endpoints.keys():
        endpoint_results = [r for r in all_results if r["endpoint"] == endpoint_name]
        if endpoint_results:
            success = sum(1 for r in endpoint_results if r["success"])
            total = len(endpoint_results)
            print(f"{endpoint_name.upper()}:")
            print(f"  Total: {total} requisições")
            print(f"  Sucessos: {success} ({(success/total*100):.2f}%)")
            print(f"  Falhas: {total - success} ({((total-success)/total*100):.2f}%)")
    
    print(f"\n📈 Taxa de Sucesso por Fase:\n")
    for phase_num in range(1, len(LOAD_PHASES) + 1):
        phase_results = [r for r in all_results if r["phase"] == phase_num]
        if phase_results:
            success = sum(1 for r in phase_results if r["success"])
            total = len(phase_results)
            rpm, duration = LOAD_PHASES[phase_num - 1]
            print(f"Fase {phase_num} ({rpm} req/min): {success}/{total} "
                  f"({(success/total*100):.1f}% sucesso)")
    
    status_counter = Counter()
    for r in all_results:
        status_counter[r["status"]] += 1
    
    print(f"\n🔢 Distribuição de Status HTTP:\n")
    for status, count in sorted(status_counter.items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count} ({(count/total_requests*100):.2f}%)")
    
    output_dir = "Inputs-data"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"results_gradual_{architecture}.json")
    
    phase_stats = []
    for phase_num in range(1, len(LOAD_PHASES) + 1):
        phase_results = [r for r in all_results if r["phase"] == phase_num]
        rpm, duration = LOAD_PHASES[phase_num - 1]
        
        phase_data = {
            "phase": phase_num,
            "req_per_min": rpm,
            "duration_min": duration,
            "total_requests": len(phase_results),
            "total_success": sum(1 for r in phase_results if r["success"]),
            "total_failed": sum(1 for r in phase_results if not r["success"]),
            "success_rate": (sum(1 for r in phase_results if r["success"]) / len(phase_results) * 100) if phase_results else 0,
            "endpoints": {}
        }
        
        for endpoint_name in endpoints.keys():
            ep_results = [r for r in phase_results if r["endpoint"] == endpoint_name]
            if ep_results:
                phase_data["endpoints"][endpoint_name] = {
                    "total": len(ep_results),
                    "success": sum(1 for r in ep_results if r["success"]),
                    "failed": sum(1 for r in ep_results if not r["success"]),
                    "success_rate": (sum(1 for r in ep_results if r["success"]) / len(ep_results) * 100)
                }
        
        phase_stats.append(phase_data)
    
    summary = {
        "architecture": architecture,
        "base_url": base_url if base_url else f"accounts={MICROSERVICES_ACCOUNTS}, transactions={MICROSERVICES_TRANSACTIONS}",
        "endpoints": list(endpoints.keys()),
        "timestamp": datetime.now().isoformat(),
        "test_duration_minutes": test_duration / 60,
        "configuration": {
            "phases": [{"req_per_min": rpm, "duration_min": dur} for rpm, dur in LOAD_PHASES],
            "max_workers": MAX_WORKERS,
            "timeout": TIMEOUT
        },
        "summary": {
            "total_requests": total_requests,
            "total_success": total_success,
            "total_failed": total_failed,
            "success_rate": (total_success/total_requests*100) if total_requests > 0 else 0,
            "failure_rate": (total_failed/total_requests*100) if total_requests > 0 else 0
        },
        "endpoint_stats": {
            endpoint: {
                "total": len([r for r in all_results if r["endpoint"] == endpoint]),
                "success": sum(1 for r in all_results if r["endpoint"] == endpoint and r["success"]),
                "success_rate": (sum(1 for r in all_results if r["endpoint"] == endpoint and r["success"]) /
                                len([r for r in all_results if r["endpoint"] == endpoint]) * 100)
                                if [r for r in all_results if r["endpoint"] == endpoint] else 0
            }
            for endpoint in endpoints.keys()
        },
        "phase_stats": phase_stats,
        "status_distribution": dict(status_counter),
        "detailed_results": all_results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Resultados salvos em: {output_file}")
    print(f"{'='*70}\n")
    
    return summary

if __name__ == "__main__":
    try:
        print("\n" + "="*70)
        print("INICIANDO TESTES PARA AMBAS AS ARQUITETURAS")
        print("="*70)
        
        print("\n\n🔷 Testando MICROSSERVIÇOS...")
        summary_micro = run_test(test_microservices=True)
        
        print("\n\n🔶 Testando MONOLÍTICO...")
        summary_mono = run_test(test_microservices=False)
        
        print("\n\n" + "="*70)
        print("✅ TODOS OS TESTES CONCLUÍDOS!")
        print("="*70)
        print(f"\nResultados salvos:")
        print(f"  - Microsserviços: Inputs-data/results_gradual_microsservices.json")
        print(f"  - Monolítico: Inputs-data/results_gradual_monolitico.json")
        print("="*70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
