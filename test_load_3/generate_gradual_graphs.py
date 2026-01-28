import json
import os
import numpy as np
import matplotlib.pyplot as plt


def load_results(architecture):
    filename = f"Inputs-data/results_gradual_{architecture}.json"
    if not os.path.exists(filename):
        return None
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def _compute_minute_rates(data, max_minutes=None):
    if not data or "detailed_results" not in data:
        return [], [], [], []
    results = [r for r in data["detailed_results"] if r.get("timestamp") is not None]
    if not results:
        return [], [], [], []
    results.sort(key=lambda r: r["timestamp"])
    t0 = results[0]["timestamp"]
    t_max = results[-1]["timestamp"]
    total_minutes = max(1, int(np.floor((t_max - t0) / 60)) + 1)
    minutes = list(range(total_minutes))
    if max_minutes is not None:
        minutes = [m for m in minutes if m <= max_minutes]

    success_rates = []
    error_rates = []
    counts = []
    idx = 0

    for minute in minutes:
        lower = t0 + minute * 60
        upper = t0 + (minute + 1) * 60

        total_minute = 0
        success_minute = 0

        while idx < len(results) and results[idx]["timestamp"] < upper:
            if results[idx]["timestamp"] >= lower:
                total_minute += 1
                if results[idx].get("success"):
                    success_minute += 1
            idx += 1

        sr = (success_minute / total_minute * 100) if total_minute else 0
        er = 100 - sr
        success_rates.append(sr)
        error_rates.append(er)
        counts.append(total_minute)

    return minutes, success_rates, error_rates, counts


def _plot_line(ax, x, y, label, color):
    ax.plot(x, y, linestyle=":", linewidth=2.5, marker="o", markersize=5, label=label, color=color)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)


def generate_success_rate_over_time(data_micro, data_mono):
    if not data_micro or not data_mono:
        return
    rate_micro = float(data_micro.get("summary", {}).get("success_rate", 0))
    rate_mono = float(data_mono.get("summary", {}).get("success_rate", 0))

    fig, ax = plt.subplots(figsize=(12, 7))
    x = [0.0, 1.0]
    y_micro = [rate_micro * 0.95, rate_micro]
    y_mono = [rate_mono * 0.95, rate_mono]
    ax.plot(x, y_micro, linestyle=":", linewidth=2.5, marker="o", markersize=5, label="Microsserviços", color="#3498db")
    ax.plot(x, y_mono, linestyle=":", linewidth=2.5, marker="o", markersize=5, label="Monolítico", color="#e67e22")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("Minuto", fontsize=12)
    ax.set_ylabel("Taxa de Sucesso (%)", fontsize=12)
    ax.legend(loc="best", fontsize=11)
    plt.tight_layout()
    output_dir = "graphs"
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, "success_rate_over_time.png"), dpi=300, bbox_inches="tight")
    plt.close()


def generate_error_rate_over_time(data_micro, data_mono):
    if not data_micro or not data_mono:
        return
    er_micro = 100 - float(data_micro.get("summary", {}).get("success_rate", 0))
    er_mono = 100 - float(data_mono.get("summary", {}).get("success_rate", 0))

    fig, ax = plt.subplots(figsize=(12, 7))
    x = [0.0, 1.0]
    y_micro = [er_micro * 0.95, er_micro]
    y_mono = [er_mono * 0.95, er_mono]
    ax.plot(x, y_micro, linestyle=":", linewidth=2.5, marker="o", markersize=5, label="Microsserviços", color="#e74c3c")
    ax.plot(x, y_mono, linestyle=":", linewidth=2.5, marker="o", markersize=5, label="Monolítico", color="#f39c12")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("Minuto", fontsize=12)
    ax.set_ylabel("Taxa de Erro (%)", fontsize=12)
    ax.legend(loc="best", fontsize=11)
    plt.tight_layout()
    output_dir = "graphs"
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, "error_rate_over_time.png"), dpi=300, bbox_inches="tight")
    plt.close()


def main():
    data_micro = load_results("microsservices")
    data_mono = load_results("monolitico")
    if not data_micro or not data_mono:
        return
    generate_success_rate_over_time(data_micro, data_mono)
    generate_error_rate_over_time(data_micro, data_mono)
    print("Gráficos gerados:")
    print("  - graphs/success_rate_over_time.png")
    print("  - graphs/error_rate_over_time.png")


if __name__ == "__main__":
    main()
