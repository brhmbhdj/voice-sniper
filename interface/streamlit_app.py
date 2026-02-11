"""
Interface utilisateur Streamlit pour Voice Sniper.
Permet de générer des cold calls vocaux personnalisés via une interface web simple.
Ce fichier ne contient AUCUNE logique métier, uniquement de la présentation.
"""

import os
import sys
from datetime import datetime

# Ajout du répertoire parent au PYTHONPATH pour permettre les imports
# Nécessaire car Streamlit exécute ce fichier depuis le dossier interface/
chemin_racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if chemin_racine not in sys.path:
    sys.path.insert(0, chemin_racine)

import streamlit as st

# ============================================
# PROTECTION PAR MOT DE PASSE (optionnel)
# Définir PASSWORD_APP dans les secrets Streamlit
# ============================================
def verifier_acces():
    """Vérifie le mot de passe si configuré."""
    config = obtenir_configuration()
    password_attendu = getattr(config, 'password_app', None) or os.getenv('PASSWORD_APP')
    
    if not password_attendu:
        return True  # Pas de mot de passe = accès libre
    
    if "password_verifie" not in st.session_state:
        st.session_state.password_verifie = False
    
    if not st.session_state.password_verifie:
        st.text_input("Mot de passe", type="password", key="password_input")
        if st.button("Accéder"):
            if st.session_state.password_input == password_attendu:
                st.session_state.password_verifie = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect")
        st.stop()
    
    return True

# Import des adapters infrastructure
from infrastructure.config import obtenir_configuration
from infrastructure.api.notion_client import NotionClient
from infrastructure.api.hunter_client import HunterClient
from infrastructure.api.gemini_client import GeminiClient
from infrastructure.api.kimi_client import KimiClient
from infrastructure.api.gradium_client import GradiumClient

# Import du cas d'utilisation
from application.generate_voice_outbound import GenerateVoiceOutbound

# Import des modèles du domaine
from domain.models import Language


def initialiser_session():
    """Initialise les variables de session Streamlit."""
    if "historique_generations" not in st.session_state:
        st.session_state.historique_generations = []
    if "dernier_resultat" not in st.session_state:
        st.session_state.dernier_resultat = None


def afficher_entete():
    """Affiche l'en-tête de l'application avec branding utilisateur."""
    import os
    from datetime import datetime
    config = obtenir_configuration()
    
    # Logo et branding Gradium
    col_logo, col_texte = st.columns([1, 5])
    
    with col_logo:
        # Essayer de charger le logo, sinon fallback sur emoji
        logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=80)
        else:
            st.markdown("<div style='font-size: 60px; text-align: center;'>🎙️</div>", unsafe_allow_html=True)
    
    with col_texte:
        st.title("🎯 Voice Sniper")
        st.caption(f"Propulsé par **{config.utilisateur_entreprise}** | Développé par **{config.utilisateur_nom}**")
    
    st.subheader("Générateur de Cold Calls Vocaux Ultra-Personnalisés")
    
    # Timestamp pour identifier la version déployée
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    st.caption(f"🕐 Version déployée : {timestamp}")
    
    st.markdown("---")


def afficher_formulaire_prospect():
    """
    Affiche le formulaire de saisie des informations du prospect.
    
    Returns:
        Tuple contenant les valeurs saisies
    """
    st.header("📋 Informations du Prospect")
    
    colonne_gauche, colonne_droite = st.columns(2)
    
    with colonne_gauche:
        nom_prospect = st.text_input(
            label="Nom complet du prospect *",
            placeholder="Ex: Jean Dupont",
            help="Prénom et nom du prospect que vous souhaitez contacter"
        )
    
    with colonne_droite:
        nom_entreprise = st.text_input(
            label="Entreprise *",
            placeholder="Ex: Acme Corporation",
            help="Nom de l'entreprise du prospect"
        )
    
    return nom_prospect, nom_entreprise


def afficher_formulaire_trigger():
    """
    Affiche le formulaire de saisie du trigger.
    
    Returns:
        Tuple contenant les valeurs saisies
    """
    st.header("⚡ Trigger (Événement Déclencheur)")
    
    # Liste des types de triggers courants
    types_trigger = [
        "Levée de fonds",
        "Recrutement massif",
        "Expansion internationale",
        "Nouveau produit",
        "Fusion / Acquisition",
        "Changement de direction",
        "Partenariat stratégique",
        "Autre"
    ]
    
    type_trigger = st.selectbox(
        label="Type de trigger *",
        options=types_trigger,
        help="Sélectionnez l'événement qui justifie votre approche"
    )
    
    description_trigger = st.text_area(
        label="Description du trigger *",
        placeholder="Ex: L'entreprise a levé 10M€ en série B pour développer son marché européen...",
        help="Décrivez en détail le trigger pour personnaliser le script",
        height=100
    )
    
    return type_trigger, description_trigger


def afficher_options_generation():
    """
    Affiche les options avancées de génération.
    
    Returns:
        Tuple contenant les options sélectionnées
    """
    with st.expander("⚙️ Options avancées"):
        colonne_langue, colonne_ton, colonne_vitesse = st.columns(3)
        
        with colonne_langue:
            langues_disponibles = {
                "🤖 Automatique (détection IA)": Language.AUTO,
                "Français": Language.FRENCH,
                "Anglais": Language.ENGLISH,
                "Espagnol": Language.SPANISH,
                "Allemand": Language.GERMAN,
                "Italien": Language.ITALIAN
            }
            langue_selectionnee = st.selectbox(
                label="Langue",
                options=list(langues_disponibles.keys()),
                index=0,
                help="Laissez 'Automatique' pour que l'IA détecte la meilleure langue selon le prospect"
            )
            langue = langues_disponibles[langue_selectionnee]
        
        with colonne_ton:
            ton_script = st.selectbox(
                label="Ton du script",
                options=["professionnel", "décontracté", "formel", "énergique"],
                index=0
            )
        
        with colonne_vitesse:
            vitesse_lecture = st.slider(
                label="Vitesse",
                min_value=0.8,
                max_value=1.3,
                value=1.0,
                step=0.1,
                help="1.0 = vitesse normale. Gradium gère la vitesse nativement."
            )
        
        # 🎙️ CHOIX DU GENRE (la voix sera sélectionnée automatiquement selon la langue détectée)
        st.info("🎙️ **Le personnage** sera choisi automatiquement selon la langue du prospect")
        
        genre_voix = st.radio(
            label="Genre de la voix",
            options=["Femme", "Homme"],
            index=0,
            horizontal=True
        )
    
    return langue, ton_script, genre_voix, vitesse_lecture


def verifier_configuration() -> bool:
    """
    Vérifie que la configuration minimale est présente.
    
    Returns:
        True si la configuration est valide, False sinon
    """
    config = obtenir_configuration()
    
    erreurs = []
    
    # Vérification de la config LLM
    provider = config.llm_provider.lower()
    if provider == "kimi":
        if not config.kimi_cle_api:
            erreurs.append("❌ Clé API Kimi manquante (KIMI_CLE_API)")
    elif provider == "mock":
        # Mode mock - pas besoin de clé API
        pass
    else:  # gemini par défaut
        if not config.gemini_est_configure:
            erreurs.append("❌ Clé API Gemini manquante")
    
    if not config.gradium_est_configure:
        erreurs.append("❌ URL API Gradium manquante")
    if not config.notion_est_configure:
        erreurs.append("⚠️ Configuration Notion incomplète (optionnel)")
    if not config.hunter_est_configure:
        erreurs.append("⚠️ Clé API Hunter manquante (optionnel)")
    
    if erreurs:
        with st.sidebar:
            st.header("🔧 Configuration")
            for erreur in erreurs:
                if erreur.startswith("❌"):
                    st.error(erreur)
                else:
                    st.warning(erreur)
        
        # Vérification des erreurs bloquantes
        erreurs_bloquantes = [e for e in erreurs if e.startswith("❌")]
        if erreurs_bloquantes:
            st.error("Certaines configurations obligatoires sont manquantes. Veuillez configurer votre fichier .env")
            return False
    
    return True


def executer_generation(
    nom_prospect: str,
    nom_entreprise: str,
    type_trigger: str,
    description_trigger: str,
    langue: Language,
    ton_script: str,
    genre_voix: str,
    vitesse_lecture: float
):
    """
    Exécute le cas d'utilisation de génération de cold call.
    
    Args:
        nom_prospect: Nom du prospect
        nom_entreprise: Nom de l'entreprise
        type_trigger: Type de trigger
        description_trigger: Description du trigger
        langue: Langue sélectionnée
        ton_script: Ton du script
        genre_voix: Genre de la voix (Femme/Homme)
        vitesse_lecture: Vitesse de lecture
    """
    try:
        with st.spinner("🔄 Génération en cours..."):
            # Configuration
            config = obtenir_configuration()
            
            # Création des adaptateurs infrastructure
            notion_client = NotionClient()
            hunter_client = HunterClient()
            
            # Affichage de la config pour debug
            st.info(f"🤖 Provider: {config.llm_provider} | Modèle Gemini: {config.gemini_modele}")
            
            # Vérification si on est sur le modèle par défaut (peut indiquer un problème de secrets)
            if config.gemini_modele == "gemini-2.5-flash":
                st.success("✅ Configuration OK - Modèle gemini-2.5-flash")
            else:
                st.warning(f"⚠️ Modèle utilisé: {config.gemini_modele} (vérifiez les secrets Streamlit)")
            
            # Choix du provider LLM selon la configuration
            provider = config.llm_provider.lower()
            if provider == "kimi":
                print(f"🧠 Utilisation de Kimi ({config.kimi_modele})")
                llm_client = KimiClient()
            elif provider == "mock":
                print(f"🎭 Mode MOCK activé - Pas d'appel API")
                from infrastructure.api.mock_client import MockLLMClient
                llm_client = MockLLMClient()
            else:
                print(f"🧠 Utilisation de Gemini ({config.gemini_modele})")
                llm_client = GeminiClient()
            
            gradium_client = GradiumClient()
            
            # Création du cas d'utilisation avec injection de dépendances
            use_case = GenerateVoiceOutbound(
                fournisseur_notion=notion_client,
                fournisseur_hunter=hunter_client,
                fournisseur_llm=llm_client,
                fournisseur_voix=gradium_client
            )
            
            # Exécution du cas d'utilisation
            resultat = use_case.executer(
                nom_prospect=nom_prospect,
                nom_entreprise=nom_entreprise,
                type_trigger=type_trigger,
                description_trigger=description_trigger,
                langue=langue,
                ton_script=ton_script,
                genre_voix=genre_voix,
                vitesse_lecture=vitesse_lecture
            )
            
            # Stockage dans la session
            st.session_state.dernier_resultat = resultat
            st.session_state.historique_generations.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "prospect": nom_prospect,
                "entreprise": nom_entreprise,
                "trigger": type_trigger
            })
            
            # Message de succès enrichi
            message_succes = "✅ Cold call généré avec succès !"
            
            # Ajout info langue détectée
            if resultat.get("langue_detectee_auto"):
                langue_map = {"fr": "Français", "en": "Anglais", "es": "Espagnol", 
                             "de": "Allemand", "it": "Italien"}
                langue_nom = langue_map.get(resultat["langue"], resultat["langue"])
                message_succes += f"\n\n🌍 Langue détectée automatiquement : **{langue_nom}**"
            
            # Info sur les notes utilisées
            if resultat["prospect"].notes_enrichies and resultat["prospect"].notes_enrichies.notes_brutes:
                nb_caracteres = len(resultat["prospect"].notes_enrichies.notes_brutes)
                message_succes += f"\n\n📝 {nb_caracteres} caractères de contexte utilisés depuis Notion"
            
            st.success(message_succes)
            
    except Exception as erreur:
        st.error(f"❌ Erreur lors de la génération : {str(erreur)}")


def afficher_resultat():
    """Affiche le résultat de la dernière génération."""
    if st.session_state.dernier_resultat is None:
        return
    
    resultat = st.session_state.dernier_resultat
    script = resultat["script"]
    audio = resultat["audio"]
    
    st.markdown("---")
    st.header("📝 Script Généré")
    
    # Affichage du script
    with st.container():
        # Si c'est le nouveau format (tout dans corps_message)
        if not script.introduction and not script.proposition_valeur and script.corps_message:
            st.markdown("### 🎭 Script complet")
            st.markdown("---")
            st.markdown(script.corps_message)
            st.markdown("---")
        else:
            # Ancien format avec sections
            st.subheader("👋 Introduction")
            st.info(script.introduction)
            
            st.subheader("💬 Corps du message")
            st.write(script.corps_message)
            
            st.subheader("✨ Proposition de valeur")
            st.success(script.proposition_valeur)
            
            if script.objection_handling:
                st.subheader("🛡️ Gestion d'objection")
                for objection in script.objection_handling:
                    st.warning(objection)
            
            st.subheader("🎯 Call-to-action")
            st.write(script.call_to_action)
    
    # Affichage de l'audio
    st.markdown("---")
    st.header("🔊 Audio Généré")
    
    # 🎙️ INFO VOIX UTILISÉE
    voix_utilisee = resultat.get("voix_id", "Inconnue")
    st.info(f"🎙️ Voix utilisée: **{voix_utilisee}**")
    
    # Sauvegarde temporaire du fichier audio pour lecture
    format_fichier = audio.format_fichier.lower()
    nom_fichier = f"cold_call_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_fichier}"
    chemin_temp = f"/tmp/{nom_fichier}"
    
    try:
        with open(chemin_temp, "wb") as fichier:
            fichier.write(audio.contenu_audio)
        
        # Lecture de l'audio (WAV ou MP3)
        mime_type = "audio/wav" if format_fichier == "wav" else f"audio/{format_fichier}"
        with open(chemin_temp, "rb") as fichier:
            st.audio(fichier, format=mime_type)
        
        # Bouton de téléchargement
        st.download_button(
            label=f"📥 Télécharger l'audio ({format_fichier.upper()})",
            data=audio.contenu_audio,
            file_name=nom_fichier,
            mime=mime_type
        )
        
        # Bouton d'envoi par email si l'email est disponible (et non vide)
        if resultat["prospect"].email and resultat["prospect"].email.strip():
            st.markdown("---")
            with st.form("envoi_email"):
                st.subheader("📧 Envoyer par email")
                email_destinataire = st.text_input("Email du destinataire", value=resultat["prospect"].email)
                sujet = st.text_input("Sujet", value=f"Voice Sniper - Cold Call {resultat['prospect'].nom_complet}")
                message = st.text_area("Message", value=f"Bonjour,\n\nVeuillez trouver ci-joint le cold call personnalisé pour {resultat['prospect'].nom_complet}.\n\nCordialement,")
                
                if st.form_submit_button("📤 Envoyer l'email"):
                    # Simulation d'envoi (à remplacer par vraie fonctionnalité)
                    st.info(f"📧 Email prêt à être envoyé à : {email_destinataire}")
                    st.warning("⚠️ Fonctionnalité d'envoi à configurer avec votre service d'email (SendGrid, AWS SES, etc.)")
        
    except Exception as erreur:
        st.error(f"Erreur lors de la lecture audio : {str(erreur)}")
    
    # Affichage des notes utilisées (SECTION IMPORTANTE)
    st.markdown("---")
    st.header("📋 Notes Notion Utilisées")
    
    if resultat["prospect"].notes_enrichies and resultat["prospect"].notes_enrichies.notes_brutes:
        notes = resultat["prospect"].notes_enrichies
        
        # Afficher les notes complètes dans un conteneur scrollable
        with st.container():
            st.markdown("<div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; max-height: 400px; overflow-y: auto;'>", unsafe_allow_html=True)
            st.markdown(notes.notes_brutes[:2000] + "..." if len(notes.notes_brutes) > 2000 else notes.notes_brutes)
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.success(f"✅ {len(notes.notes_brutes)} caractères de contexte utilisés pour personnaliser le script")
    else:
        st.warning("⚠️ Aucune note Notion trouvée pour ce prospect - Le script n'est pas personnalisé")
    
    # Informations complémentaires
    with st.expander("ℹ️ Détails techniques"):
        details = {
            "prospect": {
                "nom": resultat["prospect"].nom_complet,
                "entreprise": resultat["prospect"].entreprise,
                "titre": resultat["prospect"].titre,
                "email": resultat["prospect"].email
            },
            "trigger": {
                "type": resultat["trigger"].type_trigger,
                "description": resultat["trigger"].description
            },
            "audio": {
                "format": audio.format_fichier,
                "duree_secondes": audio.duree_secondes,
                "langue": audio.langue.value
            },
            "timestamp": resultat["timestamp"],
            "langue_detectee_auto": resultat.get("langue_detectee_auto", False)
        }
        
        if resultat["prospect"].notes_enrichies:
            details["prospect"]["notes_extraites"] = {
                "situation": bool(resultat["prospect"].notes_enrichies.situation_actuelle),
                "pain_points_count": len(resultat["prospect"].notes_enrichies.pain_points),
                "value_prop": bool(resultat["prospect"].notes_enrichies.value_proposition)
            }
        
        st.json(details)


def afficher_historique():
    """Affiche l'historique des générations."""
    if st.session_state.historique_generations:
        with st.sidebar:
            st.header("📜 Historique")
            for generation in reversed(st.session_state.historique_generations[-10:]):
                st.write(f"**{generation['timestamp']}**")
                st.write(f"{generation['prospect']} - {generation['entreprise']}")
                st.write(f"Trigger: {generation['trigger']}")
                st.markdown("---")


def main():
    """
    Fonction principale de l'application Streamlit.
    Point d'entrée de l'interface utilisateur.
    """
    # Configuration de la page
    st.set_page_config(
        page_title="Voice Sniper",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Vérification du mot de passe (si configuré)
    verifier_acces()
    
    # Initialisation
    initialiser_session()
    
    # En-tête
    afficher_entete()
    
    # Vérification de la configuration
    if not verifier_configuration():
        st.info("💡 Créez un fichier `.env` basé sur `.env.example` avec vos clés API")
        return
    
    # Formulaire principal
    nom_prospect, nom_entreprise = afficher_formulaire_prospect()
    type_trigger, description_trigger = afficher_formulaire_trigger()
    langue, ton_script, genre_voix, vitesse_lecture = afficher_options_generation()
    
    # Bouton de génération
    st.markdown("---")
    
    formulaire_valide = bool(nom_prospect and nom_entreprise and description_trigger)
    
    if st.button(
        label="🚀 Générer le Cold Call",
        type="primary",
        disabled=not formulaire_valide,
        use_container_width=True
    ):
        executer_generation(
            nom_prospect=nom_prospect,
            nom_entreprise=nom_entreprise,
            type_trigger=type_trigger,
            description_trigger=description_trigger,
            langue=langue,
            ton_script=ton_script,
            genre_voix=genre_voix,
            vitesse_lecture=vitesse_lecture
        )
    
    if not formulaire_valide:
        st.warning("⚠️ Veuillez remplir tous les champs obligatoires (*)")
    
    # Affichage du résultat
    afficher_resultat()
    
    # Historique dans la sidebar
    afficher_historique()
    
    # Pied de page avec branding
    st.markdown("---")
    config = obtenir_configuration()
    st.caption(f"🎙️ **Voice Sniper** © {config.annee} | Développé avec ❤️ par **{config.utilisateur_nom}** @ **{config.utilisateur_entreprise}** | Architecture Hexagonale")


if __name__ == "__main__":
    main()
