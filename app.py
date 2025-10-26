from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file , flash
import mysql.connector
import secrets
from datetime import datetime, date
import os
from werkzeug.utils import secure_filename
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from chatbot_service import ChatbotService

# Tentative d'import des services optionnels
try:
    from mobile_enhancements import MobileEnhancementService
    mobile_service = MobileEnhancementService()
    MOBILE_ENABLED = True
except ImportError:
    mobile_service = None
    MOBILE_ENABLED = False
    print("⚠️ Service mobile non disponible")
# Initialisation de l'application
app = Flask(__name__)
chatbot_service = ChatbotService()

# Rendre datetime disponible dans tous les templates
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

# Configuration
app.config['SECRET_KEY'] = 'votre-cle-secrete'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

# Configuration Gmail SMTP
GMAIL_USER = 'gestionstagiaire10@gmail.com'
GMAIL_PASSWORD = 'bgrf funx rdpt lumu'

# Créer le dossier uploads s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ===========================================
# FONCTIONS UTILITAIRES
# ===========================================

def get_db_connection():
    """Fonction de connexion à la base de données"""
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='gestion_stagiaire'
    )
    return connection

def generer_matricule():
    """Fonction pour générer un matricule unique"""
    date_str = datetime.now().strftime('%Y%m%d')
    random_str = secrets.token_hex(2).upper()
    return f"STA{date_str}{random_str}"

def get_public_url():
    """URL publique pour accès réseau"""
    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        base_url = f"http://{local_ip}:5000"
        print(f"🌐 URL réseau: {base_url}")
        return base_url
    except:
        return "http://localhost:5000"

def allowed_file(filename):
    """Vérifier les fichiers autorisés"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def envoyer_email_gmail_direct(email_destinataire, matricule, nom, prenom):
    """Envoyer email avec Gmail SMTP"""
    try:
        base_url = get_public_url()
        suivi_url = f"{base_url}/suivi/{matricule}"
        
        # Configuration du message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎫 Votre matricule de candidature : {matricule}"
        msg['From'] = f"Gestion Stagiaire <{GMAIL_USER}>"
        msg['To'] = email_destinataire

        # Email HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .matricule-box {{ background: #e3f2fd; border-left: 5px solid #667eea; padding: 25px; margin: 25px 0; border-radius: 8px; text-align: center; }}
                .matricule {{ font-family: 'Courier New', monospace; font-size: 32px; font-weight: bold; color: #1976d2; letter-spacing: 4px; }}
                .button {{ display: block; background: linear-gradient(135deg, #27ae60, #229954); color: white; padding: 20px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; text-align: center; font-size: 18px; margin: 30px auto; max-width: 300px; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎫 Candidature Reçue !</h1>
                    <p>Votre matricule de suivi est prêt</p>
                </div>
                
                <div class="content">
                    <p>Bonjour <strong>{prenom} {nom}</strong>,</p>
                    
                    <p style="color: #27ae60; font-weight: bold; font-size: 18px;">✅ Nous avons bien reçu votre candidature de stage !</p>
                    
                    <p>Voici votre matricule de suivi :</p>
                    
                    <div class="matricule-box">
                        <div class="matricule">{matricule}</div>
                        <p style="margin: 15px 0 0 0; color: #1976d2; font-weight: 500;">
                            📱💻 Fonctionne sur tous les appareils
                        </p>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{suivi_url}" class="button">
                            🚀 Accéder au Suivi
                        </a>
                    </div>
                    
                    <p>Cordialement,<br>
                    <strong>L'équipe Gestion Stagiaire</strong></p>
                </div>
                
                <div class="footer">
                    <p>© 2025 Gestion Stagiaire - Plateforme digitale</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Version texte
        text_content = f"""
        🎫 CANDIDATURE REÇUE AVEC SUCCÈS !
        
        Bonjour {prenom} {nom},
        ✅ Nous avons bien reçu votre candidature de stage !
        
        🎫 Votre matricule de suivi : {matricule}
        🚀 Accès au suivi : {suivi_url}
        
        Cordialement,
        L'équipe Gestion Stagiaire
        """

        # Attacher les versions
        text_part = MIMEText(text_content, 'plain', 'utf-8')
        html_part = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(text_part)
        msg.attach(html_part)

        # Envoi
        context = ssl.create_default_context()
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls(context=context)
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
            
        print(f"✅ Email envoyé à {email_destinataire}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur envoi email: {str(e)}")
        return False

# ===========================================
# ROUTES PRINCIPALES
# ===========================================

@app.route('/')
def accueil():
    return render_template('accueil.html')  

@app.route('/stagiaire')
def stagiaire():
    return render_template('espace_stagiaire.html')

@app.route('/personnel')
def personnel():
    return render_template('espace_personnel.html')

@app.route('/admin')
def admin_login():
    return render_template('espace_admin.html')

# ===========================================
# ROUTES MOBILES (si disponibles)
# ===========================================

if MOBILE_ENABLED and mobile_service:
    @app.route('/mobile/suivi/<matricule>')
    def mobile_suivi_candidature(matricule):
        """Interface mobile optimisée"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query_candidature = "SELECT * FROM candidature WHERE matricule = %s"
            cursor.execute(query_candidature, (matricule,))
            candidature = cursor.fetchone()
            
            if not candidature:
                return redirect(url_for('suivi'))
            
            # Pour candidatures non acceptées
            if candidature['statut'] != 'ACCEPTEE':
                return render_template('mobile_suivi.html', 
                                     candidature=candidature,
                                     documents=[])
            
            # Pour candidatures acceptées
            query_stagiaire = """
                SELECT s.*, 
                       e.nom as encadrant_nom, 
                       e.prenom as encadrant_prenom,
                       e.email as encadrant_email,
                       e.specialite as encadrant_specialite
                FROM stagiaire s
                LEFT JOIN encadrant e ON s.encadrant_id = e.id
                WHERE s.matricule = %s
            """
            cursor.execute(query_stagiaire, (matricule,))
            stagiaire = cursor.fetchone()
            
            if not stagiaire:
                return render_template('mobile_suivi.html', 
                                     candidature=candidature,
                                     documents=[])
            
            # Vérifier attestation
            cursor.execute("""
                SELECT id, generee, date_generation, chemin_fichier 
                FROM attestation 
                WHERE stagiaire_id = %s
                ORDER BY date_generation DESC
                LIMIT 1
            """, (stagiaire['id'],))
            attestation = cursor.fetchone()
            
            # Documents
            doc_query = "SELECT * FROM document WHERE candidature_id = %s"
            cursor.execute(doc_query, (candidature['id'],))
            documents = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            # Calculer progression
            progression = 0
            if stagiaire['date_debut_stage'] and stagiaire['date_fin_stage']:
                debut = stagiaire['date_debut_stage']
                fin = stagiaire['date_fin_stage']
                aujourd_hui = date.today()
                
                if isinstance(debut, datetime):
                    debut = debut.date()
                if isinstance(fin, datetime):
                    fin = fin.date()
                
                if aujourd_hui >= debut:
                    duree_totale = (fin - debut).days
                    jours_ecoules = (aujourd_hui - debut).days
                    if duree_totale > 0:
                        progression = min(100, max(0, int((jours_ecoules / duree_totale) * 100)))
            
            # Données complètes
            donnees_completes = {
                'matricule': candidature['matricule'],
                'nom': candidature['nom'],
                'prenom': candidature['prenom'],
                'email': candidature['email'],
                'etablissement': candidature['etablissement'],
                'specialite': candidature['specialite'],
                'statut': candidature['statut'],
                'date_soumission': candidature['date_soumission'],
                'commentaire': candidature.get('commentaire'),
                'stagiaire_id': stagiaire['id'],
                'candidature_id': stagiaire['candidature_id'],
                'date_debut_stage': stagiaire['date_debut_stage'],
                'date_fin_stage': stagiaire['date_fin_stage'],
                'statut_stage': stagiaire['statut_avancement'],
                'progression': progression,
                'sujet': stagiaire['sujet'],
                'encadrant_nom': stagiaire.get('encadrant_nom'),
                'encadrant_prenom': stagiaire.get('encadrant_prenom'),
                'encadrant_email': stagiaire.get('encadrant_email'),
                'encadrant_specialite': stagiaire.get('encadrant_specialite'),
                'attestation_demandee': attestation is not None,
                'attestation_generee': attestation['generee'] if attestation else False,
                'attestation_date': attestation['date_generation'] if attestation else None,
                'attestation_fichier': attestation['chemin_fichier'] if attestation else None
            }
            
            return render_template('mobile_suivi.html', 
                                 candidature=donnees_completes,
                                 documents=documents)
            
        except Exception as e:
            print(f"Erreur mobile suivi: {str(e)}")
            return redirect(url_for('suivi'))

# ===========================================
# ROUTES AUTHENTIFICATION
# ===========================================

@app.route('/personnel/login', methods=['POST'])
def personnel_login_post():
    try:
        matricule = request.form.get('username', '').strip()
        mot_de_passe = request.form.get('password', '').strip()
        
        if not matricule or not mot_de_passe:
            return redirect(url_for('personnel'))
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Vérifier RH
        query = "SELECT * FROM service_rh WHERE matricule = %s AND mot_de_passe = %s AND actif = 1"
        cursor.execute(query, (matricule, mot_de_passe))
        rh = cursor.fetchone()
        
        if rh:
            session['rh_logged_in'] = True
            session['rh_id'] = rh['id']
            session['rh_nom'] = rh['nom']
            session['rh_prenom'] = rh['prenom']
            session['rh_matricule'] = rh['matricule']
            
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard_rh'))
        
        # Vérifier Encadrant
        cursor.execute("SELECT * FROM encadrant WHERE matricule = %s AND mot_de_passe = %s AND actif = 1", (matricule, mot_de_passe))
        encadrant = cursor.fetchone()
        
        if encadrant:
            session['encadrant_logged_in'] = True
            session['encadrant_id'] = encadrant['id']
            session['encadrant_nom'] = encadrant['nom']
            session['encadrant_prenom'] = encadrant['prenom']
            session['encadrant_matricule'] = encadrant['matricule']
            
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard_encadrant'))
        
        cursor.close()
        connection.close()
        return redirect(url_for('personnel'))
            
    except Exception as e:
        print(f"Erreur login personnel: {str(e)}")
        return redirect(url_for('personnel'))

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    try:
        matricule = request.form.get('username')
        mot_de_passe = request.form.get('password')
        
        if not matricule or not mot_de_passe:
            return redirect(url_for('admin_login'))
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT * FROM admin WHERE matricule = %s AND mot_de_passe = %s"
        cursor.execute(query, (matricule, mot_de_passe))
        admin = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if admin:
            session['admin_logged_in'] = True
            session['admin_id'] = admin['id']
            session['admin_nom'] = admin['nom']
            session['admin_matricule'] = admin['matricule']
            
            return redirect(url_for('dashboard_admin'))
        else:
            return redirect(url_for('admin_login'))
            
    except Exception as e:
        print(f"Erreur login admin: {str(e)}")
        return redirect(url_for('admin_login'))

# ===========================================
# ROUTES DASHBOARDS
# ===========================================

@app.route('/dashboard-rh')
def dashboard_rh():
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        rh_id = session.get('rh_id')
        
        # Candidatures
        query = "SELECT * FROM candidature ORDER BY date_soumission DESC"
        cursor.execute(query)
        candidatures = cursor.fetchall()
        
        # Évaluations en attente
        cursor.execute("SELECT COUNT(*) as count FROM evaluation WHERE validee_par_rh = 0")
        result = cursor.fetchone()
        evaluations_en_attente = result['count'] if result else 0
        
        # Vérifier si c'est encore le mot de passe par défaut
        cursor.execute("SELECT mot_de_passe FROM service_rh WHERE id = %s", (rh_id,))
        current_password = cursor.fetchone()
        is_default_password = current_password['mot_de_passe'] == 'rh123456' if current_password else False
        
        stats = {
            'nouvelles': len([c for c in candidatures if c['statut'] == 'EN_ATTENTE']),
            'en_cours': len([c for c in candidatures if c['statut'] == 'EN_COURS']),
            'acceptees': len([c for c in candidatures if c['statut'] == 'ACCEPTEE']),
            'refusees': len([c for c in candidatures if c['statut'] == 'REFUSEE'])
        }
        
        cursor.close()
        connection.close()
        
        return render_template('rh.html', 
                             candidatures=candidatures,
                             stats=stats,
                             evaluations_en_attente=evaluations_en_attente,
                             is_default_password=is_default_password,  # ← Nouvelle variable
                             rh_nom=session.get('rh_nom'),
                             rh_prenom=session.get('rh_prenom'))
        
    except Exception as e:
        print(f"Erreur dashboard RH: {str(e)}")
        return redirect(url_for('personnel'))

@app.route('/dashboard-encadrant')
def dashboard_encadrant():
    if not session.get('encadrant_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        # Infos encadrant
        cursor.execute("SELECT * FROM encadrant WHERE id = %s", (encadrant_id,))
        encadrant = cursor.fetchone()
        
        # Stagiaires de cet encadrant
        query_stagiaires = """
            SELECT s.*, c.nom, c.prenom, c.email, c.etablissement, c.specialite,
                   DATEDIFF(CURDATE(), s.date_debut_stage) as jours_ecoules,
                   DATEDIFF(s.date_fin_stage, s.date_debut_stage) as duree_totale,
                   EXISTS(SELECT 1 FROM evaluation e WHERE e.stagiaire_id = s.id) as est_evalue
            FROM stagiaire s
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.encadrant_id = %s
            ORDER BY s.date_debut_stage DESC
        """
        cursor.execute(query_stagiaires, (encadrant_id,))
        stagiaires = cursor.fetchall()
        
        stats = {
            'total': len(stagiaires),
            'actifs': len([s for s in stagiaires if s['statut_avancement'] == 'EN_COURS']),
            'termines': len([s for s in stagiaires if s['statut_avancement'] == 'TERMINE']),
            'evaluations': len([s for s in stagiaires if s['est_evalue']])
        }
        
        cursor.close()
        connection.close()
        
        return render_template('encadrant.html', 
                             encadrant=encadrant,
                             stagiaires=stagiaires,
                             stats=stats,
                             encadrant_nom=session.get('encadrant_nom'),
                             encadrant_prenom=session.get('encadrant_prenom'))
        
    except Exception as e:
        print(f"Erreur dashboard encadrant: {str(e)}")
        return redirect(url_for('personnel'))

@app.route('/dashboard-admin')
def dashboard_admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Statistiques générales
        cursor.execute("SELECT COUNT(*) as total FROM candidature")
        result = cursor.fetchone()
        total_candidatures = result['total'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as total FROM service_rh")
        result = cursor.fetchone()
        total_rh = result['total'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as total FROM encadrant")
        result = cursor.fetchone()
        total_encadrants = result['total'] if result else 0
        
        # Personnel RH
        cursor.execute("SELECT id, nom, prenom, matricule, email, actif FROM service_rh ORDER BY nom")
        personnel_rh = cursor.fetchall()
        
        # Encadrants
        cursor.execute("SELECT id, nom, prenom, matricule, email, specialite, disponible FROM encadrant ORDER BY nom")
        encadrants = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        stats = {
            'total_candidatures': total_candidatures,
            'total_rh': total_rh,
            'total_encadrants': total_encadrants
        }
        
        return render_template('admin.html', 
                             stats=stats, 
                             personnel_rh=personnel_rh, 
                             encadrants=encadrants,
                             admin_nom=session.get('admin_nom'))
        
    except Exception as e:
        print(f"Erreur dashboard admin: {str(e)}")
        return redirect(url_for('admin_login'))

# ===========================================
# ROUTES CANDIDATURES
# ===========================================

@app.route('/candidature', methods=['GET', 'POST'])
def candidature():
    if request.method == 'POST':
        try:
            nom = request.form.get('nom')
            prenom = request.form.get('prenom')
            email = request.form.get('email')
            etablissement = request.form.get('etablissement')
            specialite = request.form.get('specialite')
            date_debut = request.form.get('date_debut')
            date_fin = request.form.get('date_fin')
            mode_notification = request.form.get('mode_notification', 'EMAIL')
            
            # Validation
            if not all([nom, prenom, email, etablissement, specialite, date_debut, date_fin]):
                return render_template('candidature_form.html')
            
            matricule = generer_matricule()
            
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Insérer candidature
            query = """
                INSERT INTO candidature (matricule, nom, prenom, email, etablissement, 
                                       specialite, date_debut, date_fin, statut, date_soumission, mode_notification)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                matricule, nom, prenom, email, etablissement, 
                specialite, date_debut, date_fin, 'EN_ATTENTE', datetime.now(), mode_notification
            )
            
            cursor.execute(query, values)
            candidature_id = cursor.lastrowid
            
            # ✅ CORRECTION ICI - Mapping corrigé selon votre ENUM
            file_types_mapping = {
                'cv': 'CV',
                'lettre': 'LETTRE_MOTIVATION',  # ✅ Maintenant correct
                'convention': 'CONVENTION'
            }
            
            print(f"📁 Traitement des fichiers avec mapping: {file_types_mapping}")  # Debug
            
            for file_field, type_db in file_types_mapping.items():
                print(f"🔄 Traitement: {file_field} -> {type_db}")  # Debug
                
                if file_field in request.files:
                    file = request.files[file_field]
                    print(f"📁 Fichier reçu: {file.filename}")  # Debug
                    
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"{matricule}_{file_field}_{filename}"
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        
                        file.save(file_path)
                        print(f"💾 Fichier sauvegardé: {file_path}")  # Debug
                        
                        if os.path.exists(file_path):
                            file_size = os.path.getsize(file_path)
                            
                            doc_query = """
                                INSERT INTO document (candidature_id, nom, type, chemin_fichier, 
                                                    taille_fichier, format, date_upload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """
                            
                            doc_values = (
                                candidature_id, filename, type_db,  # type_db = 'LETTRE_MOTIVATION'
                                unique_filename, file_size, 'PDF', datetime.now()
                            )
                            
                            print(f"📝 Insertion document: candidature_id={candidature_id}, type={type_db}")  # Debug
                            cursor.execute(doc_query, doc_values)
                            print(f"✅ Document {type_db} inséré avec succès!")  # Debug
                        else:
                            print(f"❌ Fichier non trouvé après sauvegarde: {file_path}")
                    else:
                        print(f"❌ Fichier invalide pour {file_field}")
                else:
                    print(f"❌ Champ {file_field} non trouvé dans request.files")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            # Envoi email
            if mode_notification == 'EMAIL':
                email_envoye = envoyer_email_gmail_direct(email, matricule, nom, prenom)
                
                if email_envoye:
                    pass
                else:
                    pass
            else:
            
                pass
            return redirect(url_for('candidature_confirmee', matricule=matricule))
            
        except Exception as e:
            print(f"❌ Erreur candidature: {str(e)}")
            import traceback
            traceback.print_exc()
            return render_template('candidature_form.html')
    
    return render_template('candidature_form.html')

@app.route('/candidature/confirmee/<matricule>')
def candidature_confirmee(matricule):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT * FROM candidature WHERE matricule = %s"
        cursor.execute(query, (matricule,))
        candidature = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if candidature:
            return render_template('candidature_confirmee.html', candidature=candidature)
        else:
            return redirect(url_for('stagiaire'))
            
    except Exception as e:
        return redirect(url_for('stagiaire'))

# ===========================================
# ROUTES SUIVI
# ===========================================

@app.route('/suivi', methods=['GET', 'POST'])
def suivi():
    if request.method == 'POST':
        matricule = request.form.get('matricule')
        
        if matricule:
            return redirect(url_for('consulter_suivi', matricule=matricule))
        else:
    
            pass
    return render_template('suivi_form.html')

@app.route('/suivi/<matricule>')
def consulter_suivi(matricule):
    """Suivi intelligent qui redirige selon l'appareil"""
    try:
        # Détection mobile simple
        user_agent = request.headers.get('User-Agent', '').lower()
        is_mobile = any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad'])
        
        # Si mobile et service disponible, rediriger vers interface mobile
        if is_mobile and MOBILE_ENABLED:
            return redirect(url_for('mobile_suivi_candidature', matricule=matricule))
        
        # Sinon, interface desktop classique
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query_candidature = "SELECT * FROM candidature WHERE matricule = %s"
        cursor.execute(query_candidature, (matricule,))
        candidature = cursor.fetchone()
        
        if not candidature:
            return redirect(url_for('suivi'))
        
        if candidature['statut'] != 'ACCEPTEE':
            cursor.close()
            connection.close()
            return render_template('suivi_candidature.html', candidature=candidature)
        
        query_stagiaire = """
            SELECT s.*, 
                   e.nom as encadrant_nom, 
                   e.prenom as encadrant_prenom,
                   e.email as encadrant_email,
                   e.specialite as encadrant_specialite
            FROM stagiaire s
            LEFT JOIN encadrant e ON s.encadrant_id = e.id
            WHERE s.matricule = %s
        """
        cursor.execute(query_stagiaire, (matricule,))
        stagiaire = cursor.fetchone()
        
        if not stagiaire:
            cursor.close()
            connection.close()
            return redirect(url_for('suivi'))
        
        # Vérifier attestation
        cursor.execute("""
            SELECT id, generee, date_generation, chemin_fichier 
            FROM attestation 
            WHERE stagiaire_id = %s
            ORDER BY date_generation DESC
            LIMIT 1
        """, (stagiaire['id'],))
        attestation = cursor.fetchone()
        
        doc_query = "SELECT * FROM document WHERE candidature_id = %s"
        cursor.execute(doc_query, (candidature['id'],))
        documents = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        donnees_completes = {
            'matricule': candidature['matricule'],
            'nom': candidature['nom'],
            'prenom': candidature['prenom'],
            'email': candidature['email'],
            'etablissement': candidature['etablissement'],
            'specialite': candidature['specialite'],
            'statut': candidature['statut'],
            'date_soumission': candidature['date_soumission'],
            'stagiaire_id': stagiaire['id'],
            'candidature_id': stagiaire['candidature_id'],
            'date_debut_stage': stagiaire['date_debut_stage'],
            'date_fin_stage': stagiaire['date_fin_stage'],
            'statut_avancement': stagiaire['statut_avancement'],
            'sujet': stagiaire['sujet'],
            'encadrant_nom': stagiaire.get('encadrant_nom'),
            'encadrant_prenom': stagiaire.get('encadrant_prenom'),
            'encadrant_email': stagiaire.get('encadrant_email'),
            'encadrant_specialite': stagiaire.get('encadrant_specialite'),
            'attestation_demandee': attestation is not None,
            'attestation_generee': attestation['generee'] if attestation else False,
            'attestation_date': attestation['date_generation'] if attestation else None,
            'attestation_fichier': attestation['chemin_fichier'] if attestation else None
        }
        
        return render_template('stagiaire_dashboard.html', 
                             candidature=donnees_completes,
                             documents=documents)
        
    except Exception as e:
        return redirect(url_for('suivi'))

@app.route('/stagiaire/<matricule>/actualiser')
def actualiser_stagiaire(matricule):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT c.statut as statut_candidature, 
                   s.statut_avancement, s.date_debut_stage, s.date_fin_stage,
                   s.encadrant_id,
                   DATEDIFF(CURDATE(), s.date_debut_stage) as jours_ecoules,
                   DATEDIFF(s.date_fin_stage, s.date_debut_stage) as duree_totale
            FROM candidature c
            JOIN stagiaire s ON c.matricule = s.matricule
            WHERE c.matricule = %s AND c.statut = 'ACCEPTEE'
        """
        cursor.execute(query, (matricule,))
        data = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if data:
            progression = 0
            if data['duree_totale'] and data['jours_ecoules'] >= 0:
                progression = min(100, max(0, int((data['jours_ecoules'] / data['duree_totale']) * 100)))
            
            return jsonify({
                'success': True,
                'statut_candidature': data['statut_candidature'],
                'statut_stage': data['statut_avancement'],
                'progression': progression,
                'jours_ecoules': data['jours_ecoules'] or 0,
                'duree_totale': data['duree_totale'] or 0,
                'has_encadrant': data['encadrant_id'] is not None,
                'message': 'Données actualisées avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Stagiaire introuvable ou candidature non acceptée'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })

@app.route('/stagiaire/<matricule>/demander-attestation', methods=['POST'])
def demander_attestation_stagiaire(matricule):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT s.id as stagiaire_id, c.nom, c.prenom, s.statut_avancement
            FROM stagiaire s
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.matricule = %s
        """
        cursor.execute(query, (matricule,))
        stagiaire = cursor.fetchone()
        
        if not stagiaire:
            return jsonify({
                'success': False,
                'message': 'Stagiaire introuvable'
            })
        
        cursor.execute("""
            SELECT * FROM attestation 
            WHERE stagiaire_id = %s AND demandee = 1 
            AND date_demande > DATE_SUB(NOW(), INTERVAL 30 DAY)
            ORDER BY date_demande DESC LIMIT 1
        """, (stagiaire['stagiaire_id'],))
        demande_existante = cursor.fetchone()
        
        if demande_existante:
            return jsonify({
                'success': False,
                'message': 'Une demande d\'attestation a déjà été faite récemment. Veuillez attendre.'
            })
        
        cursor.execute("""
            INSERT INTO attestation (stagiaire_id, demandee, date_demande) 
            VALUES (%s, 1, NOW())
        """, (stagiaire['stagiaire_id'],))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'message': '✅ Demande d\'attestation envoyée ! Le service RH va traiter votre demande sous 24-48h.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur lors de la demande: {str(e)}'
        })

@app.route('/stagiaire/<matricule>/telecharger-attestation')
def stagiaire_telecharger_attestation(matricule):
    """Télécharger l'attestation du stagiaire"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT a.chemin_fichier, c.nom, c.prenom
            FROM attestation a
            JOIN stagiaire s ON a.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.matricule = %s AND a.generee = 1
            ORDER BY a.date_generation DESC
            LIMIT 1
        """
        cursor.execute(query, (matricule,))
        attestation = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if attestation and attestation['chemin_fichier']:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], attestation['chemin_fichier'])
            if os.path.exists(filepath):
                download_name = f"Attestation_Stage_{attestation['prenom']}_{attestation['nom']}.pdf"
                return send_file(filepath, as_attachment=True, download_name=download_name)
            else:
                pass
        else:
        
            pass
        return redirect(url_for('consulter_suivi', matricule=matricule))
        
    except Exception as e:
        return redirect(url_for('suivi'))

# ===========================================
# ROUTES RH - GESTION CANDIDATURES
# ===========================================

@app.route('/rh/candidature/<matricule>')
def get_candidature_details(matricule):
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT * FROM candidature WHERE matricule = %s"
        cursor.execute(query, (matricule,))
        candidature = cursor.fetchone()
        
        if not candidature:
            return jsonify({'success': False, 'error': 'Candidature introuvable'})
        
        doc_query = "SELECT * FROM document WHERE candidature_id = %s"
        cursor.execute(doc_query, (candidature['id'],))
        documents = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        if candidature['date_soumission']:
            candidature['date_soumission'] = candidature['date_soumission'].isoformat()
        
        for doc in documents:
            if doc['date_upload']:
                doc['date_upload'] = doc['date_upload'].isoformat()
        
        return jsonify({
            'success': True,
            'candidature': candidature,
            'documents': documents
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rh/candidature/<matricule>/status', methods=['POST'])
def update_candidature_status(matricule):
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        commentaire = data.get('commentaire', '').strip()
        
        if new_status not in ['ACCEPTEE', 'REFUSEE', 'EN_COURS']:
            return jsonify({'success': False, 'error': 'Statut invalide'})
        
        if new_status == 'REFUSEE' and not commentaire:
            return jsonify({
                'success': False, 
                'error': 'Un commentaire est obligatoire pour justifier le refus'
            })
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer infos du candidat
        cursor.execute("SELECT * FROM candidature WHERE matricule = %s", (matricule,))
        candidature = cursor.fetchone()
        
        if not candidature:
            return jsonify({'success': False, 'error': 'Candidature introuvable'})
        
        # Mise à jour
        if commentaire:
            query = """
                UPDATE candidature 
                SET statut = %s, commentaire = %s, date_commentaire = NOW() 
                WHERE matricule = %s
            """
            cursor.execute(query, (new_status, commentaire, matricule))
        else:
            query = "UPDATE candidature SET statut = %s WHERE matricule = %s"
            cursor.execute(query, (new_status, matricule))
        
        connection.commit()
        
        # Actions selon le statut
        if new_status == 'ACCEPTEE':
            try:
                creer_stagiaire_automatique(matricule)
                envoyer_email_acceptation(
                    candidature['email'],
                    matricule,
                    candidature['nom'],
                    candidature['prenom']
                )
            except Exception as email_error:
                print(f"❌ Erreur email acceptation: {email_error}")

        elif new_status == 'REFUSEE':
            try:
                envoyer_email_refus(
                    candidature['email'],
                    candidature['nom'],
                    candidature['prenom'],
                    commentaire
                )
            except Exception as email_error:
                print(f"❌ Erreur email refus: {email_error}")

        cursor.close()
        connection.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def envoyer_email_acceptation(email_destinataire, matricule, nom, prenom):
    """Envoyer un email d'acceptation de candidature"""
    try:
        base_url = get_public_url()
        suivi_url = f"{base_url}/suivi/{matricule}"
        
        # Configuration du message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎉 Félicitations ! Votre candidature a été acceptée - {matricule}"
        msg['From'] = f"Gestion Stagiaire <{GMAIL_USER}>"
        msg['To'] = email_destinataire

        # Email HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #27ae60, #229954); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .matricule-box {{ background: #e3f2fd; border-left: 5px solid #27ae60; padding: 25px; margin: 25px 0; border-radius: 8px; text-align: center; }}
                .matricule {{ font-family: 'Courier New', monospace; font-size: 32px; font-weight: bold; color: #1976d2; letter-spacing: 4px; }}
                .button {{ display: block; background: linear-gradient(135deg, #27ae60, #229954); color: white; padding: 20px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; text-align: center; font-size: 18px; margin: 30px auto; max-width: 300px; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 14px; }}
                .info-box {{ background: #f8f9fa; border-left: 4px solid #27ae60; padding: 15px; margin: 15px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Félicitations !</h1>
                    <p>Votre candidature a été acceptée</p>
                </div>
                
                <div class="content">
                    <p>Bonjour <strong>{prenom} {nom}</strong>,</p>
                    
                    <p style="color: #27ae60; font-weight: bold; font-size: 18px;">
                        ✅ Votre candidature de stage a été acceptée !
                    </p>
                    
                    <div class="info-box">
                        <p><strong>Prochaines étapes :</strong></p>
                        <ul>
                            <li>Un encadrant vous sera prochainement assigné</li>
                            <li>Vous recevrez les détails de votre stage par email</li>
                            <li>Vous pouvez suivre l'avancement avec votre matricule</li>
                        </ul>
                    </div>
                    
                    <p>Votre matricule de suivi :</p>
                    
                    <div class="matricule-box">
                        <div class="matricule">{matricule}</div>
                        <p style="margin: 15px 0 0 0; color: #1976d2; font-weight: 500;">
                            📱💻 Suivez l'avancement de votre stage
                        </p>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{suivi_url}" class="button">
                            🚀 Accéder au Suivi
                        </a>
                    </div>
                    
                    <p>Nous vous contacterons prochainement pour les détails de votre stage.</p>
                    
                    <p>Cordialement,<br>
                    <strong>L'équipe Gestion Stagiaire</strong></p>
                </div>
                
                <div class="footer">
                    <p>© 2025 Gestion Stagiaire - Plateforme digitale</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Version texte
        text_content = f"""
        FÉLICITATIONS ! VOTRE CANDIDATURE A ÉTÉ ACCEPTÉE 🎉
        
        Bonjour {prenom} {nom},
        ✅ Votre candidature de stage a été acceptée !
        
        🎫 Votre matricule de suivi : {matricule}
        🚀 Accès au suivi : {suivi_url}
        
        Prochaines étapes :
        - Un encadrant vous sera prochainement assigné
        - Vous recevrez les détails de votre stage par email
        - Vous pouvez suivre l'avancement avec votre matricule
        
        Nous vous contacterons prochainement pour les détails de votre stage.
        
        Cordialement,
        L'équipe Gestion Stagiaire
        """

        # Attacher les versions
        text_part = MIMEText(text_content, 'plain', 'utf-8')
        html_part = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(text_part)
        msg.attach(html_part)

        # Envoi
        context = ssl.create_default_context()
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls(context=context)
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
            
        print(f"✅ Email d'acceptation envoyé à {email_destinataire}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur envoi email d'acceptation: {str(e)}")
        return False

def envoyer_email_refus(email_destinataire, nom, prenom, commentaire):
    """Envoyer un email de refus de candidature"""
    try:
        base_url = get_public_url()

        msg = MIMEMultipart('alternative')
        msg['Subject'] = "❌ Réponse à votre candidature - Refus"
        msg['From'] = f"Gestion Stagiaire <{GMAIL_USER}>"
        msg['To'] = email_destinataire

        # Version texte simple
        text_content = f"""
Bonjour {prenom} {nom},

Nous vous remercions pour l'intérêt que vous portez à notre organisation.

Après étude de votre candidature, nous sommes au regret de vous informer qu'elle n'a pas été retenue.

Raison du refus :
{commentaire}

Nous vous souhaitons beaucoup de succès dans vos futures démarches.

Cordialement,
L'équipe Gestion Stagiaire
        """

        # Version HTML stylée
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #e74c3c, #c0392b); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .reason-box {{ background: #fdecea; border-left: 5px solid #e74c3c; padding: 20px; margin: 25px 0; border-radius: 8px; }}
                .reason-title {{ color: #c0392b; font-weight: bold; font-size: 18px; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>❌ Candidature non retenue</h1>
                    <p>Merci pour votre intérêt</p>
                </div>
                <div class="content">
                    <p>Bonjour <strong>{prenom} {nom}</strong>,</p>
                    <p>Nous vous remercions sincèrement pour l'intérêt que vous portez à notre organisation.</p>
                    <p>Après étude approfondie de votre dossier, nous sommes au regret de vous informer que votre candidature n'a pas été retenue.</p>
                    
                    <div class="reason-box">
                        <div class="reason-title">💡 Raison du refus :</div>
                        <p>{commentaire}</p>
                    </div>

                    <p>Nous vous encourageons à poursuivre vos démarches et vous souhaitons beaucoup de réussite dans vos futurs projets.</p>
                    
                    <p>Cordialement,<br>
                    <strong>L'équipe Gestion Stagiaire</strong></p>
                </div>
                <div class="footer">
                    <p>© 2025 Gestion Stagiaire - Plateforme digitale</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Attachement des parties
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        # Envoi via SMTP
        context = ssl.create_default_context()
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls(context=context)
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email de refus envoyé à {email_destinataire}")
        return True

    except Exception as e:
        print(f"❌ Erreur envoi email refus: {str(e)}")
        return False
    
@app.route('/rh/document/<path:filename>')
def view_document(filename):
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path) and file_path.startswith(app.config['UPLOAD_FOLDER']):
            return send_file(file_path, as_attachment=False)
        else:
            return redirect(url_for('dashboard_rh'))
            
    except Exception as e:
        return redirect(url_for('dashboard_rh'))

@app.route('/candidatures-acceptees')
def candidatures_acceptees():
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Candidatures acceptées
        query_stagiaires = """
    SELECT s.*, c.nom, c.prenom, c.email, c.etablissement, c.specialite, 
           c.date_debut, c.date_fin, c.date_soumission,
           e.nom as encadrant_nom, e.prenom as encadrant_prenom, 
           e.email as encadrant_email, e.specialite as encadrant_specialite,
           DATEDIFF(NOW(), c.date_soumission) as jours_attente
    FROM stagiaire s
    JOIN candidature c ON s.matricule = c.matricule
    LEFT JOIN encadrant e ON s.encadrant_id = e.id
    WHERE c.statut = 'ACCEPTEE' AND s.statut_avancement != 'TERMINE'
    ORDER BY c.date_soumission DESC
"""
        cursor.execute(query_stagiaires)
        stagiaires = cursor.fetchall()
        
        # Calculer le statut_config
        sujet_a_definir = "À définir par l'encadrant"
        
        for stagiaire in stagiaires:
            if stagiaire['encadrant_id'] is None:
                stagiaire['statut_config'] = 'EN_ATTENTE'
            elif stagiaire['sujet'] == sujet_a_definir or stagiaire['sujet'] is None:
                stagiaire['statut_config'] = 'ENCADRANT_ASSIGNE'
            else:
                stagiaire['statut_config'] = 'CONFIGURE'
        
        # Encadrants disponibles
        query_encadrants = """
            SELECT e.*, 
                   COUNT(s.id) as stagiaires_actuels,
                   (e.quota_max - COUNT(s.id)) as places_libres
            FROM encadrant e
            LEFT JOIN stagiaire s ON e.id = s.encadrant_id 
                AND s.statut_avancement IN ('EN_COURS', 'EN_ATTENTE')
            WHERE e.disponible = 1 AND e.actif = 1
            GROUP BY e.id
            ORDER BY places_libres DESC, e.specialite
        """
        cursor.execute(query_encadrants)
        encadrants = cursor.fetchall()
        
        # Évaluations en attente
        cursor.execute("SELECT COUNT(*) as count FROM evaluation WHERE validee_par_rh = 0")
        result = cursor.fetchone()
        evaluations_en_attente = result['count'] if result else 0
        
        stats = {
            'en_attente': len([s for s in stagiaires if s['statut_config'] == 'EN_ATTENTE']),
            'encadrant_assigne': len([s for s in stagiaires if s['statut_config'] == 'ENCADRANT_ASSIGNE']),
            'configure': len([s for s in stagiaires if s['statut_config'] == 'CONFIGURE']),
            'urgent': len([s for s in stagiaires if s['jours_attente'] > 7 and s['statut_config'] == 'EN_ATTENTE'])
        }
        
        cursor.close()
        connection.close()
        
        return render_template('candidatures_acceptees.html', 
                             stagiaires=stagiaires,
                             encadrants=encadrants,
                             stats=stats,
                             evaluations_en_attente=evaluations_en_attente,
                             rh_nom=session.get('rh_nom'),
                             rh_prenom=session.get('rh_prenom'))
                             
    except Exception as e:
        print(f"Erreur candidatures acceptées: {str(e)}")
        return redirect(url_for('dashboard_rh'))

@app.route('/assign-encadrant', methods=['POST'])
def assign_encadrant():
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        stagiaire_matricule = data.get('stagiaire_matricule')
        encadrant_id = data.get('encadrant_id')
        
        if not stagiaire_matricule or not encadrant_id:
            return jsonify({'success': False, 'error': 'Données manquantes'})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Vérifier capacité encadrant
        cursor.execute("""
            SELECT e.quota_max, COUNT(s.id) as charge_actuelle
            FROM encadrant e
            LEFT JOIN stagiaire s ON e.id = s.encadrant_id 
                AND s.statut_avancement IN ('EN_COURS', 'EN_ATTENTE')
            WHERE e.id = %s
            GROUP BY e.id
        """, (encadrant_id,))
        
        encadrant_info = cursor.fetchone()
        if not encadrant_info:
            return jsonify({'success': False, 'error': 'Encadrant introuvable'})
        
        if encadrant_info['charge_actuelle'] >= encadrant_info['quota_max']:
            return jsonify({'success': False, 'error': 'Encadrant déjà à pleine capacité'})
        
        sujet_generique = "À définir par l'encadrant"
        
        cursor.execute("""
            UPDATE stagiaire 
            SET encadrant_id = %s, 
                sujet = %s,
                statut_avancement = 'EN_ATTENTE'
            WHERE matricule = %s
        """, (encadrant_id, sujet_generique, stagiaire_matricule))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': 'Encadrant assigné avec succès ! L\'encadrant doit maintenant définir le sujet de stage.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rh/archives-stages')
def archives_stages():
    """Page d'archives des stages terminés"""
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer tous les stages terminés avec évaluations
        query = """
            SELECT s.*, c.nom, c.prenom, c.email, c.etablissement, c.specialite,
                   c.date_debut, c.date_fin, c.date_soumission,
                   e.nom as encadrant_nom, e.prenom as encadrant_prenom,
                   e.email as encadrant_email, e.specialite as encadrant_specialite,
                   ev.id as evaluation_id, ev.note_globale, ev.recommandation,
                   ev.date_evaluation, ev.validee_par_rh,
                   a.generee as attestation_generee,
                   DATEDIFF(s.date_fin_stage, s.date_debut_stage) as duree_jours
            FROM stagiaire s
            JOIN candidature c ON s.matricule = c.matricule
            LEFT JOIN encadrant e ON s.encadrant_id = e.id
            LEFT JOIN evaluation ev ON s.id = ev.stagiaire_id
            LEFT JOIN attestation a ON s.id = a.stagiaire_id AND a.generee = 1
            WHERE s.statut_avancement = 'TERMINE'
            ORDER BY s.date_fin_stage DESC, c.nom
        """
        cursor.execute(query)
        stages_archives = cursor.fetchall()
        
        # Statistiques
        cursor.execute("SELECT COUNT(*) as total FROM stagiaire WHERE statut_avancement = 'TERMINE'")
        total_archives = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT COUNT(*) as ce_mois FROM stagiaire 
            WHERE statut_avancement = 'TERMINE' 
            AND MONTH(date_fin_stage) = MONTH(CURDATE()) 
            AND YEAR(date_fin_stage) = YEAR(CURDATE())
        """)
        ce_mois = cursor.fetchone()['ce_mois']
        
        cursor.execute("""
            SELECT COUNT(*) as evalues FROM stagiaire s
            JOIN evaluation e ON s.id = e.stagiaire_id
            WHERE s.statut_avancement = 'TERMINE'
        """)
        evalues = cursor.fetchone()['evalues']
        
        cursor.execute("""
            SELECT AVG(ev.note_globale) as moyenne FROM evaluation ev
            JOIN stagiaire s ON ev.stagiaire_id = s.id
            WHERE s.statut_avancement = 'TERMINE'
        """)
        result = cursor.fetchone()
        note_moyenne = round(result['moyenne'], 1) if result['moyenne'] else 0.0
        
        stats = {
            'total_archives': total_archives,
            'ce_mois': ce_mois,
            'evalues': evalues,
            'note_moyenne': note_moyenne
        }
        
        cursor.close()
        connection.close()
        
        return render_template('archives_stages.html',
                             stages_archives=stages_archives,
                             stats=stats,
                             rh_nom=session.get('rh_nom'),
                             rh_prenom=session.get('rh_prenom'))
        
    except Exception as e:
        print(f"Erreur archives stages: {str(e)}")
        return redirect(url_for('dashboard_rh'))

# ===========================================
# ROUTES RH - ÉVALUATIONS
# ===========================================

@app.route('/rh/evaluations')
def liste_evaluations_rh():
    """Page de validation des évaluations pour le RH"""
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT ev.*, s.matricule, c.nom, c.prenom, c.email, c.etablissement, c.specialite,
                   e.nom as encadrant_nom, e.prenom as encadrant_prenom,
                   DATEDIFF(CURDATE(), ev.date_evaluation) as jours_attente
            FROM evaluation ev
            JOIN stagiaire s ON ev.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            JOIN encadrant e ON ev.encadrant_id = e.id
            ORDER BY 
                CASE WHEN ev.validee_par_rh = 0 THEN 0 ELSE 1 END,
                ev.date_evaluation DESC
        """
        cursor.execute(query)
        evaluations = cursor.fetchall()
        
        a_valider = [e for e in evaluations if e['validee_par_rh'] == 0]
        validees = [e for e in evaluations if e['validee_par_rh'] == 1]
        
        stats = {
            'total': len(evaluations),
            'a_valider': len(a_valider),
            'validees': len(validees),
            'urgent': len([e for e in a_valider if e['jours_attente'] and e['jours_attente'] > 3])
        }
        
        cursor.close()
        connection.close()
        
        return render_template('rh_evaluations.html', 
                             a_valider=a_valider,
                             validees=validees,
                             stats=stats,
                             rh_nom=session.get('rh_nom'),
                             rh_prenom=session.get('rh_prenom'))
        
    except Exception as e:
        print(f"Erreur liste évaluations RH: {str(e)}")
        return redirect(url_for('dashboard_rh'))

@app.route('/rh/valider-evaluation', methods=['POST'])
def valider_evaluation_rh():
    """Validation d'une évaluation par le RH"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        evaluation_id = data.get('evaluation_id')
        
        if not evaluation_id:
            return jsonify({'success': False, 'error': 'ID évaluation manquant'})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT ev.id, s.matricule, c.nom, c.prenom, ev.validee_par_rh
            FROM evaluation ev
            JOIN stagiaire s ON ev.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            WHERE ev.id = %s
        """, (evaluation_id,))
        
        evaluation = cursor.fetchone()
        
        if not evaluation:
            return jsonify({'success': False, 'error': 'Évaluation non trouvée'})
        
        if evaluation['validee_par_rh'] == 1:
            return jsonify({'success': False, 'error': 'Évaluation déjà validée'})
        
        cursor.execute("UPDATE evaluation SET validee_par_rh = 1 WHERE id = %s", (evaluation_id,))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': f'✅ Évaluation de {evaluation["prenom"]} {evaluation["nom"]} validée avec succès !',
            'matricule': evaluation['matricule']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===========================================
# ROUTES RH - ATTESTATIONS
# ===========================================

@app.route('/rh/attestations')
def rh_attestations():
    """Page de gestion des attestations pour le RH"""
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Demandes en attente
        query_demandes = """
            SELECT a.*, s.matricule, c.nom, c.prenom, c.email, c.etablissement,
                   s.date_debut_stage, s.date_fin_stage, s.sujet,
                   e.nom as encadrant_nom, e.prenom as encadrant_prenom,
                   ev.note_globale, ev.recommandation,
                   DATEDIFF(CURDATE(), a.date_demande) as jours_attente
            FROM attestation a
            JOIN stagiaire s ON a.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            LEFT JOIN encadrant e ON s.encadrant_id = e.id
            LEFT JOIN evaluation ev ON s.id = ev.stagiaire_id
            WHERE a.demandee = 1 AND (a.generee = 0 OR a.generee IS NULL)
            ORDER BY a.date_demande ASC
        """
        cursor.execute(query_demandes)
        demandes = cursor.fetchall()
        
        # Attestations générées
        query_generees = """
            SELECT a.*, s.matricule, c.nom, c.prenom, c.email,
                   s.date_debut_stage, s.date_fin_stage,
                   e.nom as encadrant_nom, e.prenom as encadrant_prenom
            FROM attestation a
            JOIN stagiaire s ON a.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            LEFT JOIN encadrant e ON s.encadrant_id = e.id
            WHERE a.generee = 1
            ORDER BY a.date_generation DESC
            LIMIT 50
        """
        cursor.execute(query_generees)
        generees = cursor.fetchall()
        
        stats = {
            'total_demandes': len(demandes) + len(generees),
            'en_attente': len(demandes),
            'generees': len(generees),
            'urgent': len([d for d in demandes if d['jours_attente'] and d['jours_attente'] > 2])
        }
        
        cursor.close()
        connection.close()
        
        return render_template('rh_attestations.html', 
                             demandes=demandes,
                             generees=generees,
                             stats=stats,
                             rh_nom=session.get('rh_nom'),
                             rh_prenom=session.get('rh_prenom'))
        
    except Exception as e:
        print(f"Erreur page attestations RH: {str(e)}")
        return redirect(url_for('dashboard_rh'))

@app.route('/rh/generer-attestation', methods=['POST'])
def generer_attestation_pdf():
    """Générer l'attestation en PDF selon le modèle ministériel exact - VERSION FINALE"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        # Vérifier ReportLab
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm, mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT, TA_LEFT
            from reportlab.platypus.flowables import HRFlowable
            print("✅ ReportLab importé avec succès")
        except ImportError as e:
            print(f"❌ Erreur import ReportLab: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ReportLab non installé. Exécutez: pip install reportlab'
            })
        
        data = request.get_json()
        attestation_id = data.get('attestation_id')
        
        print(f"🔍 Demande génération attestation ID: {attestation_id}")
        
        if not attestation_id:
            return jsonify({'success': False, 'error': 'ID attestation manquant'})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer toutes les informations nécessaires
        query = """
            SELECT a.*, s.matricule, s.date_debut_stage, s.date_fin_stage, s.sujet,
                   c.nom, c.prenom, c.email, c.etablissement, c.specialite,
                   e.nom as encadrant_nom, e.prenom as encadrant_prenom,
                   ev.note_globale, ev.recommandation
            FROM attestation a
            JOIN stagiaire s ON a.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            LEFT JOIN encadrant e ON s.encadrant_id = e.id
            LEFT JOIN evaluation ev ON s.id = ev.stagiaire_id
            WHERE a.id = %s
        """
        cursor.execute(query, (attestation_id,))
        attestation_data = cursor.fetchone()
        
        if not attestation_data:
            return jsonify({'success': False, 'error': 'Attestation non trouvée'})
        
        print(f"📋 Données récupérées pour: {attestation_data['prenom']} {attestation_data['nom']}")
        
        # Générer le numéro d'attestation unique
        numero_attestation = f"MTAESS/DRH/ATT-{datetime.now().year}-{attestation_id:04d}"
        
        # Créer le nom de fichier unique
        filename = f"attestation_{attestation_data['matricule']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        print(f"📄 Création du PDF: {filepath}")
        
        # ============================================
        # GÉNÉRATION PDF SELON LE MODÈLE EXACT
        # ============================================
        
        # Créer le document PDF avec marges exactes
        doc = SimpleDocTemplate(
            filepath, 
            pagesize=A4,
            topMargin=2*cm, 
            bottomMargin=3*cm,
            leftMargin=2.5*cm, 
            rightMargin=2.5*cm
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # ============================================
        # STYLES EXACTS DU MINISTÈRE
        # ============================================
        
        # Style pour le header principal (noir, centré)
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=16,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            leading=20,
            spaceAfter=5
        )
        
        # Style pour la direction (noir, centré, plus petit)
        direction_style = ParagraphStyle(
            'DirectionStyle',
            parent=styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            leading=16,
            spaceAfter=30
        )
        
        # Style pour le titre ATTESTATION DE STAGE (rouge, très grand)
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Normal'],
            fontSize=26,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#c1272d'),  # Rouge ministériel
            fontName='Helvetica-Bold',
            spaceBefore=20,
            spaceAfter=15,
            leading=30
        )
        
        # Style pour le numéro (noir, centré)
        numero_style = ParagraphStyle(
            'NumeroStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica',
            spaceAfter=25
        )
        
        # Style pour le texte principal
        main_text_style = ParagraphStyle(
            'MainTextStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_JUSTIFY,
            textColor=colors.black,
            fontName='Helvetica',
            leading=18,
            spaceBefore=8,
            spaceAfter=8
        )
        
        # Style pour le texte en gras
        bold_text_style = ParagraphStyle(
            'BoldTextStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_JUSTIFY,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            leading=18,
            spaceBefore=8,
            spaceAfter=8
        )
        
        # Style pour la signature
        signature_style = ParagraphStyle(
            'SignatureStyle',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_RIGHT,
            textColor=colors.black,
            fontName='Helvetica',
            spaceBefore=30
        )
        
        # ============================================
        # CONSTRUCTION DU DOCUMENT SELON LE MODÈLE EXACT
        # ============================================
        
        try:
            # 1. EN-TÊTE AVEC LOGO DU ROYAUME DU MAROC (format exact)
            logo_path = os.path.join('static', 'images', 'logo_ministere.png')
            
            if os.path.exists(logo_path):
                print(f"🔸 Logo trouvé: {logo_path}")
                try:
                    # Logo des armoiries du Royaume du Maroc (proportions correctes)
                    # Maintenir les proportions naturelles du logo
                    logo_img = Image(logo_path, width=2.5*cm, height=2.5*cm, kind='proportional')
                    
                    # Créer tableau pour disposer logo + texte ministériel (format exact)
                    header_data = [[
                        logo_img,
                        Paragraph("""<b>Royaume du Maroc<br/>
                        Ministère du Tourisme, de l'Artisanat<br/>
                        et de l'Économie Sociale et Solidaire</b>""", header_style)
                    ]]
                    
                    header_table = Table(header_data, colWidths=[3*cm, 13*cm])
                    header_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),  # Logo centré dans sa cellule
                        ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # Texte centré
                        ('LEFTPADDING', (0, 0), (-1, -1), 5),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ]))
                    
                    story.append(header_table)
                    print("✅ En-tête avec logo officiel créé selon le modèle exact")
                    
                except Exception as logo_error:
                    print(f"⚠️ Erreur chargement logo: {str(logo_error)}")
                    # Fallback sans logo mais avec le bon format
                    story.append(Paragraph("<b>Royaume du Maroc<br/>Ministère du Tourisme, de l'Artisanat<br/>et de l'Économie Sociale et Solidaire</b>", header_style))
            else:
                print(f"⚠️ Logo non trouvé: {logo_path}")
                # En-tête sans logo mais avec le bon format
                story.append(Paragraph("<b>Royaume du Maroc<br/>Ministère du Tourisme, de l'Artisanat<br/>et de l'Économie Sociale et Solidaire</b>", header_style))
            
            story.append(Spacer(1, 8))
            
            # 2. DIRECTION DES RESSOURCES HUMAINES (position exacte)
            story.append(Paragraph("<b>Direction des Ressources Humaines</b>", direction_style))
            
            # 3. LIGNE ROUGE DE SÉPARATION (épaisseur et couleur exactes)
            story.append(Spacer(1, 15))
            story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#c1272d')))
            story.append(Spacer(1, 25))
            
            # 4. TITRE PRINCIPAL "ATTESTATION DE STAGE" (rouge, grand)
            story.append(Paragraph("ATTESTATION DE STAGE", title_style))
            
            # 5. NUMÉRO D'ATTESTATION
            story.append(Paragraph(f"N° {numero_attestation}", numero_style))
            story.append(Spacer(1, 15))
            
            # 6. TEXTE D'INTRODUCTION (exactement comme le modèle)
            intro_text = """Le Directeur des Ressources Humaines du Ministère du Tourisme, de l'Artisanat et de l'Économie Sociale et Solidaire atteste par la présente que :"""
            story.append(Paragraph(intro_text, main_text_style))
            story.append(Spacer(1, 20))
            
            # 7. TABLEAU DES INFORMATIONS (format exact du modèle)
            info_data = [
                ['Nom et Prénom', f"{attestation_data['prenom']} {attestation_data['nom']}"],
                ['Matricule', attestation_data['matricule']],
                ['Établissement', attestation_data['etablissement']],
                ['Spécialité', attestation_data['specialite']]
            ]
            
            info_table = Table(info_data, colWidths=[4*cm, 10*cm])
            info_table.setStyle(TableStyle([
                # Bordures exactes comme le modèle
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                
                # Colonne de gauche (labels)
                ('BACKGROUND', (0, 0), (0, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                
                # Colonne de droite (valeurs)
                ('BACKGROUND', (1, 0), (1, -1), colors.white),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                
                # Alignement et padding
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 20))
            
            # 8. PÉRIODE DE STAGE (format exact du modèle)
            date_debut = attestation_data['date_debut_stage']
            date_fin = attestation_data['date_fin_stage']
            
            if date_debut and date_fin:
                # Assurer que ce sont des objets date
                if hasattr(date_debut, 'date'):
                    date_debut = date_debut.date() if date_debut else None
                if hasattr(date_fin, 'date'):
                    date_fin = date_fin.date() if date_fin else None
                
                if date_debut and date_fin:
                    date_debut_str = date_debut.strftime('%d/%m/%Y')
                    date_fin_str = date_fin.strftime('%d/%m/%Y')
                    
                    # Calculer la durée exacte comme dans le modèle
                    duree_jours = (date_fin - date_debut).days + 1
                    mois = duree_jours // 30
                    jours_restants = duree_jours % 30
                    
                    if mois > 0:
                        if jours_restants > 0:
                            duree_text = f"{mois} mois et {jours_restants} jour{'s' if jours_restants > 1 else ''}"
                        else:
                            duree_text = f"{mois} mois"
                    else:
                        duree_text = f"{duree_jours} jour{'s' if duree_jours > 1 else ''}"
                    
                    # Format exact : "A effectué un stage au sein de notre Ministère durant la période du ... au ..., soit une durée de ..."
                    periode_text = f"""A effectué un stage au sein de notre Ministère durant la période du <b>{date_debut_str}</b> au <b>{date_fin_str}</b>, soit une durée de <b>{duree_text}</b>."""
                else:
                    periode_text = "A effectué un stage au sein de notre Ministère."
            else:
                periode_text = "A effectué un stage au sein de notre Ministère."
            
            story.append(Paragraph(periode_text, main_text_style))
            story.append(Spacer(1, 20))
            
            # 9. SUJET DU STAGE (format exact du modèle)
            if attestation_data['sujet'] and attestation_data['sujet'] != 'À définir par l\'encadrant':
                story.append(Paragraph("<b>Sujet du stage :</b>", main_text_style))
                story.append(Spacer(1, 8))
                # Format exact avec guillemets
                story.append(Paragraph(f'"{attestation_data["sujet"]}"', main_text_style))
                story.append(Spacer(1, 15))
            
            # 10. ENCADRANT (format exact du modèle)
            if attestation_data['encadrant_nom']:
                encadrant_text = f"<b>Encadrant :</b> {attestation_data['encadrant_prenom']} {attestation_data['encadrant_nom']}"
                story.append(Paragraph(encadrant_text, main_text_style))
                story.append(Spacer(1, 20))
            
            # 11. ÉVALUATION ET RECOMMANDATION (format exact du modèle)
            if attestation_data['note_globale'] is not None:
                note = float(attestation_data['note_globale'])
                
                # Calcul de la mention (exactement comme le modèle)
                if note >= 16:
                    mention = "Très Bien"
                elif note >= 14:
                    mention = "Bien"
                elif note >= 12:
                    mention = "Assez Bien"
                elif note >= 10:
                    mention = "Passable"
                else:
                    mention = "Insuffisant"
                
                # Format exact du modèle avec guillemets français
                note_text = f"""Le/La stagiaire a obtenu la note de <b>{note:.2f}/20</b> avec la mention « <b>{mention}</b> »."""
                story.append(Paragraph(note_text, main_text_style))
                story.append(Spacer(1, 15))
                
                # Recommandation (format exact)
                if attestation_data['recommandation']:
                    recommandation_text = "Le Ministère recommande ce/cette stagiaire pour ses qualités professionnelles et son sérieux durant la période de stage."
                    story.append(Paragraph(recommandation_text, main_text_style))
                    story.append(Spacer(1, 20))
            
            # 12. CONCLUSION OFFICIELLE (format exact)
            conclusion = "Cette attestation est délivrée à l'intéressé(e) pour servir et valoir ce que de droit."
            story.append(Paragraph(conclusion, main_text_style))
            story.append(Spacer(1, 50))
            
            # 13. SIGNATURE (format exact du modèle)
            date_actuelle = datetime.now().strftime('%d/%m/%Y')
            
            # Créer la signature exactement comme dans le modèle
            signature_data = [
                [f"Fait à Rabat, le {date_actuelle}", "Le Directeur des Ressources"],
                ["", "Humaines"],
                ["", ""],
                ["", ""],
                ["", ""]  # Espace pour signature manuscrite
            ]
            
            signature_table = Table(signature_data, colWidths=[8*cm, 8*cm])
            signature_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (1, 0), (1, 1), 'Helvetica-Bold'),  # "Le Directeur..." en gras
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            
            story.append(signature_table)
            
            # Ajouter le nom du signataire (RH qui génère l'attestation)
            story.append(Spacer(1, 30))
            rh_nom = session.get('rh_nom', 'Service RH')
            rh_prenom = session.get('rh_prenom', '')
            signataire = f"{rh_prenom} {rh_nom}" if rh_prenom else rh_nom
            
            story.append(Paragraph(f"<para align='right'><b>{signataire}</b></para>", main_text_style))
            
            print("📋 Contenu du document préparé selon le modèle exact")
            
        except Exception as content_error:
            print(f"❌ Erreur préparation contenu: {str(content_error)}")
            return jsonify({'success': False, 'error': f'Erreur contenu: {str(content_error)}'})
        
        # ============================================
        # GÉNÉRATION DU PDF
        # ============================================
        
        try:
            print("📄 Génération du PDF en cours...")
            doc.build(story)
            print(f"✅ PDF généré avec succès: {filepath}")
        except Exception as pdf_error:
            print(f"❌ Erreur génération PDF: {str(pdf_error)}")
            return jsonify({'success': False, 'error': f'Erreur PDF: {str(pdf_error)}'})
        
        # Vérifications
        if not os.path.exists(filepath):
            print(f"❌ Fichier non créé: {filepath}")
            return jsonify({'success': False, 'error': 'Le fichier PDF n\'a pas été créé'})
        
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            print(f"❌ Fichier vide: {filepath}")
            return jsonify({'success': False, 'error': 'Le fichier PDF généré est vide'})
        
        print(f"📊 Taille du fichier: {file_size} bytes")
        
        # Mettre à jour la base de données
        try:
            update_query = """
                UPDATE attestation 
                SET generee = 1, 
                    date_generation = NOW(), 
                    chemin_fichier = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (filename, attestation_id))
            connection.commit()
            print("✅ Base de données mise à jour")
        except Exception as db_error:
            print(f"⚠️ Erreur mise à jour DB: {str(db_error)}")
        
        cursor.close()
        connection.close()
        
        print(f"🎉 SUCCÈS - Attestation générée selon le modèle exact: {filename}")
        
        return jsonify({
            'success': True,
            'message': f'✅ Attestation ministérielle générée selon le modèle exact ! Taille: {round(file_size/1024, 1)} KB',
            'filename': filename,
            'numero': numero_attestation,
            'matricule': attestation_data['matricule'],
            'size': file_size
        })
        
    except Exception as e:
        print(f"❌ ERREUR GLOBALE: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Erreur interne: {str(e)}'})

@app.route('/rh/telecharger-attestation/<filename>')
def rh_telecharger_attestation(filename):
    """Télécharger une attestation PDF générée côté RH"""
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Vérifier que le fichier existe et est un PDF d'attestation
        if (os.path.exists(file_path) and 
            filename.startswith('attestation_') and 
            filename.endswith('.pdf')):
            
            print(f"📥 Téléchargement attestation PDF: {filename}")
            
            return send_file(file_path, 
                           as_attachment=True, 
                           download_name=filename,
                           mimetype='application/pdf')
        else:
            print(f"❌ Fichier PDF non trouvé: {filename}")
            return redirect(url_for('rh_attestations'))
            
    except Exception as e:
        print(f"❌ Erreur téléchargement attestation: {str(e)}")
        return redirect(url_for('rh_attestations'))

@app.route('/rh/upload-attestation', methods=['POST'])
def upload_attestation():
    """Upload manuel d'une attestation PDF uniquement"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        attestation_id = request.form.get('attestation_id')
        
        if not attestation_id:
            return jsonify({'success': False, 'error': 'ID attestation manquant'})
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'})
        
        # Vérifier STRICTEMENT que c'est un PDF
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Seuls les fichiers PDF sont acceptés'})
        
        # Vérifier le type MIME
        if file.content_type != 'application/pdf':
            return jsonify({'success': False, 'error': 'Le fichier doit être un PDF valide'})
        
        # Générer un nom unique pour le fichier PDF
        filename = f"attestation_upload_{attestation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Sauvegarder le fichier
        file.save(filepath)
        
        # Vérifier la taille du fichier
        file_size = os.path.getsize(filepath)
        if file_size > 5 * 1024 * 1024:  # 5MB max
            os.remove(filepath)
            return jsonify({'success': False, 'error': 'Le fichier PDF ne peut pas dépasser 5MB'})
        
        # Vérifier que c'est vraiment un PDF en lisant l'en-tête
        with open(filepath, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                os.remove(filepath)
                return jsonify({'success': False, 'error': 'Le fichier n\'est pas un PDF valide'})
        
        # Mettre à jour la base de données
        connection = get_db_connection()
        cursor = connection.cursor()
        
        update_query = """
            UPDATE attestation 
            SET generee = 1, 
                date_generation = NOW(), 
                chemin_fichier = %s
            WHERE id = %s
        """
        cursor.execute(update_query, (filename, attestation_id))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        print(f"✅ Attestation PDF uploadée: {filename} ({file_size} bytes)")
        
        return jsonify({
            'success': True,
            'message': f'Attestation PDF uploadée avec succès ! Taille: {round(file_size/1024, 1)} KB',
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# 5. FONCTION DE VÉRIFICATION
@app.route('/rh/verifier-attestations-pdf')
def verifier_attestations_pdf():
    """Vérifier que toutes les attestations sont bien en PDF"""
    if not session.get('rh_logged_in'):
        return jsonify({'error': 'Non autorisé'})
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer toutes les attestations générées
        cursor.execute("""
            SELECT id, chemin_fichier 
            FROM attestation 
            WHERE generee = 1 AND chemin_fichier IS NOT NULL
        """)
        attestations = cursor.fetchall()
        
        pdf_count = 0
        non_pdf_count = 0
        missing_files = 0
        
        for att in attestations:
            filename = att['chemin_fichier']
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            if not os.path.exists(file_path):
                missing_files += 1
                continue
            
            if filename.endswith('.pdf'):
                pdf_count += 1
            else:
                non_pdf_count += 1
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'total': len(attestations),
            'pdf_count': pdf_count,
            'non_pdf_count': non_pdf_count,
            'missing_files': missing_files,
            'status': 'OK' if non_pdf_count == 0 and missing_files == 0 else 'PROBLEMES_DETECTES'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===========================================
# ROUTES ENCADRANT
# ===========================================

@app.route('/encadrant/definir-sujet/<matricule>', methods=['POST'])
def definir_sujet_stagiaire(matricule):
    if not session.get('encadrant_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        nouveau_sujet = data.get('sujet', '').strip()
        
        if not nouveau_sujet:
            return jsonify({'success': False, 'error': 'Le sujet ne peut pas être vide'})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        cursor.execute("""
            SELECT s.id, c.nom, c.prenom, s.sujet
            FROM stagiaire s
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.matricule = %s AND s.encadrant_id = %s
        """, (matricule, encadrant_id))
        
        stagiaire = cursor.fetchone()
        if not stagiaire:
            return jsonify({'success': False, 'error': 'Stagiaire non trouvé ou non assigné à vous'})
        
        cursor.execute("""
            UPDATE stagiaire 
            SET sujet = %s, 
                statut_avancement = 'EN_COURS'
            WHERE matricule = %s AND encadrant_id = %s
        """, (nouveau_sujet, matricule, encadrant_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': f'Stage démarré avec succès pour {stagiaire["prenom"]} {stagiaire["nom"]} !',
            'sujet': nouveau_sujet
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/encadrant/terminer-stage/<matricule>', methods=['POST'])
def terminer_stage(matricule):
    if not session.get('encadrant_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        cursor.execute("""
            SELECT s.id, c.nom, c.prenom
            FROM stagiaire s
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.matricule = %s AND s.encadrant_id = %s AND s.statut_avancement = 'EN_COURS'
        """, (matricule, encadrant_id))
        
        stagiaire = cursor.fetchone()
        if not stagiaire:
            return jsonify({'success': False, 'error': 'Stagiaire non trouvé ou stage déjà terminé'})
        
        cursor.execute("""
            UPDATE stagiaire 
            SET statut_avancement = 'TERMINE'
            WHERE matricule = %s AND encadrant_id = %s
        """, (matricule, encadrant_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': f'Stage de {stagiaire["prenom"]} {stagiaire["nom"]} terminé avec succès ! Vous pouvez maintenant l\'évaluer.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/encadrant/evaluer/<matricule>')
def evaluer_stagiaire_form(matricule):
    if not session.get('encadrant_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        cursor.execute("""
            SELECT s.*, c.nom, c.prenom, c.email, c.etablissement, c.specialite,
                   ev.id as evaluation_id, ev.note_globale, ev.commentaires, 
                   ev.recommandation, ev.validee_par_rh
            FROM stagiaire s
            JOIN candidature c ON s.matricule = c.matricule
            LEFT JOIN evaluation ev ON s.id = ev.stagiaire_id
            WHERE s.matricule = %s AND s.encadrant_id = %s AND s.statut_avancement = 'TERMINE'
        """, (matricule, encadrant_id))
        
        stagiaire = cursor.fetchone()
        
        if not stagiaire:
            return redirect(url_for('dashboard_encadrant'))
        
        cursor.close()
        connection.close()
        
        return render_template('evaluation_form.html', 
                             stagiaire=stagiaire,
                             encadrant_nom=session.get('encadrant_nom'),
                             encadrant_prenom=session.get('encadrant_prenom'))
        
    except Exception as e:
        print(f"Erreur formulaire évaluation: {str(e)}")
        return redirect(url_for('dashboard_encadrant'))

@app.route('/encadrant/sauvegarder-evaluation', methods=['POST'])
def sauvegarder_evaluation():
    if not session.get('encadrant_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        matricule = data.get('matricule')
        note_globale = data.get('note_globale')
        commentaires = data.get('commentaires', '').strip()
        recommandation = data.get('recommandation', False)
        
        # Validations
        if not matricule or note_globale is None:
            return jsonify({'success': False, 'error': 'Données manquantes'})
        
        try:
            note_globale = float(note_globale)
            if note_globale < 0 or note_globale > 20:
                return jsonify({'success': False, 'error': 'La note doit être entre 0 et 20'})
        except ValueError:
            return jsonify({'success': False, 'error': 'Note invalide'})
        
        if not commentaires or len(commentaires) < 10:
            return jsonify({'success': False, 'error': 'Les commentaires sont obligatoires (minimum 10 caractères)'})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        cursor.execute("""
            SELECT s.id, c.nom, c.prenom
            FROM stagiaire s
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.matricule = %s AND s.encadrant_id = %s AND s.statut_avancement = 'TERMINE'
        """, (matricule, encadrant_id))
        
        stagiaire = cursor.fetchone()
        if not stagiaire:
            return jsonify({'success': False, 'error': 'Stagiaire non trouvé ou stage non terminé'})
        
        # Vérifier si évaluation existe
        cursor.execute("SELECT id FROM evaluation WHERE stagiaire_id = %s", (stagiaire['id'],))
        evaluation_existante = cursor.fetchone()
        
        if evaluation_existante:
            # Mise à jour
            cursor.execute("""
                UPDATE evaluation 
                SET note_globale = %s, commentaires = %s, recommandation = %s, 
                    date_evaluation = NOW()
                WHERE stagiaire_id = %s
            """, (note_globale, commentaires, recommandation, stagiaire['id']))
            message = f'Évaluation de {stagiaire["prenom"]} {stagiaire["nom"]} mise à jour avec succès'
        else:
            # Nouvelle évaluation
            cursor.execute("""
                INSERT INTO evaluation (stagiaire_id, encadrant_id, note_globale, 
                                      commentaires, recommandation, date_evaluation, validee_par_rh)
                VALUES (%s, %s, %s, %s, %s, NOW(), 0)
            """, (stagiaire['id'], encadrant_id, note_globale, commentaires, recommandation))
            message = f'Évaluation de {stagiaire["prenom"]} {stagiaire["nom"]} créée avec succès'
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': message
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===========================================
# ROUTES ADMIN
# ===========================================

@app.route('/admin/ajouter_rh', methods=['POST'])
def ajouter_rh():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Validation des données
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        email = request.form.get('email', '').strip()
        
        # Vérifier que tous les champs requis sont présents
        if not nom or not prenom or not email:
            flash('Tous les champs sont requis', 'error')
            return redirect(url_for('dashboard_admin'))
        
        # Validation basique de l'email
        if '@' not in email or '.' not in email:
            flash('Email invalide', 'error')
            return redirect(url_for('dashboard_admin'))
        
        matricule_rh = f"RH{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(2).upper()}"
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Vérifier si l'email existe déjà
        cursor.execute("SELECT id FROM service_rh WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('Cet email est déjà utilisé', 'error')
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard_admin'))
        
        query = """INSERT INTO service_rh (nom, prenom, matricule, email, mot_de_passe, actif, date_creation)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        
        mot_de_passe_defaut = "rh123456"  # Considérez le hachage du mot de passe
        
        cursor.execute(query, (nom, prenom, matricule_rh, email, mot_de_passe_defaut, 1, datetime.now()))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        flash(f'RH {nom} {prenom} ajouté avec succès. Matricule: {matricule_rh}', 'success')
        
    except mysql.connector.Error as e:
        flash(f'Erreur de base de données: {str(e)}', 'error')
        logging.error(f"Erreur DB lors de l'ajout RH: {e}")
        
    except Exception as e:
        flash(f'Erreur inattendue: {str(e)}', 'error')
        logging.error(f"Erreur lors de l'ajout RH: {e}")
    
    return redirect(url_for('dashboard_admin'))


@app.route('/admin/ajouter_encadrant', methods=['POST'])
def ajouter_encadrant():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Validation des données
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        email = request.form.get('email', '').strip()
        specialite = request.form.get('specialite', '').strip()
        
        # Vérifier que tous les champs requis sont présents
        if not nom or not prenom or not email or not specialite:
            flash('Tous les champs sont requis', 'error')
            return redirect(url_for('dashboard_admin'))
        
        # Validation basique de l'email
        if '@' not in email or '.' not in email:
            flash('Email invalide', 'error')
            return redirect(url_for('dashboard_admin'))
        
        matricule_enc = f"ENC{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(2).upper()}"
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Vérifier si l'email existe déjà
        cursor.execute("SELECT id FROM encadrant WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('Cet email est déjà utilisé', 'error')
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard_admin'))
        
        query = """INSERT INTO encadrant (nom, prenom, matricule, email, mot_de_passe, actif,
                   quota_max, specialite, disponible, date_creation)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        
        mot_de_passe_defaut = "enc123456"  # Considérez le hachage du mot de passe
        quota_max = 5
        
        cursor.execute(query, (nom, prenom, matricule_enc, email, mot_de_passe_defaut, 1,
                              quota_max, specialite, 1, datetime.now()))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        flash(f'Encadrant {nom} {prenom} ajouté avec succès. Matricule: {matricule_enc}', 'success')
        
    except mysql.connector.Error as e:
        flash(f'Erreur de base de données: {str(e)}', 'error')
        logging.error(f"Erreur DB lors de l'ajout encadrant: {e}")
        
    except Exception as e:
        flash(f'Erreur inattendue: {str(e)}', 'error')
        logging.error(f"Erreur lors de l'ajout encadrant: {e}")
    
    return redirect(url_for('dashboard_admin'))

@app.route('/admin/modifier_rh_form/<int:rh_id>')
def modifier_rh_form(rh_id):
    """Formulaire de modification d'un personnel RH"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM service_rh WHERE id = %s", (rh_id,))
        edit_rh = cursor.fetchone()
        
        if not edit_rh:
            return redirect(url_for('dashboard_admin'))
        
        cursor.close()
        connection.close()
        
        return render_template('admin_modifier.html', 
                             edit_rh=edit_rh,
                             admin_nom=session.get('admin_nom'))
        
    except Exception as e:
        print(f"Erreur formulaire modification RH: {str(e)}")
        return redirect(url_for('dashboard_admin'))

@app.route('/admin/modifier_rh', methods=['POST'])
def modifier_rh():
    """Traiter la modification d'un personnel RH"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        rh_id = request.form.get('id')
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([rh_id, nom, prenom, email]):
            return redirect(url_for('modifier_rh_form', rh_id=rh_id))
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        if password and password.strip():
            query = """
                UPDATE service_rh 
                SET nom = %s, prenom = %s, email = %s, mot_de_passe = %s
                WHERE id = %s
            """
            cursor.execute(query, (nom, prenom, email, password.strip(), rh_id))
        else:
            query = """
                UPDATE service_rh 
                SET nom = %s, prenom = %s, email = %s
                WHERE id = %s
            """
            cursor.execute(query, (nom, prenom, email, rh_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return redirect(url_for('dashboard_admin'))
        
    except mysql.connector.Error as e:
        return redirect(url_for('modifier_rh_form', rh_id=rh_id))
    except Exception as e:
        return redirect(url_for('modifier_rh_form', rh_id=rh_id))

@app.route('/admin/supprimer_rh/<int:rh_id>', methods=['POST'])
def supprimer_rh(rh_id):
    """Supprimer un personnel RH"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT nom, prenom FROM service_rh WHERE id = %s", (rh_id,))
        rh_info = cursor.fetchone()
        
        if not rh_info:
            return redirect(url_for('dashboard_admin'))
        
        cursor.execute("DELETE FROM service_rh WHERE id = %s", (rh_id,))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return redirect(url_for('dashboard_admin'))
        
    except mysql.connector.Error as e:
        return redirect(url_for('dashboard_admin'))
    except Exception as e:
        return redirect(url_for('dashboard_admin'))

# ===========================================
# ROUTES CHATBOT
# ===========================================

@app.route('/api/chatbot', methods=['POST'])
def chatbot_api():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False, 
                'error': 'Message vide'
            })
        
        if len(user_message) > 500:
            return jsonify({
                'success': False,
                'error': 'Message trop long (max 500 caractères)'
            })
        
        result = chatbot_service.get_response(user_message)
        
        return jsonify({
            'success': result['success'],
            'response': result['response'],
            'provider': result.get('provider', 'Unknown'),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Erreur serveur',
            'response': """🔧 **Une erreur technique s'est produite.**

📞 **Support disponible :**
📧 support@gestion-stagiaire.com  
📞 +33 1 23 45 67 89
🕒 Lundi-Vendredi 9h-17h

🔄 Veuillez réessayer dans quelques instants."""
        })

@app.route('/api/chatbot/health', methods=['GET'])
def chatbot_health():
    try:
        ollama_available = chatbot_service.check_ollama_connection()
        
        status = 'healthy' if ollama_available else 'limited'
        
        return jsonify({
            'ollama_available': ollama_available,
            'status': status,
            'message': {
                'healthy': '✅ Chatbot IA opérationnel',
                'limited': '⚠️ Fonctionnalités limitées'
            }.get(status, '❌ Hors service')
        })
        
    except Exception as e:
        return jsonify({
            'ollama_available': False,
            'status': 'error',
            'message': f'❌ Erreur: {str(e)}'
        })

# ===========================================
# ROUTES LOGOUT
# ===========================================

@app.route('/rh/logout')
def rh_logout():
    session.pop('rh_logged_in', None)
    session.pop('rh_id', None)
    session.pop('rh_nom', None)
    session.pop('rh_prenom', None)
    session.pop('rh_matricule', None)
    
    return redirect(url_for('personnel'))

@app.route('/encadrant/logout')
def encadrant_logout():
    session.pop('encadrant_logged_in', None)
    session.pop('encadrant_id', None)
    session.pop('encadrant_nom', None)
    session.pop('encadrant_prenom', None)
    session.pop('encadrant_matricule', None)
    
    return redirect(url_for('personnel'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    session.pop('admin_nom', None)
    session.pop('admin_matricule', None)
    
    return redirect(url_for('accueil'))

# ===========================================
# ROUTES SUPPLÉMENTAIRES UTILITAIRES
# ===========================================

@app.route('/get-encadrants-by-specialite/<specialite>')
def get_encadrants_by_specialite(specialite):
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT e.*, 
                   COUNT(s.id) as stagiaires_actuels,
                   (e.quota_max - COUNT(s.id)) as places_libres
            FROM encadrant e
            LEFT JOIN stagiaire s ON e.id = s.encadrant_id 
                AND s.statut_avancement IN ('EN_COURS', 'EN_ATTENTE')
            WHERE e.disponible = 1 AND e.actif = 1
                AND (e.specialite LIKE %s OR e.specialite LIKE '%%Généraliste%%')
            GROUP BY e.id
            HAVING places_libres > 0
            ORDER BY 
                CASE WHEN e.specialite LIKE %s THEN 0 ELSE 1 END,
                places_libres DESC
        """, (f'%{specialite}%', f'%{specialite}%'))
        
        encadrants = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'encadrants': encadrants})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/bulk-assign', methods=['POST'])
def bulk_assign():
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        assignments = data.get('assignments', [])
        
        if not assignments:
            return jsonify({'success': False, 'error': 'Aucune assignation fournie'})
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        success_count = 0
        errors = []
        sujet_generique = "À définir par l'encadrant"
        
        for assignment in assignments:
            try:
                matricule = assignment['stagiaire_matricule']
                encadrant_id = assignment['encadrant_id']
                
                cursor.execute("""
                    UPDATE stagiaire 
                    SET encadrant_id = %s, 
                        sujet = %s,
                        statut_avancement = 'EN_ATTENTE'
                    WHERE matricule = %s
                """, (encadrant_id, sujet_generique, matricule))
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Erreur pour {matricule}: {str(e)}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': f'{success_count} assignations réussies. Les encadrants doivent définir les sujets.',
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===========================================
# ROUTES MOBILES SUPPLÉMENTAIRES (si disponibles)
# ===========================================

if MOBILE_ENABLED and mobile_service:
    @app.route('/mobile/stagiaire/<matricule>/demander-attestation', methods=['POST'])
    def mobile_demander_attestation_stagiaire(matricule):
        """Version mobile de la demande d'attestation"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT s.id as stagiaire_id, c.nom, c.prenom, s.statut_avancement
                FROM stagiaire s
                JOIN candidature c ON s.matricule = c.matricule
                WHERE s.matricule = %s
            """
            cursor.execute(query, (matricule,))
            stagiaire = cursor.fetchone()
            
            if not stagiaire:
                return jsonify({
                    'success': False,
                    'message': '❌ Stagiaire introuvable'
                })
            
            cursor.execute("""
                SELECT * FROM attestation 
                WHERE stagiaire_id = %s AND demandee = 1 
                AND date_demande > DATE_SUB(NOW(), INTERVAL 30 DAY)
                ORDER BY date_demande DESC LIMIT 1
            """, (stagiaire['stagiaire_id'],))
            demande_existante = cursor.fetchone()
            
            if demande_existante:
                return jsonify({
                    'success': False,
                    'message': '⏳ Une demande d\'attestation a déjà été faite récemment.'
                })
            
            cursor.execute("""
                INSERT INTO attestation (stagiaire_id, demandee, date_demande) 
                VALUES (%s, 1, NOW())
            """, (stagiaire['stagiaire_id'],))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return jsonify({
                'success': True,
                'message': '✅ Demande d\'attestation envoyée depuis mobile ! 📱'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'❌ Erreur mobile: {str(e)}'
            })

    @app.route('/api/mobile/quick-status/<matricule>')
    def mobile_quick_status(matricule):
        """API rapide pour récupérer le statut sur mobile"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT c.statut, c.date_soumission, c.commentaire,
                       s.statut_avancement, s.date_debut_stage, s.date_fin_stage,
                       s.encadrant_id
                FROM candidature c
                LEFT JOIN stagiaire s ON c.matricule = s.matricule
                WHERE c.matricule = %s
            """
            cursor.execute(query, (matricule,))
            result = cursor.fetchone()
            
            if result:
                progression = 0
                if result['date_debut_stage'] and result['date_fin_stage']:
                    debut = result['date_debut_stage']
                    fin = result['date_fin_stage']
                    aujourd_hui = date.today()
                    
                    if isinstance(debut, datetime):
                        debut = debut.date()
                    if isinstance(fin, datetime):
                        fin = fin.date()
                    
                    if aujourd_hui >= debut:
                        duree_totale = (fin - debut).days
                        jours_ecoules = (aujourd_hui - debut).days
                        if duree_totale > 0:
                            progression = min(100, max(0, int((jours_ecoules / duree_totale) * 100)))
                
                cursor.close()
                connection.close()
                
                return jsonify({
                    'success': True,
                    'status': result['statut'],
                    'status_stage': result['statut_avancement'],
                    'date': result['date_soumission'].isoformat() if result['date_soumission'] else None,
                    'commentaire': result['commentaire'],
                    'progression': progression,
                    'has_encadrant': result['encadrant_id'] is not None,
                    'mobile_optimized': True,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({'success': False, 'error': 'Matricule introuvable'})
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

# ===========================================
# ROUTES API SUPPLÉMENTAIRES
# ===========================================

@app.route('/api/stats')
def get_stats():
    """API pour récupérer les statistiques générales"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Statistiques générales
        cursor.execute("SELECT COUNT(*) as total FROM candidature")
        total_candidatures = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM candidature WHERE statut = 'EN_ATTENTE'")
        en_attente = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM candidature WHERE statut = 'ACCEPTEE'")
        acceptees = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM stagiaire WHERE statut_avancement = 'EN_COURS'")
        stages_actifs = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM evaluation WHERE validee_par_rh = 0")
        evaluations_pending = cursor.fetchone()['total']
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_candidatures': total_candidatures,
                'en_attente': en_attente,
                'acceptees': acceptees,
                'stages_actifs': stages_actifs,
                'evaluations_pending': evaluations_pending
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/search/<term>')
def search_candidatures(term):
    """API de recherche de candidatures"""
    if not session.get('rh_logged_in') and not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT matricule, nom, prenom, email, etablissement, statut, date_soumission
            FROM candidature 
            WHERE matricule LIKE %s 
               OR nom LIKE %s 
               OR prenom LIKE %s 
               OR email LIKE %s
               OR etablissement LIKE %s
            ORDER BY date_soumission DESC
            LIMIT 20
        """
        
        search_term = f"%{term}%"
        cursor.execute(query, (search_term, search_term, search_term, search_term, search_term))
        results = cursor.fetchall()
        
        # Convertir les dates
        for result in results:
            if result['date_soumission']:
                result['date_soumission'] = result['date_soumission'].isoformat()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===========================================
# ROUTES D'EXPORT ET RAPPORTS
# ===========================================

@app.route('/export/candidatures')
def export_candidatures():
    """Exporter les candidatures en CSV"""
    if not session.get('rh_logged_in') and not session.get('admin_logged_in'):
        return redirect(url_for('accueil'))
    
    try:
        import csv
        import io
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT c.matricule, c.nom, c.prenom, c.email, c.etablissement, 
                   c.specialite, c.statut, c.date_soumission,
                   s.statut_avancement, s.date_debut_stage, s.date_fin_stage
            FROM candidature c
            LEFT JOIN stagiaire s ON c.matricule = s.matricule
            ORDER BY c.date_soumission DESC
        """
        cursor.execute(query)
        candidatures = cursor.fetchall()
        
        # Créer le CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow([
            'Matricule', 'Nom', 'Prénom', 'Email', 'Établissement', 
            'Spécialité', 'Statut Candidature', 'Date Soumission',
            'Statut Stage', 'Date Début', 'Date Fin'
        ])
        
        # Données
        for c in candidatures:
            writer.writerow([
                c['matricule'], c['nom'], c['prenom'], c['email'], 
                c['etablissement'], c['specialite'], c['statut'],
                c['date_soumission'].strftime('%d/%m/%Y') if c['date_soumission'] else '',
                c['statut_avancement'] or '',
                c['date_debut_stage'].strftime('%d/%m/%Y') if c['date_debut_stage'] else '',
                c['date_fin_stage'].strftime('%d/%m/%Y') if c['date_fin_stage'] else ''
            ])
        
        cursor.close()
        connection.close()
        
        # Préparer la réponse
        output.seek(0)
        from flask import Response
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=candidatures_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
        
    except Exception as e:
        return redirect(url_for('dashboard_rh'))

# ===========================================
# ROUTES DE MAINTENANCE ET DEBUG
# ===========================================

@app.route('/api/health')
def health_check():
    """Vérification de l'état de l'application"""
    try:
        # Test DB
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        connection.close()
        db_status = True
    except:
        db_status = False
    
    # Test services
    chatbot_status = chatbot_service.check_ollama_connection() if chatbot_service else False
    mobile_status = MOBILE_ENABLED
    cv_analysis_status = CV_ANALYSIS_ENABLED
    
    return jsonify({
        'status': 'healthy' if db_status else 'unhealthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'database': db_status,
            'chatbot': chatbot_status,
            'mobile': mobile_status,
            'cv_analysis': cv_analysis_status
        },
        'version': '1.0.0'
    })

@app.route('/debug/session')
def debug_session():
    """Debug des sessions (en développement seulement)"""
    if app.debug:
        return jsonify({
            'session_data': dict(session),
            'user_agent': request.headers.get('User-Agent'),
            'ip': request.remote_addr,
            'url': request.url
        })
    else:
        return jsonify({'error': 'Debug mode disabled'})

# ===========================================
# ROUTES MANQUANTES POUR ENCADRANTS
# ===========================================

@app.route('/encadrant/mes-evaluations')
def mes_evaluations_encadrant():
    if not session.get('encadrant_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        query = """
            SELECT ev.*, s.matricule, c.nom, c.prenom, c.email, c.etablissement, c.specialite,
                   s.sujet, s.date_debut_stage, s.date_fin_stage,
                   DATEDIFF(CURDATE(), ev.date_evaluation) as jours_depuis_evaluation,
                   CASE 
                       WHEN ev.validee_par_rh = 1 THEN 'Validée par RH'
                       WHEN ev.validee_par_rh = 0 THEN 'En attente de validation RH'
                       ELSE 'Statut inconnu'
                   END as statut_validation
            FROM evaluation ev
            JOIN stagiaire s ON ev.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            WHERE ev.encadrant_id = %s
            ORDER BY ev.date_evaluation DESC
        """
        cursor.execute(query, (encadrant_id,))
        evaluations = cursor.fetchall()
        
        # Calculer les statistiques
        stats = {
            'total': len(evaluations),
            'validees': len([e for e in evaluations if e['validee_par_rh'] == 1]),
            'en_attente': len([e for e in evaluations if e['validee_par_rh'] == 0]),
            'moyenne_notes': round(sum([e['note_globale'] for e in evaluations]) / len(evaluations), 2) if evaluations else 0,
            'recommandations': len([e for e in evaluations if e['recommandation'] == 1])
        }
        
        cursor.close()
        connection.close()
        
        return render_template('mes_evaluations_encadrant.html', 
                             evaluations=evaluations,
                             stats=stats,
                             encadrant_nom=session.get('encadrant_nom'),
                             encadrant_prenom=session.get('encadrant_prenom'))
        
    except Exception as e:
        print(f"Erreur mes évaluations encadrant: {str(e)}")
        return redirect(url_for('dashboard_encadrant'))
@app.route('/encadrant/planning')
def planning_encadrant():
    if not session.get('encadrant_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        query = """
            SELECT s.*, c.nom, c.prenom, c.email, c.etablissement, c.specialite
            FROM stagiaire s
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.encadrant_id = %s AND s.date_debut_stage IS NOT NULL
            ORDER BY s.date_debut_stage ASC
        """
        cursor.execute(query, (encadrant_id,))
        stagiaires = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('planning_encadrant.html', 
                             stagiaires=stagiaires,
                             encadrant_nom=session.get('encadrant_nom'),
                             encadrant_prenom=session.get('encadrant_prenom'))
        
    except Exception as e:
        return redirect(url_for('dashboard_encadrant'))

@app.route('/encadrant/update-evaluation', methods=['POST'])
def update_evaluation():
    if not session.get('encadrant_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        evaluation_id = data.get('evaluation_id')
        note_globale = data.get('note_globale')
        commentaires = data.get('commentaires', '').strip()
        recommandation = data.get('recommandation', False)
        
        # Validations
        if not evaluation_id or note_globale is None:
            return jsonify({'success': False, 'error': 'Données manquantes'})
        
        try:
            note_globale = float(note_globale)
            if note_globale < 0 or note_globale > 20:
                return jsonify({'success': False, 'error': 'La note doit être entre 0 et 20'})
        except ValueError:
            return jsonify({'success': False, 'error': 'Note invalide'})
        
        if not commentaires or len(commentaires) < 10:
            return jsonify({'success': False, 'error': 'Les commentaires sont obligatoires (minimum 10 caractères)'})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        # Vérifier que l'évaluation appartient à cet encadrant
        cursor.execute("""
            SELECT ev.id, s.matricule, c.nom, c.prenom
            FROM evaluation ev
            JOIN stagiaire s ON ev.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            WHERE ev.id = %s AND ev.encadrant_id = %s
        """, (evaluation_id, encadrant_id))
        
        evaluation = cursor.fetchone()
        if not evaluation:
            return jsonify({'success': False, 'error': 'Évaluation non trouvée ou non autorisée'})
        
        # Mettre à jour l'évaluation
        cursor.execute("""
            UPDATE evaluation 
            SET note_globale = %s, commentaires = %s, recommandation = %s, 
                date_evaluation = NOW(), validee_par_rh = 0
            WHERE id = %s
        """, (note_globale, commentaires, recommandation, evaluation_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': f'Évaluation de {evaluation["prenom"]} {evaluation["nom"]} modifiée avec succès'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/encadrant/modifier-evaluation/<int:evaluation_id>')
def modifier_evaluation_encadrant(evaluation_id):
    """Formulaire de modification d'une évaluation existante"""
    if not session.get('encadrant_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        # Récupérer l'évaluation avec les données du stagiaire
        cursor.execute("""
            SELECT s.*, c.nom, c.prenom, c.email, c.etablissement, c.specialite,
                   ev.id as evaluation_id, ev.note_globale, ev.commentaires, 
                   ev.recommandation, ev.validee_par_rh
            FROM evaluation ev
            JOIN stagiaire s ON ev.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            WHERE ev.id = %s AND ev.encadrant_id = %s
        """, (evaluation_id, encadrant_id))
        
        stagiaire = cursor.fetchone()
        
        if not stagiaire:
            return redirect(url_for('mes_evaluations_encadrant'))
        
        # Vérifier si l'évaluation est déjà validée par RH
        if stagiaire['validee_par_rh'] == 1:
            return redirect(url_for('mes_evaluations_encadrant'))
        
        cursor.close()
        connection.close()
        
        return render_template('evaluation_form.html', 
                             stagiaire=stagiaire,
                             encadrant_nom=session.get('encadrant_nom'),
                             encadrant_prenom=session.get('encadrant_prenom'))
        
    except Exception as e:
        print(f"Erreur modification évaluation: {str(e)}")
        return redirect(url_for('mes_evaluations_encadrant'))
# ===========================================
# ROUTES DE CRÉATION DE STAGIAIRE AUTOMATIQUE
# ===========================================

def creer_stagiaire_automatique(matricule):
    """Créer automatiquement un stagiaire quand candidature acceptée"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer candidature
        cursor.execute("SELECT * FROM candidature WHERE matricule = %s", (matricule,))
        candidature = cursor.fetchone()
        
        if not candidature:
            return False
        
        # Vérifier si stagiaire existe déjà
        cursor.execute("SELECT id FROM stagiaire WHERE matricule = %s", (matricule,))
        if cursor.fetchone():
            return True  # Déjà créé
        
        # Créer stagiaire
        insert_query = """
            INSERT INTO stagiaire (
                matricule, candidature_id, date_debut_stage, date_fin_stage,
                statut_avancement, sujet, date_creation
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            matricule,
            candidature['id'],
            candidature['date_debut'],
            candidature['date_fin'],
            'EN_ATTENTE',
            'À définir par l\'encadrant',
            datetime.now()
        ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"✅ Stagiaire créé automatiquement pour {matricule}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur création stagiaire auto: {str(e)}")
        return False

# Hook pour créer stagiaire automatiquement
@app.route('/webhook/candidature-acceptee', methods=['POST'])
def webhook_candidature_acceptee():
    """Webhook appelé quand une candidature est acceptée"""
    try:
        data = request.get_json()
        matricule = data.get('matricule')
        
        if matricule:
            success = creer_stagiaire_automatique(matricule)
            return jsonify({'success': success})
        
        return jsonify({'success': False, 'error': 'Matricule manquant'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
#===========================================
# ===========================================
# ROUTES MOBILES MANQUANTES (à ajouter dans app.py)
# ===========================================

@app.route('/mobile/document/<matricule>/<filename>')
def mobile_view_document(matricule, filename):
    """Visualiser un document en mode mobile"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Vérifier que le document appartient bien à ce matricule
        cursor.execute("""
            SELECT d.chemin_fichier, d.nom, c.matricule
            FROM document d
            JOIN candidature c ON d.candidature_id = c.id
            WHERE c.matricule = %s AND d.chemin_fichier = %s
        """, (matricule, filename))
        
        document = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if not document:
            return "Document introuvable", 404
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=False)
        else:
            return "Fichier introuvable", 404
            
    except Exception as e:
        print(f"Erreur vue document mobile: {str(e)}")
        return "Erreur serveur", 500

@app.route('/mobile/document/<matricule>/<filename>/download')
def mobile_download_document(matricule, filename):
    """Télécharger un document en mode mobile"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Vérifier que le document appartient bien à ce matricule
        cursor.execute("""
            SELECT d.chemin_fichier, d.nom, c.matricule, d.type
            FROM document d
            JOIN candidature c ON d.candidature_id = c.id
            WHERE c.matricule = %s AND d.chemin_fichier = %s
        """, (matricule, filename))
        
        document = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if not document:
            return "Document introuvable", 404
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            # Nom de téléchargement plus lisible
            download_name = f"{document['type']}_{matricule}_{document['nom']}"
            return send_file(file_path, as_attachment=True, download_name=download_name)
        else:
            return "Fichier introuvable", 404
            
    except Exception as e:
        print(f"Erreur téléchargement document mobile: {str(e)}")
        return "Erreur serveur", 500

@app.route('/mobile/suivi/<matricule>/actualiser')
def mobile_actualiser_stagiaire(matricule):
    """Actualiser le statut d'un stagiaire en mode mobile"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT c.statut as statut_candidature, 
                   s.statut_avancement, s.date_debut_stage, s.date_fin_stage,
                   s.encadrant_id,
                   DATEDIFF(CURDATE(), s.date_debut_stage) as jours_ecoules,
                   DATEDIFF(s.date_fin_stage, s.date_debut_stage) as duree_totale,
                   DATEDIFF(CURDATE(), c.date_soumission) as jours_depuis_soumission
            FROM candidature c
            LEFT JOIN stagiaire s ON c.matricule = s.matricule
            WHERE c.matricule = %s
        """
        cursor.execute(query, (matricule,))
        data = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if data:
            progression = 0
            if data['duree_totale'] and data['jours_ecoules'] and data['jours_ecoules'] >= 0:
                progression = min(100, max(0, int((data['jours_ecoules'] / data['duree_totale']) * 100)))
            
            return jsonify({
                'success': True,
                'statut_candidature': data['statut_candidature'],
                'statut_stage': data['statut_avancement'],
                'progression': progression,
                'jours_ecoules': data['jours_ecoules'] or 0,
                'duree_totale': data['duree_totale'] or 0,
                'jours_depuis_soumission': data['jours_depuis_soumission'] or 0,
                'has_encadrant': data['encadrant_id'] is not None,
                'message': 'Données actualisées avec succès',
                'mobile_optimized': True,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Matricule introuvable'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })

@app.route('/api/mobile/stats/<matricule>')
def mobile_get_stats(matricule):
    """Récupérer les statistiques avancées pour mobile"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Statistiques de base
        cursor.execute("""
            SELECT c.*, s.statut_avancement,
                   DATEDIFF(CURDATE(), c.date_soumission) as jours_depuis_soumission,
                   CASE 
                       WHEN c.statut = 'EN_ATTENTE' THEN 'Examen en cours'
                       WHEN c.statut = 'EN_COURS' THEN 'Révision approfondie'
                       WHEN c.statut = 'ACCEPTEE' AND s.statut_avancement IS NULL THEN 'Préparation du stage'
                       WHEN c.statut = 'ACCEPTEE' AND s.statut_avancement = 'EN_ATTENTE' THEN 'Affectation encadrant'
                       WHEN c.statut = 'ACCEPTEE' AND s.statut_avancement = 'EN_COURS' THEN 'Stage en cours'
                       WHEN c.statut = 'ACCEPTEE' AND s.statut_avancement = 'TERMINE' THEN 'Stage terminé'
                       WHEN c.statut = 'REFUSEE' THEN 'Candidature refusée'
                       ELSE 'Statut inconnu'
                   END as etape_actuelle
            FROM candidature c
            LEFT JOIN stagiaire s ON c.matricule = s.matricule
            WHERE c.matricule = %s
        """, (matricule,))
        
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            return jsonify({
                'success': True,
                'stats': {
                    'jours_depuis_soumission': result['jours_depuis_soumission'],
                    'etape_actuelle': result['etape_actuelle'],
                    'statut': result['statut'],
                    'statut_stage': result['statut_avancement']
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Matricule introuvable'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/attestation/<matricule>')
def view_attestation(matricule):
    """Afficher l'attestation PDF dans le navigateur"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer l'attestation la plus récente
        cursor.execute("""
            SELECT a.chemin_fichier, c.nom, c.prenom
            FROM attestation a
            JOIN stagiaire s ON a.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.matricule = %s AND a.generee = 1
            ORDER BY a.date_generation DESC
            LIMIT 1
        """, (matricule,))
        
        attestation = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if not attestation:
            return "❌ Attestation introuvable", 404
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], attestation['chemin_fichier'])
        
        if os.path.exists(file_path):
            print(f"📄 Affichage attestation PDF: {file_path}")
            # Servir le PDF directement dans le navigateur
            return send_file(file_path, 
                           as_attachment=False, 
                           mimetype='application/pdf',
                           download_name=f"Attestation_{attestation['prenom']}_{attestation['nom']}.pdf")
        else:
            print(f"❌ Fichier d'attestation non trouvé: {file_path}")
            return "Fichier d'attestation introuvable", 404
            
    except Exception as e:
        print(f"❌ Erreur vue attestation: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Erreur: {str(e)}", 500
@app.route('/attestation/<matricule>/download')

@app.route('/attestation/<matricule>/download')
def download_attestation(matricule):
    """Télécharger l'attestation PDF"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT a.chemin_fichier, c.nom, c.prenom
            FROM attestation a
            JOIN stagiaire s ON a.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.matricule = %s AND a.generee = 1
            ORDER BY a.date_generation DESC
            LIMIT 1
        """, (matricule,))
        
        attestation = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if attestation and attestation['chemin_fichier']:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], attestation['chemin_fichier'])
            if os.path.exists(file_path):
                print(f"📥 Téléchargement attestation PDF: {file_path}")
                download_name = f"Attestation_Stage_{attestation['prenom']}_{attestation['nom']}.pdf"
                return send_file(file_path, 
                               as_attachment=True, 
                               download_name=download_name,
                               mimetype='application/pdf')
        
        return "Attestation introuvable", 404
        
    except Exception as e:
        print(f"❌ Erreur téléchargement attestation: {str(e)}")
        return f"Erreur: {str(e)}", 500

# Route pour vérifier le statut des attestations
@app.route('/api/attestation-status/<matricule>')
def get_attestation_status(matricule):
    """API pour vérifier si une attestation existe"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT a.generee, a.date_generation, a.chemin_fichier, c.nom, c.prenom
            FROM attestation a
            JOIN stagiaire s ON a.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.matricule = %s
            ORDER BY a.date_generation DESC
            LIMIT 1
        """, (matricule,))
        
        attestation = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if attestation:
            file_exists = False
            if attestation['chemin_fichier']:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], attestation['chemin_fichier'])
                file_exists = os.path.exists(file_path)
            
            return jsonify({
                'success': True,
                'exists': attestation['generee'] == 1,
                'file_exists': file_exists,
                'date_generation': attestation['date_generation'].isoformat() if attestation['date_generation'] else None,
                'filename': attestation['chemin_fichier'],
                'student_name': f"{attestation['prenom']} {attestation['nom']}"
            })
        else:
            return jsonify({
                'success': True,
                'exists': False,
                'file_exists': False
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Debug route pour lister les attestations
@app.route('/debug/attestations')
def debug_attestations():
    """Route de debug pour voir toutes les attestations"""
    if not app.debug:
        return "Mode debug requis", 403
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT a.*, s.matricule, c.nom, c.prenom
            FROM attestation a
            JOIN stagiaire s ON a.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            ORDER BY a.date_generation DESC
        """)
        
        attestations = cursor.fetchall()
        cursor.close()
        connection.close()
        
        result = []
        for att in attestations:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], att['chemin_fichier']) if att['chemin_fichier'] else None
            file_exists = os.path.exists(file_path) if file_path else False
            
            result.append({
                'matricule': att['matricule'],
                'nom': f"{att['prenom']} {att['nom']}",
                'generee': att['generee'],
                'fichier': att['chemin_fichier'],
                'file_exists': file_exists,
                'date_generation': att['date_generation'].isoformat() if att['date_generation'] else None
            })
        
        return jsonify({
            'upload_folder': app.config['UPLOAD_FOLDER'],
            'attestations': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/debug/check-attestation/<matricule>')
def debug_check_attestation(matricule):
    """Debug spécifique pour un matricule"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT a.*, s.matricule, c.nom, c.prenom
            FROM attestation a
            JOIN stagiaire s ON a.stagiaire_id = s.id
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.matricule = %s
        """, (matricule,))
        
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], result['chemin_fichier']) if result['chemin_fichier'] else None
            
            return jsonify({
                'found': True,
                'matricule': result['matricule'],
                'generee': result['generee'],
                'fichier': result['chemin_fichier'],
                'file_path': file_path,
                'file_exists': os.path.exists(file_path) if file_path else False,
                'upload_folder': app.config['UPLOAD_FOLDER'],
                'date_generation': result['date_generation'].isoformat() if result['date_generation'] else None
            })
        else:
            return jsonify({'found': False, 'matricule': matricule})
            
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })
# ==========================================
# ROUTES PARAMÈTRES RH (à ajouter dans app.py)
# ==========================================

@app.route('/rh/parametres')
def rh_parametres():
    """Page des paramètres du compte RH"""
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        rh_id = session.get('rh_id')
        
        # Récupérer les infos complètes du RH
        cursor.execute("""
            SELECT id, nom, prenom, matricule, email, date_creation, actif
            FROM service_rh 
            WHERE id = %s
        """, (rh_id,))
        rh_info = cursor.fetchone()
        
        if not rh_info:
            return redirect(url_for('dashboard_rh'))
        
        # Statistiques d'activité du RH
        cursor.execute("""
            SELECT 
                COUNT(*) as total_candidatures,
                SUM(CASE WHEN statut = 'ACCEPTEE' THEN 1 ELSE 0 END) as acceptees,
                SUM(CASE WHEN statut = 'REFUSEE' THEN 1 ELSE 0 END) as refusees,
                SUM(CASE WHEN DATE(date_soumission) = CURDATE() THEN 1 ELSE 0 END) as aujourd_hui
            FROM candidature
        """)
        stats = cursor.fetchone()
        
        # Compter les attestations générées
        cursor.execute("SELECT COUNT(*) as total FROM attestation WHERE generee = 1")
        attestations_count = cursor.fetchone()['total']
        
        # Vérifier si c'est encore le mot de passe par défaut
        cursor.execute("""
            SELECT mot_de_passe 
            FROM service_rh 
            WHERE id = %s
        """, (rh_id,))
        current_password = cursor.fetchone()['mot_de_passe']
        is_default_password = current_password == 'rh123456'
        
        # Activité récente (simulée pour l'exemple)
        cursor.execute("""
            SELECT matricule, nom, prenom, statut, date_soumission
            FROM candidature 
            ORDER BY date_soumission DESC 
            LIMIT 5
        """)
        recent_activity = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('rh_parametres.html', 
                             rh_info=rh_info,
                             stats=stats,
                             attestations_count=attestations_count,
                             is_default_password=is_default_password,
                             recent_activity=recent_activity,
                             rh_nom=session.get('rh_nom'),
                             rh_prenom=session.get('rh_prenom'))
        
    except Exception as e:
        print(f"Erreur paramètres RH: {str(e)}")
        return redirect(url_for('dashboard_rh'))

@app.route('/rh/update-profile', methods=['POST'])
def rh_update_profile():
    """Mettre à jour le profil RH"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        nom = data.get('nom', '').strip()
        prenom = data.get('prenom', '').strip()
        email = data.get('email', '').strip()
        
        if not all([nom, prenom, email]):
            return jsonify({'success': False, 'error': 'Tous les champs sont obligatoires'})
        
        # Validation email
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'success': False, 'error': 'Format email invalide'})
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        rh_id = session.get('rh_id')
        
        # Vérifier si l'email existe déjà pour un autre utilisateur
        cursor.execute("""
            SELECT id FROM service_rh 
            WHERE email = %s AND id != %s
        """, (email, rh_id))
        
        if cursor.fetchone():
            return jsonify({'success': False, 'error': 'Cette adresse email est déjà utilisée'})
        
        # Mettre à jour les informations
        cursor.execute("""
            UPDATE service_rh 
            SET nom = %s, prenom = %s, email = %s
            WHERE id = %s
        """, (nom, prenom, email, rh_id))
        
        connection.commit()
        
        # Mettre à jour la session
        session['rh_nom'] = nom
        session['rh_prenom'] = prenom
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': 'Profil mis à jour avec succès !',
            'data': {
                'nom': nom,
                'prenom': prenom,
                'email': email
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rh/change-password', methods=['POST'])
def rh_change_password():
    """Changer le mot de passe RH - VERSION CORRIGÉE"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        print("🔐 Début changement mot de passe RH")
        
        data = request.get_json()
        if not data:
            print("❌ Aucune donnée JSON reçue")
            return jsonify({'success': False, 'error': 'Aucune donnée reçue'})
        
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        print(f"📝 Données reçues - Current: {'[SET]' if current_password else '[EMPTY]'}, New: {'[SET]' if new_password else '[EMPTY]'}, Confirm: {'[SET]' if confirm_password else '[EMPTY]'}")
        
        # Validation des champs obligatoires
        if not all([current_password, new_password, confirm_password]):
            print("❌ Champs manquants")
            return jsonify({'success': False, 'error': 'Tous les champs sont obligatoires'})
        
        # Vérification correspondance mots de passe
        if new_password != confirm_password:
            print("❌ Mots de passe ne correspondent pas")
            return jsonify({'success': False, 'error': 'Les nouveaux mots de passe ne correspondent pas'})
        
        # Validation longueur minimum
        if len(new_password) < 8:
            print("❌ Mot de passe trop court")
            return jsonify({'success': False, 'error': 'Le mot de passe doit contenir au moins 8 caractères'})
        
        # Validations de complexité (ASSOUPLIE)
        import re
        
        validations_failed = []
        
        if not re.search(r'[A-Z]', new_password):
            validations_failed.append('une majuscule')
        
        if not re.search(r'[a-z]', new_password):
            validations_failed.append('une minuscule')
        
        if not re.search(r'\d', new_password):
            validations_failed.append('un chiffre')
        
        # Caractères spéciaux ASSOUPLIS (plus de choix)
        if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\\/~`]', new_password):
            validations_failed.append('un caractère spécial (!@#$%^&*(),.?":{}|<>-_+=[]\\\/~`)')
        
        if validations_failed:
            error_msg = f"Le mot de passe doit contenir : {', '.join(validations_failed)}"
            print(f"❌ Validation échouée: {error_msg}")
            return jsonify({'success': False, 'error': error_msg})
        
        print("✅ Validations passées, connexion à la DB")
        
        # Connexion à la base de données
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        rh_id = session.get('rh_id')
        print(f"👤 RH ID: {rh_id}")
        
        # Vérifier le mot de passe actuel
        cursor.execute("""
            SELECT mot_de_passe, nom, prenom 
            FROM service_rh 
            WHERE id = %s
        """, (rh_id,))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            print("❌ Utilisateur introuvable")
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Utilisateur introuvable'})
        
        stored_password = user_data['mot_de_passe']
        user_name = f"{user_data['prenom']} {user_data['nom']}"
        
        print(f"🔍 Mot de passe stocké: {'[DEFAULT]' if stored_password == 'rh123456' else '[CUSTOM]'}")
        print(f"🔍 Mot de passe saisi: {'[MATCHES]' if stored_password == current_password else '[NO MATCH]'}")
        
        if stored_password != current_password:
            print("❌ Mot de passe actuel incorrect")
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Mot de passe actuel incorrect'})
        
        # Vérifier que le nouveau mot de passe est différent
        if new_password == current_password:
            print("❌ Nouveau mot de passe identique à l'ancien")
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Le nouveau mot de passe doit être différent de l\'ancien'})
        
        print("🔄 Mise à jour du mot de passe...")
        
        # Mettre à jour le mot de passe
        cursor.execute("""
            UPDATE service_rh 
            SET mot_de_passe = %s
            WHERE id = %s
        """, (new_password, rh_id))
        
        # Vérifier que la mise à jour a fonctionné
        if cursor.rowcount == 0:
            print("❌ Aucune ligne mise à jour")
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Erreur lors de la mise à jour'})
        
        connection.commit()
        print(f"✅ Mot de passe mis à jour avec succès pour {user_name}")
        
        # Vérification finale
        cursor.execute("SELECT mot_de_passe FROM service_rh WHERE id = %s", (rh_id,))
        verification = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if verification and verification['mot_de_passe'] == new_password:
            print("✅ Vérification finale réussie")
            return jsonify({
                'success': True, 
                'message': f'✅ Mot de passe changé avec succès pour {user_name} ! Votre compte est maintenant sécurisé.'
            })
        else:
            print("❌ Vérification finale échouée")
            return jsonify({'success': False, 'error': 'Erreur de vérification finale'})
        
    except mysql.connector.Error as db_error:
        print(f"❌ Erreur base de données: {str(db_error)}")
        return jsonify({'success': False, 'error': f'Erreur base de données: {str(db_error)}'})
    except Exception as e:
        print(f"❌ Erreur générale: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Erreur interne: {str(e)}'})
    
@app.route('/api/archive-details/<matricule>')
def get_archive_details(matricule):
    """API pour récupérer tous les détails d'un stage archivé"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer toutes les informations détaillées
        query = """
            SELECT s.*, c.nom, c.prenom, c.email, c.etablissement, c.specialite,
                   c.date_debut, c.date_fin, c.date_soumission,
                   e.nom as encadrant_nom, e.prenom as encadrant_prenom,
                   e.email as encadrant_email, e.specialite as encadrant_specialite,
                   ev.id as evaluation_id, ev.note_globale, ev.commentaires, 
                   ev.recommandation, ev.date_evaluation, ev.validee_par_rh,
                   a.generee as attestation_generee, a.date_generation as attestation_date,
                   DATEDIFF(s.date_fin_stage, s.date_debut_stage) as duree_jours
            FROM stagiaire s
            JOIN candidature c ON s.matricule = c.matricule
            LEFT JOIN encadrant e ON s.encadrant_id = e.id
            LEFT JOIN evaluation ev ON s.id = ev.stagiaire_id
            LEFT JOIN attestation a ON s.id = a.stagiaire_id AND a.generee = 1
            WHERE s.matricule = %s AND s.statut_avancement = 'TERMINE'
        """
        cursor.execute(query, (matricule,))
        details = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not details:
            return jsonify({'success': False, 'error': 'Stage archivé introuvable'})
        
        # Formater les dates pour l'affichage
        if details['date_debut_stage']:
            details['date_debut'] = details['date_debut_stage'].strftime('%d/%m/%Y')
        if details['date_fin_stage']:
            details['date_fin'] = details['date_fin_stage'].strftime('%d/%m/%Y')
        if details['date_evaluation']:
            details['date_evaluation'] = details['date_evaluation'].strftime('%d/%m/%Y')
        if details['date_soumission']:
            details['date_soumission'] = details['date_soumission'].strftime('%d/%m/%Y')
        if details['attestation_date']:
            details['attestation_date'] = details['attestation_date'].strftime('%d/%m/%Y')
        
        return jsonify({
            'success': True,
            'details': details
        })
        
    except Exception as e:
        print(f"Erreur détails archive: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rh/logout-all-sessions', methods=['POST'])
def rh_logout_all_sessions():
    """Déconnecter toutes les sessions (simulation)"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        # Ici vous pourriez implémenter une vraie gestion des sessions multiples
        # Pour l'instant, on simule en nettoyant la session actuelle
        
        rh_nom = session.get('rh_nom')
        rh_prenom = session.get('rh_prenom')
        
        # Nettoyer la session
        session.pop('rh_logged_in', None)
        session.pop('rh_id', None)
        session.pop('rh_nom', None)
        session.pop('rh_prenom', None)
        session.pop('rh_matricule', None)
        
        return jsonify({
            'success': True, 
            'message': f'Toutes les sessions de {rh_prenom} {rh_nom} ont été fermées avec succès',
            'redirect': '/personnel'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rh/activity-export', methods=['GET'])
def rh_activity_export():
    """Exporter l'historique d'activité"""
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        import csv
        import io
        from flask import Response
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer l'historique complet
        cursor.execute("""
            SELECT matricule, nom, prenom, email, etablissement, specialite, 
                   statut, date_soumission, commentaire
            FROM candidature 
            ORDER BY date_soumission DESC
        """)
        candidatures = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # Créer le CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow([
            'Date', 'Matricule', 'Nom', 'Prénom', 'Email', 
            'Établissement', 'Spécialité', 'Statut', 'Commentaire'
        ])
        
        # Données
        for c in candidatures:
            writer.writerow([
                c['date_soumission'].strftime('%d/%m/%Y %H:%M') if c['date_soumission'] else '',
                c['matricule'] or '',
                c['nom'] or '',
                c['prenom'] or '',
                c['email'] or '',
                c['etablissement'] or '',
                c['specialite'] or '',
                c['statut'] or '',
                c['commentaire'] or ''
            ])
        
        output.seek(0)
        
        rh_nom = session.get('rh_nom', 'RH')
        filename = f"activite_rh_{rh_nom}_{datetime.now().strftime('%Y%m%d')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        return redirect(url_for('rh_parametres'))
# ==========================================
# ROUTE CANDIDATURES REFUSÉES (à ajouter dans app.py)
# ==========================================

@app.route('/candidatures-refusees')
def candidatures_refusees():
    """Page de gestion des candidatures refusées"""
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer toutes les candidatures refusées avec détails
        query_refusees = """
            SELECT c.*, 
                   DATEDIFF(CURDATE(), c.date_soumission) as jours_depuis_soumission,
                   DATEDIFF(CURDATE(), c.date_commentaire) as jours_depuis_refus
            FROM candidature c
            WHERE c.statut = 'REFUSEE'
            ORDER BY 
                CASE WHEN c.date_commentaire IS NOT NULL THEN c.date_commentaire ELSE c.date_soumission END DESC
        """
        cursor.execute(query_refusees)
        candidatures_refusees = cursor.fetchall()
        
        # Calculer les statistiques
        cursor.execute("SELECT COUNT(*) as total FROM candidature WHERE statut = 'REFUSEE'")
        total_refusees = cursor.fetchone()['total']
        
        # Candidatures refusées ce mois
        cursor.execute("""
            SELECT COUNT(*) as ce_mois FROM candidature 
            WHERE statut = 'REFUSEE' 
            AND (
                (date_commentaire IS NOT NULL AND MONTH(date_commentaire) = MONTH(CURDATE()) AND YEAR(date_commentaire) = YEAR(CURDATE()))
                OR 
                (date_commentaire IS NULL AND MONTH(date_soumission) = MONTH(CURDATE()) AND YEAR(date_soumission) = YEAR(CURDATE()))
            )
        """)
        ce_mois = cursor.fetchone()['ce_mois']
        
        # Candidatures avec commentaire
        cursor.execute("""
            SELECT COUNT(*) as avec_commentaire FROM candidature 
            WHERE statut = 'REFUSEE' AND commentaire IS NOT NULL AND commentaire != ''
        """)
        avec_commentaire = cursor.fetchone()['avec_commentaire']
        
        # Candidatures refusées cette semaine
        cursor.execute("""
            SELECT COUNT(*) as recentes FROM candidature 
            WHERE statut = 'REFUSEE' 
            AND (
                (date_commentaire IS NOT NULL AND date_commentaire >= DATE_SUB(CURDATE(), INTERVAL 7 DAY))
                OR 
                (date_commentaire IS NULL AND date_soumission >= DATE_SUB(CURDATE(), INTERVAL 7 DAY))
            )
        """)
        recentes = cursor.fetchone()['recentes']
        
        # Évaluations en attente (pour la sidebar)
        cursor.execute("SELECT COUNT(*) as count FROM evaluation WHERE validee_par_rh = 0")
        result = cursor.fetchone()
        evaluations_en_attente = result['count'] if result else 0
        
        # Vérifier si c'est encore le mot de passe par défaut
        rh_id = session.get('rh_id')
        cursor.execute("SELECT mot_de_passe FROM service_rh WHERE id = %s", (rh_id,))
        current_password = cursor.fetchone()
        is_default_password = current_password['mot_de_passe'] == 'rh123456' if current_password else False
        
        stats = {
            'total_refusees': total_refusees,
            'ce_mois': ce_mois,
            'avec_commentaire': avec_commentaire,
            'recentes': recentes
        }
        
        cursor.close()
        connection.close()
        
        return render_template('candidatures_refusees.html',
                             candidatures_refusees=candidatures_refusees,
                             stats=stats,
                             evaluations_en_attente=evaluations_en_attente,
                             is_default_password=is_default_password,
                             rh_nom=session.get('rh_nom'),
                             rh_prenom=session.get('rh_prenom'))
        
    except Exception as e:
        print(f"Erreur candidatures refusées: {str(e)}")
        return redirect(url_for('dashboard_rh'))

# ==========================================
# ROUTES SUPPLÉMENTAIRES POUR GESTION DES REFUS
# ==========================================

@app.route('/rh/candidature/<matricule>/add-comment', methods=['POST'])
def add_refus_comment():
    """Ajouter un commentaire à une candidature refusée"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        matricule = data.get('matricule')
        commentaire = data.get('commentaire', '').strip()
        
        if not matricule or not commentaire:
            return jsonify({'success': False, 'error': 'Matricule et commentaire obligatoires'})
        
        if len(commentaire) > 500:
            return jsonify({'success': False, 'error': 'Le commentaire ne peut pas dépasser 500 caractères'})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Vérifier que la candidature existe et est refusée
        cursor.execute("""
            SELECT id, statut, nom, prenom 
            FROM candidature 
            WHERE matricule = %s AND statut = 'REFUSEE'
        """, (matricule,))
        
        candidature = cursor.fetchone()
        if not candidature:
            return jsonify({'success': False, 'error': 'Candidature non trouvée ou non refusée'})
        
        # Mettre à jour le commentaire
        cursor.execute("""
            UPDATE candidature 
            SET commentaire = %s, date_commentaire = NOW() 
            WHERE matricule = %s
        """, (commentaire, matricule))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': f'Commentaire ajouté pour {candidature["prenom"]} {candidature["nom"]}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rh/candidature/<matricule>/reopen', methods=['POST'])
def reopen_candidature():
    """Remettre une candidature refusée en cours d'examen"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Vérifier que la candidature existe et est refusée
        cursor.execute("""
            SELECT id, statut, nom, prenom 
            FROM candidature 
            WHERE matricule = %s AND statut = 'REFUSEE'
        """, (matricule,))
        
        candidature = cursor.fetchone()
        if not candidature:
            return jsonify({'success': False, 'error': 'Candidature non trouvée ou non refusée'})
        
        # Remettre en cours avec commentaire explicatif
        cursor.execute("""
            UPDATE candidature 
            SET statut = 'EN_COURS', 
                commentaire = %s,
                date_commentaire = NOW()
            WHERE matricule = %s
        """, (f'Candidature réexaminée par le service RH le {datetime.now().strftime("%d/%m/%Y à %H:%M")}', matricule))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': f'Candidature de {candidature["prenom"]} {candidature["nom"]} remise en cours d\'examen'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rh/export-candidatures-refusees')
def export_candidatures_refusees():
    """Exporter les candidatures refusées en CSV"""
    if not session.get('rh_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        import csv
        import io
        from flask import Response
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer toutes les candidatures refusées
        query = """
            SELECT matricule, nom, prenom, email, etablissement, specialite, 
                   date_soumission, date_commentaire, commentaire,
                   DATEDIFF(COALESCE(date_commentaire, date_soumission), date_soumission) as delai_traitement
            FROM candidature 
            WHERE statut = 'REFUSEE'
            ORDER BY date_soumission DESC
        """
        cursor.execute(query)
        candidatures = cursor.fetchall()
        
        # Créer le CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow([
            'Matricule', 'Nom', 'Prénom', 'Email', 'Établissement', 
            'Spécialité', 'Date Soumission', 'Date Refus', 'Délai Traitement (jours)',
            'Motif du Refus'
        ])
        
        # Données
        for c in candidatures:
            writer.writerow([
                c['matricule'] or '',
                c['nom'] or '',
                c['prenom'] or '',
                c['email'] or '',
                c['etablissement'] or '',
                c['specialite'] or '',
                c['date_soumission'].strftime('%d/%m/%Y %H:%M') if c['date_soumission'] else '',
                c['date_commentaire'].strftime('%d/%m/%Y %H:%M') if c['date_commentaire'] else 'Non définie',
                c['delai_traitement'] if c['delai_traitement'] is not None else 'N/A',
                c['commentaire'] or 'Aucun commentaire'
            ])
        
        cursor.close()
        connection.close()
        
        output.seek(0)
        
        filename = f"candidatures_refusees_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        return redirect(url_for('candidatures_refusees'))

@app.route('/rh/stats-refus')
def stats_refus():
    """API pour obtenir des statistiques détaillées sur les refus"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Statistiques par mois (6 derniers mois)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(COALESCE(date_commentaire, date_soumission), '%Y-%m') as mois,
                COUNT(*) as nombre_refus
            FROM candidature 
            WHERE statut = 'REFUSEE' 
            AND COALESCE(date_commentaire, date_soumission) >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(COALESCE(date_commentaire, date_soumission), '%Y-%m')
            ORDER BY mois DESC
        """)
        stats_mensuelles = cursor.fetchall()
        
        # Statistiques par établissement
        cursor.execute("""
            SELECT etablissement, COUNT(*) as nombre_refus
            FROM candidature 
            WHERE statut = 'REFUSEE'
            GROUP BY etablissement
            ORDER BY nombre_refus DESC
            LIMIT 10
        """)
        stats_etablissements = cursor.fetchall()
        
        # Statistiques par spécialité
        cursor.execute("""
            SELECT specialite, COUNT(*) as nombre_refus
            FROM candidature 
            WHERE statut = 'REFUSEE'
            GROUP BY specialite
            ORDER BY nombre_refus DESC
            LIMIT 10
        """)
        stats_specialites = cursor.fetchall()
        
        # Délai moyen de traitement
        cursor.execute("""
            SELECT 
                AVG(DATEDIFF(COALESCE(date_commentaire, date_soumission), date_soumission)) as delai_moyen,
                MIN(DATEDIFF(COALESCE(date_commentaire, date_soumission), date_soumission)) as delai_min,
                MAX(DATEDIFF(COALESCE(date_commentaire, date_soumission), date_soumission)) as delai_max
            FROM candidature 
            WHERE statut = 'REFUSEE'
        """)
        stats_delais = cursor.fetchone()
        
        # Pourcentage avec/sans commentaire
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN commentaire IS NOT NULL AND commentaire != '' THEN 1 ELSE 0 END) as avec_commentaire,
                SUM(CASE WHEN commentaire IS NULL OR commentaire = '' THEN 1 ELSE 0 END) as sans_commentaire,
                COUNT(*) as total
            FROM candidature 
            WHERE statut = 'REFUSEE'
        """)
        stats_commentaires = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'mensuelles': stats_mensuelles,
                'etablissements': stats_etablissements,
                'specialites': stats_specialites,
                'delais': {
                    'moyen': round(stats_delais['delai_moyen'], 1) if stats_delais['delai_moyen'] else 0,
                    'min': stats_delais['delai_min'] or 0,
                    'max': stats_delais['delai_max'] or 0
                },
                'commentaires': {
                    'avec': stats_commentaires['avec_commentaire'],
                    'sans': stats_commentaires['sans_commentaire'],
                    'total': stats_commentaires['total'],
                    'pourcentage_avec': round((stats_commentaires['avec_commentaire'] / stats_commentaires['total']) * 100, 1) if stats_commentaires['total'] > 0 else 0
                }
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rh/candidatures-refusees/bulk-action', methods=['POST'])
def bulk_action_refusees():
    """Actions en lot sur les candidatures refusées"""
    if not session.get('rh_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        action = data.get('action')  # 'reopen', 'add_comment', 'archive'
        matricules = data.get('matricules', [])
        commentaire = data.get('commentaire', '').strip()
        
        if not action or not matricules:
            return jsonify({'success': False, 'error': 'Action et matricules requis'})
        
        if len(matricules) > 50:
            return jsonify({'success': False, 'error': 'Maximum 50 candidatures à la fois'})
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        success_count = 0
        errors = []
        
        for matricule in matricules:
            try:
                if action == 'reopen':
                    cursor.execute("""
                        UPDATE candidature 
                        SET statut = 'EN_COURS', 
                            commentaire = %s,
                            date_commentaire = NOW()
                        WHERE matricule = %s AND statut = 'REFUSEE'
                    """, (f'Réexamen en lot le {datetime.now().strftime("%d/%m/%Y")}', matricule))
                    
                elif action == 'add_comment' and commentaire:
                    cursor.execute("""
                        UPDATE candidature 
                        SET commentaire = %s, date_commentaire = NOW() 
                        WHERE matricule = %s AND statut = 'REFUSEE'
                    """, (commentaire, matricule))
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Erreur pour {matricule}: {str(e)}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': f'{success_count} candidatures traitées avec succès',
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
# ==========================================
# ROUTES PROFIL ENCADRANT
# ==========================================

@app.route('/encadrant/profil')
def encadrant_profil():
    """Page du profil de l'encadrant"""
    if not session.get('encadrant_logged_in'):
        return redirect(url_for('personnel'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        # Récupérer les informations complètes de l'encadrant
        cursor.execute("""
            SELECT id, nom, prenom, matricule, email, specialite, 
                   quota_max, disponible, actif, date_creation, mot_de_passe
            FROM encadrant 
            WHERE id = %s
        """, (encadrant_id,))
        
        encadrant = cursor.fetchone()
        
        if not encadrant:
            return redirect(url_for('dashboard_encadrant'))
        
        # Statistiques de l'encadrant
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN statut_avancement = 'EN_COURS' THEN 1 ELSE 0 END) as actifs,
                SUM(CASE WHEN statut_avancement = 'TERMINE' THEN 1 ELSE 0 END) as termines
            FROM stagiaire 
            WHERE encadrant_id = %s
        """, (encadrant_id,))
        
        stats_result = cursor.fetchone()
        
        # Compter les évaluations
        cursor.execute("""
            SELECT COUNT(*) as evaluations
            FROM evaluation 
            WHERE encadrant_id = %s
        """, (encadrant_id,))
        
        eval_result = cursor.fetchone()
        
        stats = {
            'total': stats_result['total'] if stats_result else 0,
            'actifs': stats_result['actifs'] if stats_result else 0,
            'termines': stats_result['termines'] if stats_result else 0,
            'evaluations': eval_result['evaluations'] if eval_result else 0
        }
        
        # Vérifier si c'est encore le mot de passe par défaut
        is_default_password = encadrant['mot_de_passe'] == 'enc123456'
        
        cursor.close()
        connection.close()
        
        return render_template('encadrant_profil.html', 
                             encadrant=encadrant,
                             stats=stats,
                             is_default_password=is_default_password,
                             encadrant_nom=session.get('encadrant_nom'),
                             encadrant_prenom=session.get('encadrant_prenom'))
        
    except Exception as e:
        print(f"Erreur profil encadrant: {str(e)}")
        return redirect(url_for('dashboard_encadrant'))

@app.route('/encadrant/change-password', methods=['POST'])
def encadrant_change_password():
    """Changer le mot de passe de l'encadrant"""
    if not session.get('encadrant_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Aucune donnée reçue'})
        
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        # Validation des champs obligatoires
        if not all([current_password, new_password, confirm_password]):
            return jsonify({'success': False, 'error': 'Tous les champs sont obligatoires'})
        
        # Vérification correspondance mots de passe
        if new_password != confirm_password:
            return jsonify({'success': False, 'error': 'Les nouveaux mots de passe ne correspondent pas'})
        
        # Validation longueur minimum
        if len(new_password) < 8:
            return jsonify({'success': False, 'error': 'Le mot de passe doit contenir au moins 8 caractères'})
        
        # Validations de complexité simplifiées
        import re
        
        validations_failed = []
        
        if not re.search(r'[A-Z]', new_password):
            validations_failed.append('une majuscule')
        
        if not re.search(r'[a-z]', new_password):
            validations_failed.append('une minuscule')
        
        if not re.search(r'\d', new_password):
            validations_failed.append('un chiffre')
        
        if validations_failed:
            error_msg = f"Le mot de passe doit contenir : {', '.join(validations_failed)}"
            return jsonify({'success': False, 'error': error_msg})
        
        # Connexion à la base de données
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        encadrant_id = session.get('encadrant_id')
        
        # Vérifier le mot de passe actuel
        cursor.execute("""
            SELECT mot_de_passe, nom, prenom 
            FROM encadrant 
            WHERE id = %s
        """, (encadrant_id,))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Utilisateur introuvable'})
        
        stored_password = user_data['mot_de_passe']
        user_name = f"{user_data['prenom']} {user_data['nom']}"
        
        if stored_password != current_password:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Mot de passe actuel incorrect'})
        
        # Vérifier que le nouveau mot de passe est différent
        if new_password == current_password:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Le nouveau mot de passe doit être différent de l\'ancien'})
        
        # Mettre à jour le mot de passe
        cursor.execute("""
            UPDATE encadrant 
            SET mot_de_passe = %s
            WHERE id = %s
        """, (new_password, encadrant_id))
        
        # Vérifier que la mise à jour a fonctionné
        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Erreur lors de la mise à jour'})
        
        connection.commit()
        
        # Vérification finale
        cursor.execute("SELECT mot_de_passe FROM encadrant WHERE id = %s", (encadrant_id,))
        verification = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if verification and verification['mot_de_passe'] == new_password:
            return jsonify({
                'success': True, 
                'message': f'Mot de passe changé avec succès pour {user_name} ! Votre compte est maintenant sécurisé.'
            })
        else:
            return jsonify({'success': False, 'error': 'Erreur de vérification finale'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erreur interne: {str(e)}'})

# ===========================================
# ROUTES ADMIN - GESTION AVANCÉE DES UTILISATEURS
# Ajouter ces routes dans app.py
# ===========================================

@app.route('/admin/gerer_rh/<int:rh_id>')
def gerer_rh(rh_id):
    """Page de gestion détaillée d'un personnel RH"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer les infos RH
        cursor.execute("""
            SELECT id, nom, prenom, matricule, email, mot_de_passe, 
                   actif, date_creation
            FROM service_rh 
            WHERE id = %s
        """, (rh_id,))
        rh_info = cursor.fetchone()
        
        if not rh_info:
            return redirect(url_for('dashboard_admin'))
        
        # Statistiques d'activité du RH
        cursor.execute("""
            SELECT 
                COUNT(*) as total_candidatures,
                SUM(CASE WHEN statut = 'ACCEPTEE' THEN 1 ELSE 0 END) as acceptees,
                SUM(CASE WHEN statut = 'REFUSEE' THEN 1 ELSE 0 END) as refusees,
                SUM(CASE WHEN DATE(date_soumission) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as ce_mois
            FROM candidature
        """)
        stats_candidatures = cursor.fetchone()
        
        # Évaluations validées par ce RH
        cursor.execute("""
            SELECT COUNT(*) as evaluations_validees
            FROM evaluation 
            WHERE validee_par_rh = 1
        """)
        evaluations = cursor.fetchone()
        
        # Attestations générées
        cursor.execute("""
            SELECT COUNT(*) as attestations_generees
            FROM attestation 
            WHERE generee = 1
        """)
        attestations = cursor.fetchone()
        
        # Vérifier si mot de passe par défaut
        is_default_password = rh_info['mot_de_passe'] == 'rh123456'
        
        # Dernières connexions (simulées pour cet exemple)
        dernieres_connexions = [
            {'date': '15/08/2025 14:30', 'ip': '192.168.1.100'},
            {'date': '14/08/2025 09:15', 'ip': '192.168.1.100'},
            {'date': '13/08/2025 16:45', 'ip': '192.168.1.102'}
        ]
        
        cursor.close()
        connection.close()
        
        return render_template('admin_gerer_rh.html', 
                         rh_info=rh_info,
                         stats_candidatures=stats_candidatures,
                         evaluations=evaluations,
                         attestations=attestations,
                         is_default_password=is_default_password,
                         dernieres_connexions=dernieres_connexions,
                         admin_nom=session.get('admin_nom'))
        
    except Exception as e:
        print(f"Erreur gestion RH: {str(e)}")
        return redirect(url_for('dashboard_admin'))

@app.route('/admin/gerer_encadrant/<int:encadrant_id>')
def gerer_encadrant(encadrant_id):
    """Page de gestion détaillée d'un encadrant"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer les infos encadrant
        cursor.execute("""
            SELECT id, nom, prenom, matricule, email, specialite, 
                   quota_max, disponible, actif, date_creation, mot_de_passe
            FROM encadrant 
            WHERE id = %s
        """, (encadrant_id,))
        encadrant_info = cursor.fetchone()
        
        if not encadrant_info:
            return redirect(url_for('dashboard_admin'))
        
        # Stagiaires actuels
        cursor.execute("""
            SELECT s.*, c.nom, c.prenom, c.email, c.etablissement
            FROM stagiaire s
            JOIN candidature c ON s.matricule = c.matricule
            WHERE s.encadrant_id = %s AND s.statut_avancement IN ('EN_COURS', 'EN_ATTENTE')
            ORDER BY s.date_debut_stage DESC
        """, (encadrant_id,))
        stagiaires_actuels = cursor.fetchall()
        
        # Statistiques de l'encadrant
        cursor.execute("""
            SELECT 
                COUNT(*) as total_stagiaires,
                SUM(CASE WHEN statut_avancement = 'TERMINE' THEN 1 ELSE 0 END) as termines,
                SUM(CASE WHEN statut_avancement = 'EN_COURS' THEN 1 ELSE 0 END) as en_cours
            FROM stagiaire 
            WHERE encadrant_id = %s
        """, (encadrant_id,))
        stats_stagiaires = cursor.fetchone()
        
        # Évaluations réalisées
        cursor.execute("""
            SELECT 
                COUNT(*) as total_evaluations,
                AVG(note_globale) as note_moyenne,
                SUM(CASE WHEN recommandation = 1 THEN 1 ELSE 0 END) as recommandations
            FROM evaluation 
            WHERE encadrant_id = %s
        """, (encadrant_id,))
        stats_evaluations = cursor.fetchone()
        
        # Vérifier si mot de passe par défaut
        is_default_password = encadrant_info['mot_de_passe'] == 'enc123456'
        
        cursor.close()
        connection.close()
        
        return render_template('admin_gerer_encadrant.html', 
                         encadrant_info=encadrant_info,
                         stagiaires_actuels=stagiaires_actuels,
                         stats_stagiaires=stats_stagiaires,
                         stats_evaluations=stats_evaluations,
                         is_default_password=is_default_password,
                         admin_nom=session.get('admin_nom'))
        
    except Exception as e:
        print(f"Erreur gestion encadrant: {str(e)}")
        return redirect(url_for('dashboard_admin'))

@app.route('/admin/reset_password', methods=['POST'])
def admin_reset_password():
    """Réinitialiser le mot de passe d'un utilisateur"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        user_type = data.get('user_type')  # 'rh' ou 'encadrant'
        user_id = data.get('user_id')
        
        if not user_type or not user_id:
            return jsonify({'success': False, 'error': 'Données manquantes'})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        if user_type == 'rh':
            new_password = 'rh123456'
            cursor.execute("""
                UPDATE service_rh 
                SET mot_de_passe = %s 
                WHERE id = %s
            """, (new_password, user_id))
            
            cursor.execute("SELECT nom, prenom FROM service_rh WHERE id = %s", (user_id,))
            user_info = cursor.fetchone()
            
        elif user_type == 'encadrant':
            new_password = 'enc123456'
            cursor.execute("""
                UPDATE encadrant 
                SET mot_de_passe = %s 
                WHERE id = %s
            """, (new_password, user_id))
            
            cursor.execute("SELECT nom, prenom FROM encadrant WHERE id = %s", (user_id,))
            user_info = cursor.fetchone()
        
        else:
            return jsonify({'success': False, 'error': 'Type utilisateur invalide'})
        
        connection.commit()
        cursor.close()
        connection.close()
        
        if user_info:
            return jsonify({
                'success': True, 
                'message': f'Mot de passe réinitialisé pour {user_info["prenom"]} {user_info["nom"]}',
                'new_password': new_password
            })
        else:
            return jsonify({'success': False, 'error': 'Utilisateur introuvable'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
# ===========================================
# ROUTE UTILITAIRE - VÉRIFIER STATUT UTILISATEUR
# ===========================================

@app.route('/admin/check_user_status/<user_type>/<int:user_id>')
def check_user_status(user_type, user_id):
    """Vérifier le statut actuel d'un utilisateur"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        if user_type == 'rh':
            cursor.execute("""
                SELECT id, nom, prenom, actif, 
                       (SELECT COUNT(*) FROM service_rh WHERE actif = 1) as total_rh_actifs
                FROM service_rh 
                WHERE id = %s
            """, (user_id,))
        elif user_type == 'encadrant':
            cursor.execute("""
                SELECT e.id, e.nom, e.prenom, e.actif, e.disponible,
                       COUNT(s.id) as stagiaires_actifs
                FROM encadrant e
                LEFT JOIN stagiaire s ON e.id = s.encadrant_id 
                    AND s.statut_avancement IN ('EN_COURS', 'EN_ATTENTE')
                WHERE e.id = %s
                GROUP BY e.id
            """, (user_id,))
        else:
            return jsonify({'success': False, 'error': 'Type utilisateur invalide'})
        
        user_info = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if user_info:
            can_be_disabled = True
            reason = ""
            
            if user_type == 'rh' and user_info['actif'] and user_info['total_rh_actifs'] <= 1:
                can_be_disabled = False
                reason = "Dernier RH actif du système"
            elif user_type == 'encadrant' and user_info.get('stagiaires_actifs', 0) > 0:
                can_be_disabled = False
                reason = f"{user_info['stagiaires_actifs']} stagiaire(s) actif(s)"
            
            return jsonify({
                'success': True,
                'user_info': user_info,
                'can_be_disabled': can_be_disabled,
                'reason': reason
            })
        else:
            return jsonify({'success': False, 'error': 'Utilisateur introuvable'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===========================================
# ROUTE BATCH - ACTIVER/DÉSACTIVER EN LOT
# ===========================================

@app.route('/admin/bulk_toggle_status', methods=['POST'])
def admin_bulk_toggle_status():
    """Activer/Désactiver plusieurs utilisateurs en lot"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        user_type = data.get('user_type')  # 'rh' ou 'encadrant'
        user_ids = data.get('user_ids', [])  # Liste d'IDs
        new_status = data.get('status')  # True/False
        
        if not user_type or not user_ids or new_status is None:
            return jsonify({'success': False, 'error': 'Données manquantes'})
        
        if len(user_ids) > 50:
            return jsonify({'success': False, 'error': 'Maximum 50 utilisateurs à la fois'})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        success_count = 0
        errors = []
        
        for user_id in user_ids:
            try:
                if user_type == 'rh':
                    # Vérifications spécifiques RH
                    if not new_status:  # Désactiver
                        cursor.execute("SELECT COUNT(*) as count FROM service_rh WHERE actif = 1 AND id != %s", (user_id,))
                        autres_rh = cursor.fetchone()['count']
                        if autres_rh == 0:
                            errors.append(f"RH ID {user_id}: Dernier RH actif")
                            continue
                    
                    cursor.execute("UPDATE service_rh SET actif = %s WHERE id = %s", (new_status, user_id))
                    
                elif user_type == 'encadrant':
                    # Vérifications spécifiques Encadrant
                    if not new_status:  # Désactiver
                        cursor.execute("""
                            SELECT COUNT(*) as count FROM stagiaire 
                            WHERE encadrant_id = %s AND statut_avancement IN ('EN_COURS', 'EN_ATTENTE')
                        """, (user_id,))
                        stagiaires = cursor.fetchone()['count']
                        if stagiaires > 0:
                            errors.append(f"Encadrant ID {user_id}: {stagiaires} stagiaire(s) actif(s)")
                            continue
                    
                    cursor.execute("UPDATE encadrant SET actif = %s, disponible = %s WHERE id = %s", 
                                 (new_status, new_status, user_id))
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"ID {user_id}: {str(e)}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        status_text = "activés" if new_status else "désactivés"
        message = f'✅ {success_count} utilisateur(s) {status_text} avec succès'
        
        return jsonify({
            'success': True,
            'message': message,
            'success_count': success_count,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/admin/update_quota', methods=['POST'])
def admin_update_quota():
    """Modifier le quota d'un encadrant"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        encadrant_id = data.get('encadrant_id')
        nouveau_quota = data.get('quota')
        
        if not encadrant_id or not nouveau_quota:
            return jsonify({'success': False, 'error': 'Données manquantes'})
        
        nouveau_quota = int(nouveau_quota)
        if nouveau_quota < 1 or nouveau_quota > 20:
            return jsonify({'success': False, 'error': 'Le quota doit être entre 1 et 20'})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            UPDATE encadrant 
            SET quota_max = %s 
            WHERE id = %s
        """, (nouveau_quota, encadrant_id))
        
        cursor.execute("SELECT nom, prenom FROM encadrant WHERE id = %s", (encadrant_id,))
        user_info = cursor.fetchone()
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': f'Quota de {user_info["prenom"]} {user_info["nom"]} mis à jour: {nouveau_quota} stagiaires'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/delete_user', methods=['POST'])
def admin_delete_user():
    """Supprimer un utilisateur (avec vérifications)"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        user_type = data.get('user_type')
        user_id = data.get('user_id')
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        if user_type == 'rh':
            # Vérifier s'il y a d'autres RH actifs
            cursor.execute("SELECT COUNT(*) as count FROM service_rh WHERE actif = 1 AND id != %s", (user_id,))
            autres_rh = cursor.fetchone()['count']
            
            if autres_rh == 0:
                return jsonify({'success': False, 'error': 'Impossible de supprimer le dernier RH actif'})
            
            cursor.execute("SELECT nom, prenom FROM service_rh WHERE id = %s", (user_id,))
            user_info = cursor.fetchone()
            
            cursor.execute("DELETE FROM service_rh WHERE id = %s", (user_id,))
            
        elif user_type == 'encadrant':
            # Vérifier s'il a des stagiaires actifs
            cursor.execute("""
                SELECT COUNT(*) as count FROM stagiaire 
                WHERE encadrant_id = %s AND statut_avancement IN ('EN_COURS', 'EN_ATTENTE')
            """, (user_id,))
            stagiaires_actifs = cursor.fetchone()['count']
            
            if stagiaires_actifs > 0:
                return jsonify({'success': False, 'error': f'Impossible de supprimer: {stagiaires_actifs} stagiaire(s) actif(s)'})
            
            cursor.execute("SELECT nom, prenom FROM encadrant WHERE id = %s", (user_id,))
            user_info = cursor.fetchone()
            
            cursor.execute("DELETE FROM encadrant WHERE id = %s", (user_id,))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True, 
            'message': f'{user_info["prenom"]} {user_info["nom"]} a été supprimé avec succès'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===========================================
# ROUTES ADMIN - MODIFICATION ENCADRANT (À ajouter dans app.py)
# ===========================================

@app.route('/admin/modifier_encadrant_form/<int:encadrant_id>')
def modifier_encadrant_form(encadrant_id):
    """Formulaire de modification d'un encadrant"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM encadrant WHERE id = %s", (encadrant_id,))
        edit_encadrant = cursor.fetchone()
        
        if not edit_encadrant:
            return redirect(url_for('dashboard_admin'))
        
        cursor.close()
        connection.close()
        
        return render_template('admin_modifier.html', 
                             edit_encadrant=edit_encadrant,
                             admin_nom=session.get('admin_nom'))
        
    except Exception as e:
        print(f"Erreur formulaire modification encadrant: {str(e)}")
        return redirect(url_for('dashboard_admin'))

@app.route('/admin/modifier_encadrant', methods=['POST'])
def modifier_encadrant():
    """Traiter la modification d'un encadrant"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        encadrant_id = request.form.get('id')
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        email = request.form.get('email')
        specialite = request.form.get('specialite')
        quota_max = request.form.get('quota_max')
        password = request.form.get('password')
        
        if not all([encadrant_id, nom, prenom, email, specialite, quota_max]):
            return redirect(url_for('modifier_encadrant_form', encadrant_id=encadrant_id))
        
        # Validation du quota
        try:
            quota_max = int(quota_max)
            if quota_max < 1 or quota_max > 20:
                return redirect(url_for('modifier_encadrant_form', encadrant_id=encadrant_id))
        except ValueError:
            return redirect(url_for('modifier_encadrant_form', encadrant_id=encadrant_id))
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Vérifier si l'email existe déjà pour un autre encadrant
        cursor.execute("""
            SELECT id FROM encadrant 
            WHERE email = %s AND id != %s
        """, (email, encadrant_id))
        
        if cursor.fetchone():
            cursor.close()
            connection.close()
            return redirect(url_for('modifier_encadrant_form', encadrant_id=encadrant_id))
        
        if password and password.strip():
            # Mise à jour avec nouveau mot de passe
            query = """
                UPDATE encadrant 
                SET nom = %s, prenom = %s, email = %s, specialite = %s, 
                    quota_max = %s, mot_de_passe = %s
                WHERE id = %s
            """
            cursor.execute(query, (nom, prenom, email, specialite, quota_max, password.strip(), encadrant_id))
        else:
            # Mise à jour sans changer le mot de passe
            query = """
                UPDATE encadrant 
                SET nom = %s, prenom = %s, email = %s, specialite = %s, quota_max = %s
                WHERE id = %s
            """
            cursor.execute(query, (nom, prenom, email, specialite, quota_max, encadrant_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return redirect(url_for('dashboard_admin'))
        
    except mysql.connector.Error as e:
        print(f"Erreur DB modification encadrant: {str(e)}")
        return redirect(url_for('modifier_encadrant_form', encadrant_id=encadrant_id))
    except Exception as e:
        print(f"Erreur modification encadrant: {str(e)}")
        return redirect(url_for('modifier_encadrant_form', encadrant_id=encadrant_id))

@app.route('/admin/supprimer_encadrant/<int:encadrant_id>', methods=['POST'])
def supprimer_encadrant(encadrant_id):
    """Supprimer un encadrant"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Vérifier s'il a des stagiaires actifs
        cursor.execute("""
            SELECT COUNT(*) as stagiaires_actifs
            FROM stagiaire 
            WHERE encadrant_id = %s AND statut_avancement IN ('EN_COURS', 'EN_ATTENTE')
        """, (encadrant_id,))
        
        result = cursor.fetchone()
        if result['stagiaires_actifs'] > 0:
            print(f"Impossible de supprimer: {result['stagiaires_actifs']} stagiaires actifs")
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard_admin'))
        
        # Récupérer les infos pour le log
        cursor.execute("SELECT nom, prenom FROM encadrant WHERE id = %s", (encadrant_id,))
        encadrant_info = cursor.fetchone()
        
        if not encadrant_info:
            cursor.close()
            connection.close()
            return redirect(url_for('dashboard_admin'))
        
        # Supprimer l'encadrant
        cursor.execute("DELETE FROM encadrant WHERE id = %s", (encadrant_id,))
        connection.commit()
        
        print(f"✅ Encadrant supprimé: {encadrant_info['prenom']} {encadrant_info['nom']}")
        
        cursor.close()
        connection.close()
        
        return redirect(url_for('dashboard_admin'))
        
    except mysql.connector.Error as e:
        print(f"❌ Erreur DB suppression encadrant: {str(e)}")
        return redirect(url_for('dashboard_admin'))
    except Exception as e:
        print(f"❌ Erreur suppression encadrant: {str(e)}")
        return redirect(url_for('dashboard_admin'))


# ===========================================
# ROUTES FLASK COMPLÈTES POUR LE PROFIL ADMINISTRATEUR
# Version mise à jour avec gestion de la date de modification du mot de passe
# À ajouter dans votre app.py
# ===========================================

@app.route('/admin/profil')
def admin_profil():
    """Page de profil de l'administrateur - VERSION COMPLÈTE"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        admin_id = session.get('admin_id')
        
        # Récupérer les informations de l'administrateur avec date de modification du mot de passe
        cursor.execute("""
            SELECT id, matricule, nom, email, date_modif_mdp
            FROM admin 
            WHERE id = %s
        """, (admin_id,))
        admin_info = cursor.fetchone()
        
        if not admin_info:
            print(f"❌ Admin introuvable avec ID: {admin_id}")
            return redirect(url_for('admin_login'))
        
        print(f"✅ Admin trouvé: {admin_info}")
        
        # Calculer des statistiques pour le tableau de bord
        try:
            cursor.execute("SELECT COUNT(*) as total FROM candidature")
            total_candidatures = cursor.fetchone()['total']
        except:
            total_candidatures = 0
        
        try:
            cursor.execute("SELECT COUNT(*) as total FROM service_rh")
            total_rh = cursor.fetchone()['total']
        except:
            total_rh = 0
        
        try:
            cursor.execute("SELECT COUNT(*) as total FROM encadrant")
            total_encadrants = cursor.fetchone()['total']
        except:
            total_encadrants = 0
        
        cursor.close()
        connection.close()
        
        stats = {
            'total_candidatures': total_candidatures,
            'total_rh': total_rh,
            'total_encadrants': total_encadrants
        }
        
        print(f"📊 Statistiques: {stats}")
        print(f"🔑 Date modification mot de passe: {admin_info.get('date_modif_mdp')}")
        
        return render_template('admin_profil.html', 
                             admin_info=admin_info,
                             stats=stats,
                             admin_nom=session.get('admin_nom'))
        
    except Exception as e:
        print(f"❌ Erreur profil admin: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('dashboard_admin'))

@app.route('/admin/update-profile', methods=['POST'])
def admin_update_profile():
    """Mettre à jour le profil administrateur - VERSION COMPLÈTE"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        data = request.get_json()
        nom = data.get('nom', '').strip()
        email = data.get('email', '').strip()
        
        print(f"🔄 Mise à jour profil admin: nom={nom}, email={email}")
        
        if not nom or not email:
            return jsonify({'success': False, 'error': 'Tous les champs sont obligatoires'})
        
        # Validation email
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'success': False, 'error': 'Format email invalide'})
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        admin_id = session.get('admin_id')
        
        # Vérifier si l'email existe déjà pour un autre administrateur
        cursor.execute("""
            SELECT id FROM admin 
            WHERE email = %s AND id != %s
        """, (email, admin_id))
        
        if cursor.fetchone():
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Cette adresse email est déjà utilisée'})
        
        # Mettre à jour les informations
        cursor.execute("""
            UPDATE admin 
            SET nom = %s, email = %s
            WHERE id = %s
        """, (nom, email, admin_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Aucune modification effectuée'})
        
        connection.commit()
        
        # Mettre à jour la session
        session['admin_nom'] = nom
        
        cursor.close()
        connection.close()
        
        print(f"✅ Profil admin mis à jour avec succès")
        
        return jsonify({
            'success': True, 
            'message': 'Profil mis à jour avec succès !',
            'data': {
                'nom': nom,
                'email': email
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur mise à jour profil admin: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/change-password', methods=['POST'])
def admin_change_password():
    """Changer le mot de passe administrateur avec mise à jour de la date - VERSION COMPLÈTE"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        print("🔑 Début changement mot de passe admin")
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Aucune donnée reçue'})
        
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        print(f"🔍 Données reçues - Current: {'[SET]' if current_password else '[EMPTY]'}, New: {'[SET]' if new_password else '[EMPTY]'}")
        
        # Validation des champs obligatoires
        if not all([current_password, new_password, confirm_password]):
            return jsonify({'success': False, 'error': 'Tous les champs sont obligatoires'})
        
        # Vérification correspondance mots de passe
        if new_password != confirm_password:
            return jsonify({'success': False, 'error': 'Les nouveaux mots de passe ne correspondent pas'})
        
        # Validation longueur minimum
        if len(new_password) < 8:
            return jsonify({'success': False, 'error': 'Le mot de passe doit contenir au moins 8 caractères'})
        
        # Validations de complexité
        import re
        
        validations_failed = []
        
        if not re.search(r'[A-Z]', new_password):
            validations_failed.append('une majuscule')
        
        if not re.search(r'[a-z]', new_password):
            validations_failed.append('une minuscule')
        
        if not re.search(r'\d', new_password):
            validations_failed.append('un chiffre')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\\/~`]', new_password):
            validations_failed.append('un caractère spécial')
        
        if validations_failed:
            error_msg = f"Le mot de passe doit contenir : {', '.join(validations_failed)}"
            return jsonify({'success': False, 'error': error_msg})
        
        print("✅ Validations passées")
        
        # Connexion à la base de données
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        admin_id = session.get('admin_id')
        
        # Vérifier le mot de passe actuel
        cursor.execute("""
            SELECT mot_de_passe, nom 
            FROM admin 
            WHERE id = %s
        """, (admin_id,))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Utilisateur introuvable'})
        
        stored_password = user_data['mot_de_passe']
        user_name = user_data['nom']
        
        print(f"🔐 Vérification mot de passe pour: {user_name}")
        
        if stored_password != current_password:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Mot de passe actuel incorrect'})
        
        # Vérifier que le nouveau mot de passe est différent
        if new_password == current_password:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Le nouveau mot de passe doit être différent de l\'ancien'})
        
        print("🔄 Mise à jour du mot de passe avec date...")
        
        # Mettre à jour le mot de passe ET la date de modification
        cursor.execute("""
            UPDATE admin 
            SET mot_de_passe = %s, date_modif_mdp = NOW()
            WHERE id = %s
        """, (new_password, admin_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': 'Erreur lors de la mise à jour'})
        
        connection.commit()
        
        # Vérification finale
        cursor.execute("""
            SELECT mot_de_passe, date_modif_mdp 
            FROM admin 
            WHERE id = %s
        """, (admin_id,))
        verification = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if verification and verification['mot_de_passe'] == new_password:
            print(f"✅ Mot de passe changé avec succès pour {user_name}")
            print(f"📅 Date de modification mise à jour: {verification['date_modif_mdp']}")
            return jsonify({
                'success': True, 
                'message': f'Mot de passe changé avec succès pour {user_name} ! Votre compte est maintenant sécurisé.',
                'date_modif': verification['date_modif_mdp'].isoformat() if verification['date_modif_mdp'] else None
            })
        else:
            return jsonify({'success': False, 'error': 'Erreur de vérification finale'})
        
    except Exception as e:
        print(f"❌ Erreur changement mot de passe admin: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Erreur interne: {str(e)}'})

@app.route('/admin/logout-all-sessions', methods=['POST'])
def admin_logout_all_sessions():
    """Déconnecter toutes les sessions administrateur"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        admin_nom = session.get('admin_nom', 'Administrateur')
        
        print(f"🚪 Déconnexion de toutes les sessions pour: {admin_nom}")
        
        # Nettoyer la session
        session.pop('admin_logged_in', None)
        session.pop('admin_id', None)
        session.pop('admin_nom', None)
        session.pop('admin_matricule', None)
        
        return jsonify({
            'success': True, 
            'message': f'Toutes les sessions de {admin_nom} ont été fermées avec succès',
            'redirect': '/admin'
        })
        
    except Exception as e:
        print(f"❌ Erreur déconnexion sessions admin: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# ==========================================
# ROUTES ADMINISTRATEUR - STATISTIQUES COMPLÈTES
# À ajouter dans app.py
# ==========================================

@app.route('/admin/statistiques')
def admin_statistiques():
    """Page de statistiques complètes pour l'administrateur"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # ============================================
        # STATISTIQUES DES CANDIDATURES
        # ============================================
        
        # Répartition par statut
        cursor.execute("""
            SELECT 
                statut,
                COUNT(*) as nombre,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM candidature), 1) as pourcentage
            FROM candidature 
            GROUP BY statut
            ORDER BY nombre DESC
        """)
        stats_candidatures = cursor.fetchall()
        
        # Évolution mensuelle des candidatures (12 derniers mois)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(date_soumission, '%Y-%m') as mois,
                COUNT(*) as total,
                SUM(CASE WHEN statut = 'ACCEPTEE' THEN 1 ELSE 0 END) as acceptees,
                SUM(CASE WHEN statut = 'REFUSEE' THEN 1 ELSE 0 END) as refusees
            FROM candidature 
            WHERE date_soumission >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(date_soumission, '%Y-%m')
            ORDER BY mois ASC
        """)
        evolution_candidatures = cursor.fetchall()
        
        # Top établissements
        cursor.execute("""
            SELECT 
                etablissement,
                COUNT(*) as nombre_candidatures,
                SUM(CASE WHEN statut = 'ACCEPTEE' THEN 1 ELSE 0 END) as acceptees,
                ROUND(SUM(CASE WHEN statut = 'ACCEPTEE' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as taux_acceptation
            FROM candidature 
            GROUP BY etablissement
            HAVING COUNT(*) >= 3
            ORDER BY nombre_candidatures DESC
            LIMIT 10
        """)
        top_etablissements = cursor.fetchall()
        
        # Top spécialités
        cursor.execute("""
            SELECT 
                specialite,
                COUNT(*) as nombre_candidatures,
                SUM(CASE WHEN statut = 'ACCEPTEE' THEN 1 ELSE 0 END) as acceptees
            FROM candidature 
            GROUP BY specialite
            ORDER BY nombre_candidatures DESC
            LIMIT 10
        """)
        top_specialites = cursor.fetchall()
        
        # ============================================
        # STATISTIQUES DES STAGIAIRES
        # ============================================
        
        # Répartition par statut de stage
        cursor.execute("""
            SELECT 
                statut_avancement,
                COUNT(*) as nombre,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM stagiaire), 1) as pourcentage
            FROM stagiaire 
            GROUP BY statut_avancement
        """)
        stats_stagiaires = cursor.fetchall()
        
        # Durée moyenne des stages terminés
        cursor.execute("""
            SELECT 
                AVG(DATEDIFF(date_fin_stage, date_debut_stage)) as duree_moyenne,
                MIN(DATEDIFF(date_fin_stage, date_debut_stage)) as duree_min,
                MAX(DATEDIFF(date_fin_stage, date_debut_stage)) as duree_max,
                COUNT(*) as total_termines
            FROM stagiaire 
            WHERE statut_avancement = 'TERMINE' 
            AND date_debut_stage IS NOT NULL 
            AND date_fin_stage IS NOT NULL
        """)
        duree_stages = cursor.fetchone()
        
        # ============================================
        # STATISTIQUES DES ÉVALUATIONS
        # ============================================
        
        # Répartition des notes
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN note_globale >= 16 THEN 'Très Bien (16-20)'
                    WHEN note_globale >= 14 THEN 'Bien (14-16)'
                    WHEN note_globale >= 12 THEN 'Assez Bien (12-14)'
                    WHEN note_globale >= 10 THEN 'Passable (10-12)'
                    ELSE 'Insuffisant (<10)'
                END as mention,
                COUNT(*) as nombre,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM evaluation WHERE note_globale IS NOT NULL), 1) as pourcentage
            FROM evaluation 
            WHERE note_globale IS NOT NULL
            GROUP BY 
                CASE 
                    WHEN note_globale >= 16 THEN 'Très Bien (16-20)'
                    WHEN note_globale >= 14 THEN 'Bien (14-16)'
                    WHEN note_globale >= 12 THEN 'Assez Bien (12-14)'
                    WHEN note_globale >= 10 THEN 'Passable (10-12)'
                    ELSE 'Insuffisant (<10)'
                END
            ORDER BY MIN(note_globale) DESC
        """)
        repartition_notes = cursor.fetchall()
        
        # Statistiques générales des évaluations
        cursor.execute("""
            SELECT 
                COUNT(*) as total_evaluations,
                SUM(CASE WHEN validee_par_rh = 1 THEN 1 ELSE 0 END) as validees,
                SUM(CASE WHEN validee_par_rh = 0 THEN 1 ELSE 0 END) as en_attente,
                AVG(note_globale) as note_moyenne,
                SUM(CASE WHEN recommandation = 1 THEN 1 ELSE 0 END) as recommandations
            FROM evaluation
        """)
        stats_evaluations = cursor.fetchone()
        
        # Top encadrants par nombre d'évaluations
        cursor.execute("""
            SELECT 
                e.nom, e.prenom, e.specialite,
                COUNT(ev.id) as nombre_evaluations,
                AVG(ev.note_globale) as note_moyenne,
                SUM(CASE WHEN ev.recommandation = 1 THEN 1 ELSE 0 END) as recommandations
            FROM encadrant e
            JOIN evaluation ev ON e.id = ev.encadrant_id
            GROUP BY e.id
            ORDER BY nombre_evaluations DESC
            LIMIT 10
        """)
        top_encadrants = cursor.fetchall()
        
        # ============================================
        # STATISTIQUES DES ATTESTATIONS
        # ============================================
        
        # Statistiques générales des attestations
        cursor.execute("""
            SELECT 
                COUNT(*) as total_demandes,
                SUM(CASE WHEN generee = 1 THEN 1 ELSE 0 END) as generees,
                SUM(CASE WHEN generee = 0 OR generee IS NULL THEN 1 ELSE 0 END) as en_attente,
                ROUND(SUM(CASE WHEN generee = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as taux_generation
            FROM attestation
        """)
        stats_attestations = cursor.fetchone()
        
        # Évolution mensuelle des attestations générées
        cursor.execute("""
            SELECT 
                DATE_FORMAT(date_generation, '%Y-%m') as mois,
                COUNT(*) as nombre
            FROM attestation 
            WHERE generee = 1 
            AND date_generation >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(date_generation, '%Y-%m')
            ORDER BY mois ASC
        """)
        evolution_attestations = cursor.fetchall()
        
        # ============================================
        # STATISTIQUES DES UTILISATEURS
        # ============================================
        
        # Personnel RH
        cursor.execute("""
            SELECT 
                COUNT(*) as total_rh,
                SUM(CASE WHEN actif = 1 THEN 1 ELSE 0 END) as actifs,
                SUM(CASE WHEN actif = 0 THEN 1 ELSE 0 END) as inactifs
            FROM service_rh
        """)
        stats_rh = cursor.fetchone()
        
        # Encadrants
        cursor.execute("""
            SELECT 
                COUNT(*) as total_encadrants,
                SUM(CASE WHEN disponible = 1 THEN 1 ELSE 0 END) as disponibles,
                SUM(CASE WHEN actif = 1 THEN 1 ELSE 0 END) as actifs,
                AVG(quota_max) as quota_moyen
            FROM encadrant
        """)
        stats_encadrants = cursor.fetchone()
        
        # Charge de travail des encadrants
        cursor.execute("""
            SELECT 
                e.nom, e.prenom, e.quota_max,
                COUNT(s.id) as stagiaires_actuels,
                ROUND(COUNT(s.id) * 100.0 / e.quota_max, 1) as taux_occupation
            FROM encadrant e
            LEFT JOIN stagiaire s ON e.id = s.encadrant_id 
                AND s.statut_avancement IN ('EN_COURS', 'EN_ATTENTE')
            WHERE e.actif = 1
            GROUP BY e.id
            ORDER BY taux_occupation DESC
        """)
        charge_encadrants = cursor.fetchall()
        
        # ============================================
        # STATISTIQUES GÉNÉRALES ET KPI
        # ============================================
        
        # Total général
        cursor.execute("SELECT COUNT(*) as total FROM candidature")
        total_candidatures = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM stagiaire")
        total_stagiaires = cursor.fetchone()['total']
        
        # Délai moyen de traitement des candidatures
        cursor.execute("""
            SELECT 
                AVG(DATEDIFF(
                    CASE 
                        WHEN date_commentaire IS NOT NULL THEN date_commentaire
                        ELSE CURDATE()
                    END, 
                    date_soumission
                )) as delai_moyen_traitement
            FROM candidature 
            WHERE statut IN ('ACCEPTEE', 'REFUSEE')
        """)
        delai_traitement = cursor.fetchone()
        
        # Taux de conversion global
        taux_conversion = 0
        if total_candidatures > 0:
            cursor.execute("SELECT COUNT(*) as acceptees FROM candidature WHERE statut = 'ACCEPTEE'")
            acceptees = cursor.fetchone()['acceptees']
            taux_conversion = round((acceptees / total_candidatures) * 100, 1)
        
        cursor.close()
        connection.close()
        
        # Préparer toutes les données pour le template
        data = {
            'stats_candidatures': stats_candidatures,
            'evolution_candidatures': evolution_candidatures,
            'top_etablissements': top_etablissements,
            'top_specialites': top_specialites,
            'stats_stagiaires': stats_stagiaires,
            'duree_stages': duree_stages,
            'repartition_notes': repartition_notes,
            'stats_evaluations': stats_evaluations,
            'top_encadrants': top_encadrants,
            'stats_attestations': stats_attestations,
            'evolution_attestations': evolution_attestations,
            'stats_rh': stats_rh,
            'stats_encadrants': stats_encadrants,
            'charge_encadrants': charge_encadrants,
            'total_candidatures': total_candidatures,
            'total_stagiaires': total_stagiaires,
            'delai_traitement': delai_traitement,
            'taux_conversion': taux_conversion
        }
        
        return render_template('admin_statistiques.html', 
                             **data,
                             admin_nom=session.get('admin_nom'))
        
    except Exception as e:
        print(f"Erreur statistiques admin: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('dashboard_admin'))

@app.route('/api/admin/export-stats', methods=['GET'])
def admin_export_stats():
    """Exporter toutes les statistiques en CSV"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        import csv
        import io
        from flask import Response
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer toutes les données
        cursor.execute("""
            SELECT 
                c.matricule, c.nom, c.prenom, c.email, c.etablissement, c.specialite,
                c.statut, c.date_soumission, c.date_commentaire,
                s.date_debut_stage, s.date_fin_stage, s.statut_avancement,
                e.nom as encadrant_nom, e.prenom as encadrant_prenom,
                ev.note_globale, ev.recommandation,
                a.generee as attestation_generee
            FROM candidature c
            LEFT JOIN stagiaire s ON c.matricule = s.matricule
            LEFT JOIN encadrant e ON s.encadrant_id = e.id
            LEFT JOIN evaluation ev ON s.id = ev.stagiaire_id
            LEFT JOIN attestation a ON s.id = a.stagiaire_id AND a.generee = 1
            ORDER BY c.date_soumission DESC
        """)
        
        data = cursor.fetchall()
        cursor.close()
        connection.close()
        
        # Créer le CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow([
            'Matricule', 'Nom', 'Prénom', 'Email', 'Établissement', 'Spécialité',
            'Statut Candidature', 'Date Soumission', 'Date Traitement',
            'Date Début Stage', 'Date Fin Stage', 'Statut Stage',
            'Encadrant', 'Note Évaluation', 'Recommandé', 'Attestation Générée'
        ])
        
        # Données
        for row in data:
            writer.writerow([
                row['matricule'] or '',
                row['nom'] or '',
                row['prenom'] or '',
                row['email'] or '',
                row['etablissement'] or '',
                row['specialite'] or '',
                row['statut'] or '',
                row['date_soumission'].strftime('%d/%m/%Y') if row['date_soumission'] else '',
                row['date_commentaire'].strftime('%d/%m/%Y') if row['date_commentaire'] else '',
                row['date_debut_stage'].strftime('%d/%m/%Y') if row['date_debut_stage'] else '',
                row['date_fin_stage'].strftime('%d/%m/%Y') if row['date_fin_stage'] else '',
                row['statut_avancement'] or '',
                f"{row['encadrant_prenom']} {row['encadrant_nom']}" if row['encadrant_nom'] else '',
                f"{row['note_globale']}/20" if row['note_globale'] else '',
                'Oui' if row['recommandation'] else 'Non' if row['recommandation'] is not None else '',
                'Oui' if row['attestation_generee'] else 'Non'
            ])
        
        output.seek(0)
        
        filename = f"statistiques_completes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/stats-realtime')
def admin_stats_realtime():
    """API pour récupérer les statistiques en temps réel - VERSION CORRIGÉE"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Non autorisé'})
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        print("🔍 Début récupération stats temps réel")
        
        # Statistiques du jour - REQUÊTE CORRIGÉE
        cursor.execute("""
            SELECT 
                COUNT(*) as candidatures_jour,
                SUM(CASE WHEN statut = 'ACCEPTEE' THEN 1 ELSE 0 END) as acceptees_jour,
                SUM(CASE WHEN statut = 'REFUSEE' THEN 1 ELSE 0 END) as refusees_jour
            FROM candidature 
            WHERE DATE(date_soumission) = CURDATE()
        """)
        stats_jour = cursor.fetchone()
        
        print(f"📊 Stats jour récupérées: {stats_jour}")
        
        # Si pas de résultat, initialiser à 0
        if not stats_jour:
            stats_jour = {
                'candidatures_jour': 0,
                'acceptees_jour': 0,
                'refusees_jour': 0
            }
        
        # Évaluations en attente
        cursor.execute("""
            SELECT COUNT(*) as evaluations_attente
            FROM evaluation 
            WHERE validee_par_rh = 0
        """)
        eval_result = cursor.fetchone()
        evaluations_attente = eval_result['evaluations_attente'] if eval_result else 0
        
        # Attestations en attente
        cursor.execute("""
            SELECT COUNT(*) as attestations_attente
            FROM attestation 
            WHERE demandee = 1 AND (generee = 0 OR generee IS NULL)
        """)
        att_result = cursor.fetchone()
        attestations_attente = att_result['attestations_attente'] if att_result else 0
        
        cursor.close()
        connection.close()
        
        result = {
            'success': True,
            'stats': {
                'candidatures_jour': stats_jour['candidatures_jour'] or 0,
                'acceptees_jour': stats_jour['acceptees_jour'] or 0,
                'refusees_jour': stats_jour['refusees_jour'] or 0,
                'evaluations_attente': evaluations_attente,
                'attestations_attente': attestations_attente,
                'last_update': datetime.now().isoformat()
            }
        }
        
        print(f"✅ Résultat final: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur stats temps réel: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Retourner des valeurs par défaut en cas d'erreur
        return jsonify({
            'success': True,
            'stats': {
                'candidatures_jour': 0,
                'acceptees_jour': 0,
                'refusees_jour': 0,
                'evaluations_attente': 0,
                'attestations_attente': 0,
                'last_update': datetime.now().isoformat()
            }
        })
# ===========================================
# POINT D'ENTRÉE PRINCIPAL
# ===========================================

if __name__ == '__main__':
    print("🚀 Application Gestion Stagiaires")
    print("=" * 50)
    
    base_url = get_public_url()
    
    print(f"✅ Application disponible sur:")
    print(f"   🖥️  Desktop: {base_url}")
    print(f"   📱 Mobile: {base_url}/mobile/suivi/[MATRICULE]")
    print(f"   📋 Admin: {base_url}/admin")
    print(f"   👥 Personnel: {base_url}/personnel")
    print()
    print("🔧 Les emails utiliseront cette URL de base")
    print("🌐 Accessible depuis votre réseau local")
    
    # Afficher les services disponibles
    print("\n📦 Services disponibles:")
    print(f"   🤖 Chatbot: ✅")
    print(f"   📱 Mobile: {'✅' if MOBILE_ENABLED else '❌'}")
    
    print("=" * 50)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )