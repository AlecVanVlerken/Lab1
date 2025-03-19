import socket
import os
import datetime
import threading
import sys


MAILBOX_DIR = "./users"


def handle_client(client_socket, mailbox_dir):
    """
    Handles an SMTP client session, processing commands such as HELO, MAIL FROM, RCPT TO, DATA, and QUIT.
    
    Args:
        client_socket (socket.socket): The socket connected to the client.
        mailbox_dir (str): The directory where user mailboxes are stored.
    """
    try:
        domain_name = "kuleuven.be"
        client_socket.send(f"220 {domain_name} Service Ready\r\n".encode()) 

        mail_data = ""
        sender, recipient = None, None
        state = "INITIAL"  # Tracks the SMTP session state
        
        while True:
            data = client_socket.recv(1024).decode()
            if not data: 
                break

            if data.startswith("HELO"): 
                if state != "INITIAL":
                    client_socket.send(b"503 Bad sequence of commands\r\n")
                    continue
                state = "GREET"
                client_socket.send(f"250 OK Hello {domain_name}\r\n".encode())
            
            elif data.startswith("MAIL FROM:"):
                if state not in ["GREET", "DONE"]:  
                    client_socket.send(b"503 Bad sequence of commands\r\n")
                    continue
                sender = data.split(":")[1].strip()
                state = "MAIL"
                client_socket.send(f"250 OK Sender {sender}\r\n".encode())
            
            elif data.startswith("RCPT TO:"):
                if state not in ["MAIL", "RCPT"]:
                    client_socket.send(b"503 Bad sequence of commands\r\n")
                    continue
                if not sender:
                    client_socket.send(b"503 Bad sequence of commands: MAIL FROM must come before RCPT TO\r\n")
                    continue

                recipient = data.split(":")[1].strip()
                #recipient_domain = data.split(":")[1].strip().split('@')[1]

                if os.path.exists(os.path.join(mailbox_dir, recipient)):
                    state = "RCPT"
                    client_socket.send(f"250 OK Recipient {recipient}\r\n".encode())
                else:
                    client_socket.send(b"550 No such user\r\n")
                    continue
            
            elif data.startswith("DATA"):
                if state != "RCPT":
                    client_socket.send(b"503 Bad sequence of commands\r\n")
                    continue
                
                client_socket.send(b"354 Start mail input; end with <CRLF>.<CRLF>\r\n")
                
                while True:
                    line = client_socket.recv(1024).decode().strip() 
                    if line == ".":
                        break
                    elif line.startswith("From:") or line.startswith("To:"):
                        continue
                    elif line.startswith("Subject:"):
                        subject = line[len("Subject:"):].strip()
                        if len(subject) > 150:
                            subject = subject[:150]
                    else:
                        mail_data += line + "\n"
                
                timestamp = datetime.datetime.now().strftime("%d/%m/%Y : %H:%M")
                mail_data = f"\n{mail_data}"
                formatted_mail = (
                    f"From: {sender}\n"
                    f"To: {recipient}\n"
                    f"Subject: {subject if 'subject' in locals() else 'No Subject'}\n"
                    f"Received: {timestamp}\n"
                    f"{mail_data.strip()}\n.\n"
                    )
                
                mailbox_path = os.path.join(mailbox_dir, recipient, "my_mailbox.txt")
                with open(mailbox_path, "a") as mailbox:
                    mailbox.write(formatted_mail)
                
                client_socket.send(b"250 Message accepted for delivery\r\n")               
                state = "DONE"
                sender, recipient, mail_data = None, None, ""

            elif data.startswith("QUIT"):
                break
    
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.send(f"221 {domain_name} Service closing transmission channel\r\n".encode())
        client_socket.close()


def start_mail_server(port, mailbox_dir=MAILBOX_DIR):
    """
    Starts an SMTP mail server that listens for incoming connections and spawns a thread for each client.
    
    Args:
        port (int): The port number the server listens on.
        mailbox_dir (str): The directory where mailboxes are stored.
    """
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
        client_thread = threading.Thread(target=handle_client, args=(client_socket, MAILBOX_DIR))
        client_thread.start()
        

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python mailserver_smtp.py <port>")
        sys.exit(1)
    
    try:
        my_port = int(sys.argv[1])
    except ValueError:
        print(f"Error: The port '{sys.argv[1]}' is not a valid number.")
        sys.exit(1)
    
    start_mail_server(my_port)