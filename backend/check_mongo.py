import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('UP' if s.connect_ex(('localhost', 27017)) == 0 else 'DOWN')
s.close()
