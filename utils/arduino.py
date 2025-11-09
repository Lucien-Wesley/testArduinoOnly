import serial
from serial.tools import list_ports # Importation de l'outil pour lister les ports
import threading
import time
import os
import sys # Pour vérifier le mode d'exécution (interactif ou non)

# --- Configuration ---
# Port par défaut/fallback si aucun port n'est sélectionné ou trouvé.
# REMPLACER par le port série de votre Arduino. Exemples:
# - Windows: 'COM3', 'COM12', etc.
# - Linux: '/dev/ttyACM0' ou '/dev/ttyUSB0'
# - macOS: '/dev/tty.usbmodemXXXX'
ARDUINO_PORT = 'COM12' 
BAUD_RATE = 9600
STATUS_FILE_PATH = 'last_message.txt'

# Nouvelle fonction pour lister les ports et permettre la sélection
def select_serial_port():
    """Liste les ports série disponibles et demande à l'utilisateur d'en sélectionner un par numéro."""
    ports = list(list_ports.comports())
    
    if not ports:
        print("INFO: Aucun port série trouvé. Utilisation du port par défaut:", ARDUINO_PORT)
        return ARDUINO_PORT
    
    print("\n--- Ports Série Disponibles ---")
    for i, port in enumerate(ports):
        # Affiche le numéro, le nom du port et sa description
        print(f"[{i+1}] {port.device} - {port.description}")
    print("------------------------------")
    
    # Tente la sélection interactive
    selected_port = None
    max_index = len(ports)
    
    # Vérifie si le script est exécuté dans un terminal interactif
    if sys.stdin.isatty():
        while selected_port is None:
            try:
                # Note : Utilisez input() ici uniquement si vous exécutez le script directement.
                choice = input(f"Entrez le numéro (1-{max_index}) pour choisir le port Arduino, ou 'd' pour utiliser le port par défaut ('{ARDUINO_PORT}'): ").strip().lower()
                
                if choice == 'd':
                    selected_port = ARDUINO_PORT
                    break

                index = int(choice)
                if 1 <= index <= max_index:
                    selected_port = ports[index - 1].device
                    break
                else:
                    print(f"ERREUR: Numéro invalide. Entrez un nombre entre 1 et {max_index}, ou 'd'.")
            except ValueError:
                print("ERREUR: Entrée invalide. Veuillez entrer un numéro ou 'd'.")
            except EOFError:
                # Gestion du mode non-interactif si l'entrée utilisateur est coupée
                print("\nAVERTISSEMENT: Entrée utilisateur non disponible. Utilisation du premier port trouvé.")
                selected_port = ports[0].device
                break
    else:
        # Fallback pour les environnements non-interactifs (serveur, conteneur, etc.)
        print("\nAVERTISSEMENT: Mode non-interactif détecté (l'entrée utilisateur n'est pas possible).")
        # Utilise le premier port disponible comme meilleure estimation non-bloquante
        selected_port = ports[0].device 
        print(f"INFO: Utilisation automatique du premier port disponible: '{selected_port}'")
            
    return selected_port if selected_port else ARDUINO_PORT

# --- SÉLECTION GLOBALE DU PORT ---
# Cette fonction est appelée UNE SEULE FOIS lors du chargement initial du module, 
# évitant ainsi les sélections répétées lors du rechargement de Flask.
try:
    GLOBAL_SELECTED_PORT = select_serial_port()
except Exception as e:
    print(f"ERREUR FATALE lors de la sélection du port. Utilisation du port par défaut '{ARDUINO_PORT}'. Détail: {e}")
    GLOBAL_SELECTED_PORT = ARDUINO_PORT

class ArduinoSerialManager:
    """
    Gère la connexion série Arduino et la lecture en arrière-plan.
    """
    _instance = None
    _is_running = False

    def __new__(cls, *args, **kwargs):
        """Implémente le pattern Singleton."""
        if cls._instance is None:
            cls._instance = super(ArduinoSerialManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.ser = None
        self.reader_thread = None
        self.last_message = "Initialisation en cours..."
        self.message_lock = threading.Lock()
        self._initialized = True
        self._is_running = False
        
        # Le port est déjà sélectionné globalement, il suffit d'établir la connexion.
        self.connect_serial()

    def connect_serial(self):
        """Tente d'établir la connexion série."""
        
        # Utilise le port globalement sélectionné au démarrage du module
        port_to_use = GLOBAL_SELECTED_PORT

        try:
            self.ser = serial.Serial(port_to_use, BAUD_RATE, timeout=0)
            print(f"INFO: Connexion série établie sur {port_to_use} @ {BAUD_RATE} bps")
            # Démarrer le thread de lecture après la connexion
            self.start_reader()
        except serial.SerialException as e:
            print(f"ERREUR: Impossible de se connecter au port {port_to_use}. L'API fonctionnera en mode sans Arduino. Détail: {e}")
            self.ser = None
            self._is_running = False
            self._save_last_message("CAPTEUR: ERREUR - Connexion série échouée.")

    def _save_last_message(self, message):
        """Met à jour le dernier message et l'écrit dans le fichier."""
        with self.message_lock:
            self.last_message = message
            try:
                with open(STATUS_FILE_PATH, 'w', encoding='utf-8') as f:
                    # Ajoute un timestamp pour la traçabilité
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {message}")
            except IOError as e:
                print(f"AVERTISSEMENT: Impossible d'écrire dans le fichier de statut: {e}")

    def _serial_reader(self):
        """Fonction du thread: lit en continu le port série."""
        print("INFO: Thread de lecture série démarré.")
        while self._is_running and self.ser:
            try:
                # Lecture ligne par ligne non bloquante
                if self.ser.in_waiting > 0:
                    # Le .readline() bloquerait si le timeout était non-nul. 
                    # Avec timeout=0, il retourne immédiatement. On s'assure qu'il y a des données.
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"ARDUINO -> {line}")
                        self._save_last_message(line)
                else:
                    time.sleep(0.05) # Petite pause pour libérer le CPU
            except serial.SerialTimeoutException:
                pass # Géré par in_waiting, mais bonne pratique de l'inclure
            except serial.SerialException as e:
                print(f"ERREUR SÉRIE (lecture): {e}")
                self._save_last_message(f"ERREUR SÉRIE: {e}")
                self.ser = None # Déconnecter en cas d'erreur grave
                self._is_running = False
            except Exception as e:
                print(f"ERREUR INCONNUE (lecture): {e}")
                time.sleep(1)

        print("INFO: Thread de lecture série arrêté.")


    def start_reader(self):
        """Démarre le thread de lecture."""
        if self.ser and not self._is_running:
            self._is_running = True
            self.reader_thread = threading.Thread(target=self._serial_reader, daemon=True)
            self.reader_thread.start()

    def send_command(self, command):
        """Envoie une commande à l'Arduino."""
        if not self.ser:
            # Mode sans Arduino, renvoyer une erreur explicite
            error_msg = f"ERREUR: Non connecté au port série (sélectionné ou par défaut)."
            self._save_last_message(error_msg)
            return False, error_msg

        try:
            # Les commandes de l'Arduino attendent un \n
            self.ser.write((command + '\n').encode('utf-8'))
            print(f"PC -> {command}")
            return True, f"Commande '{command}' envoyée."
        except serial.SerialException as e:
            self._save_last_message(f"ERREUR SÉRIE (écriture): {e}")
            print(f"ERREUR SÉRIE (écriture): {e}")
            self.ser = None
            self._is_running = False
            return False, f"Erreur lors de l'envoi de la commande: {e}"
        except Exception as e:
            return False, f"Erreur inattendue lors de l'envoi: {e}"

    def get_last_message(self):
        """Récupère le dernier message lu."""
        with self.message_lock:
            return self.last_message

    def shutdown(self):
        """Arrête le thread et ferme la connexion série."""
        if self._is_running:
            self._is_running = False
            if self.reader_thread and self.reader_thread.is_alive():
                self.reader_thread.join(timeout=2)
        if self.ser:
            self.ser.close()
            print("INFO: Connexion série fermée.")

# Initialiser l'instance globale du gestionnaire
# (L'initialisation de la connexion/du thread se fait ici)
arduino_manager = ArduinoSerialManager()