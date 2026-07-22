import socket
import struct
import time
import statistics

# IP address of the HSMS equipment.
EQUIPMENT_IP = "<EQUIPMENT_IP>"

# TCP port used for the HSMS connection.
PORT = <PORT>

# Size of the message payload in bytes.
PAYLOAD_SIZE_BYTES = <PAYLOAD_SIZE_IN_BYTES>

# Payload size label used only in the output file name.
PAYLOAD_SIZE = "<PAYLOAD_SIZE_LABEL>"

# Duration of each measurement in seconds.
DURATION = <MEASUREMENT_DURATION_IN_SECONDS>

# Number of times the complete measurement is repeated.
MEASUREMENT_COUNT = <NUMBER_OF_MEASUREMENTS>

# Available encryption methods.
# The selected value is used only in the output file name.
ENCRYPTION_TYPES = {
    "B": "baseline",
    "OV": "openvpn",
    "MT": "mtls",
    "WG": "wireguard",
    "ITUM": "ipsec-tunnelmode",
    "ITRM": "ipsec-transportmode"
}

# Select the encryption method used during the measurement.
# Available keys: "B", "OV", "MT", "WG", "ITUM", "ITRM"
ENCRYPTION_USED = ENCRYPTION_TYPES["<ENCRYPTION_TYPE_KEY>"]

# Initial value of the HSMS System Bytes counter.
# This value normally does not need to be changed.
system_counter = 0

def next_system_bytes():
    global system_counter
    system_counter += 1
    return system_counter


def receive_full_msg(sock, byte_count):
    data = b""

    while len(data) < byte_count:
        chunk = sock.recv(byte_count - len(data))
        if not chunk:
            raise ConnectionError("Socket closed")
        data += chunk

    return data


def receive_hsms(sock):
    length = struct.unpack(">I", receive_full_msg(sock, 4))[0]
    msg = receive_full_msg(sock, length)
    return msg


def send_hsms(sock, msg):
    sock.sendall(struct.pack(">I", len(msg)) + msg)


def hsms_header(session_id, stream, function, wbit, ptype, stype, system_bytes):
    stream_byte = stream | (0x80 if wbit else 0x00)

    return struct.pack(
        ">HBBBBI",
        session_id,
        stream_byte,
        function,
        ptype,
        stype,
        system_bytes
    )


def item_header(fmt, length):
    if length <= 0xFF:
        return bytes([fmt | 1, length])
    elif length <= 0xFFFF:
        return bytes([fmt | 2]) + struct.pack(">H", length)
    else:
        return bytes([fmt | 3]) + length.to_bytes(3, "big")


def secs_list(items):
    body = b"".join(items)
    return item_header(0x00, len(items)) + body


def secs_u4(value):
    return item_header(0xB0, 4) + struct.pack(">I", value)


def secs_binary(data):
    return item_header(0x20, len(data)) + data


def create_s1f1():
    system_bytes = next_system_bytes()

    return hsms_header(
        session_id=0,
        stream=1,
        function=1,
        wbit=True,
        ptype=0,
        stype=0,
        system_bytes=system_bytes
    )


def create_s6f11(payload_size):
    payload = b"A" * payload_size

    body = secs_list([
        secs_u4(1),       # DATAID
        secs_u4(1001),    # CEID
        secs_list([
            secs_list([
                secs_u4(1),       # RPTID
                secs_list([
                    secs_binary(payload)
                ])
            ])
        ])
    ])

    system_bytes = next_system_bytes()

    return hsms_header(
        session_id=0,
        stream=6,
        function=11,
        wbit=True,
        ptype=0,
        stype=0,
        system_bytes=system_bytes
    ) + body


def select(sock):
    system_bytes = next_system_bytes()

    select_message = hsms_header(
        session_id=0,
        stream=0,
        function=0,
        wbit=False,
        ptype=0,
        stype=1,
        system_bytes=system_bytes
    )

    send_hsms(sock, select_message)

    response = receive_hsms(sock)
    response_stype = response[5]

    if response_stype == 2:
        print("Selected")
        return True

    raise RuntimeError(f"Expected Select.rsp, got SType={response_stype}")


def verify_s1f2(response):
    stream = response[2] & 0x7F
    function = response[3]

    if stream != 1 or function != 2:
        raise RuntimeError(f"Expected S1F2, got S{stream}F{function}")


def verify_s6f12(response):
    stream = response[2] & 0x7F
    function = response[3]

    if stream != 6 or function != 12:
        raise RuntimeError(f"Expected S6F12, got S{stream}F{function}")


def run_single_measurement(run_count):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.connect((EQUIPMENT_IP, PORT))

    select(sock)

    print("Starting warm-up...")
    for _ in range(5):
        send_hsms(sock, create_s1f1())
        response = receive_hsms(sock)
        verify_s1f2(response)

    print("Completed warm-up")

    latencies = []
    message_count = 0
    total_payload_bytes = 0

    print("Starting throughput test...")

    start_total = time.perf_counter()

    while time.perf_counter() - start_total < DURATION:
        msg = create_s6f11(PAYLOAD_SIZE_BYTES)

        start = time.perf_counter()
        send_hsms(sock, msg)
        response = receive_hsms(sock)
        end = time.perf_counter()

        verify_s6f12(response)

        elapsed_ms = (end - start) * 1000
        latencies.append(elapsed_ms)

        message_count += 1
        total_payload_bytes += PAYLOAD_SIZE_BYTES

    end_total = time.perf_counter()
    actual_duration = end_total - start_total

    sock.close()

    messages_per_sec = message_count / actual_duration
    payload_mib_sec = (total_payload_bytes / (1024 * 1024)) / actual_duration

    print("\n--- THROUGHPUT RESULTS ---")
    print(f"Duration: {actual_duration:.3f} sec")
    print(f"Messages: {message_count}")
    print(f"Messages/sec: {messages_per_sec:.2f}")
    print(f"Payload throughput: {payload_mib_sec:.2f} MiB/sec")
    print(f"Mean RTT: {statistics.mean(latencies):.3f} ms")
    print(f"Median RTT: {statistics.median(latencies):.3f} ms")
    print(f"StdDev: {statistics.stdev(latencies):.3f} ms")
    print(f"Min: {min(latencies):.3f} ms")
    print(f"Max: {max(latencies):.3f} ms")

    file_name = (
        f"results_throughput{PAYLOAD_SIZE}_"
        f"{ENCRYPTION_USED}_{run_count + 1}.txt"
    )

    with open(file_name, "w") as f:
        f.write(f"Messages/sec={messages_per_sec:.2f}\n")
        f.write(f"duration_sec={actual_duration:.3f}\n")
        f.write(f"payload_size_bytes={PAYLOAD_SIZE_BYTES}\n")
        f.write(f"total_messages={message_count}\n")
        f.write(f"payload_throughput_MiB_sec={payload_mib_sec:.2f}\n")
        f.write(f"mean_rtt_ms={statistics.mean(latencies):.3f}\n")
        f.write(f"median_rtt_ms={statistics.median(latencies):.3f}\n")
        f.write(f"stddev_ms={statistics.stdev(latencies):.3f}\n")
        f.write(f"min_ms={min(latencies):.3f}\n")
        f.write(f"max_ms={max(latencies):.3f}\n")
        f.write("---raw_latencies_ms---\n")

        for t in latencies:
            f.write(f"{t}\n")


for x in range(MEASUREMENT_COUNT):
    print(f"\nStarting run {x + 1}/{MEASUREMENT_COUNT}")
    run_single_measurement(x)
    print(f"Completed run {x + 1}/{MEASUREMENT_COUNT}")
