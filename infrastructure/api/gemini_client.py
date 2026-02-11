"""
Client pour l'API Gemini (Google AI).
Implémente le port LLMProvider défini dans le domaine.
Le modèle est lu directement depuis GEMINI_MODELE dans le fichier .env.
"""

import re
from typing import Optional

import google.generativeai as genai

from domain.models import Prospect, Trigger, Script, Language
from domain.ports import LLMProvider
from infrastructure.config import obtenir_configuration


class GeminiClient(LLMProvider):
    """
    Adaptateur pour le modèle de langage Gemini de Google.
    Utilise le modèle spécifié dans GEMINI_MODELE (fichier .env).
    """

    def __init__(
        self,
        cle_api: Optional[str] = None,
        nom_modele: Optional[str] = None
    ):
        """
        Initialise le client Gemini avec configuration minimale.
        Le modèle n'est pas configuré ici (lazy loading).
        
        Args:
            cle_api: Clé API Gemini (si None, utilise la config)
            nom_modele: Nom du modèle préféré (si None, utilise la config)
        """
        config = obtenir_configuration()
        self.cle_api = cle_api or config.gemini_cle_api
        self.nom_modele_preference = nom_modele or config.gemini_modele
        
        # Configuration de l'API Gemini (sans modèle spécifique)
        genai.configure(api_key=self.cle_api)
        
        # Le modèle sera initialisé à la demande (lazy loading)
        self._modele: Optional[genai.GenerativeModel] = None
        self._nom_modele_effectif: Optional[str] = None
        
        # Configuration de la génération (indépendante du modèle)
        self.config_generation = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,  
        }

    def _get_model(self) -> genai.GenerativeModel:
        """
        Initialise le modèle Gemini depuis la config (.env).
        Utilise directement GEMINI_MODELE sans fallback.
        
        Returns:
            Instance de GenerativeModel prête à l'emploi
        """
        # Si déjà initialisé, retourne le modèle en cache
        if self._modele is not None:
            return self._modele
        
        # Recharger la config à chaque fois pour prendre en compte les modifications du .env
        from infrastructure.config import obtenir_configuration
        config = obtenir_configuration()
        nom_modele = self.nom_modele_preference or config.gemini_modele
        
        print(f"🤖 Modèle Gemini (depuis .env): {nom_modele}")
        
        try:
            modele = genai.GenerativeModel(nom_modele)
            self._modele = modele
            self._nom_modele_effectif = nom_modele
            print(f"✅ Modèle chargé: {nom_modele}")
            return self._modele
        except Exception as erreur:
            raise Exception(
                f"❌ Impossible de charger le modèle '{nom_modele}'.\n"
                f"Erreur: {str(erreur)[:200]}\n"
                f"Vérifiez GEMINI_MODELE dans votre fichier .env"
            )

    def generer_script_cold_call(
        self,
        prospect: Prospect,
        trigger: Trigger,
        langue: Language,
        ton: str = "professionnel"
    ) -> Script:
        """
        Génère un script de cold call personnalisé avec Gemini.
        
        Args:
            prospect: Informations sur le prospect
            trigger: Événement déclencheur
            langue: Langue souhaitée pour le script
            ton: Ton de la conversation
            
        Returns:
            Script complet généré par l'IA
            
        Raises:
            Exception: Si la génération échoue
        """
        try:
            # Récupération du modèle (avec lazy loading et découverte dynamique)
            modele = self._get_model()
            
            # Construction du prompt
            prompt = self._construire_prompt(prospect, trigger, langue, ton)
            
            print(f"📝 Génération du script avec {self._nom_modele_effectif}...")
            
            # Génération avec Gemini
            reponse = modele.generate_content(
                prompt,
                generation_config=self.config_generation
            )
            
            # Retourner le texte brut sans parsing
            contenu_genere = reponse.text.strip()
            
            # Si le contenu est vide, retourner un script par défaut
            if not contenu_genere:
                return Script(
                    introduction="",
                    corps_message="Script non généré. Veuillez réessayer.",
                    proposition_valeur="",
                    langue=langue
                )
            
            # Retourner tout le texte dans corps_message, sans parsing
            return Script(
                introduction="",
                corps_message=contenu_genere,
                proposition_valeur="",
                langue=langue,
                duree_estimee=60
            )
            
        except Exception as erreur:
            erreur_str = str(erreur)
            # Détection du quota dépassé (erreur 429)
            if "429" in erreur_str or "quota" in erreur_str.lower() or "exceeded" in erreur_str.lower():
                config = obtenir_configuration()
                modele_actuel = config.gemini_modele
                raise Exception(
                    f"🚫 Quota Gemini dépassé !\n\n"
                    f"Le modèle '{modele_actuel}' a atteint sa limite quotidienne.\n"
                    f"Les quotas gratuits se réinitialisent chaque jour.\n\n"
                    f"💡 Solutions :\n"
                    f"• Modifiez GEMINI_MODELE dans .env (ex: gemini-1.5-flash-latest)\n"
                    f"• Passez à Kimi (LLM_PROVIDER=kimi)\n"
                    f"• Réessayez demain (quotas réinitialisés à minuit UTC)"
                )
            raise Exception(
                f"Erreur lors de la génération du script avec Gemini : {erreur_str}"
            )

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
        prenoms_fr = ['marie', 'jean', 'pierre', 'constance', 'marine', 'sophie', 'julien', 'thomas', 'nicolas', 'alexandre', 'brahim']
        for prenom in prenoms_fr:
            if prenom in nom_lower:
                return Language.FRENCH
        
        # Indices dans les notes
        mots_fr = ['france', 'paris', 'lyon', 'marseille', 'euros', 'levee', 'fonds', 'startup francaise', 'francaise']
        for mot in mots_fr:
            if mot in notes_lower or mot in entreprise_lower:
                return Language.FRENCH
        
        # Mots anglais
        mots_en = ['inc', 'llc', 'corp', 'ltd', 'uk', 'usa', 'america', 'london', 'new york', 'san francisco']
        for mot in mots_en:
            if mot in notes_lower or mot in entreprise_lower:
                return Language.ENGLISH
        
        # Par défaut: Français (car Gradium est FR)
        return Language.FRENCH

    def _detecter_langue_par_defaut(self, prospect: Prospect) -> Language:
        """
        Détection de langue par défaut basée sur des règles simples.
        
        Args:
            prospect: Prospect à analyser
            
        Returns:
            Langue détectée
        """
        entreprise_lower = prospect.entreprise.lower()
        nom_lower = prospect.nom_complet.lower()
        
        # Mots-clés français
        mots_fr = ["sas", "france", "paris", "lyon", "marseille", "bordeaux", "lille", 
                   "toulouse", "nantes", "strasbourg", "fr", "français"]
        
        # Mots-clés internationaux (anglais probable)
        mots_intl = ["inc", "corp", "llc", "ltd", "gmbh", "ag", "bv", "sl", "global", 
                     "international", "ai", "tech", "labs", "io", "app", "cloud"]
        
        # Mots-clés allemands
        mots_de = ["gmbh", "ag", "kg", "germany", "deutschland", "berlin", "munich"]
        
        # Vérification
        for mot in mots_fr:
            if mot in entreprise_lower or mot in nom_lower:
                return Language.FRENCH
        
        for mot in mots_de:
            if mot in entreprise_lower or mot in nom_lower:
                return Language.GERMAN
                
        for mot in mots_intl:
            if mot in entreprise_lower or mot in nom_lower:
                return Language.ENGLISH
        
        # Par défaut : anglais pour le B2B international
        return Language.ENGLISH

    def _construire_prompt(
        self,
        prospect: Prospect,
        trigger: Trigger,
        langue: Language,
        ton: str
    ) -> str:
        """
        Construit le prompt pour la génération du script.
        Utilise les notes enrichies si disponibles pour ultra-personnalisation.
        
        Args:
            prospect: Informations du prospect
            trigger: Événement déclencheur
            langue: Langue souhaitée
            ton: Ton du script
            
        Returns:
            Prompt formaté pour Gemini
        """
        # Récupération du nom du vendeur depuis la config
        from infrastructure.config import obtenir_configuration
        config = obtenir_configuration()
        nom_vendeur = config.utilisateur_nom
        
        # Mapping des langues pour le prompt
        langues_texte = {
            Language.FRENCH: "français",
            Language.ENGLISH: "anglais",
            Language.SPANISH: "espagnol",
            Language.GERMAN: "allemand",
            Language.ITALIAN: "italien"
        }
        
        nom_langue = langues_texte.get(langue, "français")
        
        # Toutes les informations du prospect depuis Notion
        titre_info = f"Titre/Poste : {prospect.titre}" if prospect.titre else ""
        taille_info = f"Taille entreprise : {prospect.taille}" if prospect.taille else ""
        statut_info = f"Statut pipeline : {prospect.statut}" if prospect.statut else ""
        secteur_info = f"Secteur : {prospect.secteur_activite}" if prospect.secteur_activite else ""
        
        # Construction du contexte enrichi depuis les notes Notion
        contexte_enrichi = ""
        if prospect.notes_enrichies:
            notes = prospect.notes_enrichies
            
            # LES NOTES BRUTES SONT LE PLUS IMPORTANT
            if notes.notes_brutes:
                contexte_enrichi += f"\n📝 NOTES BRUTES DU PROSPECT (à utiliser obligatoirement) :\n{notes.notes_brutes}\n"
            
            if notes.situation_actuelle:
                contexte_enrichi += f"\n📊 SITUATION ACTUELLE :\n{notes.situation_actuelle}\n"
            
            if notes.pain_points:
                contexte_enrichi += "\n🎯 PAIN POINTS IDENTIFIÉS :\n"
                for i, pain in enumerate(notes.pain_points, 1):
                    contexte_enrichi += f"{i}. {pain}\n"
            
            if notes.value_proposition:
                contexte_enrichi += f"\n💎 ANGLES DE VALEUR :\n{notes.value_proposition}\n"
        
        # Contexte des notes - UTILISATION OBLIGATOIRE
        notes_context = ""
        if prospect.notes_enrichies and prospect.notes_enrichies.notes_brutes:
            notes = prospect.notes_enrichies.notes_brutes[:3000]  # Limite pour éviter de dépasser les tokens
            notes_context = f"""
🚨 CONTEXTE OBLIGATOIRE - NOTES NOTION DU PROSPECT :
{notes}
🚨 FIN DES NOTES - TU DOIS UTILISER CE CONTEXTE DANS LE SCRIPT
"""
        
        prompt = f"""
Tu es Brahim Bouhadja, sales chez Gradium. Tu dois écrire un cold call VENDEUR et PERCUTANT pour {prospect.nom_complet}.

========================================
QUI EST GRADIUM ? (À UTILISER DANS LE SCRIPT)
========================================
Gradium est une startup française qui développe des Audio LLMs natifs. Notre techno:
- Des agents vocaux IA ultra-naturels avec latence quasi-nulle
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

⏱️ DURÉE MAXIMALE : 1 MINUTE (60 secondes) - Pas plus long. Un cold call efficace est court et percutant.

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
- Utiliser un ton trop formel ou trop familier - Trouve le juste milieu percutant
- Utiliser des phrases génériques sans personnalisation
- Faire un script trop long ou trop court - vise 50-60 secondes
- commencer par "(Le téléphone sonne, Constance décroche)"

✅ FORMAT DE SORTIE :
Un script FLUIDE, NATUREL, sans numéros de section. Juste du texte qui se lit comme une vraie conversation téléphonique percutante. Le script doit faire 45-60 secondes à l'oral.
"""
        
        return prompt

    def _parser_script(self, contenu: str, langue: Language) -> Script:
        """Parse la réponse de Gemini - Version simple et robuste."""
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


