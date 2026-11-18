import sys
import socket
import select
import struct
import time


ON_PORT = 5000
TIMEOUT = 1.0
LSP_PERIOD = 15.0
PRINT_PERIOD = 15.0


my_id = None
neighbors = {}
global_map = {}
last_lsp_time = 0.0
last_print_time = 0.0
seq_no = 0
received_seq_nums = {}


def encode_lsp(origin_id, seq_num, links):
    pkt = origin_id.encode('ascii')                         # 1 byte
    pkt += seq_num.to_bytes(4, byteorder='big')             # 4 bytes
    pkt += len(links).to_bytes(2, byteorder='big')          # 2 bytes
    for dest_id, cost in links.items():
        pkt += dest_id.encode('ascii')                      # 1 byte
        pkt += cost.to_bytes(4, byteorder='big', signed=True) # 4 bytes
    return pkt


def decode_lsp(data):
    origin_id = data[0:1].decode('ascii')
    seq_num   = int.from_bytes(data[1:5], 'big')
    count     = int.from_bytes(data[5:7], 'big')
    links = {}
    offset = 7
    for _ in range(count):
        dest_id = data[offset : offset + 1].decode('ascii')
        cost    = int.from_bytes(data[offset + 1 : offset + 5], 'big', signed=True)
        links[dest_id] = cost
        offset += 5
    return origin_id, seq_num, links


def udp_update(data, sender_addr, udp_sock):
    global global_map, received_seq_nums

    try:
        origin_id, lsp_seq, links = decode_lsp(data)
    except Exception as e:
        print(f"Error decoding LSP from {sender_addr}: {e}", file=sys.stderr)
        return False
    if origin_id == my_id:
        return False

    highest_seen = received_seq_nums.get(origin_id, 0)

    if lsp_seq <= highest_seen:
        return False

    received_seq_nums[origin_id] = lsp_seq
    global_map[origin_id] = links
    print(f"[{my_id}] Received LSP from node {origin_id} (seq={lsp_seq}): {links}")

    if udp_sock is not None:
        send_info(udp_sock, lsp_data=data, exclude_addr=sender_addr)

    return True


def tcp_update(num_tuples: int, data: bytes):
    global neighbors, global_map, my_id

    new_neighbors = {}
    new_id = None
    offset = 0

    for _ in range(num_tuples):
        node_id = data[offset : offset + 1].decode("ascii")
        ip = socket.inet_ntoa(data[offset + 1 : offset + 5])
        port = int.from_bytes(data[offset + 5 : offset + 7], "big")
        cost = int.from_bytes(data[offset + 7 : offset + 11], "big", signed=True)
        offset += 11

        if cost == 0:
            new_id = node_id
        elif cost > 0:
            new_neighbors[node_id] = {"ip": ip, "port": port, "cost": cost}

    if new_id is not None:
        my_id = new_id

    neighbors.clear()
    neighbors.update(new_neighbors)

    if my_id is not None:
        global_map[my_id] = {nid: info["cost"] for nid, info in neighbors.items()}
        parts = [f"{my_id}=0"] + [
            f"{nid}={info['cost']}" for nid, info in sorted(neighbors.items())
        ]
        print(f"Neighbor link state: {','.join(parts)}")



def send_info(
    udp_sock: socket.socket, lsp_data: bytes = None, exclude_addr: tuple = None
):
    global my_id, seq_no, neighbors

    if lsp_data is None:
        if my_id is None:
            return
        seq_no += 1
        own_links = {nid: info["cost"] for nid, info in neighbors.items()}
        lsp_data = encode_lsp(my_id, seq_no, own_links)
        print(
            f"[{my_id}] Sending LSP (seq={seq_no}) to neighbours: {list(neighbors.keys())}"
        )

    for nid, info in neighbors.items():
        dest_addr = (info["ip"], info["port"])
        if exclude_addr and dest_addr == exclude_addr:
            continue
        try:
            udp_sock.sendto(lsp_data, dest_addr)
        except OSError as e:
            print(
                f"Error sending UDP packet to {nid} at {dest_addr}: {e}",
                file=sys.stderr,
            )


def set_up_udp(vn_ip, udp_port):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_sock.bind((vn_ip, udp_port))
    except OSError as e:
        print(f"Error: cannot bind UDP port {udp_port}: {e}", file=sys.stderr)
        sys.exit(1)

    return udp_sock


def set_up_tcp(on_ip):
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp_sock.connect((on_ip, ON_PORT))
    except OSError as e:
        print(f"Error: cannot connect to {on_ip}:{ON_PORT}: {e}", file=sys.stderr)
        sys.exit(1)

    return tcp_sock


def parse_args():
    if len(sys.argv) != 4:
        print("Usage: ./v_node <on-ip> <vn-ip> <udp-port>", file=sys.stderr)
        sys.exit(1)

    on_ip = sys.argv[1]
    vn_ip = sys.argv[2]
    try:
        udp_port = int(sys.argv[3])
    except ValueError:
        print("Error: UDP Port must be an integer", file=sys.stderr)
        sys.exit(1)

    return on_ip, vn_ip, udp_port


def on_connect(tcp_sock, vn_ip, udp_port):
    ip_bytes = socket.inet_aton(vn_ip)                  # 4 bytes
    port_bytes = udp_port.to_bytes(2, byteorder="big")  # 2 bytes
    tcp_sock.sendall(ip_bytes + port_bytes)
    print("CONNECT sent")


def print_global_graph():
    global global_map, my_id

    if not global_map:
        return

    all_nodes = sorted(
        set(global_map.keys()) | {dst for links in global_map.values() for dst in links}
    )

    print("\n" + "-" * 50)
    print(f"Global Knowledge of {my_id}")
    print(f"Nodes: {', '.join(all_nodes)}")
    print("Per Node neighbor information:")
    for u in all_nodes:
        nbrs = global_map.get(u, {})
        nbr_str = (
            ", ".join(f"{v}:{c}" for v, c in sorted(nbrs.items())) if nbrs else "none"
        )
        print(f"  Node {u} -> {nbr_str}")

    print("\nNeighbor cost matrix:\n")
    print(" " + "\t ".join(all_nodes))
    for i, u in enumerate(all_nodes):
        targets = all_nodes
        costs = []
        
        for v in targets:
            cost = global_map.get(u, {}).get(v, global_map.get(v, {}).get(u, -1))
            if u == v:
                cost = 0
            if cost != -1:
                costs.append(" " + str(cost))
            else:    
                costs.append(str(cost))
        # indent = "\t" * i
        # print(f"# Costs from {u} to {', '.join(targets)}")
        print(f"\t".join(costs))
    print("\n" + "-" * 50)


def main():
    global last_lsp_time, last_print_time

    on_ip, vn_ip, udp_port = parse_args()

    udp_sock = set_up_udp(vn_ip, udp_port)

    tcp_sock = set_up_tcp(on_ip)

    sock_list = [udp_sock, tcp_sock]

    on_connect(tcp_sock, vn_ip, udp_port)

    last_lsp_time = time.monotonic()
    last_print_time = time.monotonic()
    tcp_buffer = b""

    try:
        while True:
            try:
                readable, _, _ = select.select(sock_list, [], [], TIMEOUT)
            except OSError as e:
                print(f"Select error: {e}", file=sys.stderr)
                break

            for sock in readable:
                if sock is tcp_sock:
                    # decode message and update neighbors and global_map
                    try:
                        data = tcp_sock.recv(4096)
                    except OSError as e:
                        print(f"TCP error recv: {e}", file=sys.stderr)
                        data = b""

                    if not data:
                        print("Oracle Node disconnected...")
                        sock_list.remove(tcp_sock)
                        tcp_sock.close()

                    else:
                        tcp_buffer += data
                        while len(tcp_buffer) >= 2:
                            num_tuples = int.from_bytes(tcp_buffer[:2], "big")
                            expected_len = 2 + num_tuples * 11
                            if len(tcp_buffer) < expected_len:
                                break
                            tuple_data = tcp_buffer[2:expected_len]
                            tcp_buffer = tcp_buffer[expected_len:]
                            tcp_update(num_tuples, tuple_data)
                            send_info(udp_sock)
                            last_lsp_time = time.monotonic()

                elif sock is udp_sock:
                    try:
                        data, addr = udp_sock.recvfrom(4096)
                        udp_update(data, addr, udp_sock)
                    except OSError as e:
                        print(f"UDP recv error: {e}", file=sys.stderr)

            now = time.monotonic()

            if now - last_lsp_time >= LSP_PERIOD:
                send_info(udp_sock)
                last_lsp_time = now
            if now - last_print_time >= PRINT_PERIOD:
                print_global_graph()
                last_print_time = now
    except (KeyboardInterrupt, SystemExit):
        print("\nShutting down virtual node...")
    finally:
        tcp_sock.close()
        udp_sock.close()


if __name__ == "__main__":
    main()