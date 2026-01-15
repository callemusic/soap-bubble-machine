#!/usr/bin/env python
# Test TCP server that keeps running
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 8080))
s.listen(5)
print("TCP server listening on port 8080... (Ctrl+C to stop)")

while True:
    conn, addr = s.accept()
    print("Connection from:", addr)
    try:
        data = conn.recv(1024)
        print("Received:", data[:100])
        response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: 13\r\n\r\nHello World!"
        conn.sendall(response)
        print("Response sent")
        conn.close()
    except Exception as e:
        print("Error:", e)
        conn.close()

