import re
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


LATENCY_DIR = Path("results/latency")
THROUGHPUT_DIR = Path("results/throughput")
OUTPUT_DIR = Path("figures")

OUTPUT_DIR.mkdir(exist_ok=True)

PAYLOAD_ORDER = ["10KB", "50KB", "100KB", "500KB", "1MB", "8MB", "15MB"]

METHOD_NAMES = {
    "baseline": "Referenzwert",
    "mtls": "mTLS",
    "openvpn": "OpenVPN",
    "wireguard": "WireGuard",
    "ipsec-tunnelmode": "IPsec Tunnel",
    "ipsec-transportmode": "IPsec Transport",
}


def extract_payload(payload_text):
    match = re.search(r"(10KB|50KB|100KB|500KB|1MB|8MB|15MB)", str(payload_text))
    if not match:
        raise ValueError(f"Could not extract payload from: {payload_text}")
    return match.group(1)


def extract_method_from_filename(file_path):
    name = file_path.stem.lower()

    for key, label in METHOD_NAMES.items():
        if key in name:
            return label

    raise ValueError(f"Could not detect encryption method from filename: {file_path.name}")


def load_csvs(folder):
    all_data = []

    for file_path in sorted(folder.glob("*.csv")):
        df = pd.read_csv(file_path)

        df["method"] = extract_method_from_filename(file_path)
        df["payload_clean"] = df["payload"].apply(extract_payload)

        df["payload_clean"] = pd.Categorical(
            df["payload_clean"],
            categories=PAYLOAD_ORDER,
            ordered=True
        )

        df = df.sort_values("payload_clean")
        all_data.append(df)

    if not all_data:
        raise RuntimeError(f"No CSV files found in {folder}")

    return pd.concat(all_data, ignore_index=True)


def plot_line(
    df,
    y_column,
    y_label,
    title,
    output_name,
    stddev_column=None
):
    plt.figure(figsize=(9, 5))

    for method in df["method"].unique():
        data = df[df["method"] == method].sort_values("payload_clean")

        x = data["payload_clean"].astype(str)
        y = data[y_column]

        if stddev_column is not None:
            plt.errorbar(
                x,
                y,
                yerr=data[stddev_column],
                marker="o",
                linewidth=2,
                capsize=5,
                label=method
            )
        else:
            plt.plot(
                x,
                y,
                marker="o",
                linewidth=2,
                label=method
            )

    plt.xlabel("Nutzdatengröße")
    plt.ylabel(y_label)
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    output_path = OUTPUT_DIR / output_name
    plt.savefig(output_path, dpi=300)
    plt.close()

    print(f"Saved: {output_path}")


latency_df = load_csvs(LATENCY_DIR)
throughput_df = load_csvs(THROUGHPUT_DIR)

throughput_df["avg_payload_throughput_MB_sec"] = (
    throughput_df["avg_payload_throughput_MiB_sec"] * 1.048576
)


# Latency with standard deviation
plot_line(
    df=latency_df,
    y_column="avg_mean_ms",
    stddev_column="avg_stddev_ms",
    y_label="Mean RTT (ms)",
    title="Latenz nach Nutzdatengröße",
    output_name="figure_1_latency_by_payload.png"
)


# Messages per second
plot_line(
    df=throughput_df,
    y_column="avg_messages_per_sec",
    y_label="Nachrichtendurchsatz (Nachrichten/s)",
    title="Nachrichtendurchsatz nach Nutzdatengröße",
    output_name="figure_2_messages_per_second.png"
)


# Payload throughput
plot_line(
    df=throughput_df,
    y_column="avg_payload_throughput_MB_sec",
    y_label="Nutzdatendurchsatz (MB/s)",
    title="Nutzdatendurchsatz nach Nutzdatengröße",
    output_name="figure_3_payload_throughput_MB_sec.png"
)


# RTT during throughput measurement with standard deviation
plot_line(
    df=throughput_df,
    y_column="avg_mean_rtt_ms",
    stddev_column="avg_stddev_ms",
    y_label="Mean RTT (ms)",
    title="RTT während der Durchsatzmessung",
    output_name="figure_4_throughput_rtt.png"
)


print("All figures created successfully.")