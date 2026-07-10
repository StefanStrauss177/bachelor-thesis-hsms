# Messdaten und Auswertungsskripte der Bachelorarbeit

Dieses Repository enthält die im Rahmen der Bachelorarbeit erhobenen Rohdaten, die verwendeten Messskripte sowie die Skripte zur Auswertung und Visualisierung der Messergebnisse.

Untersucht wurden verschiedene Verfahren zur Absicherung der HSMS-Kommunikation. Dazu gehören mTLS, OpenVPN, WireGuard sowie IPsec im Transport- und Tunnelmodus. Zusätzlich wurden unverschlüsselte Referenzmessungen durchgeführt.

## Verzeichnisstruktur

```text
├── HardwareTesterMessergebnisse/
│   ├── Equipment_Messergebnisse/
│   │   ├── baseline/
│   │   └── mtls/
│   │
│   └── Host_Messergebnisse/
│       ├── baseline/
│       └── mtls/
│
└── Vergleichsmessergebnisse/
    ├── Auswertungsskripte/
    │   ├── iperf_throughput_plot.py
    │   ├── measurements_graph.py
    │   └── summary_tool_script.py
    │
    ├── IPsec_Transport_Messungen/
    ├── IPsec_Tunnel_Messungen/
    ├── Messskripte/
    │   ├── host.py
    │   ├── latency_equipment.py
    │   └── throughput_equipment.py
    │
    ├── mTLS-Messungen/
    ├── OpenVPN-Messungen/
    ├── Referenz_Messungen/
    └── WireGuard-Messungen/
```

## HardwareTesterMessergebnisse

Dieses Verzeichnis enthält die Messergebnisse vom FabLinkHardwareTester.

Die Messergebnisse sind nach Host- und Equipment-Seite sowie nach unverschlüsselter Referenzverbindung und mTLS-Verbindung getrennt.
### Equipment_Messergebnisse

Dieses Verzeichnis enthält die auf der Equipment-Seite erfassten Messergebnisse.

- `baseline`: Messergebnisse der unverschlüsselten Referenzverbindung
- `mtls`: Messergebnisse der mit mTLS abgesicherten Verbindung

### Host_Messergebnisse

Dieses Verzeichnis enthält die auf der Host-Seite erfassten Messergebnisse.

- `baseline`: Messergebnisse der unverschlüsselten Referenzverbindung
- `mtls`: Messergebnisse der mit mTLS abgesicherten Verbindung

## Vergleichsmessergebnisse

Dieses Verzeichnis enthält die Rohdaten, Messskripte und Auswertungsskripte des praktischen Vergleichs der untersuchten Verschlüsselungsverfahren.
Die Messungen wurden für die folgenden Varianten durchgeführt:

- unverschlüsselte Referenzverbindung
- mTLS
- OpenVPN
- WireGuard
- IPsec im Transportmodus
- IPsec im Tunnelmodus

### Referenz_Messungen

Enthält die Messergebnisse der unverschlüsselten Referenzverbindung.

Diese Messungen dienen als Vergleichsgrundlage für die Bewertung der durch die Verschlüsselungsverfahren verursachten Änderungen.

### mTLS-Messungen

Enthält die Messergebnisse der mit mTLS abgesicherten HSMS-Verbindung.

### OpenVPN-Messungen

Enthält die Messergebnisse der über OpenVPN abgesicherten Verbindung.

### WireGuard-Messungen

Enthält die Messergebnisse der über WireGuard abgesicherten Verbindung.

### IPsec_Transport_Messungen

Enthält die Messergebnisse der mit IPsec im Transportmodus abgesicherten Verbindung.

### IPsec_Tunnel_Messungen

Enthält die Messergebnisse der mit IPsec im Tunnelmodus abgesicherten Verbindung.

## Messskripte

Das Verzeichnis `Messskripte` enthält die Python-Skripte, die für die Durchführung der praktischen HSMS-Messungen verwendet wurden.

Die konfigurierbaren Parameter befinden sich jeweils am Anfang der Skripte. Dazu gehören beispielsweise:

- IP-Adresse des HSMS-Equipments
- verwendeter TCP-Port
- Größe der übertragenen Nutzdaten
- Anzahl der Nachrichten
- Dauer einer Messung
- Anzahl der Messwiederholungen
- verwendetes Verschlüsselungsverfahren

### host.py

Das Skript `host.py` implementiert eine passive HSMS-Gegenstelle.

Es öffnet einen TCP-Server, wartet auf eingehende Verbindungen und beantwortet empfangene HSMS- und SECS-II-Nachrichten. Dabei werden unter anderem folgende Nachrichten verarbeitet:

- `Select.req` mit `Select.rsp`
- `S1F1` mit `S1F2`
- `S6F11` mit `S6F12`

Trotz des Dateinamens baut dieses Skript selbst keine Verbindung auf und verhält sich technisch wie die passive Equipment-Seite.

### latency_equipment.py

Das Skript `latency_equipment.py` implementiert die aktive Seite der Latenzmessung.

Es baut eine TCP-Verbindung zur passiven HSMS-Gegenstelle auf, führt den HSMS-Select-Vorgang durch und sendet zunächst mehrere `S1F1`-Nachrichten zur Aufwärmung der Verbindung. Anschließend überträgt es eine festgelegte Anzahl von `S6F11`-Nachrichten und misst jeweils die Zeit bis zum Empfang der zugehörigen `S6F12`-Antwort.

Aus den gemessenen Antwortzeiten werden statistische Kennwerte wie Mittelwert, Median, Standardabweichung, Minimum und Maximum berechnet und gemeinsam mit den Rohwerten in einer Textdatei gespeichert.

### throughput_equipment.py

Das Skript `throughput_equipment.py` implementiert die aktive Seite der Durchsatzmessung.

Es baut eine TCP-Verbindung zur passiven HSMS-Gegenstelle auf, führt den HSMS-Select-Vorgang durch und sendet zunächst mehrere `S1F1`-Nachrichten zur Aufwärmung der Verbindung. Danach werden für eine festgelegte Messdauer fortlaufend `S6F11`-Nachrichten mit einer konfigurierbaren Nutzdatengröße gesendet und die jeweiligen `S6F12`-Antworten empfangen.

Das Skript ermittelt unter anderem die Anzahl der übertragenen Nachrichten pro Sekunde, den Nutzdatendurchsatz sowie statistische Kennwerte der gemessenen Antwortzeiten. Die Ergebnisse und Rohwerte werden anschließend in einer Textdatei gespeichert.

### iperf_throughput_plot.py

Das Skript `iperf_throughput_plot.py` verarbeitet die mit `iperf3` erzeugten Durchsatzmessungen.

Aus den Messdaten werden Diagramme erstellt, die einen Vergleich des erreichbaren Netzwerkdurchsatzes zwischen der Referenzmessung und den verschiedenen Verschlüsselungsverfahren ermöglichen.

### measurements_graph.py

Das Skript `measurements_graph.py` erstellt Diagramme aus den Ergebnissen der HSMS-Messungen.

Je nach verwendeter Eingabedatei können damit beispielsweise folgende Messgrößen dargestellt werden:

- Latenz
- Nachrichtendurchsatz
- Verbindungsaufbauzeit
- Abweichung gegenüber der Referenzmessung

### summary_tool_script.py

Das Skript `summary_tool_script.py` fasst die Ergebnisse mehrerer Messdurchläufe zusammen.

Dabei können zentrale statistische Kennwerte berechnet werden, beispielsweise:

- Mittelwert
- Median
- Standardabweichung
- Minimum
- Maximum

Die zusammengefassten Werte dienen als Grundlage für die tabellarische und grafische Auswertung in der Bachelorarbeit.
