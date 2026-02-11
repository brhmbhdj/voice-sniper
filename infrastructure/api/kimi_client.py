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
            contenu_genere = data["choices"][0]["message"]["content"].strip()
            
            # Retourner le texte brut sans parsing
            if not contenu_genere:
                return Script(
                    introduction="",
                    corps_message="Script non généré. Veuillez réessayer.",
                    proposition_valeur="",
                    langue=langue
                )
            
            return Script(
                introduction="",
                corps_message=contenu_genere,
                proposition_valeur="",
                langue=langue,
                duree_estimee=60
            )
            
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
        Priorité: Colonne Notion > Règles > Défaut (Français)
        """
        # 1. Priorité à la colonne Langue de Notion
        if prospect.langue:
            langue_notion = prospect.langue.upper().strip()
            if langue_notion in ['FR', 'FRENCH']:
                return Language.FRENCH
            elif langue_notion in ['UK', 'EN', 'ENGLISH', 'US']:
                return Language.ENGLISH
            elif langue_notion in ['ES', 'SPANISH']:
                return Language.SPANISH
            elif langue_notion in ['DE', 'GERMAN']:
                return Language.GERMAN
            elif langue_notion in ['IT', 'ITALIAN']:
                return Language.ITALIAN
        
        # 2. Règles par défaut
        nom_lower = prospect.nom_complet.lower() if prospect.nom_complet else ""
        entreprise_lower = prospect.entreprise.lower() if prospect.entreprise else ""
        notes_lower = prospect.notes_enrichies.notes_brutes.lower() if prospect.notes_enrichies and prospect.notes_enrichies.notes_brutes else ""
        
        # Noms typiquement français
        prenoms_fr = ['marie', 'jean', 'pierre', 'constance', 'marine', 'sophie', 'julien', 'thomas', 'nicolas', 'alexandre']
        for prenom in prenoms_fr:
            if prenom in nom_lower:
                return Language.FRENCH
        
        # Indices dans les notes
        mots_fr = ['france', 'paris', 'lyon', 'marseille', 'euros', 'levee', 'fonds', 'startup francaise']
        for mot in mots_fr:
            if mot in notes_lower or mot in entreprise_lower:
                return Language.FRENCH
        
        # Mots anglais
        mots_en = ['inc', 'llc', 'corp', 'ltd', 'uk', 'usa', 'america', 'london', 'new york']
        for mot in mots_en:
            if mot in notes_lower or mot in entreprise_lower:
                return Language.ENGLISH
        
        # Par défaut: Français (car Gradium est FR)
        return Language.FRENCH

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
Tu es Brahim Bouhadja, fondateur de Gradium (anciennement Wesh). Tu dois écrire un cold call VENDEUR et PERCUTANT pour {prospect.nom_complet}.

========================================
QUI EST GRADIUM ? (À UTILISER DANS LE SCRIPT)
========================================
Gradium est une startup française qui développe des Audio LLMs natifs. Notre techno:
- Des agents vocaux IA ultra-naturels avec latence quasi-nulle
- Capables de qualifier des leads 24/7 comme des humains
- 10x moins chers qu'une équipe de BDR
- Pas des voice bots basiques - de vrais LLM vocaux avec émotion et fluidité

EXEMPLE DE SCRIPT PERCUTANT (pour inspiration):
"C'est ton premier BDR qui ne dort jamais. Je suis le modèle Gradium v1. Je viens de qualifier 500 leads pendant que tu prenais ton café, et j'ai détecté 12 opportunités chaudes pour ton équipe.

J'ai coûté 4$ ce matin. Un humain t'aurait coûté 200$.

[Prénom], si je suis capable de te convaincre maintenant avec cette fluidité et cette latence nulle... imagine ce que je peux faire avec tes clients.

On me déploie quand sur ton CRM ?"

OU CE STYLE :
"Bonjour [Prénom],

Je vois que vous scalez massivement l'équipe Sales pour distribuer [produit].

Le problème des équipes BDR humaines, c'est qu'elles sont limitées par le nombre d'heures dans une journée. Le problème des Voice Bots actuels, c'est la latence et le manque d'émotion qui tuent la conversion.

Gradium est différent : Nous développons des Audio LLMs natifs. Résultat : des interactions vocales ultra-rapides, naturelles et expressives, capables de qualifier vos leads aussi bien que vos meilleurs humains, mais à l'échelle infinie.

Si vous cherchez à ce que votre 'Outbound' soit aussi intelligent que votre modèle, on devrait se parler."

========================================
INFORMATIONS DU PROSPECT (OBLIGATOIRE - UTILISER CES DÉTAILS)
========================================
- Nom : {prospect.nom_complet}
- Entreprise : {prospect.entreprise}
- Poste : {prospect.titre or 'Non spécifié'}
{notes_context}

========================================
TRIGGER
========================================
- Type : {trigger.type_trigger}
- Description : {trigger.description}

========================================
INSTRUCTIONS ABSOLUES
========================================

🎯 OBJECTIF : VENDRE Gradium. Pas être sympa. VENDRE. Le prospect doit sentir l'urgence et l'opportunité.

🌐 LANGUE : 100% EN {nom_langue.upper()} - INTERDICTION TOTALE DE MÉLANGER LES LANGUES

⚠️ RÈGLES :
1. Commence directement par l'accroche - pas de "Bonjour, comment allez-vous"
2. Utilise les NOTES NOTION ci-dessus pour personnaliser
3. Sois direct, percutant, presque provocateur mais professionnel
4. Mentionne Gradium comme la solution ultime à leur problème de scale
5. Crée de l'urgence : "Pendant qu'on parle, vos concurrents..."
6. Le ton doit être : confiant, expert, légèrement provocateur

🚫 INTERDICTIONS ABSOLUES :
- "I believe we can help you achieve better results" → NUL
- "With that kind of..." → NUL
- "Nous sommes une entreprise qui..." → NUL
- Parler de soi au lieu du prospect
- Mélanger français et anglais

✅ FORMAT DE SORTIE :
Un script FLUIDE, NATUREL, sans numéros de section. Juste du texte qui se lit comme une vraie conversation téléphonique percutante. Le script doit faire 45-60 secondes à l'oral.
"""

    def _parser_script(self, contenu: str, langue: Language) -> Script:
        """Parse la réponse de Kimi - Version simple et robuste."""
        import re
        
        contenu = contenu.strip()
        
        if not contenu:
            return Script(
                introduction="Hi, I'm calling about your company.",
                corps_message="I've noticed you're growing fast.",
                proposition_valeur="I can help you optimize your processes.",
                langue=langue
            )
        
        # Découper en blocs (séparés par ligne vide ou numéro de section)
        # Remplacer les numéros de section par des marqueurs
        contenu_clean = re.sub(r'\n?\s*(\d+)\.\s*', r'\n\nSECTION_\1\n\n', contenu)
        
        # Découper en paragraphes
        paragraphes = [p.strip() for p in contenu_clean.split('\n\n') if p.strip() and len(p.strip()) > 10]
        
        # Nettoyer les préfixes de section
        def nettoyer_bloc(texte):
            # Enlever les préfixes comme SECTION_1, INTRODUCTION, etc.
            texte = re.sub(r'^SECTION_\d+\s*', '', texte, flags=re.IGNORECASE)
            texte = re.sub(r'^(INTRODUCTION|CORPS|PROPOSITION|OBJECTION|CALL-TO-ACTION|CTA)[\s:]*', '', texte, flags=re.IGNORECASE)
            return texte.strip()
        
        # Assigner les paragraphes aux sections
        introduction = nettoyer_bloc(paragraphes[0]) if len(paragraphes) > 0 else ""
        corps_message = nettoyer_bloc(paragraphes[1]) if len(paragraphes) > 1 else ""
        proposition_valeur = nettoyer_bloc(paragraphes[2]) if len(paragraphes) > 2 else ""
        objection_text = nettoyer_bloc(paragraphes[3]) if len(paragraphes) > 3 else ""
        call_to_action = nettoyer_bloc(paragraphes[-1]) if len(paragraphes) > 4 else ""
        
        # Fallback si sections vides - prendre tout le contenu
        if not introduction:
            lines = contenu.split('\n')
            introduction = lines[0] if lines else ""
        
        # Valeurs par défaut si toujours vide
        if not introduction:
            introduction = "Hi, I'm calling about your company."
        if not corps_message:
            corps_message = "I've noticed some interesting developments at your company."
        if not proposition_valeur:
            proposition_valeur = "I believe we can help you achieve better results."
        if not call_to_action:
            # CTA dans la bonne langue
            if langue == Language.FRENCH:
                call_to_action = "Pouvons-nous convenir d'un appel de 15 minutes cette semaine ?"
            elif langue == Language.SPANISH:
                call_to_action = "¿Podemos programar una breve llamada esta semana?"
            elif langue == Language.GERMAN:
                call_to_action = "Können wir diese Woche einen kurzen Anruf vereinbaren?"
            elif langue == Language.ITALIAN:
                call_to_action = "Possiamo organizzare una breve chiamata questa settimana?"
            else:  # ENGLISH par défaut
                call_to_action = "Can we schedule a brief 15-minute call this week?"
        
        objection_handling = [objection_text] if objection_text else []
        
        return Script(
            introduction=introduction,
            corps_message=corps_message,
            proposition_valeur=proposition_valeur,
            objection_handling=objection_handling,
            call_to_action=call_to_action,
            langue=langue,
            duree_estimee=75
        )
