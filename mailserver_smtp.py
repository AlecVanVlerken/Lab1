import socket
import os
import datetime
import threading
import sys


MAILBOX_DIR = "./users"

# note: foute inputs en randgevallen vermijden door deze te hardcoden
# Maak een socket aan
def handle_client(client_socket, mailbox_dir): #moeten we niet checken dat de client socket ook niet met TCP werkt?
    try:
        domain_name = "kuleuven.be"  # Hardcode for now, maybe use dynamically fetched domain name later 
        client_socket.send(f"220 {domain_name} Service Ready\r\n".encode()) 

        # Bind de socket aan alle IP-adressen van de computer en de opgegeven poort
        # server_socket.bind(("0.0.0.0", port))  ??? in start_mail_server
        mail_data = ""
        sender, recipient = None, None
        
        # state variable to track the SMTP session state
        state = "INITIAL"  # Will change to GREET after HELO, etc.
        
        while True:
            data = client_socket.recv(1024).decode() #waarom max 1024 bytes ?? ongv 8 zinnen
            if not data: 
                break # WAAROM NIET CONTINUE?
            #moeten we niet checken dat eerst helo gestuur is, voor mail from...
            # HELO
            if data.startswith("HELO"): #wat gebeurt als ik helo niet schrijf ? (telnet)
                if state != "INITIAL":
                    client_socket.send(b"503 Bad sequence of commands\r\n")
                    continue
                state = "GREET"
                client_socket.send(f"250 OK Hello {domain_name}\r\n".encode())
            
            # MAIL
            elif data.startswith("MAIL FROM:"):
                # Only valid if we have already done HELO (GREET) or if we want to start a new transaction after DATA
                if state not in ["GREET", "DONE"]:  
                    client_socket.send(b"503 Bad sequence of commands\r\n")
                    continue
                sender = data.split(":")[1].strip()
                state = "MAIL"
                client_socket.send(f"250 OK Sender {sender}\r\n".encode())
            
            # RCPT
            elif data.startswith("RCPT TO:"):
                # Must come after MAIL
                if state not in ["MAIL", "RCPT"]:
                    client_socket.send(b"503 Bad sequence of commands\r\n")
                    continue

                if not sender:
                    client_socket.send(b"503 Bad sequence of commands: MAIL FROM must come before RCPT TO\r\n")
                    continue

                recipient = data.split(":")[1].strip()
                recipient_domain = data.split(":")[1].strip().split('@')[1]


                if os.path.exists(os.path.join(mailbox_dir, recipient)):
                    state = "RCPT"
                    client_socket.send(f"250 OK Recipient {recipient}\r\n".encode())
                else:
                    client_socket.send(b"550 No such user\r\n")
                    continue
            
            # DATA
            elif data.startswith("DATA"):
                # Must come after at least one RCPT
                if state != "RCPT":
                    client_socket.send(b"503 Bad sequence of commands\r\n")
                    continue
                
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
                mail_data = f"\n{mail_data}"
                formatted_mail = (
                    f"From: {sender}\n"
                    f"To: {recipient}\n"
                    f"Subject: {subject if 'subject' in locals() else 'No Subject'}\n"
                    f"Received: {timestamp}\n"
                    f"{mail_data.strip()}\n.\n"
                    )
                
                # Save the message to the recipient's mailbox
                mailbox_path = os.path.join(mailbox_dir, recipient, "my_mailbox.txt") #vroeger stond my_mailbox
                with open(mailbox_path, "a") as mailbox:
                    mailbox.write(formatted_mail)
                
                client_socket.send(b"250 Message accepted for delivery\r\n")
                
                # After DATA is finished, we set the state to allow a new transaction or QUIT
                state = "DONE"
                # Reset sender, recipient, and mail_data for a new possible transaction
                sender, recipient = None, None
                mail_data = ""

            
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