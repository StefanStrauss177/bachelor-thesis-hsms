import socket
import struct
import time
import statistics

# IP address of the HSMS equipment.
HOST_IP = "<HOST_IP>"

# TCP port used for the HSMS connection.
PORT = <PORT>

# Size of the message payload in bytes.
PAYLOAD_SIZE_BYTES = <PAYLOAD_SIZE_IN_BYTES>

# Number of messages sent during each measurement.
RUNS = <NUMBER_OF_MESSAGES>

# Payload size label used only in the output file name.
PAYLOAD_SIZE = "<PAYLOAD_SIZE_LABEL>"

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
    """
    System Bytes are a 4 Byte field in the header, and are used to uniquely identify a Stream Function transaction
    from the set of all open transactions. It can understood as a unique HSMS Message ID.
    """
    global system_counter
    system_counter += 1
    return system_counter



def receive_full_msg(sock, byte_count):
    """
    Reads exactly n bytes from a TCP socket.

    TCP is a byte-stream protocol and does not preserve message boundaries. A single send() may be received in multiple
    recv() calls, or multiple sends may be combined into a single recv() call.

    This function repeatedly reads from the socket until exactly n bytes have been received, ensuring that the complete
    message is reconstructed.

    :param sock: The socket to read from
    :param byte_count: States how many bytes to read from the incoming stream, ensures that a message is complete
    :return: The reconstructed byte sequence
    """
    data = b""
    while len(data) < byte_count:
        chunk = sock.recv(byte_count - len(data))
        if not chunk:
            raise ConnectionError("Socket closed")
        data += chunk
    return data




def receive_hsms(sock):
    """
    Receives one HSMS message.

    :param sock: The socket to read from
    :return: The received HSMS message
    """
    # Retrieves the length of the HSMS message from the header, this is needed so the message can be fully reconstructed
    length = struct.unpack(">I", receive_full_msg(sock, 4))[0]
    # Get the full message from the TCP socket
    msg = receive_full_msg(sock, length)
    return msg


def send_hsms(sock, msg):
    """
        Sends a single HSMS message
    """
    sock.sendall(struct.pack(">I", len(msg)) + msg)

def hsms_header(session_id, stream, function, wbit, ptype, stype, system_bytes):
    """
    Creates a 10-byte HSMS message header.

    The header is used for both HSMS control messages (e.g. Select.req,
    Select.rsp) and SECS-II data messages (e.g. S1F1, S1F2, S6F11).

    :param session_id: HSMS Session ID (2-byte unsigned integer). Typically, 0xFFFF for HSMS control messages and a
    configured session ID for SECS-II messages.

    :param stream: SECS-II stream number (0-127). The most significant bit of the stream byte is reserved for the W-bit.

    :param function: SECS-II function number.

    :param wbit: Wait Bit. If True, the receiver is expected to send a reply. If False, no reply is expected.

    :param ptype: HSMS Presentation Type. Normally 0 for standard SECS-II messages.

    :param stype: HSMS Session Type. Used to distinguish control messages such as Select.req, Select.rsp, Linktest.req
    and Separate.req. Set to 0 for normal SECS-II messages.

    :param system_bytes: 4-byte transaction identifier used to connect requests and responses.

    :return: A struct packed 10-byte HSMS header as a bytes object.
    """
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
    """
    Creates a SECS-II item header.

    A SECS-II item header consists of a format code and a length field. The lower two bits of the first byte indicate
    how many bytes are used to encode the length (1, 2, or 3 bytes).

    :param fmt: SECS-II format code (e.g. List, U4, Binary).
    :param length: Number of data bytes contained in the item.

    :return: Encoded SECS-II item header as bytes.
    """
    if length <= 0xFF:
        return bytes([fmt | 1, length])
    elif length <= 0xFFFF:
        return bytes([fmt | 2]) + struct.pack(">H", length)
    else:
        return bytes([fmt | 3]) + length.to_bytes(3, "big")


def secs_list(items):
    """
    Creates a SECS-II List item.

    A List is a container that can hold one or more SECS-II items, including nested Lists. The List length field
    specifies the number of contained items, not the number of payload bytes.

    :param items: Iterable containing already encoded SECS-II items.

    :return: Encoded SECS-II List item.
    """
    body = b"".join(items)
    return item_header(0x00, len(items)) + body


def secs_u4(value):
    """
    Creates a SECS-II U4 (Unsigned 4-byte Integer) item.

    The value is encoded as a 32-bit unsigned integer using big-endian byte order.

    :param value: Integer value to encode.

    :return: Encoded SECS-II U4 item.
    """
    return item_header(0xB0, 4) + struct.pack(">I", value)


def secs_binary(data):
    """
    Creates a SECS-II Binary item.

    Binary items contain arbitrary byte data and are commonly used for raw payloads, bit fields, or vendor-specific
    information.

    :param data: Byte sequence to encode.

    :return: Encoded SECS-II Binary item.
    """
    return item_header(0x20, len(data)) + data

def create_s1f1():
    """
    Creates a s1f1 (Are you there?) message.

    s1f1 is typically used to ensure that a communication partner is still reachable. The W-Bit is set as this message
    expects a s1f2 response from the recipient.

    This message usually has no payload, so it has an empty SECS-II body. Therefore, the returned HSMS-Header represents
    the entire s1f1 message.

    :return: 10-byte HSMS header for an S1F1 message.
    """
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
    """
    Creates a s6f11 payload of the desired size using the passed payload size parameter.

    A s6f11 message uses a so-called SECS list. A SECS list can contain multiple SECS data items which are the smallest
    building blocks of a message, or additional SECS lists. A SECS data item is a information packet that defines a
    specific parameter along which its actual data value, like data collected during a specific event.

    A standard s6f11 message is structured as follows:
    <List
        DataID: unique identifier for the data set/transaction
        CEID: unique ID of the event that triggered the ERS message. Example: Wafer complete
        <List
            RPTID: id of the specific report linked to the triggered CEID. A single Event can have multiple reports.
            <L
                PAYLOAD: The actual data being sent by the report, these can be things like sensor readings.
            >
        >
    >

    :param payload_size: The size of the message, this can be adjusted using the constant PAYLOAD_SIZE.
    :return: A s6f11 message complete with a header.
    """
    payload = b"A" * payload_size

    body = secs_list([
        secs_u4(1),
        secs_u4(1001),
        secs_list([
            secs_list([
                secs_u4(1),
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
    """
    Performs the HSMS select procedure, the client sends Select.req, a response is received in form of a Select.rsp.
    If the response is not a Select.rsp, an Error is raised.

    :param sock: The socket to listen to
    :return: True if a Select.rsp was received, else an error is raised.
    :exception: If no Select.rsp was received, an Error is raised.
    """
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

    # Was a Select.rsp received?
    if response_stype == 2:
        print("Selected")
        return True
    else:
        raise RuntimeError(
            f"Expected Select.rsp, got {response_stype} instead"
        )


def main(run_count):
    """
    Sets the TCP socket up.
    - AF_INET: Tells the socket to communicate with IPv4 addresses
    - SOCK_STREAM: Tells the Socket to use TCP
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Ensures that TCP sends data immediately.
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.connect((EQUIPMENT_IP, PORT))

    # Performs the Select.req/Select.rsp transaction
    select(sock)

    """
        Perform a warm up to ensure that the connection has been established and exclude any latency spikes during
        connection establishment from the measurement.
    """
    print("Starting warm-up...")
    for _ in range(5):
        send_hsms(sock, create_s1f1())
        receive_hsms(sock)

    print("Completed warm-up")

    times = []

    """
        Performs i RUNS and sends multiple s6f11 messages while measuring the RTT, resulting in the latency that an encryption
        method adds to the connection. 
    """
    for i in range(RUNS):
        msg = create_s6f11(PAYLOAD_SIZE_BYTES)

        start = time.perf_counter()
        send_hsms(sock, msg)
        receive_hsms(sock)
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000
        times.append(elapsed_ms)

        print(f"{i + 1}/{RUNS}: {elapsed_ms:.3f} ms")

    # Close the Socket
    sock.close()

    print(f"Mean: {statistics.mean(times):.3f} ms")
    print(f"Median: {statistics.median(times):.3f} ms")
    print(f"StandardDeviation: {statistics.stdev(times):.3f} ms")
    print(f"Min: {min(times):.3f} ms")
    print(f"Max: {max(times):.3f} ms")

    file_name = f"results_latency{PAYLOAD_SIZE}_{ENCRYPTION_USED}{run_count+1}.txt"
    # Print the output in a file that can then be used/read
    with open(file_name, "w") as f:
        f.write(f"payload_size_bytes={PAYLOAD_SIZE_BYTES}\n")
        f.write(f"runs={RUNS}\n")
        f.write(f"mean_ms={statistics.mean(times):.3f}\n")
        f.write(f"median_ms={statistics.median(times):.3f}\n")
        f.write(f"stddev_ms={statistics.stdev(times):.3f}\n")
        f.write(f"min_ms={min(times):.3f}\n")
        f.write(f"max_ms={max(times):.3f}\n")
        f.write("---raw---\n")
        for t in times:
            f.write(f"{t}\n")


for x in range(MEASUREMENT_COUNT):
    print(f"Starting run {x + 1}")
    main(x)
    print(f"Completed run {x + 1}")