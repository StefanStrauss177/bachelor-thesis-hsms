import socket
import struct

# IP address of the HSMS equipment.
EQUIPMENT = "<Equipment_IP>"

# TCP port used for the HSMS connection.
PORT = <PORT>


def receive_full_msg(sock, byte_count):
    """
    Reads exactly the specified number of bytes from a TCP socket.

    TCP is a byte-stream protocol and does not preserve message boundaries. A single send() may be received in multiple
    recv() calls, or multiple sends may be combined into a single recv() call.

    This function repeatedly reads from the socket until exactly the requested number of bytes have been received,
    ensuring that the complete message is reconstructed.

    :param sock: The socket to read from
    :param byte_count: Number of bytes to read from the incoming stream
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
    Receives one complete HSMS message.

    The first four bytes of an HSMS transmission contain the message length. After reading this length field, the
    function reads the exact number of bytes belonging to the HSMS message.

    :param sock: The socket to read from
    :return: The received HSMS message without the 4-byte length field
    """
    length = struct.unpack(">I", receive_full_msg(sock, 4))[0]
    msg = receive_full_msg(sock, length)
    return msg


def send_hsms(sock, msg):
    """
    Sends a single HSMS message.

    HSMS messages are preceded by a 4-byte length field. This function adds the length field and then sends the complete
    byte sequence over the TCP socket.

    :param sock: The socket to send to
    :param msg: The HSMS message without the 4-byte length field
    """
    sock.sendall(struct.pack(">I", len(msg)) + msg)


def hsms_header(session_id, stream, function, wbit, ptype, stype, system_bytes):
    """
    Creates a 10-byte HSMS message header.

    The header is used for both HSMS control messages, such as Select.req and Select.rsp, and SECS-II data messages,
    such as S1F1, S1F2, S6F11 and S6F12.

    :param session_id: HSMS Session ID as a 2-byte unsigned integer
    :param stream: SECS-II stream number. The most significant bit of this byte is used as the W-bit
    :param function: SECS-II function number
    :param wbit: Wait Bit. If True, the receiver is expected to send a response
    :param ptype: HSMS Presentation Type. Normally 0 for standard SECS-II messages
    :param stype: HSMS Session Type. Used for control messages. Set to 0 for normal SECS-II data messages
    :param system_bytes: 4-byte transaction identifier used to connect requests and responses
    :return: A 10-byte HSMS header as a bytes object
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
    how many bytes are used to encode the length.

    :param fmt: SECS-II format code, for example List, ASCII or U1
    :param length: Length of the item. For normal data items this is the number of data bytes. For List items this is
    the number of contained list elements
    :return: Encoded SECS-II item header as bytes
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
    specifies the number of contained items.

    :param items: Iterable containing already encoded SECS-II items
    :return: Encoded SECS-II List item
    """
    body = b"".join(items)
    return item_header(0x00, len(items)) + body


def secs_ascii(text):
    """
    Creates a SECS-II ASCII item.

    This is used in the S1F2 response to return a simple model and revision string.

    :param text: ASCII text to encode
    :return: Encoded SECS-II ASCII item
    """
    data = text.encode("ascii")
    return item_header(0x40, len(data)) + data


def secs_u1(value):
    """
    Creates a SECS-II U1 item.

    U1 represents an unsigned 1-byte integer. In this script it is used for the S6F12 acknowledgement code.

    :param value: Integer value between 0 and 255
    :return: Encoded SECS-II U1 item
    """
    return item_header(0xA4, 1) + bytes([value])


def create_s1f2():
    """
    Creates an S1F2 response message body.

    S1F2 is the response to S1F1. In this simplified implementation it returns a list containing a model name and a
    software revision string.

    :return: Encoded SECS-II body for S1F2
    """
    return secs_list([
        secs_ascii("MODEL123"),
        secs_ascii("1.0")
    ])


def create_s6f12():
    """
    Creates an S6F12 response message body.

    S6F12 acknowledges an S6F11 Event Report Send message. In this simplified implementation U1 0 is used as the
    acknowledgement value, meaning that the report was accepted.

    :return: Encoded SECS-II body for S6F12
    """
    return secs_u1(0)


def handle_connection(conn):
    """
    Handles messages received through an established HSMS connection.

    The function continuously receives complete HSMS messages, extracts the HSMS header fields and responds to the
    supported message types:
    - Select.req with Select.rsp
    - S1F1 with S1F2
    - S6F11 with S6F12

    :param conn: Established TCP socket connection to the HSMS host
    """
    while True:
        # Receive one complete HSMS message.
        msg = receive_hsms(conn)

        # Extract the HSMS header fields from the 10-byte HSMS header.
        session_id = struct.unpack(">H", msg[0:2])[0]
        stream = msg[2] & 0x7F
        function = msg[3]
        ptype = msg[4]
        stype = msg[5]
        system_bytes = struct.unpack(">I", msg[6:10])[0]

        # Select.req received, respond with Select.rsp.
        if stype == 1:
            response_header = hsms_header(
                session_id=session_id,
                stream=0,
                function=0,
                wbit=False,
                ptype=0,
                stype=2,
                system_bytes=system_bytes
            )
            send_hsms(conn, response_header)
            print("Select.rsp sent")
            continue

        # S1F1 received, respond with S1F2.
        if stream == 1 and function == 1:
            body = create_s1f2()
            response_header = hsms_header(
                session_id=session_id,
                stream=1,
                function=2,
                wbit=False,
                ptype=0,
                stype=0,
                system_bytes=system_bytes
            )
            send_hsms(conn, response_header + body)
            continue

        # S6F11 received, respond with S6F12.
        if stream == 6 and function == 11:
            body = create_s6f12()
            response_header = hsms_header(
                session_id=session_id,
                stream=6,
                function=12,
                wbit=False,
                ptype=0,
                stype=0,
                system_bytes=system_bytes
            )
            send_hsms(conn, response_header + body)
            continue


def main():
    """
    Starts the passive HSMS equipment side.

    The equipment opens a TCP server socket, waits for incoming host connections and passes each established connection
    to the connection handler.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Ensures that TCP sends data immediately instead of waiting to combine small packets.
    server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    # Bind the server socket to the equipment IP address and HSMS port.
    server.bind((HOST, PORT))

    # Allow one pending connection.
    server.listen(1)

    print(f"Equipment listening on {HOST}:{PORT}")

    try:
        while True:
            # Wait for a host/client to connect.
            conn, addr = server.accept()
            print(f"Connected from {addr}")

            try:
                handle_connection(conn)
            except ConnectionError:
                print("Connection closed by host")
            finally:
                conn.close()

    except KeyboardInterrupt:
        print("Stopping equipment")
    finally:
        server.close()


main()