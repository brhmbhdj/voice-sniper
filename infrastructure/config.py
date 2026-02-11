"""
Configuration de l'application avec validation Pydantic.
Gère les variables d'environnement et les paramètres de l'application.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration centralisée de l'application Voice Sniper.
    
    Les valeurs sont chargées depuis les variables d'environnement
    ou depuis un fichier .env situé à la racine du projet.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore les variables d'env non définies ici
        env_file_override=True  # Force le rechargement du .env
    )
    
    # Configuration générale
    nom_application: str = Field(default="Voice Sniper", description="Nom de l'application")
    version: str = Field(default="1.0.0", description="Version de l'application")
    annee: str = Field(default="2026", description="Année de copyright")
    mode_debug: bool = Field(default=False, description="Mode debug activé")
    
    # Informations utilisateur
    utilisateur_nom: str = Field(default="Brahim Bouhadja", description="Nom de l'utilisateur")
    utilisateur_entreprise: str = Field(default="Gradium", description="Entreprise de l'utilisateur")
    
    # Sécurité (optionnel)
    password_app: str = Field(default="", description="Mot de passe pour protéger l'application (optionnel)")
    
    # Configuration Notion
    notion_cle_api: str = Field(default="", description="Clé API Notion")
    notion_database_id: str = Field(default="", description="ID de la base de données Notion")
    
    # Configuration Hunter.io
    hunter_cle_api: str = Field(default="", description="Clé API Hunter.io")
    hunter_base_url: str = Field(
        default="https://api.hunter.io/v2",
        description="URL de base de l'API Hunter"
    )
    
    # Configuration LLM Provider (Gemini ou Kimi)
    llm_provider: str = Field(
        default="gemini",
        description="Provider LLM: 'gemini' ou 'kimi'"
    )
    
    # Configuration Gemini (Google AI)
    gemini_cle_api: str = Field(default="", description="Clé API Gemini")
    gemini_modele: str = Field(
        default="gemini-2.5-pro-preview-03-25",  # Gemini 2.5 Pro
        description="Modèle Gemini à utiliser"
    )
    
    # Configuration Kimi (Moonshot AI)
    kimi_cle_api: str = Field(default="", description="Clé API Kimi (Moonshot)")
    kimi_modele: str = Field(
        default="moonshot-v1-8k",
        description="Modèle Kimi à utiliser (moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k)"
    )
    
    # Configuration Gradium.ai (TTS officiel)
    gradium_url_api: str = Field(
        default="https://eu.api.gradium.ai",
        description="URL de l'API Gradium.ai (https://eu.api.gradium.ai)"
    )
    gradium_cle_api: str = Field(
        default="",
        description="Clé API Gradium (gsk_xxx) - https://eu.api.gradium.ai/studio/platform/api-keys"
    )
    gradium_timeout: int = Field(
        default=60,
        description="Timeout pour les requêtes Gradium en secondes"
    )
    
    # Configuration des fichiers audio
    repertoire_sortie_audio: str = Field(
        default="./outputs",
        description="Répertoire de sortie pour les fichiers audio"
    )
    format_audio_defaut: str = Field(
        default="mp3",
        description="Format audio par défaut"
    )
    
    @property
    def notion_est_configure(self) -> bool:
        """Vérifie si la configuration Notion est complète."""
        return bool(self.notion_cle_api and self.notion_database_id)
    
    @property
    def hunter_est_configure(self) -> bool:
        """Vérifie si la configuration Hunter est complète."""
        return bool(self.hunter_cle_api)
    
    @property
    def gemini_est_configure(self) -> bool:
        """Vérifie si la configuration Gemini est complète."""
        return bool(self.gemini_cle_api)
    
    @property
    def gradium_est_configure(self) -> bool:
        """Vérifie si la configuration Gradium est complète."""
        return bool(self.gradium_cle_api)
    
    @property
    def kimi_est_configure(self) -> bool:
        """Vérifie si la configuration Kimi est complète."""
        return bool(self.kimi_cle_api)


# Instance singleton de la configuration
configuration = Settings()


def obtenir_configuration() -> Settings:
    """
    Retourne l'instance de configuration de l'application.
    
    Returns:
        Instance Settings avec les valeurs chargées
    """
    return configuration
