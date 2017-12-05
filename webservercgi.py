import errno
import os
import signal
import socket
import cgi
import pymysql.cursors

SERVER_ADDRESS = (HOST, PORT) = '', 8888
REQUEST_QUEUE_SIZE = 1024

def grim_reaper(signum, frame):
    while True:
        try:
            pid, status = os.waitpid(
                -1,          # Wait for any child process
                 os.WNOHANG  # Do not block and return EWOULDBLOCK error
            )
        except OSError:
            return

        if pid == 0:  # no more zombies
            return

def write_header(client_connection):
    client_connection.sendall(b"HTTP/1.1 200 Document Follows\r\n")
    client_connection.sendall(b"Server: CS 252 lab 6\r\n")

def write_content_type(client_connection):
    client_connection.sendall(b"Content-Type: text/html\r\n\r\n")

def write_content(client_connection):
    client_connection.sendall(b"""<!DOCTYPE html>
<html>
<head>
<title>Pixelgraph: Welcome!</title>
</head>

<body>
<form method=\"post\" >
Username: <br>
<input type=\"text\" name=\"username\"><br>
Password: <br>
<input type=\"password\" name=\"password\"><br>
<input type=\"submit\" value=\"Submit\"><br>
</form>
<form method=\"post\">
<input type=\"hidden\" name=\"-newacct\">
<input type=\"submit\" value=\"Create Account\"><br>
</form>
</body>

</html> """)

def write_contentnomatch(client_connection):
    client_connection.sendall(b"""<!DOCTYPE html>
<html>
<head>
<title>Pixelgraph: Welcome!</title>
</head>

<body>
Error: Passwords Do Not Match!<br>
<form method=\"post\" >
Choose Username: <br>
<input type=\"text\" name=\"_newusername\"><br>
Choose Password: <br>
<input type=\"password\" name=\"_newpassword\"><br>
Repeat Password: <br>
<input type=\"password\" name=\"password\"><br>
<input type=\"submit\" value=\"Submit\"><br>
</form>


</body>

</html> """)


def write_contentwrong(client_connection):
    client_connection.sendall(b"""<!DOCTYPE html>
<html>
<head>
<title>Pixelgraph: Welcome!</title>
</head>

<body>
Wrong Username or Password!  Try again or create a new user:<br>
<form method=\"post\" >
Username: <br>
<input type=\"text\" name=\"username\"><br>
Password: <br>
<input type=\"password\" name=\"password\"><br>
<input type=\"submit\" value=\"Submit\"><br>
</form>
<form method=\"post\">
<input type=\"hidden\" name=\"-newacct\">
<input type=\"submit\" value=\"Create Account\"><br>
</form>
</body>

</html> """)

def write_contentnew(client_connection):
    client_connection.sendall(b"""<!DOCTYPE html>
<html>
<head>
<title>Pixelgraph: Welcome!</title>
</head>

<body>
<form method=\"post\" >
Choose Username: <br>
<input type=\"text\" name=\"_newusername\"><br>
Choose Password: <br>
<input type=\"password\" name=\"_newpassword\"><br>
Repeat Password: <br>
<input type=\"password\" name=\"password\"><br>
<input type=\"submit\" value=\"Submit\"><br>
</form>

</body>

</html> """)


def write_contentgraph(client_connection, user, passw):
    client_connection.sendall(b"""<!DOCTYPE html>
<html>
<head>
<title>Pixelgraph: Welcome!</title>
</head>

<body>
put graph here!
username/password = """)
    client_connection.sendall(user.encode())
    client_connection.sendall(passw.encode())
    client_connection.sendall(b"""
</body>

</html> """)



def handle_request(client_connection):
    request = client_connection.recv(1024)
    decoded = request.decode()
    
    a = decoded.split()
    print(decoded)
    geta = a[-1]
    
    http_response = b"""\
HTTP/1.1 200 OK

Hello, World!
"""
    #client_connection.sendall(http_response)
    write_header(client_connection)
    write_content_type(client_connection)
    if geta.startswith("-"):
        write_contentnew(client_connection)
    elif geta.startswith("u"):
        b = geta.split("&")
        user = b[0]
        user = user[9:]
        passw = b[1]
        passw = passw[9:]
        print(user)
        print(passw)
        print("testing username: " + user + " and password: " + passw + "\n")
        connection = pymysql.connect(host='localhost',user='root', password='gustavo', db='art', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                sql = "SELECT `username`, `password` FROM `users` WHERE `username`=%s AND `password`=%s"
                cursor.execute(sql, (user, passw))
                result = cursor.fetchone()
                print(result)
                if result != None:
                    write_contentgraph(client_connection, user, passw)
                else:
                    write_contentwrong(client_connection)
        finally:
            connection.close()

        #write_contentgraph(client_connection, user, passw)
    elif geta.startswith("_"):
        b = geta.split("&")
        user = b[0]
        user = user[13:]
        passw = b[1]
        passw = passw[13:] 
        passwt = b[2]
        passwt = passwt[9:]
        print(user)
        print(passw)
        if passwt == passw :	
            print("adding user " + user + "with password " + passw)
            connection = pymysql.connect(host='localhost',user='root', password='gustavo', db='art', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
            try:
                with connection.cursor() as cursor:
                    sql = "INSERT INTO `users` (`username`, `password`) VALUES (%s, %s)"
                    cursor.execute(sql, (user, passw))

                connection.commit()
            finally:
                connection.close()

            write_contentgraph(client_connection, user, passw)
        else:
            write_contentnomatch(client_connection)
    else:
        write_content(client_connection)
    
def serve_forever():
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(SERVER_ADDRESS)
    listen_socket.listen(REQUEST_QUEUE_SIZE)
    print('Serving HTTP on port {port} ...'.format(port=PORT))

    signal.signal(signal.SIGCHLD, grim_reaper)

    while True:
        try:
            client_connection, client_address = listen_socket.accept()
        except IOError as e:
            code, msg = e.args
            # restart 'accept' if it was interrupted
            if code == errno.EINTR:
                continue
            else:
                raise

        pid = os.fork()
        if pid == 0:  # child
            listen_socket.close()  # close child copy
            handle_request(client_connection)
            client_connection.close()
            os._exit(0)
        else:  # parent
            client_connection.close()  # close parent copy and loop over

if __name__ == '__main__':
    serve_forever()
