"""
Configuration de l'application avec validation Pydantic.
Gère les variables d'environnement, le fichier .env, et les secrets Streamlit Cloud.
"""

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_streamlit_secrets():
    """Récupère les secrets depuis Streamlit Cloud (st.secrets) si disponible."""
    try:
        import streamlit as st
        # Si on est dans un environnement Streamlit, st.secrets existe
        if hasattr(st, 'secrets'):
            return dict(st.secrets)
    except Exception:
        pass
    return {}


def get_settings_values():
    """Combine les sources de configuration (env vars, .env, st.secrets)."""
    values = {}
    
    # 1. Streamlit Cloud secrets (priorité max sur le cloud)
    streamlit_secrets = get_streamlit_secrets()
    if streamlit_secrets:
        # Mapping des noms de secrets Streamlit vers les noms de config
        mapping = {
            'GEMINI_CLE_API': 'gemini_cle_api',
            'GEMINI_MODELE': 'gemini_modele',
            'KIMI_CLE_API': 'kimi_cle_api',
            'KIMI_MODELE': 'kimi_modele',
            'NOTION_CLE_API': 'notion_cle_api',
            'NOTION_DATABASE_ID': 'notion_database_id',
            'HUNTER_CLE_API': 'hunter_cle_api',
            'GRADIUM_CLE_API': 'gradium_cle_api',
            'GRADIUM_URL_API': 'gradium_url_api',
            'LLM_PROVIDER': 'llm_provider',
        }
        for env_key, config_key in mapping.items():
            if env_key in streamlit_secrets:
                values[config_key] = streamlit_secrets[env_key]
    
    return values


class Settings(BaseSettings):
    """
    Configuration centralisée de l'application Voice Sniper.
    
    Priorité des sources :
    1. Streamlit Cloud secrets (st.secrets) - si sur Streamlit Cloud
    2. Variables d'environnement
    3. Fichier .env local
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_file_override=True
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
        default="gemini-2.5-flash",  # Modèle par défaut (rapide, bon quotas)
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
# On charge les secrets Streamlit dès le départ s'ils existent
_streamlit_values = get_settings_values()
configuration = Settings(**_streamlit_values) if _streamlit_values else Settings()


def obtenir_configuration() -> Settings:
    """
    Retourne l'instance de configuration de l'application.
    
    Returns:
        Instance Settings avec les valeurs chargées
        (depuis .env local ou Streamlit Cloud secrets)
    """
    global configuration
    # Recharger les secrets Streamlit à chaque appel (pour les mises à jour)
    _values = get_settings_values()
    if _values:
        configuration = Settings(**_values)
    return configuration
