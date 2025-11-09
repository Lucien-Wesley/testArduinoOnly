from flask import Blueprint, jsonify
from utils.arduino import arduino_manager, STATUS_FILE_PATH
import os

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/status', methods=['GET'])
def get_status():
    """
    Récupère le dernier message lu par le thread série
    et l'état de la connexion.
    """
    last_msg = arduino_manager.get_last_message()
    
    # On vérifie si le fichier de statut existe pour confirmation
    file_exists = os.path.exists(STATUS_FILE_PATH)
    
    # Lecture optionnelle du contenu brut du fichier pour vérification
    file_content = ""
    if file_exists:
        try:
            with open(STATUS_FILE_PATH, 'r', encoding='utf-8') as f:
                file_content = f.read().strip()
        except IOError:
            file_content = "Erreur de lecture du fichier."

    return jsonify({
        "status": "OK",
        "is_connected": arduino_manager.ser is not None,
        "last_message": last_msg,
        "status_file_content": file_content
    })

@api_bp.route('/verify', methods=['POST'])
def set_verify_mode():
    """
    Envoie la commande 'V' pour passer en mode VERIFICATION.
    """
    success, message = arduino_manager.send_command('V')
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "error": message}), 503

@api_bp.route('/enroll/<int:id>', methods=['POST'])
def start_enrollment(id):
    """
    Définit l'ID ('I:<id>') puis passe en mode ENREGISTREMENT ('E').
    L'ID doit être entre 0 et 127 selon le code Arduino.
    """
    if not 0 <= id <= 127:
        return jsonify({"success": False, "error": "L'ID doit être entre 0 et 127."}), 400

    # 1. Définir l'ID
    id_command = f"I{id}" 
    success_id, msg_id = arduino_manager.send_command(id_command)

    if not success_id:
        return jsonify({"success": False, "error": f"Échec de la commande ID: {msg_id}"}), 503

    # 2. Passer en mode ENREGISTREMENT
    success_enroll, msg_enroll = arduino_manager.send_command('E')

    if success_enroll:
        return jsonify({
            "success": True, 
            "message": f"ID {id} défini. Mode ENREGISTREMENT activé. Suivez les instructions Arduino."
        }), 200
    else:
        return jsonify({"success": False, "error": f"Échec de la commande ENROLL: {msg_enroll}"}), 503


@api_bp.route('/cancel', methods=['POST'])
def cancel_enrollment():
    """
    Envoie la commande 'C' pour annuler l'enregistrement en cours.
    """
    success, message = arduino_manager.send_command('C')
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "error": message}), 503