"""
Cas d'utilisation principal : Générer un cold call vocal personnalisé.
Orchestre les différents ports pour produire un résultat complet.
"""

from datetime import datetime
from domain.models import Prospect, Trigger, Script, Language
from domain.ports import (
    NotionDataProvider,
    HunterDataProvider,
    LLMProvider,
    VoiceProvider
)


class GenerateVoiceOutbound:
    """
    Service applicatif pour générer des cold calls vocaux personnalisés.
    
    Cette classe implémente le cas d'utilisation principal du système :
    1. Récupération des données du prospect (Notion + Hunter)
    2. Génération du script avec le LLM
    3. Synthèse vocale du script
    
    L'injection de dépendances permet de tester la classe en isolation
    et de changer facilement d'implémentation d'infrastructure.
    """

    def __init__(
        self,
        fournisseur_notion: NotionDataProvider,
        fournisseur_hunter: HunterDataProvider,
        fournisseur_llm: LLMProvider,
        fournisseur_voix: VoiceProvider
    ):
        """
        Initialise le service avec ses dépendances externes.
        
        Args:
            fournisseur_notion: Adaptateur pour accéder aux données Notion
            fournisseur_hunter: Adaptateur pour accéder aux données Hunter.io
            fournisseur_llm: Adaptateur pour le modèle de langage
            fournisseur_voix: Adaptateur pour la synthèse vocale
        """
        self.fournisseur_notion = fournisseur_notion
        self.fournisseur_hunter = fournisseur_hunter
        self.fournisseur_llm = fournisseur_llm
        self.fournisseur_voix = fournisseur_voix

    def executer(
        self,
        nom_prospect: str,
        nom_entreprise: str,
        type_trigger: str,
        description_trigger: str,
        langue: Language = Language.FRENCH,
        ton_script: str = "professionnel",
        voix_selectionnee: str = "default",
        vitesse_lecture: float = 1.0
    ) -> dict:
        """
        Exécute le cas d'utilisation complet de génération de cold call.
        
        Args:
            nom_prospect: Nom complet du prospect
            nom_entreprise: Nom de l'entreprise du prospect
            type_trigger: Type d'événement déclencheur
            description_trigger: Description détaillée du trigger
            langue: Langue souhaitée pour le script et l'audio
            ton_script: Ton du script (professionnel, décontracté, etc.)
            voix_selectionnee: Identifiant de la voix à utiliser
            vitesse_lecture: Vitesse de lecture de l'audio
            
        Returns:
            Dictionnaire contenant le prospect, le script, l'audio et les métadonnées
        """
        # Étape 1 : Récupérer ou créer le prospect
        prospect = self._recuperer_prospect(nom_prospect, nom_entreprise)
        
        # Étape 1.5 : Détecter la langue si mode automatique
        langue_finale = langue
        if langue == Language.AUTO:
            langue_detectee = self.fournisseur_llm.detecter_langue_ideale(prospect)
            langue_finale = langue_detectee
            # Log pour debug
            print(f"🌍 Langue détectée automatiquement : {langue_finale.value}")
        
        # Étape 2 : Créer l'objet trigger
        # Si des notes enrichies existent, on les utilise pour améliorer le trigger
        description_enrichie = description_trigger
        if prospect.notes_enrichies and prospect.notes_enrichies.situation_actuelle:
            # Enrichit la description avec les notes Notion
            description_enrichie = f"{description_trigger}\n\nContexte détaillé depuis Notion :\n{prospect.notes_enrichies.situation_actuelle}"
        
        trigger = Trigger(
            type_trigger=type_trigger,
            description=description_enrichie,
            date_evenement=datetime.now()
        )
        
        # Étape 3 : Générer le script personnalisé
        script = self.fournisseur_llm.generer_script_cold_call(
            prospect=prospect,
            trigger=trigger,
            langue=langue_finale,
            ton=ton_script
        )
        
        # Étape 4 : Synthétiser la voix
        audio = self.fournisseur_voix.synthetiser_voix(
            texte=self._assembler_script_complet(script),
            langue=langue_finale,
            voix=voix_selectionnee,
            vitesse=vitesse_lecture
        )
        
        # Étape 5 : (Désactivé) Pas de sauvegarde dans Notion
        # On lit uniquement depuis Notion pour enrichir les scripts
        # self.fournisseur_notion.sauvegarder_interaction(...)
        pass
        
        return {
            "prospect": prospect,
            "trigger": trigger,
            "script": script,
            "audio": audio,
            "timestamp": datetime.now().isoformat(),
            "langue": langue_finale.value,
            "langue_detectee_auto": langue == Language.AUTO
        }

    def _recuperer_prospect(self, nom_complet: str, nom_entreprise: str) -> Prospect:
        """
        Récupère les informations du prospect depuis les sources internes et externes.
        
        Priorité :
        1. Recherche dans Notion (données internes)
        2. Si pas trouvé, recherche dans Hunter.io (données externes)
        3. Si toujours pas trouvé, création d'un prospect minimal
        
        Args:
            nom_complet: Nom complet du prospect
            nom_entreprise: Nom de l'entreprise
            
        Returns:
            Objet Prospect avec les informations récupérées
        """
        # Tentative de récupération depuis Notion
        prospect = self.fournisseur_notion.recuperer_prospect_par_nom(nom_complet)
        
        if prospect is None:
            # Tentative de récupération depuis Hunter.io
            prospects_trouves = self.fournisseur_hunter.rechercher_emails_entreprise(
                nom_entreprise=nom_entreprise,
                domaine=self._extraire_domaine(nom_entreprise)
            )
            
            # Recherche du prospect par correspondance de nom
            for prospect_candidate in prospects_trouves:
                if nom_complet.lower() in prospect_candidate.nom_complet.lower():
                    prospect = prospect_candidate
                    break
        
        if prospect is None:
            # Création d'un prospect minimal si aucune source n'a trouvé d'informations
            prospect = Prospect(
                nom_complet=nom_complet,
                entreprise=nom_entreprise
            )
        else:
            # Enrichissement des données du prospect
            prospect = self.fournisseur_hunter.enrichir_prospect(prospect)
        
        return prospect

    def _assembler_script_complet(self, script: Script) -> str:
        """
        Assemble les différentes parties du script en un seul texte.
        
        Args:
            script: Script avec ses différentes parties
            
        Returns:
            Texte complet prêt pour la synthèse vocale
        """
        parties_script = [
            script.introduction,
            "\n",
            script.corps_message,
            "\n",
            script.proposition_valeur,
            "\n",
            script.call_to_action
        ]
        
        return "\n".join(parties_script)

    def _extraire_domaine(self, nom_entreprise: str) -> str:
        """
        Extrait un domaine probable à partir du nom d'entreprise.
        
        Args:
            nom_entreprise: Nom de l'entreprise
            
        Returns:
            Domaine estimé (format simplifié)
        """
        # Simplification : transformation du nom en domaine basique
        # Dans un cas réel, on utiliserait une base de données ou une API
        nom_normalise = nom_entreprise.lower().replace(" ", "").replace("-", "")
        return f"{nom_normalise}.com"


