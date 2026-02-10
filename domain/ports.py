"""
Ports (interfaces abstraites) définissant les contrats avec l'extérieur.
Ces interfaces respectent le principe d'inversion de dépendance (DIP).
"""

from abc import ABC, abstractmethod
from typing import Optional

from domain.models import Prospect, Trigger, Script, AudioOutput, Language


class NotionDataProvider(ABC):
    """
    Port pour récupérer des données depuis Notion.
    Permet d'obtenir des informations internes sur les prospects stockées dans Notion.
    """

    @abstractmethod
    def recuperer_prospect_par_nom(self, nom_complet: str) -> Optional[Prospect]:
        """
        Récupère un prospect depuis Notion par son nom complet.
        
        Args:
            nom_complet: Nom et prénom du prospect recherché
            
        Returns:
            Objet Prospect si trouvé, None sinon
        """
        pass

    @abstractmethod
    def sauvegarder_interaction(self, prospect: Prospect, contenu: str) -> bool:
        """
        Sauvegarde une interaction avec un prospect dans Notion.
        
        Args:
            prospect: Prospect concerné par l'interaction
            contenu: Contenu de l'interaction
            
        Returns:
            True si la sauvegarde a réussi, False sinon
        """
        pass


class HunterDataProvider(ABC):
    """
    Port pour récupérer des données depuis Hunter.io.
    Permet d'obtenir des informations externes sur les prospects (emails, postes, etc.).
    """

    @abstractmethod
    def rechercher_emails_entreprise(self, nom_entreprise: str, domaine: str) -> list[Prospect]:
        """
        Recherche les emails professionnels d'une entreprise.
        
        Args:
            nom_entreprise: Nom de l'entreprise
            domaine: Domaine de l'entreprise (ex: example.com)
            
        Returns:
            Liste des prospects trouvés avec leurs informations
        """
        pass

    @abstractmethod
    def verifier_email(self, email: str) -> dict:
        """
        Vérifie la validité d'une adresse email.
        
        Args:
            email: Adresse email à vérifier
            
        Returns:
            Dictionnaire contenant le résultat de la vérification
        """
        pass

    @abstractmethod
    def enrichir_prospect(self, prospect: Prospect) -> Prospect:
        """
        Enrichit un prospect avec des données complémentaires depuis Hunter.
        
        Args:
            prospect: Prospect à enrichir
            
        Returns:
            Prospect enrichi avec les nouvelles informations
        """
        pass


class LLMProvider(ABC):
    """
    Port pour interagir avec un modèle de langage (LLM).
    Permet de générer des scripts de cold call personnalisés.
    """

    @abstractmethod
    def generer_script_cold_call(
        self,
        prospect: Prospect,
        trigger: Trigger,
        langue: Language,
        ton: str = "professionnel"
    ) -> Script:
        """
        Génère un script de cold call personnalisé.
        
        Args:
            prospect: Informations sur le prospect
            trigger: Événement déclencheur pour personnaliser le script
            langue: Langue souhaitée pour le script
            ton: Ton de la conversation (professionnel, décontracté, formel, etc.)
            
        Returns:
            Script complet avec introduction, corps et conclusion
        """
        pass

    @abstractmethod
    def detecter_langue_ideale(self, prospect: Prospect) -> Language:
        """
        Détecte la langue idéale pour contacter un prospect
        basée sur son entreprise, pays, ou autres indices.
        
        Args:
            prospect: Informations du prospect
            
        Returns:
            Langue recommandée pour le cold call
        """
        pass


class VoiceProvider(ABC):
    """
    Port pour la synthèse vocale (Text-to-Speech).
    Permet de convertir un script texte en audio.
    """

    @abstractmethod
    def synthetiser_voix(
        self,
        texte: str,
        langue: Language,
        voix: str = "default",
        vitesse: float = 1.0
    ) -> AudioOutput:
        """
        Convertit un texte en audio.
        
        Args:
            texte: Texte à synthétiser
            langue: Langue du texte
            voix: Identifiant de la voix à utiliser
            vitesse: Vitesse de lecture (1.0 = vitesse normale)
            
        Returns:
            Objet AudioOutput contenant les données audio
        """
        pass

    @abstractmethod
    def lister_voix_disponibles(self, langue: Language) -> list[dict]:
        """
        Sauvegarde l'audio généré dans un fichier.
        
        Args:
            audio_output: Objet audio à sauvegarder
            chemin_sortie: Chemin du fichier de sortie
            
        Returns:
            Chemin complet du fichier sauvegardé
        """
        pass
