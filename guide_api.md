Guide de Tests de l'API Arduino (Flask) avec PostmanL'API Flask s'exécute par défaut sur http://127.0.0.1:5000/. Toutes les requêtes ci-dessous doivent utiliser cette base d'URL.1. Vérification du Statut (GET)Cet endpoint permet de vérifier la connexion série et de lire le dernier message reçu de l'Arduino (qui est également enregistré dans last_message.txt).ParamètreValeurMéthodeGETURLhttp://127.0.0.1:5000/api/statusCorps (Body)AucunRéponse attendue (JSON) :{
  "is_connected": true, 
  "last_message": "CAPTEUR: OK", 
  "status": "OK",
  "status_file_content": "[YYYY-MM-DD HH:MM:SS] CAPTEUR: OK"
}
2. Passage en Mode Vérification (POST)Envoie la commande V à l'Arduino pour que le capteur d'empreintes se mette en mode vérification continue.ParamètreValeurMéthodePOSTURLhttp://127.0.0.1:5000/api/verifyCorps (Body)AucunRéponse attendue (JSON) :{
  "success": true,
  "message": "Commande 'V' envoyée."
}
Vérification : Le last_message de l'Arduino devrait changer pour afficher Mode: Verification ou un ACK:MODE:V.3. Lancement du Mode Enregistrement (POST)Cette opération en deux étapes (définir l'ID puis passer en mode Enregistrement) se fait via une seule route Flask. Remplacez <id> par l'ID que vous souhaitez enregistrer (par exemple, 1, 42, ou 127).ParamètreValeurMéthodePOSTURLhttp://127.0.0.1:5000/api/enroll/1 (Exemple avec ID 1)Corps (Body)AucunRéponse attendue (JSON) :{
  "success": true,
  "message": "ID 1 défini. Mode ENREGISTREMENT activé. Suivez les instructions Arduino."
}
Vérification : L'Arduino commencera la séquence d'enregistrement (ENREGISTREMENT: EN_COURS, puis INFO: Placez le doigt pour image 1...). Le nouveau statut apparaîtra dans /api/status.4. Annulation d'Enregistrement (POST)Envoie la commande C à l'Arduino pour annuler une séquence d'enregistrement en cours.ParamètreValeurMéthodePOSTURLhttp://127.0.0.1:5000/api/cancelCorps (Body)AucunRéponse attendue (JSON) :{
  "success": true,
  "message": "Commande 'C' envoyée."
}
Vérification : L'Arduino devrait envoyer un message ENREGISTREMENT: ABANDONNE ou similaire, puis revenir au mode vérification, ce qui sera reflété dans le statut.