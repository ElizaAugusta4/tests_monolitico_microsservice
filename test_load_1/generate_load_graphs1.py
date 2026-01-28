from __future__ import annotations
import argparse
from pathlib import Path
from typing import List
import pandas as pd
import matplotlib.pyplot as plt

try:
    import seaborn as sns  
    sns.set_theme(style='whitegrid')
except Exception:
    if 'seaborn-whitegrid' in plt.style.available:
        plt.style.use('seaborn-whitegrid')
    elif 'seaborn' in plt.style.available:
        plt.style.use('seaborn')
    elif 'ggplot' in plt.style.available:
        plt.style.use('ggplot')
    else:
        plt.style.use('default')


def parse_two_col_like(path: Path) -> pd.Series:
    lines = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            lines.append(line)

    if lines and ('"' in lines[0] or ',' in lines[0] or 'Time' in lines[0] or 'Time"' in lines[0]):
        data_lines = lines[1:]
    else:
        data_lines = lines

    timestamps = []
    values = []
    for ln in data_lines:
        try:
            left, val = ln.rsplit(None, 1)
        except ValueError:
            continue
        ts = left
        if ts.count(":") == 2 and ts.endswith(":0"):
            ts = ts[:-2] + ":00"
        timestamps.append(ts)
        try:
            v = float(val.replace(',', ''))
        except Exception:
            try:
                v = float(val.replace('"', '').replace(',', ''))
            except Exception:
                continue
        values.append(v)

    if not timestamps:
        return pd.Series(dtype=float)

    idx = pd.to_datetime(timestamps, errors='coerce')
    df = pd.Series(values, index=idx)
    df = df[~df.index.isna()]
    df = df.sort_index()
    return df


def aggregate_series(files: List[Path]) -> pd.Series:
    series_list = []
    for p in files:
        if not p.exists():
            print(f"Aviso: arquivo não encontrado: {p}")
            continue
        s = parse_two_col_like(p)
        if s.empty:
            print(f"Aviso: nenhum dado extraído de {p}")
        else:
            series_list.append(s)
    if not series_list:
        return pd.Series(dtype=float)
    df = pd.concat(series_list, axis=1)
    df_sum = df.sum(axis=1)
    df_sum = df_sum.sort_index()
    return df_sum


def plot_comparison(cpu_monolith: pd.Series, cpu_micro: pd.Series, mem_monolith: pd.Series, mem_micro: pd.Series, max_positions: int | None = 8):
    if max_positions is None or max_positions <= 0:
        raise ValueError('max_positions deve ser > 0')
    N = int(max_positions)

    def first_n_vals(s: pd.Series, n: int) -> List[float]:
        if s is None or s.empty:
            return [float('nan')] * n
        vals = list(s.dropna().values)[:n]
        if len(vals) < n:
            vals = vals + [float('nan')] * (n - len(vals))
        return vals

    cpu_mono_y = first_n_vals(cpu_monolith, N)
    cpu_micro_y = first_n_vals(cpu_micro, N)

    # CPU
    x = list(range(1, N + 1))
    plt.figure(figsize=(12, 5))
    ax = plt.gca()
    if any([not cpu_monolith.empty, not cpu_micro.empty]):
        ax.plot(x, cpu_mono_y, label='Monolítico', marker='o', markersize=6, linewidth=2)
        ax.plot(x, cpu_micro_y, label='Microservice (soma pods)', marker='o', markersize=6, linewidth=2)
        ax.set_title('Uso de CPU')
        ax.set_xlabel('Tempo')
        ax.set_ylabel('CPU (cores)')
        ax.set_xticks(x)
        ax.set_xticklabels([str(i) for i in x])
        ax.legend(loc='upper right', frameon=True)
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        ax.grid(axis='x', linestyle=':', alpha=0.6)
        plt.tight_layout()
    # ensure graphs output directory exists
    out_dir = Path('graphs')
    out_dir.mkdir(parents=True, exist_ok=True)
    cpu_out = out_dir / "cpu.png"
    plt.savefig(cpu_out, dpi=150)
    print(f"Gerado: {cpu_out}")
    plt.close()

    plt.figure(figsize=(12, 5))
    ax = plt.gca()

    mem_mono_vals = first_n_vals(mem_monolith, N)
    mem_micro_vals = first_n_vals(mem_micro, N)

    import math
    combined = [v for v in mem_mono_vals + mem_micro_vals if not (isinstance(v, float) and math.isnan(v))]
    def maybe_convert(vals: List[float]) -> List[float]:
        if not combined:
            return vals
        avg = sum(combined) / len(combined)
        if avg > 1e6:
            return [v / (1024 * 1024) if not (isinstance(v, float) and math.isnan(v)) else float('nan') for v in vals]
        return vals

    mem_mono_plot_vals = maybe_convert(mem_mono_vals)
    mem_micro_plot_vals = maybe_convert(mem_micro_vals)

    ax.plot(x, mem_mono_plot_vals, label='Monolítico', marker='o', markersize=6, linewidth=2)
    ax.plot(x, mem_micro_plot_vals, label='Microservice (soma pods)', marker='o', markersize=6, linewidth=2)

    ax.set_title('Uso de Memória')
    ax.set_xlabel('Tempo')
    ax.set_ylabel('Memória(MiB)')
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) for i in x])
    ax.legend(loc='upper right', frameon=True)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.grid(axis='x', linestyle=':', alpha=0.6)
    plt.tight_layout()
    mem_out = out_dir / "memory.png"
    plt.savefig(mem_out, dpi=150)
    print(f"Gerado: {mem_out}")
    plt.close()

def main():
    p = argparse.ArgumentParser(description='Gerar gráficos de comparação CPU e memória entre monolítico e microsserviço')
    p.add_argument('--monolith-cpu', required=False, help='Arquivo CSV do CPU do monolítico')
    p.add_argument('--micro-cpu', required=False, help='Arquivos CSV do CPU dos pods do microservice (separados por vírgula)')
    p.add_argument('--monolith-mem', required=False, help='Arquivo CSV da memória do monolítico')
    p.add_argument('--micro-mem', required=False, help='Arquivos CSV da memória dos pods do microservice (separados por vírgula)')
    p.add_argument('--max-positions', type=int, default=8, help='Número máximo de posições no eixo X (default: 8)')
    args = p.parse_args()

    def find_files(contain: List[str]) -> List[Path]:
            found: List[Path] = []
            for p in Path('.').rglob('*'):
                if not p.is_file():
                    continue
                name = p.name.lower()
                if p.suffix.lower() not in ('.csv', '.txt'):
                    continue
                if all(c.lower() in name for c in contain):
                    found.append(p)
            return found
    if not args.monolith_cpu:
        cand = find_files(['monolit', 'cpu']) + find_files(['consumo', 'cpu'])
        if cand:
            args.monolith_cpu = str(sorted(cand)[0])
            print(f"Usando arquivo padrão para monolith CPU: {args.monolith_cpu}")

    if not args.micro_cpu:
        cpu_files = [p for p in Path('.').rglob('*.csv') if 'cpu' in p.name.lower() and 'monolit' not in p.name.lower()]
        if cpu_files:
            args.micro_cpu = ','.join(str(p) for p in sorted(cpu_files))
            print(f"Usando arquivos padrão para micro CPU: {args.micro_cpu}")

    if not args.monolith_mem:
        cand = find_files(['memoria', 'monolit']) + find_files(['memoria', 'monolitico'])
        if cand:
            args.monolith_mem = str(sorted(cand)[0])
            print(f"Usando arquivo padrão para monolith Memória: {args.monolith_mem}")

    if not args.micro_mem:
        mem_files = [p for p in Path('.').rglob('*.csv') if 'memoria' in p.name.lower() and ('micro' in p.name.lower() or 'micros' in p.name.lower() or 'transactions-service' in p.name.lower())]
        if not mem_files:
            mem_files = [p for p in Path('.').rglob('*.csv') if 'memoria' in p.name.lower() and 'monolit' not in p.name.lower()]
        if mem_files:
            args.micro_mem = ','.join(str(p) for p in sorted(mem_files))
            print(f"Usando arquivos padrão para micro Memória: {args.micro_mem}")

    cpu_mono = pd.Series(dtype=float)
    cpu_micro = pd.Series(dtype=float)
    mem_mono = pd.Series(dtype=float)
    mem_micro = pd.Series(dtype=float)

    if args.monolith_cpu:
        cpu_mono = parse_two_col_like(Path(args.monolith_cpu))
    if args.micro_cpu:
        cpu_paths = [Path(s.strip()) for s in args.micro_cpu.split(',') if s.strip()]
        cpu_micro = aggregate_series(cpu_paths)
    if args.monolith_mem:
        mem_mono = parse_two_col_like(Path(args.monolith_mem))
    if args.micro_mem:
        mem_paths = [Path(s.strip()) for s in args.micro_mem.split(',') if s.strip()]
        mem_micro = aggregate_series(mem_paths)

    if cpu_mono.empty and cpu_micro.empty and mem_mono.empty and mem_micro.empty:
        print('Nenhum dado carregado; verifique os arquivos no diretório ou passe caminhos via CLI.')
        return

    plot_comparison(cpu_mono, cpu_micro, mem_mono, mem_micro, max_positions=args.max_positions)


if __name__ == '__main__':
    main()
