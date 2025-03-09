import socket
import os
import sys

# POP3 Commands
POP3_USER = "USER"
POP3_PASS = "PASS"
POP3_STAT = "STAT"
POP3_LIST = "LIST"
POP3_RETR = "RETR"
POP3_DELE = "DELE"
POP3_RSET = "RSET"
POP3_QUIT = "QUIT"

# Response messages
POP3_OK = "+OK"
POP3_ERR = "-ERR"

# Path to user information and mailboxes
USERINFO_FILE = "userinfo.txt"
MAILBOX_DIR = "./users"

def send_response(client_socket, message):
    client_socket.send(f"{message}\r\n".encode())

def handle_client(client_socket, addr):
    try:
        # Send greeting message
        send_response(client_socket, POP3_OK + " POP3 server ready")

        # Variables to track user state
        authenticated = False
        current_user = None
        mailbox_path = None
        marked_for_deletion = []

        while True:
            data = client_socket.recv(1024).decode().strip()
            if not data:
                continue

            command, *args = data.split()

            if command == POP3_USER:
                if authenticated:
                    send_response(client_socket, POP3_ERR + " Already authenticated")
                elif len(args) != 1:
                    send_response(client_socket, POP3_ERR + " Invalid USER command")
                else:
                    username = args[0]
                    current_user = username
                    send_response(client_socket, POP3_OK + " User accepted")

            elif command == POP3_PASS:
                if not current_user:
                    send_response(client_socket, POP3_ERR + " USER command must be issued first")
                elif authenticated:
                    send_response(client_socket, POP3_ERR + " Already authenticated")
                elif len(args) != 1:
                    send_response(client_socket, POP3_ERR + " Invalid PASS command")
                else:
                    password = args[0]
                    # Check if the user exists and if password matches
                    if authenticate_user(current_user, password):
                        authenticated = True
                        mailbox_path = os.path.join(MAILBOX_DIR, current_user)
                        send_response(client_socket, POP3_OK + " Password accepted")
                    else:
                        send_response(client_socket, POP3_ERR + " Invalid password")

            elif command == POP3_STAT:
                if not authenticated:
                    send_response(client_socket, POP3_ERR + " Not authenticated")
                else:
                    # Stat: Return the number of messages and the size of the mailbox
                    email_files = os.listdir(mailbox_path)
                    email_count = len(email_files)
                    total_size = sum(os.path.getsize(os.path.join(mailbox_path, email)) for email in email_files)
                    send_response(client_socket, POP3_OK + f" {email_count} {total_size}")

            elif command == POP3_LIST:
                if not authenticated:
                    send_response(client_socket, POP3_ERR + " Not authenticated")
                else:
                    # List available emails in the user's mailbox
                    email_files = os.listdir(mailbox_path)
                    email_count = len(email_files)
                    if email_count == 0:
                        send_response(client_socket, POP3_ERR + " No messages")
                    else:
                        # List the email file indexes
                        for i, email_file in enumerate(email_files):
                            email_size = os.path.getsize(os.path.join(mailbox_path, email_file))
                            send_response(client_socket, f"{i+1} {email_size}")

                        send_response(client_socket, POP3_OK + " End of message list")

            elif command == POP3_RETR:
                if not authenticated:
                    send_response(client_socket, POP3_ERR + " Not authenticated")
                elif len(args) != 1 or not args[0].isdigit():
                    send_response(client_socket, POP3_ERR + " Invalid RETR command")
                else:
                    email_index = int(args[0]) - 1
                    email_files = os.listdir(mailbox_path)

                    if email_index < 0 or email_index >= len(email_files):
                        send_response(client_socket, POP3_ERR + " No such message")
                    else:
                        email_file = email_files[email_index]
                        with open(os.path.join(mailbox_path, email_file), 'r') as f:
                            email_content = f.read()

                        send_response(client_socket, POP3_OK + " Message follows")
                        client_socket.send(email_content.encode())
                        send_response(client_socket, ".")

            elif command == POP3_DELE:
                if not authenticated:
                    send_response(client_socket, POP3_ERR + " Not authenticated")
                elif len(args) != 1 or not args[0].isdigit():
                    send_response(client_socket, POP3_ERR + " Invalid DELE command")
                else:
                    email_index = int(args[0]) - 1
                    email_files = os.listdir(mailbox_path)

                    if email_index < 0 or email_index >= len(email_files):
                        send_response(client_socket, POP3_ERR + " No such message")
                    else:
                        email_file = email_files[email_index]
                        marked_for_deletion.append(email_file)
                        send_response(client_socket, POP3_OK + " Message marked for deletion")

            elif command == POP3_RSET:
                if not authenticated:
                    send_response(client_socket, POP3_ERR + " Not authenticated")
                else:
                    # Reset: Unmark all emails marked for deletion
                    marked_for_deletion.clear()
                    send_response(client_socket, POP3_OK + " Reset completed")

            elif command == POP3_QUIT:
                if not authenticated:
                    send_response(client_socket, POP3_ERR + " Not authenticated")
                else:
                    # Delete marked emails
                    for email_file in marked_for_deletion:
                        os.remove(os.path.join(mailbox_path, email_file))

                    send_response(client_socket, POP3_OK + " Goodbye")
                    break

            else:
                send_response(client_socket, POP3_ERR + " Unknown command")

    finally:
        client_socket.close()

def authenticate_user(username, password):
    try:
        with open(USERINFO_FILE, 'r') as file:
            for line in file:
                stored_user, stored_pass = line.split()
                if stored_user == username and stored_pass == password:
                    return True
    except FileNotFoundError:
        return False
    return False

def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen()
    print(f"POP3 Server started on port {port}...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        handle_client(client_socket, addr)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python popserver.py <POP3_port>")
        sys.exit(1)

    pop3_port = int(sys.argv[1])
    start_server(pop3_port)
