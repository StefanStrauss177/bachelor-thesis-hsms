from pathlib import Path
from statistics import mean, stdev
import csv

ROOT_FOLDER = Path(".")
METHOD = "ipsec-transport-mode"
LATENCY_OUTPUT = f"summary_latency_{METHOD}.csv"
THROUGHPUT_OUTPUT = f"summary_throughput_{METHOD}.csv"


def parse_result_file(path):
    values = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("---"):
                break

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            try:
                values[key] = float(value)
            except ValueError:
                values[key] = value

    return values


def average(files, key):
    values = [
        file[key]
        for file in files
        if key in file and isinstance(file[key], (int, float))
    ]

    if not values:
        return ""

    return mean(values)


def metric_stdev(files, key):
    values = [
        file[key]
        for file in files
        if key in file and isinstance(file[key], (int, float))
    ]

    if len(values) < 2:
        return ""

    return stdev(values)


def confidence_interval_95(files, key):
    values = [
        file[key]
        for file in files
        if key in file and isinstance(file[key], (int, float))
    ]

    if len(values) < 2:
        return ""

    return 1.96 * (stdev(values) / (len(values) ** 0.5))


def get_payload_name(path):
    """
    Uses the folder name below latency_results or throughput_results as payload name.
    Example:
    results/latency_results/50KB/run1.txt -> 50KB
    """

    parts = path.parts

    if "latency_results" in parts:
        index = parts.index("latency_results")
        return parts[index + 1]

    if "throughput_results" in parts:
        index = parts.index("throughput_results")
        return parts[index + 1]

    return "unknown"


def collect_results(result_folder_name):
    folder = ROOT_FOLDER / result_folder_name
    grouped = {}

    for path in folder.rglob("*.txt"):
        values = parse_result_file(path)
        payload = get_payload_name(path)

        grouped.setdefault(payload, []).append(values)

    return grouped


def write_latency_summary():
    grouped = collect_results("latency_results")

    rows = []

    for payload, files in sorted(grouped.items()):
        rows.append({
            "payload": payload,
            "file_count": len(files),
            "avg_runs": average(files, "runs"),
            "avg_mean_ms": average(files, "mean_ms"),
            "avg_median_ms": average(files, "median_ms"),
            "avg_stddev_ms": average(files, "stddev_ms"),
            "avg_min_ms": average(files, "min_ms"),
            "avg_max_ms": average(files, "max_ms"),
            "stdev_of_mean_ms": metric_stdev(files, "mean_ms"),
            "ci95_mean_ms": confidence_interval_95(files, "mean_ms"),
        })

    write_csv(LATENCY_OUTPUT, rows)


def write_throughput_summary():
    grouped = collect_results("throughput_results")

    rows = []

    for payload, files in sorted(grouped.items()):
        rows.append({
            "payload": payload,
            "file_count": len(files),
            "avg_duration_sec": average(files, "duration_sec"),
            "avg_payload_size_bytes": average(files, "payload_size_bytes"),
            "avg_total_messages": average(files, "total_messages"),
            "avg_messages_per_sec": average(files, "Messages/sec"),
            "avg_payload_throughput_MiB_sec": average(files, "payload_throughput_MiB_sec"),
            "avg_mean_rtt_ms": average(files, "mean_rtt_ms"),
            "avg_median_rtt_ms": average(files, "median_rtt_ms"),
            "avg_stddev_ms": average(files, "stddev_ms"),
            "avg_min_ms": average(files, "min_ms"),
            "avg_max_ms": average(files, "max_ms"),

            # Fixed key name here
            "stdev_of_messages_per_sec": metric_stdev(files, "Messages/sec"),
            "ci95_messages_per_sec": confidence_interval_95(files, "Messages/sec"),
        })

    write_csv(THROUGHPUT_OUTPUT, rows)

def write_csv(output_file, rows):
    if not rows:
        print(f"No rows for {output_file}")
        return

    fieldnames = list(rows[0].keys())

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            formatted = {}

            for key, value in row.items():
                if isinstance(value, float):
                    formatted[key] = f"{value:.3f}"
                else:
                    formatted[key] = value

            writer.writerow(formatted)

    print(f"Created {output_file}")


write_latency_summary()
write_throughput_summary()