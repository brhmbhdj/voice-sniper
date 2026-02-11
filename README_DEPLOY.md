# 🎯 Voice Sniper - Déploiement

## Sécurité importante

**NE JAMAIS** pousser le fichier `.env` sur GitHub !

Le fichier `.gitignore` protège déjà vos secrets.

## Déploiement sur Streamlit Cloud (Gratuit)

### 1. Créer le repo GitHub (sans secrets)

```bash
# Seulement les fichiers code (pas .env)
git init
git add .
git commit -m "Voice Sniper v1.0"
git branch -M main
git remote add origin https://github.com/VOTRE_USERNAME/voice-sniper.git
git push -u origin main
```

### 2. Déployer sur Streamlit Cloud

1. Allez sur https://streamlit.io/cloud
2. Connectez avec GitHub
3. **New app** → Sélectionnez `voice-sniper`
4. Fichier principal : `interface/streamlit_app.py`
5. Cliquez **Deploy**

### 3. Ajouter les secrets (étape cruciale)

Dans l'interface Streamlit Cloud :
- Allez dans **Settings** → **Secrets**
- Collez vos variables d'environnement :

```toml
[secrets]
NOTION_CLE_API = "votre_cle_notion"
NOTION_DATABASE_ID = "votre_database_id"
KIMI_CLE_API = "votre_cle_kimi"
GRADIUM_CLE_API = "votre_cle_gradium"
PASSWORD_APP = "mot_de_presse_pour_constance"  # Optionnel
```

### 4. Redémarrer l'app

L'app est maintenant accessible publiquement avec vos secrets protégés !

## Protection contre la surconsommation

### Option 1 : Mot de passe (recommandé)
Ajoutez dans les secrets Streamlit :
```toml
PASSWORD_APP = "demo2024"
```

### Option 2 : Limiter les appels API
Les clés API restent sur VOTRE compte Streamlit Cloud.
Constance peut tester mais ne consomme pas vos crédits.

## URL à partager

Une fois déployé : `https://voice-sniper-xxx.streamlit.app`
# Wed Feb 11 02:50:47 CET 2026
