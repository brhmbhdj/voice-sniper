# Transition Gemini → Kimi (Moonshot AI)

## Contexte

Le projet Voice Sniper supporte maintenant deux providers LLM :
- **Gemini** (Google) - Par défaut
- **Kimi** (Moonshot AI) - Alternative

Cette dualité permet de basculer facilement en cas de quota dépassé sur l'un ou l'autre service.

---

## Configuration

### 1. Variables d'environnement (.env)

```bash
# Choix du provider (gemini ou kimi)
LLM_PROVIDER=kimi

# Configuration Kimi
KIMI_CLE_API=sk-votre_cle_api_ici
KIMI_MODELE=moonshot-v1-8k

# Configuration Gemini (utilisée si LLM_PROVIDER=gemini)
GEMINI_CLE_API=votre_cle_api_gemini_ici
GEMINI_MODELE=gemini-1.5-flash-latest
```

### 2. Obtenir une clé API Kimi

1. Se rendre sur https://platform.moonshot.cn/
2. Créer un compte
3. Générer une clé API dans la console

### 3. Modèles disponibles

| Modèle | Contexte | Use Case |
|--------|----------|----------|
| `moonshot-v1-8k` | 8K tokens | Scripts courts, réponses rapides |
| `moonshot-v1-32k` | 32K tokens | Scripts longs, contexte étendu |
| `moonshot-v1-128k` | 128K tokens | Analyse approfondie |

---

## Architecture

### Ports (Domaine)

```python
class LLMProvider(ABC):
    @abstractmethod
    def generer_script_cold_call(...) -> Script: ...
    
    @abstractmethod  
    def detecter_langue_ideale(...) -> Language: ...
```

### Adapters (Infrastructure)

| Provider | Fichier | Implémente |
|----------|---------|------------|
| Gemini | `infrastructure/api/gemini_client.py` | LLMProvider |
| Kimi | `infrastructure/api/kimi_client.py` | LLMProvider |

### Factory (Interface)

```python
# Dans interface/streamlit_app.py
if config.llm_provider.lower() == "kimi":
    llm_client = KimiClient()
else:
    llm_client = GeminiClient()
```

---

## Différences d'implémentation

### Gemini
- SDK Python officiel : `google-generativeai`
- Gestion native du streaming
- Authentification via API key

### Kimi
- API compatible OpenAI
- HTTP direct via `requests`
- Endpoint : `https://api.moonshot.cn/v1/chat/completions`
- Format de réponse identique à OpenAI

---

## Migration

Pour migrer de Gemini vers Kimi :

1. **Ajouter la clé** dans `.env` :
   ```bash
   KIMI_CLE_API=sk-votre_cle
   ```

2. **Changer le provider** :
   ```bash
   LLM_PROVIDER=kimi
   ```

3. **Relancer l'application** :
   ```bash
   streamlit run interface/streamlit_app.py
   ```

---

## Dépannage

### Erreur 429 (Quota dépassé)
```
❌ Erreur API: 429 - You exceeded your current quota
```
**Solution** : Basculez vers l'autre provider en changeant `LLM_PROVIDER`.

### Erreur 401 (Clé invalide)
```
❌ Erreur API: 401 - Unauthorized
```
**Solution** : Vérifiez que la clé API correspond au provider sélectionné.

### Timeout
```
❌ Timeout lors de la génération
```
**Solution** : Augmentez `GRADIUM_TIMEOUT` ou utilisez un modèle plus rapide.

---

## Tests

Pour tester le client Kimi sans lancer l'UI :

```python
from infrastructure.api.kimi_client import KimiClient
from domain.models import Prospect, Trigger, Language

client = KimiClient()
prospect = Prospect(nom_complet="Test", entreprise="Corp")
trigger = Trigger(type_trigger="Test", description="Desc")

# Test détection langue
langue = client.detecter_langue_ideale(prospect)

# Test génération script
script = client.generer_script_cold_call(prospect, trigger, Language.FRENCH)
```

---

## Ressources

- [Documentation Kimi](https://platform.moonshot.cn/docs)
- [Documentation Gemini](https://ai.google.dev/)
- [API Gradium](https://eu.api.gradium.ai/api_docs.html)
