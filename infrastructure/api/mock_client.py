"""
Client Mock pour tester le flow sans appeler d'API externe.
Retourne un script prédéfini pour les tests.
"""

from domain.models import Prospect, Trigger, Script, Language
from domain.ports import LLMProvider


class MockLLMClient(LLMProvider):
    """
    Adaptateur Mock pour tester l'application sans consommer de crédits API.
    Retourne toujours le même script de démo.
    """

    def __init__(self):
        """Initialise le client Mock."""
        print("🎭 Mode MOCK activé - Aucun appel API externe")

    def generer_script_cold_call(
        self,
        prospect: Prospect,
        trigger: Trigger,
        langue: Language,
        ton: str = "professionnel"
    ) -> Script:
        """
        Retourne un script mock pour les tests.
        
        Args:
            prospect: Informations sur le prospect (ignoré en mock)
            trigger: Événement déclencheur (ignoré en mock)
            langue: Langue souhaitée
            ton: Ton de la conversation (ignoré en mock)
            
        Returns:
            Script mock prédéfini
        """
        print(f"🎭 Génération MOCK pour {prospect.nom_complet} ({langue.value})")
        
        # Script mock selon la langue
        if langue == Language.FRENCH:
            contenu = f"""Bonjour {prospect.nom_complet.split()[0]},

Je suis l'Agent Gradium v1, votre premier BDR qui ne dort jamais.

Je viens de qualifier 500 leads pendant que vous preniez votre café, et j'ai détecté 12 opportunités chaudes pour votre équipe.

J'ai coûté 4€ ce matin. Un humain vous aurait coûté 200€.

Si je suis capable de vous convaincre maintenant avec cette fluidité et cette latence nulle... imaginez ce que je peux faire avec vos clients.

On me déploie quand sur votre CRM ?"""
        else:
            contenu = f"""Hi {prospect.nom_complet.split()[0]},

I'm Gradium Agent v1, your first BDR that never sleeps.

I just qualified 500 leads while you were having your morning coffee, and I identified 12 hot opportunities for your team.

I cost $4 this morning. A human would have cost you $200.

If I can convince you right now with this fluidity and zero latency... imagine what I can do with your customers.

When do we deploy me on your CRM?"""

        return Script(
            introduction="",
            corps_message=contenu,
            proposition_valeur="",
            langue=langue,
            duree_estimee=45
        )

    def detecter_langue_ideale(self, prospect: Prospect) -> Language:
        """
        Détecte la langue selon la colonne Notion ou défaut Français.
        
        Args:
            prospect: Informations du prospect
            
        Returns:
            Langue détectée (FR par défaut en mock)
        """
        # Priorité à la colonne Langue de Notion
        if prospect.langue:
            langue_notion = prospect.langue.upper().strip()
            if langue_notion in ['FR', 'FRENCH']:
                return Language.FRENCH
            elif langue_notion in ['UK', 'EN', 'ENGLISH', 'US']:
                return Language.ENGLISH
        
        return Language.FRENCH
