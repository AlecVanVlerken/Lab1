import socket
import os
import datetime

MAILBOX_DIR = "./users"


def handle_client(client_socket, mailbox_dir):
    try:
        domain_name = "kuleuven.be"  # Hardcode for now, maybe use dynamically fetched domain name later 
        client_socket.send(f"220 {domain_name} Service Ready\r\n".encode())

        mail_data = ""
        sender, recipient = None, None
        
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            
            # HELO
            if data.startswith("HELO"):
                client_socket.send(f"250 OK Hello {domain_name}\r\n".encode())
            
            # MAIL
            elif data.startswith("MAIL FROM:"):
                sender = data.split(":")[1].strip()
                client_socket.send(f"250 OK Sender {sender}\r\n".encode())
            
            # RCPT
            elif data.startswith("RCPT TO:"):
                recipient = data.split(":")[1].strip().split('@')[0]
                recipient_domain = data.split(":")[1].strip().split('@')[1]

                # Check if the recipient exists
                if os.path.exists(os.path.join(mailbox_dir, recipient)):
                    client_socket.send(f"250 OK Recipient {recipient}\r\n".encode())
                else:
                    client_socket.send(b"550 No such user\r\n")
                    break
            
            # DATA
            elif data.startswith("DATA"):
                client_socket.send(b"354 Start mail input; end with <CRLF>.<CRLF>\r\n")
                while True:
                    line = client_socket.recv(1024).decode()
                    if line == ".\r\n":
                        break
                    mail_data += line
                
                # Add time to the received message
                timestamp = datetime.datetime.now().strftime("%d/%m/%Y : %H:%M")
                mail_data = f"\n{mail_data}\nReceived: {timestamp}\n."
                
                # Save the message to the recipient's mailbox
                mailbox_path = os.path.join(mailbox_dir, recipient, "my_mailbox")
                with open(mailbox_path, "a") as mailbox:
                    mailbox.write(mail_data)
                
                client_socket.send(b"250 Message accepted for delivery\r\n")
            
            # QUIT
            elif data.startswith("QUIT"):
                break
    
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.send(f"221 {domain_name} Service closing transmission channel\r\n".encode())
        client_socket.close()


def start_mail_server(port, mailbox_dir=MAILBOX_DIR):
    if not os.path.exists(mailbox_dir):
        print(f"Error: The directory '{mailbox_dir}' does not exist.")
        sys.exit(1)
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", port))
    server_socket.listen() # insert backlog value if needed, now it's set to default
    print(f"Mail server running on port {port}...")
    
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        handle_client(client_socket, mailbox_dir)

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python mailserver_smtp.py <port>")
        sys.exit(1)
    
    try:
        my_port = int(sys.argv[1])
    except ValueError:
        print(f"Error: The port '{sys.argv[1]}' is not a valid number.")
        sys.exit(1)
    
    start_mail_server(my_port)
