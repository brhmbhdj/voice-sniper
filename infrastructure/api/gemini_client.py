"""
Client pour l'API Gemini (Google AI) avec découverte dynamique des modèles.
Implémente le port LLMProvider défini dans le domaine.
Utilise le pattern "Dynamic Discovery" pour éviter les erreurs 404.
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
    Implémente une découverte dynamique des modèles pour éviter les erreurs 404.
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
            "max_output_tokens": 2048,
        }

    def _get_model(self) -> genai.GenerativeModel:
        """
        Lazy loading du modèle Gemini avec découverte dynamique.
        Si le modèle n'est pas encore initialisé, tente de le découvrir automatiquement.
        
        Returns:
            Instance de GenerativeModel prête à l'emploi
            
        Raises:
            Exception: Si aucun modèle ne peut être trouvé
        """
        # Si déjà initialisé, retourne le modèle en cache
        if self._modele is not None:
            return self._modele
        
        print(f"🤖 Initialisation dynamique du modèle Gemini...")
        print(f"   Préférence utilisateur : {self.nom_modele_preference}")
        
        # Étape 1 : Essayer le modèle préféré (s'il est spécifié)
        if self.nom_modele_preference:
            try:
                print(f"   Tentative avec : {self.nom_modele_preference}")
                modele = genai.GenerativeModel(self.nom_modele_preference)
                # Test rapide pour vérifier que le modèle existe
                modele._model_id  # Accède à l'ID pour valider
                self._modele = modele
                self._nom_modele_effectif = self.nom_modele_preference
                print(f"✅ Modèle '{self._nom_modele_effectif}' chargé avec succès")
                return self._modele
            except Exception as erreur:
                print(f"   ⚠️  Échec avec '{self.nom_modele_preference}' : {str(erreur)[:100]}")
        
        # Étape 2 : Liste des noms à tester (ordre de préférence)
        candidats_a_tester = [
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-1.5-flash-001",
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro",
            "gemini-1.5-pro-001",
            "gemini-1.0-pro-latest",
            "gemini-1.0-pro",
            "gemini-pro",
        ]
        
        for nom_candidat in candidats_a_tester:
            if nom_candidat == self.nom_modele_preference:
                continue  # Déjà testé ci-dessus
            try:
                print(f"   Tentative avec : {nom_candidat}")
                modele = genai.GenerativeModel(nom_candidat)
                modele._model_id  # Validation
                self._modele = modele
                self._nom_modele_effectif = nom_candidat
                print(f"✅ Modèle '{self._nom_modele_effectif}' chargé avec succès")
                return self._modele
            except Exception:
                continue  # Essayer le suivant
        
        # Étape 3 : Découverte dynamique via l'API
        print(f"   🔍 Découverte dynamique via list_models()...")
        try:
            modele_trouve = self._decouvrir_modele_dynamiquement()
            if modele_trouve:
                self._modele = modele_trouve
                print(f"✅ Modèle découvert dynamiquement : '{self._nom_modele_effectif}'")
                return self._modele
        except Exception as erreur:
            print(f"   ❌ Échec de la découverte dynamique : {str(erreur)}")
        
        # Étape 4 : Échec complet
        raise Exception(
            "Impossible d'initialiser un modèle Gemini. "
            "Vérifiez votre clé API et les permissions du projet."
        )

    def _decouvrir_modele_dynamiquement(self) -> Optional[genai.GenerativeModel]:
        """
        Découvre automatiquement un modèle disponible via l'API Gemini.
        
        Stratégie de sélection :
        1. Prendre le premier modèle contenant "flash" (rapide et économique)
        2. Sinon prendre le premier contenant "pro" (plus puissant)
        3. Sinon prendre n'importe quel modèle Gemini disponible
        
        Returns:
            GenerativeModel initialisé ou None si échec
        """
        try:
            # Liste tous les modèles disponibles
            modeles_disponibles = list(genai.list_models())
            
            if not modeles_disponibles:
                raise Exception("Aucun modèle trouvé dans la liste")
            
            # Filtrer uniquement les modèles de génération (pas les embeddings)
            modeles_generatifs = [
                m for m in modeles_disponibles 
                if hasattr(m, 'name') and 'embed' not in m.name.lower()
            ]
            
            print(f"   📋 {len(modeles_generatifs)} modèle(s) génératif(s) trouvé(s)")
            
            # Affiche les modèles trouvés pour debug
            for m in modeles_generatifs[:5]:
                print(f"      - {m.name}")
            
            # Stratégie de sélection par priorité
            modele_choisi = None
            
            # Priorité 1 : Flash (rapide, économique)
            for m in modeles_generatifs:
                if 'flash' in m.name.lower():
                    modele_choisi = m.name
                    break
            
            # Priorité 2 : Pro (plus puissant)
            if not modele_choisi:
                for m in modeles_generatifs:
                    if 'pro' in m.name.lower():
                        modele_choisi = m.name
                        break
            
            # Priorité 3 : N'importe quel modèle Gemini
            if not modele_choisi and modeles_generatifs:
                modele_choisi = modeles_generatifs[0].name
            
            if modele_choisi:
                self._nom_modele_effectif = modele_choisi
                print(f"   🎯 Modèle sélectionné : {modele_choisi}")
                return genai.GenerativeModel(modele_choisi)
            
            return None
            
        except Exception as erreur:
            print(f"   Erreur lors de la découverte : {str(erreur)}")
            return None

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
            
            # Parsing de la réponse
            contenu_genere = reponse.text
            
            return self._parser_script(contenu_genere, langue)
            
        except Exception as erreur:
            raise Exception(
                f"Erreur lors de la génération du script avec Gemini : {str(erreur)}"
            )

    def detecter_langue_ideale(self, prospect: Prospect) -> Language:
        """
        Détecte la langue idéale pour contacter un prospect.
        Utilise Gemini pour analyser les indices (entreprise, secteur, notes)
        et déterminer la meilleure langue pour le cold call.
        
        Args:
            prospect: Informations du prospect
            
        Returns:
            Langue recommandée (FRENCH, ENGLISH, etc.)
        """
        try:
            modele = self._get_model()
            
            # Construction du contexte pour l'analyse
            contexte = f"""
            Analyse ce prospect et détermine la langue la plus appropriée pour un cold call professionnel.
            
            INFORMATIONS DU PROSPECT :
            - Nom : {prospect.nom_complet}
            - Entreprise : {prospect.entreprise}
            - Secteur : {prospect.secteur_activite or "Non spécifié"}
            """
            
            # Ajout des notes enrichies si disponibles
            if prospect.notes_enrichies and prospect.notes_enrichies.notes_brutes:
                contexte += f"\n- Notes : {prospect.notes_enrichies.notes_brutes[:500]}"
            
            contexte += """
            
            INSTRUCTIONS :
            Réponds UNIQUEMENT avec le code langue ISO à 2 lettres parmi :
            - "fr" pour français
            - "en" pour anglais  
            - "es" pour espagnol
            - "de" pour allemand
            - "it" pour italien
            
            Règles de décision :
            - Entreprise française ou nom français → "fr"
            - Entreprise internationale/tech/saas → "en" 
            - Entreprise allemande → "de"
            - Indices géographiques dans les notes
            - Langue des notes si rédigées en français/anglais
            
            Réponds uniquement avec le code (ex: "fr" ou "en").
            """
            
            reponse = modele.generate_content(
                contexte,
                generation_config={"temperature": 0.1, "max_output_tokens": 10}
            )
            
            # Extraction du code langue
            texte_reponse = reponse.text.strip().lower()
            
            # Mapping des codes vers l'enum
            mapping_langues = {
                "fr": Language.FRENCH,
                "en": Language.ENGLISH,
                "es": Language.SPANISH,
                "de": Language.GERMAN,
                "it": Language.ITALIAN
            }
            
            # Cherche le code dans la réponse
            for code, langue in mapping_langues.items():
                if code in texte_reponse:
                    return langue
            
            # Détection par défaut basée sur l'entreprise
            return self._detecter_langue_par_defaut(prospect)
            
        except Exception:
            # En cas d'erreur, utiliser la détection par défaut
            return self._detecter_langue_par_defaut(prospect)

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

🎯 OBJECTIF : Créer un script qui montre que tu as fait tes recherches sur le prospect et qui génère un RDV.

🌐 LANGUE : 100% DU SCRIPT DOIT ÊTRE EN {nom_langue.upper()} :
- Introduction en {nom_langue}
- Corps du message en {nom_langue}
- Proposition de valeur en {nom_langue}
- Call-to-action en {nom_langue}
- AUCUNE phrase dans une autre langue

⚠️ RÈGLES ABSOLUES :
1. Utilise IMPÉRATIVEMENT les informations des NOTES NOTION ci-dessus
2. Mentionne des éléments spécifiques trouvés dans les notes (Hyper-Recrutement, Pain Points, etc.)
3. Parle en {nom_langue} NATIF (pas de mots français si la langue est anglais)
4. Mentionne le prénom du prospect 2-3 fois
5. Sois conversationnel et direct
6. Signe-toi avec ton vrai nom : "{nom_vendeur}"

📋 STRUCTURE OBLIGATOIRE (60-90 secondes) :

SÉPARATION STRICTE ENTRE CHAQUE SECTION AVEC UNE LIGNE VIDE.

1. INTRODUCTION (10-15s)
   "Hi [Prénom], {nom_vendeur} here from Gradium..."
   → Accroche personnalisée avec contexte des notes
   → STOP - LIGNE VIDE OBLIGATOIRE APRÈS

2. CORPS DU MESSAGE (20-30s)
   → Relie le trigger à un problème concret mentionné dans les notes
   → Mentionne 1-2 détails spécifiques des notes
   → STOP - LIGNE VIDE OBLIGATOIRE APRÈS

3. PROPOSITION DE VALEUR (15-20s)
   → Évite "With that kind of..." ou phrases génériques
   → Donne une proposition CONCRÈTE et CHIFFRÉE si possible
   → Exemple : "We help companies like [Entreprise] reduce ramp-up time by 40% through automated signal detection..."
   → Explique COMMENT tu résous le problème
   → STOP - LIGNE VIDE OBLIGATOIRE APRÈS

4. GESTION D'OBJECTION (10-15s)
   → Réponse à "I'm busy / Not interested / Already have a solution"
   → STOP - LIGNE VIDE OBLIGATOIRE APRÈS

5. CALL-TO-ACTION (5-10s) STRICTEMENT EN {nom_langue.upper()}
   → Si ANGLAIS : "Can we schedule a brief 15-minute call this week?" ou "Are you available for a quick call?"
   → Si FRANÇAIS : "Pouvons-nous convenir d'un appel rapide cette semaine ?"
   → JAMAIS de mélange de langues dans le CTA

🚫 INTERDIT :
- Phrases génériques comme "With that kind of..."
- Mélanger les langues dans le script
- Parler de soi plus que du prospect
- Oublier de signer avec son nom
- Ne pas utiliser les notes fournies
- Oublier les lignes vides entre les sections

✅ FORMAT DE SORTIE EXACT :
1. [Texte introduction]

2. [Texte corps du message]

3. [Texte proposition de valeur]

4. [Texte gestion objection]

5. [Texte call-to-action EN {nom_langue.upper()}]
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


