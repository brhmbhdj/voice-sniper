"""
Client pour l'API Kimi (Moonshot AI).
Implémente le port LLMProvider défini dans le domaine.
Alternative à Gemini pour la génération de scripts.
"""

from typing import Optional

import requests

from domain.models import Prospect, Trigger, Script, Language
from domain.ports import LLMProvider
from infrastructure.config import obtenir_configuration


class KimiClient(LLMProvider):
    """
    Adaptateur pour le modèle de langage Kimi (Moonshot AI).
    Alternative à Gemini pour la génération de scripts de cold call.
    """

    def __init__(
        self,
        cle_api: Optional[str] = None,
        nom_modele: Optional[str] = None
    ):
        """
        Initialise le client Kimi avec la configuration.
        
        Args:
            cle_api: Clé API Kimi (si None, utilise la config)
            nom_modele: Nom du modèle à utiliser (si None, utilise la config)
        """
        config = obtenir_configuration()
        self.cle_api = (cle_api or config.kimi_cle_api or "").strip()
        self.nom_modele = (nom_modele or config.kimi_modele or "").strip()
        
        # Vérification que la clé est définie
        if not self.cle_api:
            raise ValueError("KIMI_CLE_API n'est pas définie dans les variables d'environnement")
        
        # Configuration de l'API Kimi
        self.base_url = "https://api.moonshot.cn/v1"
        self.headers = {
            "Authorization": f"Bearer {self.cle_api}",
            "Content-Type": "application/json"
        }

    def generer_script_cold_call(
        self,
        prospect: Prospect,
        trigger: Trigger,
        langue: Language,
        ton: str = "professionnel"
    ) -> Script:
        """
        Génère un script de cold call personnalisé avec Kimi.
        
        Args:
            prospect: Informations sur le prospect
            trigger: Événement déclencheur
            langue: Langue souhaitée pour le script
            ton: Ton de la conversation
            
        Returns:
            Script complet généré par l'IA
        """
        try:
            # Construction du prompt
            prompt = self._construire_prompt(prospect, trigger, langue, ton)
            
            print(f"📝 Génération du script avec Kimi ({self.nom_modele})...")
            
            # Appel API Kimi
            payload = {
                "model": self.nom_modele,
                "messages": [
                    {"role": "system", "content": "Tu es un expert en vente B2B spécialisé dans les cold calls."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            # Extraction du contenu généré
            data = response.json()
            contenu_genere = data["choices"][0]["message"]["content"]
            
            return self._parser_script(contenu_genere, langue)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                cle_masquee = self.cle_api[:10] + "..." if len(self.cle_api) > 10 else "(vide)"
                raise Exception(f"Clé API Kimi invalide (début: {cle_masquee}). Vérifiez KIMI_CLE_API dans .env")
            if e.response.status_code == 429:
                raise Exception("Quota Kimi dépassé. Veuillez vérifier votre plan.")
            raise Exception(f"Erreur API Kimi: {e.response.text}")
        except Exception as erreur:
            raise Exception(f"Erreur lors de la génération du script avec Kimi: {str(erreur)}")

    def detecter_langue_ideale(self, prospect: Prospect) -> Language:
        """
        Détecte la langue idéale pour contacter un prospect.
        """
        try:
            contexte = f"""
            Prospect: {prospect.nom_complet}
            Entreprise: {prospect.entreprise}
            Secteur: {prospect.secteur_activite or 'Non spécifié'}
            Notes: {prospect.notes_enrichies.notes_brutes[:500] if prospect.notes_enrichies else ''}
            
            Réponds uniquement avec le code langue: fr, en, es, de, ou it.
            """
            
            payload = {
                "model": self.nom_modele,
                "messages": [
                    {"role": "system", "content": "Tu détectes la langue idéale pour un cold call."},
                    {"role": "user", "content": contexte}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            texte_reponse = response.json()["choices"][0]["message"]["content"].strip().lower()
            
            mapping_langues = {
                "fr": Language.FRENCH,
                "en": Language.ENGLISH,
                "es": Language.SPANISH,
                "de": Language.GERMAN,
                "it": Language.ITALIAN
            }
            
            for code, langue in mapping_langues.items():
                if code in texte_reponse:
                    return langue
            
            return Language.ENGLISH
            
        except Exception:
            return Language.ENGLISH

    def _construire_prompt(
        self,
        prospect: Prospect,
        trigger: Trigger,
        langue: Language,
        ton: str
    ) -> str:
        """Construit le prompt pour Kimi."""
        from infrastructure.config import obtenir_configuration
        config = obtenir_configuration()
        nom_vendeur = config.utilisateur_nom
        
        langues_texte = {
            Language.FRENCH: "français",
            Language.ENGLISH: "anglais",
            Language.SPANISH: "espagnol",
            Language.GERMAN: "allemand",
            Language.ITALIAN: "italien"
        }
        
        nom_langue = langues_texte.get(langue, "français")
        
        titre_info = f"Titre/Poste : {prospect.titre}" if prospect.titre else ""
        taille_info = f"Taille entreprise : {prospect.taille}" if prospect.taille else ""
        secteur_info = f"Secteur : {prospect.secteur_activite}" if prospect.secteur_activite else ""
        statut_info = f"Statut pipeline : {prospect.statut}" if prospect.statut else ""
        
        notes_context = ""
        if prospect.notes_enrichies and prospect.notes_enrichies.notes_brutes:
            notes = prospect.notes_enrichies.notes_brutes[:3000]
            notes_context = f"""
🚨 CONTEXTE OBLIGATOIRE - NOTES NOTION :
{notes}
🚨 FIN DES NOTES
"""
        
        return f"""
Tu es un expert en vente B2B. Génère un script de cold call ULTRA-PERSONNALISÉ en {nom_langue} avec un ton {ton}.

========================================
TON IDENTITÉ
========================================
- Ton nom : {nom_vendeur}
- Ton entreprise : Gradium

========================================
INFORMATIONS DU PROSPECT
========================================
- Nom : {prospect.nom_complet}
- Entreprise : {prospect.entreprise}
{titre_info}
{taille_info}
{secteur_info}
{statut_info}

{notes_context}

========================================
TRIGGER
========================================
- Type : {trigger.type_trigger}
- Description : {trigger.description}

========================================
INSTRUCTIONS CRITIQUES
========================================

🎯 OBJECTIF : Créer un script qui montre que tu as fait tes recherches et qui génère un RDV.

🌐 LANGUE : 100% DU SCRIPT DOIT ÊTRE EN {nom_langue.upper()} :
- Introduction en {nom_langue}
- Corps du message en {nom_langue}
- Proposition de valeur en {nom_langue}
- Call-to-action en {nom_langue}
- AUCUNE phrase dans une autre langue

⚠️ RÈGLES STRICTES :
1. Utilise IMPÉRATIVEMENT les informations des NOTES NOTION
2. Mentionne des éléments spécifiques trouvés dans les notes
3. Parle en {nom_langue} NATIF (pas de mots français si la langue est anglais)
4. Mentionne le prénom du prospect 2-3 fois
5. Sois conversationnel et naturel
6. Signe-toi avec ton vrai nom : "{nom_vendeur}"

📋 STRUCTURE (60-90 secondes) :

1. INTRODUCTION (10-15s) :
   "Hi [Prénom], {nom_vendeur} here from Gradium..."
   → Accroche personnalisée avec contexte des notes

2. CORPS DU MESSAGE (20-30s) :
   → Relie le trigger à un problème concret du prospect
   → Mentionne 1-2 détails spécifiques des notes

3. PROPOSITION DE VALEUR (15-20s) :
   → Évite "With that kind of..." ou phrases génériques
   → Donne une proposition CONCRÈTE et CHIFFRÉE si possible
   → Exemple : "We help companies like [Entreprise] reduce ramp-up time by 40% through automated signal detection..."
   → Explique COMMENT tu résous le problème

4. GESTION D'OBJECTION (10-15s) :
   → Réponse à "I'm busy / Not interested / Already have a solution"

5. CALL-TO-ACTION (5-10s) :
   → Demande EXPLICITE de RDV STRICTEMENT EN {nom_langue.upper()}
   → Exemple EN ANGLAIS : "Can we schedule a 15-minute call this week?"
   → Le CTA DOIT être dans la MÊME LANGUE que le reste du script
   → INTERDICTION ABSOLUE de mélanger les langues dans le CTA
   → Si le script est en anglais, le CTA DOIT être : "Can we schedule a brief call this week?" ou "Are you available for a quick 15-minute chat?"
   → Si le script est en français, le CTA DOIT être : "Pouvons-nous convenir d'un appel rapide cette semaine ?"

🚫 INTERDIT :
- Phrases génériques comme "With that kind of..."
- Mélanger les langues dans le script
- Parler de soi plus que du prospect
- Oublier de signer avec son nom

✅ RÉPONDS UNIQUEMENT AVEC LE SCRIPT COMPLET, sans introduction ni commentaire.
"""

    def _parser_script(self, contenu: str, langue: Language) -> Script:
        """Parse la réponse de Kimi."""
        contenu = contenu.strip()
        
        if not contenu:
            return Script(
                introduction="Bonjour, je vous appelle concernant votre entreprise.",
                corps_message="J'ai remarqué que vous êtes en pleine expansion.",
                proposition_valeur="Je peux vous aider à optimiser vos processus.",
                langue=langue
            )
        
        # Découper en paragraphes
        paragraphes = [p.strip() for p in contenu.split('\n\n') if p.strip()]
        
        introduction = paragraphes[0] if len(paragraphes) > 0 else ""
        corps_message = paragraphes[1] if len(paragraphes) > 1 else ""
        proposition_valeur = paragraphes[2] if len(paragraphes) > 2 else ""
        objection_handling = [paragraphes[3]] if len(paragraphes) > 3 else []
        call_to_action = paragraphes[4] if len(paragraphes) > 4 else ""
        
        # Nettoyer
        import re
        def nettoyer(texte):
            texte = re.sub(r'^(\d+\.|INTRODUCTION|CORPS|PROPOSITION|OBJECTION|CALL-TO-ACTION)[\s:\-]*', '', texte, flags=re.IGNORECASE)
            return texte.strip()
        
        return Script(
            introduction=nettoyer(introduction),
            corps_message=nettoyer(corps_message),
            proposition_valeur=nettoyer(proposition_valeur),
            objection_handling=[nettoyer(o) for o in objection_handling],
            call_to_action=nettoyer(call_to_action),
            langue=langue,
            duree_estimee=75
        )
