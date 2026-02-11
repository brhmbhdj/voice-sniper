"""
Client pour l'API Hunter.io.
Implémente le port HunterDataProvider défini dans le domaine.
"""

from typing import Optional

import requests

from domain.models import Prospect
from domain.ports import HunterDataProvider
from infrastructure.config import obtenir_configuration


class HunterClient(HunterDataProvider):
    """
    Adaptateur pour l'API Hunter.io.
    Permet de rechercher des emails professionnels et d'enrichir les données de prospects.
    """

    def __init__(self, cle_api: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialise le client Hunter avec la configuration.
        
        Args:
            cle_api: Clé API Hunter (si None, utilise la config)
            base_url: URL de base de l'API (si None, utilise la config)
        """
        config = obtenir_configuration()
        self.cle_api = cle_api or config.hunter_cle_api
        self.base_url = base_url or config.hunter_base_url

    def rechercher_emails_entreprise(self, nom_entreprise: str, domaine: str) -> list[Prospect]:
        """
        Recherche les emails professionnels d'une entreprise via Hunter.
        
        Args:
            nom_entreprise: Nom de l'entreprise
            domaine: Domaine de l'entreprise (ex: example.com)
            
        Returns:
            Liste des prospects trouvés
            
        Raises:
            Exception: Si la requête échoue
        """
        # Si pas de clé API, retourner liste vide (Hunter est optionnel)
        if not self.cle_api:
            return []
        
        try:
            # Nettoyage du domaine
            domaine_nettoye = domaine.replace("https://", "").replace("http://", "").replace("www.", "")
            
            url = f"{self.base_url}/domain-search"
            params = {
                "domain": domaine_nettoye,
                "api_key": self.cle_api
            }
            
            reponse = requests.get(url, params=params, timeout=30)
            reponse.raise_for_status()
            
            donnees = reponse.json()
            emails_trouves = donnees.get("data", {}).get("emails", [])
            
            # Conversion en objets Prospect
            prospects = []
            for email_data in emails_trouves:
                prospect = Prospect(
                    nom_complet=email_data.get("first_name", "") + " " + email_data.get("last_name", ""),
                    entreprise=nom_entreprise,
                    titre=email_data.get("position") or None,
                    email=email_data.get("value") or None,
                    telephone=None  # Hunter ne fournit pas les téléphones
                )
                prospects.append(prospect)
            
            return prospects
            
        except requests.exceptions.Timeout:
            raise Exception("Timeout lors de la requête à Hunter.io")
        except requests.exceptions.HTTPError as erreur:
            if erreur.response.status_code == 401:
                raise Exception("Clé API Hunter invalide")
            elif erreur.response.status_code == 429:
                raise Exception("Limite de requêtes Hunter atteinte")
            else:
                raise Exception(f"Erreur HTTP Hunter : {erreur.response.status_code}")
        except Exception as erreur:
            raise Exception(f"Erreur lors de la recherche Hunter : {str(erreur)}")

    def verifier_email(self, email: str) -> dict:
        """
        Vérifie la validité d'une adresse email avec Hunter.
        
        Args:
            email: Adresse email à vérifier
            
        Returns:
            Dictionnaire avec le résultat de la vérification
        """
        # Si pas de clé API, retourner statut inconnu (Hunter est optionnel)
        if not self.cle_api:
            return {"email": email, "statut": "inconnu", "score": 0}
        
        try:
            url = f"{self.base_url}/email-verifier"
            params = {
                "email": email,
                "api_key": self.cle_api
            }
            
            reponse = requests.get(url, params=params, timeout=30)
            reponse.raise_for_status()
            
            donnees = reponse.json()
            return {
                "email": email,
                "statut": donnees.get("data", {}).get("status"),
                "score": donnees.get("data", {}).get("score"),
                "resultat": donnees.get("data", {}).get("result")
            }
            
        except Exception as erreur:
            return {
                "email": email,
                "statut": "inconnu",
                "erreur": str(erreur)
            }

    def enrichir_prospect(self, prospect: Prospect) -> Prospect:
        """
        Enrichit un prospect avec des données complémentaires depuis Hunter.
        Recherche des informations supplémentaires sur l'entreprise.
        
        Args:
            prospect: Prospect à enrichir
            
        Returns:
            Prospect avec les données enrichies
        """
        try:
            # Si on a un email, on peut tenter de vérifier sa validité
            if prospect.email:
                verification = self.verifier_email(prospect.email)
                # On pourrait stocker le score de confiance si nécessaire
            
            # Si on a l'entreprise mais pas le domaine, on essaie de le deviner
            if prospect.entreprise and not prospect.site_web:
                domaine_estime = self._estimer_domaine(prospect.entreprise)
                
                # Recherche des emails de l'entreprise pour trouver plus d'infos
                prospects_entreprise = self.rechercher_emails_entreprise(
                    nom_entreprise=prospect.entreprise,
                    domaine=domaine_estime
                )
                
                # On cherche un prospect correspondant au nom
                for prospect_trouve in prospects_entreprise:
                    if prospect.nom_complet.lower() in prospect_trouve.nom_complet.lower():
                        # Fusion des données
                        if not prospect.titre and prospect_trouve.titre:
                            prospect.titre = prospect_trouve.titre
                        if not prospect.email and prospect_trouve.email:
                            prospect.email = prospect_trouve.email
                        break
            
            return prospect
            
        except Exception:
            # En cas d'échec de l'enrichissement, on retourne le prospect tel quel
            return prospect

    def _estimer_domaine(self, nom_entreprise: str) -> str:
        """
        Estime le domaine d'une entreprise à partir de son nom.
        
        Args:
            nom_entreprise: Nom de l'entreprise
            
        Returns:
            Domaine estimé
        """
        # Normalisation du nom d'entreprise
        nom_normalise = (
            nom_entreprise.lower()
            .replace(" ", "")
            .replace("-", "")
            .replace("&", "")
            .replace(".", "")
            .replace(",", "")
        )
        
        # Extensions communes à tester
        extensions = [".com", ".fr", ".io", ".co", ".net"]
        
        # Pour l'instant, on retourne juste l'estimation avec .com
        # Dans un cas réel, on pourrait tester les différentes extensions
        return f"{nom_normalise}.com"
