import serial
import threading
import time
import os

# --- Configuration ---
# REMPLACER par le port série de votre Arduino (ex: 'COM3' sur Windows, '/dev/ttyUSB0' ou '/dev/ttyACM0' sur Linux/Mac)
ARDUINO_PORT = '/dev/ttyACM0' 
BAUD_RATE = 9600
STATUS_FILE_PATH = 'last_message.txt'

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
        
        self.connect_serial()

    def connect_serial(self):
        """Tente d'établir la connexion série."""
        try:
            self.ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0)
            print(f"INFO: Connexion série établie sur {ARDUINO_PORT} @ {BAUD_RATE} bps")
            # Démarrer le thread de lecture après la connexion
            self.start_reader()
        except serial.SerialException as e:
            print(f"ERREUR: Impossible de se connecter au port {ARDUINO_PORT}. L'API fonctionnera en mode sans Arduino. Détail: {e}")
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
            error_msg = f"ERREUR: Non connecté au port série ({ARDUINO_PORT})."
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