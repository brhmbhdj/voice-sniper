"""
Modèles de données métier pour Voice Sniper.
Utilisation des dataclasses pour une définition claire et type-safe.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Language(Enum):
    """Énumération des langues supportées pour la synthèse vocale."""
    AUTO = "auto"  # Détection automatique basée sur le prospect
    FRENCH = "fr"
    ENGLISH = "en"
    SPANISH = "es"
    GERMAN = "de"
    ITALIAN = "it"


@dataclass
class NotesEnrichies:
    """
    Informations enrichies extraites des notes Notion.
    
    Attributs:
        situation_actuelle: Description du contexte et triggers
        pain_points: Liste des problématiques identifiées
        value_proposition: Arguments pourquoi nous
        notes_brutes: Texte complet des notes
    """
    situation_actuelle: str = ""
    pain_points: list[str] = field(default_factory=list)
    value_proposition: str = ""
    notes_brutes: str = ""


@dataclass
class Prospect:
    """
    Représente un prospect avec ses informations de contact et son contexte.
    
    Attributs:
        nom_complet: Nom et prénom du prospect
        entreprise: Nom de l'entreprise du prospect
        titre: Poste du prospect (CRO, CEO, VP Sales, etc.)
        statut: Statut du prospect dans le pipeline (Discovery, etc.)
        taille: Taille de l'entreprise (Startup, Scale-up, etc.)
        email: Adresse email professionnelle (optionnel)
        telephone: Numéro de téléphone (optionnel)
        secteur_activite: Secteur d'activité de l'entreprise (optionnel)
        site_web: URL du site web de l'entreprise (optionnel)
        date_creation: Date de création de l'entreprise (optionnel)
        notes_enrichies: Informations détaillées depuis Notion (optionnel)
    """
    nom_complet: str
    entreprise: str
    titre: Optional[str] = None  # Poste: CRO, CEO, VP Sales, etc.
    statut: Optional[str] = None  # Discovery, Qualification, etc.
    taille: Optional[str] = None  # Startup, Scale-up, etc.
    email: Optional[str] = None
    telephone: Optional[str] = None
    secteur_activite: Optional[str] = None
    site_web: Optional[str] = None
    date_creation: Optional[datetime] = None
    notes_enrichies: Optional[NotesEnrichies] = None
    langue: Optional[str] = None  # Langue préférée (FR, UK, EN, etc.) depuis Notion


@dataclass
class Trigger:
    """
    Événement déclencheur pour personnaliser l'approche du cold call.
    
    Attributs:
        type_trigger: Type d'événement (levée de fonds, recrutement, expansion, etc.)
        description: Description détaillée du trigger
        date_evenement: Date de survenue de l'événement (optionnel)
        source: Source de l'information (optionnel)
    """
    type_trigger: str
    description: str
    date_evenement: Optional[datetime] = None
    source: Optional[str] = None


@dataclass
class Script:
    """
    Script de cold call généré par l'IA.
    
    Attributs:
        introduction: Phrase d'accroche personnalisée
        corps_message: Contenu principal du script
        proposition_valeur: Proposition de valeur spécifique au prospect
        objection_handling: Réponses aux objections courantes
        call_to_action: Action demandée en fin d'appel
        langue: Langue du script
        duree_estimee: Durée estimée de l'appel en secondes
    """
    introduction: str
    corps_message: str
    proposition_valeur: str
    objection_handling: list[str] = field(default_factory=list)
    call_to_action: str = ""
    langue: Language = Language.FRENCH
    duree_estimee: int = 60


@dataclass
class AudioOutput:
    """
    Sortie audio générée par le système TTS.
    
    Attributs:
        contenu_audio: Données binaires du fichier audio
        format_fichier: Format du fichier audio (mp3, wav, etc.)
        duree_secondes: Durée de l'audio en secondes
        langue: Langue utilisée pour la synthèse
        chemin_fichier: Chemin local du fichier généré (optionnel)
    """
    contenu_audio: bytes
    format_fichier: str
    duree_secondes: float
    langue: Language
    chemin_fichier: Optional[str] = None
