import socket
import sys

# SMTP Commands
SMTP_HELO = "HELO"
SMTP_MAIL = "MAIL FROM:"
SMTP_RCPT = "RCPT TO:"
SMTP_DATA = "DATA"
SMTP_QUIT = "QUIT"

# POP3 Commands (not used for now but prepared for future)
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

def send_smtp_command(smtp_socket, command):
    smtp_socket.send(f"{command}\r\n".encode())
    response = smtp_socket.recv(1024).decode()
    print(response)

def check_email_format(from_addr, to_addr, subject, body, username):

    if from_addr.count('@') != 1 or to_addr.count('@') != 1:
        return False
    
    from_username, from_domain = from_addr.split('@')
    to_username, to_domain = to_addr.split('@')
    
    if not to_username or from_username != username:
        return False
    
    if '.' not in from_domain or '.' not in to_domain:
        return False
    
    from_domain_parts = from_domain.split('.')
    to_domain_parts = to_domain.split('.')
    
    if len(from_domain_parts) < 2 or len(to_domain_parts) < 2:
        return False
    
    if len(from_domain_parts[-1]) < 2 or len(to_domain_parts[-1]) < 2:
        return False

    if len(subject) > 150:
        return False
    
    return True

def send_email(smtp_socket, from_addr, to_addr, subject, body):
    # Send HELO
    send_smtp_command(smtp_socket, f"{SMTP_HELO} {from_addr.split("@")[1]}")
    
    # Send MAIL FROM:
    send_smtp_command(smtp_socket, f"{SMTP_MAIL} {from_addr}")
    
    # Send RCPT TO:
    send_smtp_command(smtp_socket, f"{SMTP_RCPT} {to_addr}")
    
    # Send DATA
    send_smtp_command(smtp_socket, SMTP_DATA)
    
    # Send the email content
    smtp_socket.send(f"From: {from_addr}\r\n".encode())
    smtp_socket.send(f"To: {to_addr}\r\n".encode())
    smtp_socket.send(f"Subject: {subject}\r\n".encode())
    smtp_socket.send(f"{body}\r\n".encode())
    smtp_socket.send(b".\r\n")  # End of message

    # Confirm successful sending
    response = smtp_socket.recv(1024).decode()
    print(response)

# This one should be implemented in popserver.py maybe
def pop3_authenticate(pop3_socket, username, password):
    pop3_socket.send(f"{POP3_USER} {username}\r\n".encode())
    response = pop3_socket.recv(1024).decode()
    if not response.startswith("+OK"):
        print("Authentication failed.")
        return False
    
    pop3_socket.send(f"{POP3_PASS} {password}\r\n".encode())
    response = pop3_socket.recv(1024).decode()
    if not response.startswith("+OK"):
        print("Password incorrect.")
        return False

    return True

def list_emails(pop3_socket):
    return 0 # Implement
    
def retrieve_mailbox(pop3_socket):
    pop3_socket.send(f"{POP3_STAT}\r\n".encode())
    response = pop3_socket.recv(1024).decode()
    email_count = int(response.split()[1])
    my_mailbox = ''
    for i in range(email_count):
        pop3_socket.send(f"{POP3_RETR} {i+1}\r\n".encode())
        response = pop3_socket.recv(1024).decode()
        email_content = response[len(POP3_OK + " Message follows\r\n"):]
        my_mailbox += email_content
    return my_mailbox


def main():
    if len(sys.argv) != 2:
        print("Usage: python mail_client.py <server_IP>")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    smtp_port = 25
    pop3_port = 110 
    
    # Create and connect the SMTP socket
    smtp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    smtp_socket.connect((server_ip, smtp_port))
    
    # Create and connect the POP3 socket
    pop3_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pop3_socket.connect((server_ip, pop3_port))


    while True:
        # Create and connect the POP3 socket
        pop3_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pop3_socket.connect((server_ip, pop3_port))
        username = input("Enter your username: ")
        password = input("Enter your password: ")
        if pop3_authenticate(pop3_socket, username, password):

            while True:

                print("\nSelect an option:")
                print("a) Mail Sending")
                print("b) Mail Management")
                print("c) Mail Searching")
                print("d) Exit")
                
                choice = input("Enter your choice: ")
                
                if choice == "a":
                    from_addr = input("From: ")
                    to_addr = input("To: ")
                    subject = input("Subject: ")
                    body = ""
                    while True:
                        line = input()
                        if line == ".":
                            break
                        body += line + "\n"

                    if check_email_format(from_addr, to_addr, subject, body, username):
                        print("Mail sent successfully")
                        send_email(smtp_socket, from_addr, to_addr, subject, body)
                    else: 
                        print("This is an incorrect format")    
        
                elif choice == "b":
                    list_emails(pop3_socket)
                    while True:
                        command = input("\nPOP3 command: ").strip().upper()
                        pop3_socket.send(f"{command}\r\n".encode())
                        response = pop3_socket.recv(1024).decode()
                        print(response)
                        if "Goodbye" in response:
                            pop3_socket.close()
                            break
                    break

                elif choice == "c":
                    my_mailbox = retrieve_mailbox(pop3_socket)
                    print("Search by:")
                    print("1) Words/Sentences")
                    print("2) Time")
                    print("3) Address")
                    search_choice = input("Enter your choice: ")
                    
                    if search_choice == "1":
                        word = input("Enter words/sentences to search: ")
                        # Implement email searching based on word
                        pass
                    
                    elif search_choice == "2":
                        time = input("Enter time (MM/DD/YY): ")
                        # Implement email searching based on time
                        pass
                    
                    elif search_choice == "3":
                        address = input("Enter email address to search: ")
                        # Implement email searching based on address
                        pass

                elif choice == "d":
                    smtp_socket.send(f"{SMTP_QUIT}\r\n".encode())
                    response = smtp_socket.recv(1024).decode()
                    print(response)
                    pop3_socket.send(f"{POP3_QUIT}\r\n".encode())
                    response = pop3_socket.recv(1024).decode()
                    print(response)
                    smtp_socket.close()
                    pop3_socket.close()
                    print("Exiting the client.")
                    break

if __name__ == "__main__":
    main()
