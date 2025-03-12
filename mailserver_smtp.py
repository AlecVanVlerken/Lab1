import socket
import os
import datetime


MAILBOX_DIR = "./users"


# Maak een socket aan
def handle_client(client_socket, mailbox_dir): #moeten we niet checken dat de client socket ook niet met TCP werkt?
    try:
        domain_name = "kuleuven.be"  # Hardcode for now, maybe use dynamically fetched domain name later 
        client_socket.send(f"220 {domain_name} Service Ready\r\n".encode()) 

        # Bind de socket aan alle IP-adressen van de computer en de opgegeven poort
        # server_socket.bind(("0.0.0.0", port))  ??? in start_mail_server
        mail_data = ""
        sender, recipient = None, None
        
        while True:
            data = client_socket.recv(1024).decode() #waarom max 1024 bytes ?? ongv 8 zinnen
            if not data: 
                break
            #moeten we niet checken dat eerst helo gestuur is, voor mail from...
            # HELO
            if data.startswith("HELO"):
                client_socket.send(f"250 OK Hello {domain_name}\r\n".encode())
            
            # MAIL
            elif data.startswith("MAIL FROM:"):
                sender = data.split(":")[1].strip()
                client_socket.send(f"250 OK Sender {sender}\r\n".encode())
            
            # RCPT
            elif data.startswith("RCPT TO:"):
                recipient = data.split(":")[1].strip()
                #recipient = data.split(":")[1].strip()
                recipient_domain = data.split(":")[1].strip().split('@')[1]

                # Check if the recipient exists
                print(f"DEBUG: mailbox_dir = {mailbox_dir}")
                print(f"DEBUG: recipient = {recipient}")
                print(f"DEBUG: Full path = {os.path.join(mailbox_dir, recipient)}")

                if os.path.exists(os.path.join(mailbox_dir, recipient)):
                    client_socket.send(f"250 OK Recipient {recipient}\r\n".encode())
                else:
                    client_socket.send(b"550 No such user\r\n")
                    continue
            
            # DATA
            elif data.startswith("DATA"):
                client_socket.send(b"354 Start mail input; end with <CRLF>.<CRLF>\r\n")
                while True:
                    line = client_socket.recv(1024).decode().strip() 
                    if line == ".": #end of message
                        break
                    if line.startswith("Subject:"):
                        subject = line[len("Subject:"):].strip()
                        if len(subject) > 150:
                            subject = subject[:150]  # Trim subject to 150 characters # ZEKER ?
                    else:
                        mail_data += line + "\n"
                
                # Add time to the received message
                timestamp = datetime.datetime.now().strftime("%d/%m/%Y : %H:%M")
                mail_data = f"\n{mail_data}\nReceived: {timestamp}\n."
                formatted_mail = (
                    f"From: {sender}\n"
                    f"To: {recipient}@{recipient_domain}\n"
                    f"Subject: {subject if subject else 'No Subject'}\n"
                    f"Received: {timestamp}\n"
                    f"{mail_data.strip()}\n.\n"
                    )
                
                # Save the message to the recipient's mailbox
                mailbox_path = os.path.join(mailbox_dir, recipient, "my_mailbox.txt") #vroeger stond my_mailbox
                with open(mailbox_path, "a") as mailbox:
                    mailbox.write(formatted_mail)
                
                client_socket.send(b"250 Message accepted for delivery\r\n")

                '''        
        # Extract subject if found
        if line.startswith("Subject:"):
            subject = line[len("Subject:"):].strip()
            if len(subject) > 150:
                subject = subject[:150]  # Trim subject to 150 characters
        else:
            mail_data += line + "\n"

    # Add timestamp
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y : %H:%M")

    # Construct the email in the requested format
    formatted_mail = (
        f"From: {sender}\n"
        f"To: {recipient}@{recipient_domain}\n"
        f"Subject: {subject if subject else 'No Subject'}\n"
        f"Received: {timestamp}\n"
        f"{mail_data.strip()}\n.\n"
    )

    # Save the formatted email to the recipient's mailbox
    mailbox_path = os.path.join(mailbox_dir, recipient, "my_mailbox.txt")
    with open(mailbox_path, "a") as mailbox:
        mailbox.write(formatted_mail)

    client_socket.send(b"250 Message accepted for delivery\r\n")

                '''
            
            # QUIT
            elif data.startswith("QUIT"):
                break
    
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.send(f"221 {domain_name} Service closing transmission channel\r\n".encode())
        client_socket.close()

#print(f"SMTP-server draait op poort {my_port} en wacht op verbindingen...")


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
