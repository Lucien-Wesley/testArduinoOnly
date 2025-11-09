from flask import Flask, jsonify
from routes.arduino import api_bp
from utils.arduino import arduino_manager
import atexit

app = Flask(__name__)

# Enregistrement du Blueprint
app.register_blueprint(api_bp)

# --- Gestion de l'arrêt ---
# Assurez-vous que le thread et la connexion série sont fermés
# lorsque l'application Flask s'arrête.
def on_app_shutdown():
    """Fonction appelée à l'arrêt du serveur Flask."""
    print("\nINFO: Arrêt de l'application Flask. Fermeture du gestionnaire série...")
    arduino_manager.shutdown()

atexit.register(on_app_shutdown)

@app.route('/')
def index():
    return jsonify({
        "api_name": "Contrôleur d'accès à empreintes digitales (Arduino/Flask)",
        "status_url": "/api/status",
        "verify_url": "/api/verify (POST)",
        "enroll_url": "/api/enroll/<id> (POST)",
        "cancel_url": "/api/cancel (POST)"
    })

if __name__ == '__main__':
    # Lance le serveur Flask. Le thread de lecture série a été démarré 
    # automatiquement par l'initialisation de 'arduino_manager'.
    app.run(debug=True, host='0.0.0.0', port=5000)