import matplotlib.pyplot as plt
import numpy as np

# Messwerte aus iperf3
daten = {
    "Referenzwert": {
        "transfer_gbyte": [28.4, 31.3, 29.3, 28.8, 29.3],
        "bitrate_gbit": [4.07, 4.47, 4.20, 4.13, 4.19],
    },
    "mTLS": {
        "transfer_gbyte": [13.5, 9.67, 13.7, 9.50, 13.2],
        "bitrate_gbit": [1.94, 1.38, 1.96, 1.36, 1.90],
    },
    "IPsec Transportmodus": {
        "transfer_gbyte": [6.52, 7.43, 4.74, 6.33, 5.83],
        "bitrate_gbit": [0.934, 1.03, 0.676, 0.905, 0.827],
    },
    "IPsec Tunnelmodus": {
        "transfer_gbyte": [4.78, 2.32, 2.25, 5.92, 2.26],
        "bitrate_gbit": [0.684, 0.331, 0.321, 0.847, 0.324],
    },
    "OpenVPN": {
        "transfer_gbyte": [4.37, 4.52, 4.36, 4.58, 4.13],
        "bitrate_gbit": [0.625, 0.647, 0.624, 0.656, 0.591],
    },
    "WireGuard": {
        "transfer_gbyte": [4.68, 5.04, 6.58, 3.62, 4.62],
        "bitrate_gbit": [0.669, 0.722, 0.943, 0.519, 0.661],
    },
}

verfahren = list(daten.keys())
x = np.arange(len(verfahren))

transfer_mean = [np.mean(daten[v]["transfer_gbyte"]) for v in verfahren]
transfer_std = [np.std(daten[v]["transfer_gbyte"], ddof=1) for v in verfahren]

bitrate_mean = [np.mean(daten[v]["bitrate_gbit"]) for v in verfahren]
bitrate_std = [np.std(daten[v]["bitrate_gbit"], ddof=1) for v in verfahren]


def balkendiagramm(werte, ylabel, titel, dateiname):
    plt.figure(figsize=(11, 6))
    plt.bar(x, werte, capsize=5)
    plt.xticks(x, verfahren, rotation=30, ha="right")
    plt.ylabel(ylabel)
    plt.title(titel)
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()

    plt.savefig(f"{dateiname}.png", dpi=300)
    plt.savefig(f"{dateiname}.svg")
    plt.show()


balkendiagramm(
    transfer_mean,
    "Transfer in GByte",
    "Durchschnittlicher Transfer nach Verschlüsselungsverfahren",
    "transfer_nach_verfahren"
)

balkendiagramm(
    bitrate_mean,
    "Bitrate in Gbit/s",
    "Durchschnittliche Bitrate nach Verschlüsselungsverfahren",
    "bitrate_nach_verfahren"
)

messlaeufe = [1, 2, 3, 4, 5]

plt.figure(figsize=(11, 6))
for verfahren_name, werte in daten.items():
    plt.plot(messlaeufe, werte["bitrate_gbit"], marker="o", label=verfahren_name)

plt.xlabel("Messlauf")
plt.ylabel("Bitrate in Gbit/s")
plt.title("Bitrate je Messlauf")
plt.xticks(messlaeufe)
plt.grid(True, linestyle="--", alpha=0.7)
plt.legend()
plt.tight_layout()
plt.savefig("bitrate_je_messlauf.png", dpi=300)
plt.savefig("bitrate_je_messlauf.svg")
plt.show()