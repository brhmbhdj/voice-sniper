"""
Point d'entrée principal de l'application Voice Sniper.
Permet de lancer l'application en ligne de commande ou via Streamlit.
"""

import argparse
import sys


def executer_mode_interactif():
    """
    Exécute le mode interactif en ligne de commande.
    Permet de tester rapidement sans lancer l'interface web.
    """
    print("=" * 60)
    print("🎯 Voice Sniper - Mode Interactif")
    print("=" * 60)
    
    # Import des dépendances
    from infrastructure.config import obtenir_configuration
    from infrastructure.api.notion_client import NotionClient
    from infrastructure.api.hunter_client import HunterClient
    from infrastructure.api.gemini_client import GeminiClient
    from infrastructure.api.gradium_client import GradiumClient
    from application.generate_voice_outbound import GenerateVoiceOutbound
    from domain.models import Language
    
    # Vérification de la configuration
    config = obtenir_configuration()
    
    print("\n📋 Vérification de la configuration...")
    if not config.gemini_est_configure:
        print("❌ Clé API Gemini manquante")
        return
    if not config.gradium_est_configure:
        print("❌ URL API Gradium manquante")
        return
    
    print("✅ Configuration OK\n")
    
    # Saisie des informations
    print("-" * 60)
    nom_prospect = input("Nom du prospect : ").strip()
    nom_entreprise = input("Entreprise : ").strip()
    type_trigger = input("Type de trigger : ").strip()
    description_trigger = input("Description du trigger : ").strip()
    
    # Choix de la langue
    print("\nLangue du script :")
    print("1. 🤖 Automatique (détection IA)")
    print("2. Français")
    print("3. Anglais")
    print("4. Espagnol")
    print("5. Allemand")
    choix_langue = input("Choix (1-5, défaut: 1) : ").strip() or "1"
    
    langues = {
        "1": Language.AUTO,
        "2": Language.FRENCH,
        "3": Language.ENGLISH,
        "4": Language.SPANISH,
        "5": Language.GERMAN
    }
    langue = langues.get(choix_langue, Language.AUTO)
    
    if not all([nom_prospect, nom_entreprise, description_trigger]):
        print("❌ Tous les champs sont obligatoires")
        return
    
    print("\n🔄 Génération en cours...\n")
    
    try:
        # Création des adaptateurs
        notion_client = NotionClient()
        hunter_client = HunterClient()
        gemini_client = GeminiClient()
        gradium_client = GradiumClient()
        
        # Création du cas d'utilisation
        use_case = GenerateVoiceOutbound(
            fournisseur_notion=notion_client,
            fournisseur_hunter=hunter_client,
            fournisseur_llm=gemini_client,
            fournisseur_voix=gradium_client
        )
        
        # Exécution
        resultat = use_case.executer(
            nom_prospect=nom_prospect,
            nom_entreprise=nom_entreprise,
            type_trigger=type_trigger,
            description_trigger=description_trigger,
            langue=langue
        )
        
        # Affichage du résultat
        print("=" * 60)
        print("✅ Génération réussie !")
        print("=" * 60)
        print(f"\n👤 Prospect : {resultat['prospect'].nom_complet}")
        print(f"🏢 Entreprise : {resultat['prospect'].entreprise}")
        
        # Affichage de la langue
        langue_map = {"fr": "Français", "en": "Anglais", "es": "Espagnol", 
                     "de": "Allemand", "it": "Italien"}
        langue_nom = langue_map.get(resultat["langue"], resultat["langue"])
        if resultat.get("langue_detectee_auto"):
            print(f"🌍 Langue détectée automatiquement : {langue_nom}")
        else:
            print(f"🌍 Langue : {langue_nom}")
        
        print(f"\n📝 Script généré :\n")
        
        script = resultat['script']
        print(f"👋 Introduction : {script.introduction}")
        print(f"\n💬 Corps : {script.corps_message}")
        print(f"\n✨ Proposition : {script.proposition_valeur}")
        print(f"\n🎯 CTA : {script.call_to_action}")
        
        print(f"\n🔊 Audio : {resultat['audio'].duree_secondes} secondes")
        print(f"💾 Sauvegardé : {resultat['audio'].chemin_fichier or 'Non sauvegardé'}")
        
    except Exception as erreur:
        print(f"❌ Erreur : {str(erreur)}")


def executer_mode_streamlit():
    """
    Lance l'interface Streamlit.
    """
    import subprocess
    
    print("🚀 Lancement de l'interface Streamlit...")
    
    resultat = subprocess.run(
        ["streamlit", "run", "interface/streamlit_app.py"],
        capture_output=False
    )
    
    sys.exit(resultat.returncode)


def main():
    """
    Point d'entrée principal.
    Parse les arguments et lance le mode approprié.
    """
    parser = argparse.ArgumentParser(
        description="Voice Sniper - Générateur de Cold Calls Vocaux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python main.py                    # Lance le mode interactif
  python main.py --web              # Lance l'interface web Streamlit
  python main.py --version          # Affiche la version
        """
    )
    
    parser.add_argument(
        "--web",
        action="store_true",
        help="Lance l'interface web Streamlit"
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="Affiche la version de l'application"
    )
    
    arguments = parser.parse_args()
    
    if arguments.version:
        from infrastructure.config import obtenir_configuration
        config = obtenir_configuration()
        print(f"Voice Sniper v{config.version}")
        sys.exit(0)
    
    if arguments.web:
        executer_mode_streamlit()
    else:
        executer_mode_interactif()


if __name__ == "__main__":
    main()
