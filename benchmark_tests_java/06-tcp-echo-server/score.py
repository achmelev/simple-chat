import os
import subprocess
import socket
import time


def send_line(sock, msg):
    sock.sendall((msg + "\n").encode())


def recv_line(sock):
    data = b""
    while True:
        ch = sock.recv(1)
        if not ch or ch == b"\n":
            break
        data += ch
    return data.decode().rstrip("\r")


def score(workdir):
    bin_network = os.path.join(workdir, "bin", "org", "network")
    if not os.path.isdir(bin_network):
        return 0.0
    class_files = [f for f in os.listdir(bin_network) if f.endswith(".class")]
    if not class_files:
        return 0.0

    compiled_score = 0.3
    classpath = os.path.join(workdir, "bin")
    class_name = "org.network.EchoServer"
    port = 19283

    server_proc = None
    try:
        server_proc = subprocess.Popen(
            ["java", "-cp", classpath, class_name, str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.5)

        if server_proc.poll() is not None:
            return compiled_score

        passed = 0
        total = 0

        # Test 1: basic echo of multiple messages
        try:
            s = socket.create_connection(("localhost", port), timeout=5)
            s.settimeout(5)
            messages = ["hello", "world", "foo bar baz", "12345"]
            for msg in messages:
                total += 1
                send_line(s, msg)
                response = recv_line(s)
                if response == msg:
                    passed += 1
            send_line(s, "QUIT")
            s.close()
        except Exception:
            pass

        # Test 2: server still accepts new connection after first client left
        try:
            s = socket.create_connection(("localhost", port), timeout=5)
            s.settimeout(5)
            total += 1
            send_line(s, "second connection")
            response = recv_line(s)
            if response == "second connection":
                passed += 1
            send_line(s, "QUIT")
            s.close()
        except Exception:
            pass

        # Test 3: two concurrent connections are handled independently
        try:
            s1 = socket.create_connection(("localhost", port), timeout=5)
            s2 = socket.create_connection(("localhost", port), timeout=5)
            s1.settimeout(5)
            s2.settimeout(5)

            send_line(s1, "from client one")
            send_line(s2, "from client two")

            total += 2
            r1 = recv_line(s1)
            r2 = recv_line(s2)

            if r1 == "from client one":
                passed += 1
            if r2 == "from client two":
                passed += 1

            send_line(s1, "QUIT")
            send_line(s2, "QUIT")
            s1.close()
            s2.close()
        except Exception:
            pass

        if passed == 0:
            return compiled_score
        if passed == total:
            return 1.0
        return compiled_score + (1.0 - compiled_score) * (passed / total)

    finally:
        if server_proc is not None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()
