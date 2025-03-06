import sys
import socket

# Controleer of een poortnummer is opgegeven
if len(sys.argv) != 2:
    print("Gebruik: python mailserver_smtp.py <poortnummer>")
    sys.exit(1)

# Lees het poortnummer en zet het om naar een integer
port = int(sys.argv[1])

# Maak een socket aan
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind de socket aan alle IP-adressen van de computer en de opgegeven poort
server_socket.bind(("0.0.0.0", port))

# Laat de server luisteren naar inkomende verbindingen (maximaal 5 tegelijk in de wachtrij)
server_socket.listen(5)

print(f"SMTP-server draait op poort {port} en wacht op verbindingen...")