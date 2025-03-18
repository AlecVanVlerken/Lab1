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

#   Retrieves the number of emails using STAT, then for each email sends RETR,
#   reads the full multi-line response, parses header information, and displays it.
#   Format: No. <Sender’s email id> <When received, in date : hour : minute> <Subject> 
    # Send STAT command.
    pop3_socket.send(f"{POP3_STAT}\r\n".encode())
    response = pop3_socket.recv(1024).decode()
    if not response.startswith(POP3_OK):
        print("Error retrieving mailbox status.")
        return
    parts = response.split()
    try:
        email_count = int(parts[1])
    except (IndexError, ValueError):
        print("Error parsing STAT response.")
        return
    
    print(f"Total emails: {email_count}")
    
    # Retrieve and list each email.
    for i in range(1, email_count + 1):
        pop3_socket.send(f"{POP3_RETR} {i}\r\n".encode())
        # Read the initial response line.
        initial_response = pop3_socket.recv(1024).decode()
        if not initial_response.startswith(POP3_OK):
            print(f"Error retrieving email {i}.")
            continue
        
        # Read the multi-line email content (terminated by a single dot on a line).
        email_lines = []
        while True:
            line = pop3_socket.recv(1024).decode()
            if line.strip() == ".":
                break
            email_lines.append(line)
        email_text = "".join(email_lines)
        sender, date, subject = parse_email_headers(email_text)
        # For simplicity, we print the complete date header.
        # (Optional: Further process 'date' to show only date : hour : minute.)
        print(f"No. {i} {sender} {date} {subject}")
    
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

def parse_email_headers(email_text):
    """
    Extracts the 'From', 'Date', and 'Subject' headers from the email text.
    """
    sender = ""
    date = ""
    subject = ""
    for line in email_text.splitlines():
        if line.lower().startswith("from:"):
            sender = line.split(":", 1)[1].strip()
        elif line.lower().startswith("date:"):
            date = line.split(":", 1)[1].strip()
        elif line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
        # Headers end at the first empty line.
        if line.strip() == "":
            break
    return sender, date, subject


def pop3_command_loop(pop3_socket): # controleren en comments veranderen + Implementeren ook voor a en c
    """
    Loop for sending POP3 commands to the server.
    It accepts commands (STAT, LIST, RETR, DELE, RSET, QUIT) and handles multi-line responses
    for commands like RETR and LIST (terminated by a single dot on a line).
    """
    print("\nEnter POP3 commands (STAT, LIST, RETR, DELE, RSET, QUIT):")
    while True:
        command = input("POP3> ").strip()
        if not command:
            continue  # Skip if nothing was entered

        # Send the command to the server.
        pop3_socket.send(f"{command}\r\n".encode())
        
        # Get the initial response line.
        response = pop3_socket.recv(1024).decode()
        print("Server:", response.strip())
        
        # If the command is RETR or LIST, the server will send a multi-line response.
        if command.upper().startswith("RETR") or command.upper().startswith("LIST"):
            lines = []
            while True:
                # Read data from the socket.
                line = pop3_socket.recv(1024).decode()
                # A line with just a dot indicates the end of the response.
                if line.strip() == ".":
                    break
                lines.append(line.rstrip("\r\n"))
            print("\n".join(lines))
        
        # Check if the command was QUIT (or if the response contains a goodbye message).
        if command.upper() == "QUIT":
            # Optionally, close the socket here if not done elsewhere.
            break

# Nieuwe functie om alle e-mails op te halen als een lijst van dictionaries (voor mail searching) 
# CONTROLEER
def get_all_emails(pop3_socket):
    pop3_socket.send(f"{POP3_STAT}\r\n".encode())
    response = pop3_socket.recv(1024).decode()
    parts = response.split()
    try:
        email_count = int(parts[1])
    except (IndexError, ValueError):
        print("Error parsing STAT response.")
        return []
    emails = []
    for i in range(1, email_count + 1):
        pop3_socket.send(f"{POP3_RETR} {i}\r\n".encode())
        initial_response = pop3_socket.recv(1024).decode()
        if not initial_response.startswith(POP3_OK):
            print(f"Error retrieving email {i}.")
            continue
        email_lines = []
        while True:
            line = pop3_socket.recv(1024).decode()
            if line.strip() == ".":
                break
            email_lines.append(line)
        email_text = "".join(email_lines)
        sender, date, subject = parse_email_headers(email_text)
        emails.append({
            "from": sender,
            "date": date,
            "subject": subject,
            "full_text": email_text
        })
    return emails

    # Zoekfuncties voor mail searching
def search_emails_by_word(emails, keyword):
    matches = [email for email in emails if keyword.lower() in email["full_text"].lower()]
    return matches

def search_emails_by_time(emails, time_query):
    matches = [email for email in emails if time_query in email["date"]]
    return matches

def search_emails_by_address(emails, address_query):
    matches = [email for email in emails if address_query.lower() in email["from"].lower()]
    return matches


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
                    # Mail Management 
                    # Re-create the POP3 socket for a fresh session. ????
                    if pop3_authenticate(pop3_socket, username, password):
                        print("\nAuthenticated successfully!")
                        print("\nRetrieving email list...")
                        list_emails(pop3_socket)
                        #loop for further commands
                        pop3_command_loop(pop3_socket)
                    else:
                        print("Authentication failed. Please try again.")

                    '''
                    while True:
                        command = input("\nPOP3 command: ").strip().upper()
                        pop3_socket.send(f"{command}\r\n".encode())
                        response = pop3_socket.recv(1024).decode()
                        print(response)
                        if "Goodbye" in response:
                            pop3_socket.close()
                            break
                    break
                    '''

                elif choice == "c":
                    # Mail Searching
                    print("Retrieving all emails for searching...")
                    #my_mailbox = retrieve_mailbox(pop3_socket)
                    emails = get_all_emails(pop3_socket)
                    if not emails:
                        print("No emails found or error retrieving emails.")
                        continue
                    print("Search by:")
                    print("1) Words/Sentences")
                    print("2) Time")
                    print("3) Address")
                    search_choice = input("Enter your choice: ")
                    
                    if search_choice == "1":
                        keyword = input("Enter words/sentences to search: ")
                        matches = search_emails_by_word(emails, keyword)
                    
                    elif search_choice == "2":
                        time = input("Enter time (MM/DD/YY): ")
                        matches = search_emails_by_time(emails, time)

                    
                    elif search_choice == "3":
                        address = input("Enter email address to search: ")
                        matches = search_emails_by_address(emails, address)
                    else:
                        print("Invalid search choice.")
                        continue

                    if matches:
                        print("Found emails:")
                        for index, email in enumerate(matches, start=1):
                            print(f"No. {index} {email['from']} {email['date']} {email['subject']}")
                    else:
                        print("No emails found matching the search criteria.")




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
