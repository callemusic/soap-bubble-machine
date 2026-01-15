#!/usr/bin/env python
# Test raw TCP server to see if it's an HTTP issue
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 8080))
s.listen(1)
print("TCP server listening on port 8080...")
conn, addr = s.accept()
print("Connection from:", addr)
data = conn.recv(1024)
print("Received:", data)
conn.sendall("HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\nHello World!")
conn.close()
s.close()





