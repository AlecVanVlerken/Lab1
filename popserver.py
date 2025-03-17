import socket
import os
import sys
import threading

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

def handle_client(client_socket):
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
                continue #niet eerder break?

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
                # Path to the user's mailbox file
                mailbox_file = os.path.join(mailbox_path, "my_mailbox.txt")

                # Check if the mailbox file exists
                if not os.path.exists(mailbox_file):
                    send_response(client_socket, POP3_ERR + " 0 0")  # No emails, size 0
                else:
                    # Read the mailbox file
                    with open(mailbox_file, "r") as f:
                        # Count emails (each email ends with a single "." on a new line)
                        emails = f.read().strip().split("\n.\n")
                        
                    if len(emails) == 0 or emails == [""]:  # Check if mailbox is empty
                        send_response(client_socket, POP3_ERR + " 0 0")
                    else:
                        email_count = len(emails) if emails[0] else 0  # Avoid counting empty file

                        # Get the total size of the mailbox file in bytes
                        total_size = os.path.getsize(mailbox_file)

                        # Send response: Number of emails and total size
                        send_response(client_socket, POP3_OK + f" {email_count} {total_size}")


            elif command == POP3_LIST:
                mailbox_file = os.path.join(mailbox_path, "my_mailbox.txt")

                if not os.path.exists(mailbox_file):
                    send_response(client_socket, POP3_ERR + " No messages")
                else:
                    with open(mailbox_file, "r") as f:
                        emails = f.read().strip().split("\n.\n")  # Split emails using the delimiter "."
        
                    if len(emails) == 0 or emails == [""]:  # Check if mailbox is empty
                        send_response(client_socket, POP3_ERR + " No messages")
                    else:
                        message = ""
                        for i, email in enumerate(emails):
                            email_size = len(email.encode())  # Get email size in bytes
                            message += f"{i+1} {email_size}\r\n"
                            
                        message += POP3_OK + " End of message list"

                        send_response(client_socket, message)

            elif command == POP3_RETR:
                if len(args) != 1 or not args[0].isdigit():
                    send_response(client_socket, POP3_ERR + " Invalid RETR command")
                else:
                    email_index = int(args[0]) - 1
                    mailbox_file = os.path.join(mailbox_path, "my_mailbox.txt")
                    if not os.path.exists(mailbox_file):
                        send_response(client_socket, POP3_ERR + " No messages")
                    else:
                        with open(mailbox_file, "r") as f:
                            emails = f.read().strip().split("\n.\n")

                        if email_index < 0 or email_index >= len(emails):
                            send_response(client_socket, POP3_ERR + " No such message")
                        else:
                            email_content = emails[email_index]
                            message = POP3_OK + " Message follows\r\n" + email_content + "\r\n."
                            send_response(client_socket, message)

            elif command == POP3_DELE: # NOTE TO SELF: FOUT VOLGENS CHAT TOP Gpt
                if len(args) != 1 or not args[0].isdigit():
                    send_response(client_socket, POP3_ERR + " Invalid DELE command")
                else:
                    email_index = int(args[0]) - 1
                    mailbox_file = os.path.join(mailbox_path, "my_mailbox.txt")
                    if not os.path.exists(mailbox_file):
                        send_response(client_socket, POP3_ERR + " No messages")
                    else:
                        with open(mailbox_file, "r") as f:
                            emails = f.read().strip().split("\n.\n")

                        if email_index < 0 or email_index >= len(emails):
                            send_response(client_socket, POP3_ERR + " No such message")
                        else:
                            #if email_index not in marked_for_deletion:
                            marked_for_deletion.append(emails.pop(email_index))
                            with open(mailbox_file, "w") as f:
                                f.write("\n.\n".join(emails) + "\n.\n" if emails else "")
                            send_response(client_socket, POP3_OK + " Message marked for deletion")

            elif command == POP3_RSET:
                # Restore emails marked for deletion
                mailbox_file = os.path.join(mailbox_path, "my_mailbox.txt")

                if not os.path.exists(mailbox_file):
                    send_response(client_socket, POP3_ERR + " No messages")
                else:
                    with open(mailbox_file, "r") as f:
                        emails = f.read().strip().split("\n.\n")

                    # Add the deleted emails back into the mailbox file
                    for email in marked_for_deletion:
                        emails.append(email)

                    # Rewrite the mailbox file with the restored emails
                    with open(mailbox_file, "w") as f:
                        f.write("\n.\n".join(emails) + "\n.\n" if emails else "")

                    # Clear marked_for_deletion since the reset is complete
                    marked_for_deletion.clear()

                    send_response(client_socket, POP3_OK + " Reset completed")

            elif command == POP3_QUIT:
                marked_for_deletion.clear()

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
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python popserver.py <POP3_port>")
        sys.exit(1)

    pop3_port = int(sys.argv[1])
    start_server(pop3_port)
