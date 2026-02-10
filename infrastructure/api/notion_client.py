"""
Client pour l'API Notion.
Implémente le port NotionDataProvider défini dans le domaine.
"""

from typing import Optional

import requests

from domain.models import Prospect, NotesEnrichies
from domain.ports import NotionDataProvider
from infrastructure.config import obtenir_configuration


class NotionClient(NotionDataProvider):
    """
    Adaptateur pour l'API Notion.
    Permet de récupérer et sauvegarder des données dans une base de données Notion.
    """

    def __init__(
        self,
        cle_api: Optional[str] = None,
        database_id: Optional[str] = None
    ):
        """
        Initialise le client Notion avec la configuration.
        """
        config = obtenir_configuration()
        self.cle_api = cle_api or config.notion_cle_api
        self.database_id = database_id or config.notion_database_id
        self.base_url = "https://api.notion.com/v1"
        
        self.headers = {
            "Authorization": f"Bearer {self.cle_api}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def recuperer_prospect_par_nom(self, nom_complet: str) -> Optional[Prospect]:
        """
        Recherche un prospect dans Notion par son nom complet.
        """
        try:
            print(f"🔍 Recherche Notion: '{nom_complet}'")
            url = f"{self.base_url}/databases/{self.database_id}/query"
            
            # Recherche avec le prénom pour plus de chances
            prenom = nom_complet.split()[0] if nom_complet else nom_complet
            
            payload = {
                "filter": {
                    "property": "Nom",
                    "title": {
                        "contains": prenom
                    }
                }
            }
            
            reponse = requests.post(url=url, headers=self.headers, json=payload, timeout=30)
            reponse.raise_for_status()
            
            donnees = reponse.json()
            resultats = donnees.get("results", [])
            print(f"   {len(resultats)} résultat(s) trouvé(s)")
            
            if not resultats:
                return None
            
            # Prendre le premier résultat
            prospect = self._convertir_page_en_prospect(resultats[0])
            print(f"   → Prospect: {prospect.nom_complet}")
            if prospect.notes_enrichies:
                print(f"     ✓ Notes: {len(prospect.notes_enrichies.notes_brutes)} caractères")
            return prospect
            
        except Exception as erreur:
            print(f"   ✗ Erreur Notion: {str(erreur)}")
            return None

    def sauvegarder_interaction(self, prospect: Prospect, contenu: str) -> bool:
        """Désactivé - Lecture seule."""
        return True

    def _convertir_page_en_prospect(self, page: dict) -> Prospect:
        """
        Convertit une page Notion en objet Prospect.
        Structure Notion:
        - Nom (title): Prénom Nom
        - Titre (select): Poste (CRO, CEO, VP Sales...)
        - Compte (rich_text): Entreprise
        - Secteur (select): AI/LLM/Tech
        - Taille (select): Startup/Scale-up
        - Statut (select): Discovery/Qualification
        - Notes (rich_text): Contexte détaillé
        - Email (rich_text): Email du prospect
        """
        proprietes = page.get("properties", {})
        
        def extraire_title(nom_prop):
            """Extrait d'une propriété de type title."""
            prop = proprietes.get(nom_prop, {})
            if prop.get("type") == "title":
                title = prop.get("title", [])
                if title:
                    return title[0].get("text", {}).get("content", "")
            return ""
        
        def extraire_rich_text(nom_prop):
            """Extrait d'une propriété rich_text (concatène tous les blocs)."""
            prop = proprietes.get(nom_prop, {})
            if prop.get("type") == "rich_text":
                rich_text = prop.get("rich_text", [])
                # Concaténer tous les blocs de texte
                contenu = ""
                for bloc in rich_text:
                    texte = bloc.get("text", {}).get("content", "")
                    if texte:
                        contenu += texte
                return contenu
            return ""
        
        def extraire_select(nom_prop):
            """Extrait d'une propriété select."""
            prop = proprietes.get(nom_prop, {})
            if prop.get("type") == "select":
                select = prop.get("select")
                if select:
                    return select.get("name", "")
            return ""
        
        # Extraction selon la structure exacte de Notion
        nom_complet = extraire_title("Nom")              # Colonne title
        titre_poste = extraire_select("Titre")            # Colonne select
        compte = extraire_rich_text("Compte")             # Colonne rich_text
        statut = extraire_select("Statut")                # Colonne select
        secteur = extraire_select("Secteur")              # Colonne select
        taille = extraire_select("Taille")                # Colonne select
        email = extraire_rich_text("Email")               # Colonne rich_text
        notes_brutes = extraire_rich_text("Notes")        # Colonne rich_text
        
        if notes_brutes:
            print(f"     📝 Notes: {len(notes_brutes)} caractères")
        
        return Prospect(
            nom_complet=nom_complet,
            entreprise=compte,
            titre=titre_poste or None,
            statut=statut or None,
            taille=taille or None,
            email=email or None,
            secteur_activite=secteur or None,
            notes_enrichies=NotesEnrichies(notes_brutes=notes_brutes) if notes_brutes else None
        )
