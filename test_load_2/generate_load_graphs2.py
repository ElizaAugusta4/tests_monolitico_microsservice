import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def load_results(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def plot_latency(ms_data, mono_data, out_path: Path):
    labels = ["mean", "p50", "p90", "p95", "p99"]
    ms_vals = [ms_data["latency"].get(k) for k in labels]
    mono_vals = [mono_data["latency"].get(k) for k in labels]

    x = np.arange(len(labels))
    width = 0.35

    sns.set(style="whitegrid")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width/2, mono_vals, width, label="Monolítico")
    ax.bar(x + width/2, ms_vals, width, label="Microservice")

    ax.set_ylabel("Segundos")
    ax.set_title("Comparação de Latência (s)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    for i, (m, s) in enumerate(zip(mono_vals, ms_vals)):
        ax.text(i - width/2, m + 0.01, f"{m:.3f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + width/2, s + 0.01, f"{s:.3f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_throughput(ms_data, mono_data, out_path: Path):
    ms_th = ms_data.get("throughput_per_minute", [])
    mono_th = mono_data.get("throughput_per_minute", [])
    max_len = max(len(ms_th), len(mono_th))

    def pad(arr, n):
        return arr + [0] * (n - len(arr))

    ms_th = pad(ms_th, max_len)
    mono_th = pad(mono_th, max_len)
    x = list(range(1, max_len + 1))

    sns.set(style="whitegrid")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(x, mono_th, marker="o", label="Monolítico")
    ax.plot(x, ms_th, marker="o", label="Microservice")

    ax.set_xlabel("Minuto")
    ax.set_ylabel("Requests por minuto")
    ax.set_title("Throughput por minuto")
    ax.set_xticks(x)
    ax.legend()

    for xi, val in zip(x, ms_th):
        if val != 0 and val != np.mean(ms_th):
            ax.annotate(str(val), (xi, val), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_rates(ms_data, mono_data, out_path: Path):
    groups = ["Monolítico", "Microservice"]
    mono_success = mono_data["counts"].get("success_rate_percent", 0.0)
    mono_error = mono_data["counts"].get("error_rate_percent", 0.0)
    ms_success = ms_data["counts"].get("success_rate_percent", 0.0)
    ms_error = ms_data["counts"].get("error_rate_percent", 0.0)

    success = [mono_success, ms_success]
    error = [mono_error, ms_error]

    sns.set(style="whitegrid")
    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(groups))

    ax.bar(x, success, label="Sucesso (%)", color="#4CAF50")
    ax.bar(x, error, bottom=success, label="Erro (%)", color="#F44336")

    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylabel("Porcentagem (%)")
    ax.set_title("Taxas de Sucesso / Erro")
    ax.legend()

    # rótulos
    for xi, s, e in zip(x, success, error):
        ax.text(xi, s/2, f"{s:.1f}%", ha='center', va='center', color='white', fontsize=9)
        ax.text(xi, s + e/2, f"{e:.1f}%", ha='center', va='center', color='white', fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main():
    base = Path(__file__).parent
    ms_file = base / "results_structured_microservice.json"
    mono_file = base / "results_structured_monolitico.json"

    if not ms_file.exists() or not mono_file.exists():
        print("Arquivos JSON não encontrados. Certifique-se de que os arquivos estão no mesmo diretório do script.")
        print(f"Procurados: {ms_file}, {mono_file}")
        return

    ms = load_results(ms_file)
    mono = load_results(mono_file)

    out_latency = base / "latency.png"
    out_throughput = base / "throughput.png"
    out_rates = base / "rate_sucess_error.png"

    plot_latency(ms, mono, out_latency)
    print(f"Salvo: {out_latency}")
    plot_throughput(ms, mono, out_throughput)
    print(f"Salvo: {out_throughput}")
    plot_rates(ms, mono, out_rates)
    print(f"Salvo: {out_rates}")


if __name__ == "__main__":
    main()
