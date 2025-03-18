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


def check_email_format(from_addr, to_addr, subject, body, username): #check body size ?
    """Check email format validity."""
    if from_addr.count('@') != 1 or to_addr.count('@') != 1:
        print("There needs to be an '@' in the adresses.")
        return False      
    if not to_addr or from_addr != username:
        print("The adress doesn't exit or is incorect")
        return False
    if len(subject) > 150:
        print('Subject is too long')
        return False   
    return True


def send_email(smtp_socket, from_addr, to_addr, subject, body):
    """Send an email using SMTP."""
    send_smtp_command(smtp_socket, f"{SMTP_HELO} {from_addr.split("@")[1]}")
    send_smtp_command(smtp_socket, f"{SMTP_MAIL} {from_addr}")
    send_smtp_command(smtp_socket, f"{SMTP_RCPT} {to_addr}")
    send_smtp_command(smtp_socket, SMTP_DATA)
    
    smtp_socket.send(f"From: {from_addr}\r\n".encode())
    smtp_socket.send(f"To: {to_addr}\r\n".encode())
    smtp_socket.send(f"Subject: {subject}\r\n".encode())
    smtp_socket.send(f"{body}\r\n".encode()) 
    smtp_socket.send(b".\r\n")

    response = smtp_socket.recv(1024).decode()
    print(response)


def pop3_authenticate(pop3_socket, username, password):
    """Authenticate user with POP3 server."""
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

    
def retrieve_mailbox(pop3_socket):
    """Retrieve emails from POP3 mailbox."""
    pop3_socket.send(f"{POP3_STAT}\r\n".encode())
    response = pop3_socket.recv(1024).decode()
    email_count = int(response.split()[1])
    my_mailbox = []
    for i in range(email_count):
        pop3_socket.send(f"{POP3_RETR} {i+1}\r\n".encode())
        response = pop3_socket.recv(1024).decode()
        email_content = response[len(POP3_OK + " Message follows\r\n"):]
        my_mailbox.append(email_content)
    return my_mailbox


def parse_email_headers(email_text):
    """Extract From, Date, and Subject headers."""
    sender = ""
    date = ""
    subject = ""
    for line in email_text.splitlines():
        if line.lower().startswith("from:"):
            sender = line.split(":", 1)[1].strip()
        elif line.lower().startswith("received:"):
            date = line.split(":", 1)[1].strip()
        elif line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
        if line.strip() == "":
            break
    return [sender, date, subject]
    

if __name__ == "__main__":
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

    exit_program = False

    while not exit_program:
        username = input("Enter your username: ")
        password = input("Enter your password: ")
        if pop3_authenticate(pop3_socket, username, password):
            exit_mail_management = False

            while not exit_mail_management:

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
                        print("This is an incorrect format, tell me why 🎵")    
        
                elif choice == "b": 
                    # Mail Management - Authenticated user can view and manage emails

                    pop3_socket.send(f"{POP3_STAT}\r\n".encode())
                    response = pop3_socket.recv(1024).decode()
                    
                    if not response.startswith("+OK"):
                        print("Fout bij ophalen van mailboxstatus.")
                    else:
                        parts = response.split()
                        try:
                            email_count = int(parts[1])
                        except (IndexError, ValueError):
                            print("Fout bij verwerken van STAT-antwoord.")
                            email_count = 0

                        if email_count > 0:
                            mails = retrieve_mailbox(pop3_socket)
                            for mail in mails:
                                
                                headers = parse_email_headers(mail)
                                print(f"{mails.index(mail)+1}. {mail.strip().split("\n")[0]} {headers[1]} {headers[2]}")

                    while True:
                        command = input("POP3> ").strip()
                        if not command:
                            continue 
                        if 'RETURN' in command:
                            break

                        pop3_socket.send(f"{command}\r\n".encode())
                        response = pop3_socket.recv(1024).decode()
                        print(response)

                        if "Goodbye" in response:
                            smtp_socket.send(f"{SMTP_QUIT}\r\n".encode())
                            response = smtp_socket.recv(1024).decode()
                            smtp_socket.close()
                            pop3_socket.close()
                            print("Exiting the client.")
                            exit_program = True
                            exit_mail_management = True
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

                        matching_emails = []
                        search_terms = word.split()

                        for email in my_mailbox:
                            found = False                          
                            for term in search_terms:
                                if term.lower() in email.lower():
                                    found = True
                                    break                           
                            if found:
                                matching_emails.append(email)
                        
                        if matching_emails:
                            print("\nMatching Emails:")
                            for email in matching_emails:
                                print("-" * 40) 
                                print("From:" + email) 
                        else:
                            print("\nNo emails found with the words/sentences.")
                    
                    elif search_choice == "2":
                        time = input("Enter time (DD/MM/YY): ").strip()
                        matching_emails = []

                        for email in my_mailbox:
                            if f"{time}" in email:
                                matching_emails.append(email)

                        if matching_emails:
                            print("\nMatching Emails:")
                            for email in matching_emails:
                                print("-" * 40)
                                print("From:" + email)
                        else:
                            print("\nNo emails found for this date.")
                    
                    elif search_choice == "3":
                        address = input("Enter email address to search: ").strip()
                        matching_emails = []

                        for email in my_mailbox:
                            if f"{address}" in email or f"To: {address}" in email:
                                matching_emails.append(email)

                        if matching_emails:
                            print("\nMatching Emails:")
                            for email in matching_emails:
                                print("-" * 40)
                                print("From:" + email)
                        else:
                            print("\nNo emails found with this address.")

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
                    exit_program = True
                    break
    sys.exit(1)