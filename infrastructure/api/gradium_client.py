"""
Client pour l'API Gradium.ai officielle (Text-to-Speech).
Implémente le port VoiceProvider défini dans le domaine.
Documentation: https://gradium.ai/api_docs.html

Endpoint: POST https://eu.api.gradium.ai/api/post/speech/tts
Format réponse: NDJSON (Newline Delimited JSON) streaming
"""

import os
from typing import Optional

import requests

from domain.models import AudioOutput, Language
from domain.ports import VoiceProvider
from infrastructure.config import obtenir_configuration


class GradiumClient(VoiceProvider):
    """
    Adaptateur pour l'API TTS officielle de Gradium.ai.
    Gère le format NDJSON streaming.
    
    Endpoint: POST /api/post/speech/tts
    """

    def __init__(
        self, 
        cle_api: Optional[str] = None,
        url_api: Optional[str] = None,
        timeout: int = 60
    ):
        """
        Initialise le client Gradium.ai.
        
        Args:
            cle_api: Clé API Gradium (gsk_...) - obligatoire
            url_api: URL de base de l'API
            timeout: Timeout des requêtes en secondes
        """
        config = obtenir_configuration()
        self.cle_api = cle_api or config.gradium_cle_api
        self.url_api = url_api or config.gradium_url_api or "https://eu.api.gradium.ai"
        self.timeout = timeout or config.gradium_timeout
        
        # Endpoint officiel Gradium
        self.endpoint_tts = "/api/post/speech/tts"
        
        # Validation
        if not self.cle_api:
            raise Exception(
                "❌ Clé API Gradium manquante.\n"
                "Obtenez-la sur: https://eu.api.gradium.ai/studio/platform/api-keys"
            )
        
        # Normalisation de l'URL
        if self.url_api and not self.url_api.startswith('https://'):
            self.url_api = f"https://{self.url_api}"
        self.url_api = self.url_api.rstrip('/')
        
        # Création du répertoire de sortie
        self.repertoire_sortie = config.repertoire_sortie_audio
        os.makedirs(self.repertoire_sortie, exist_ok=True)

    def synthetiser_voix(
        self,
        texte: str,
        langue: Language,
        voix: str = "default",
        vitesse: float = 1.0
    ) -> AudioOutput:
        """
        Convertit un texte en audio via l'API Gradium.ai (format NDJSON streaming).
        
        Args:
            texte: Texte à synthétiser
            langue: Langue du texte
            voix: Identifiant de la voix Gradium (ex: Brahim, Elise, Leo)
            vitesse: Vitesse de lecture (1.0 = normal)
            
        Returns:
            Objet AudioOutput contenant les données audio
        """
        import base64
        import json
        
        try:
            url = f"{self.url_api}{self.endpoint_tts}"
            
            # Construction de la payload
            voix_finale = voix if voix != "default" else self._get_voix_par_defaut(langue)
            payload = {
                "text": texte,
                "voice": voix_finale,
                "language": self._mapper_langue(langue),
                "speed": vitesse,
                "api_key": self.cle_api,
            }
            
            print(f"🔊 Appel API Gradium: {url}")
            print(f"   Voix: {voix_finale}, Langue: {payload['language']}")
            
            headers = {"Content-Type": "application/json"}
            
            # Envoi de la requête POST
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            # Traitement de la réponse NDJSON (Newline Delimited JSON)
            content_type = response.headers.get('Content-Type', '')
            print(f"   Content-Type: {content_type}")
            
            # Parser le NDJSON ligne par ligne
            audio_chunks = []
            lignes = response.text.strip().split('\n')
            
            print(f"   Réponse: {len(lignes)} ligne(s) NDJSON")
            
            for i, ligne in enumerate(lignes):
                ligne = ligne.strip()
                if not ligne:
                    continue
                
                try:
                    chunk = json.loads(ligne)
                    
                    # Type "audio": contient les données audio en base64
                    if chunk.get("type") == "audio" and "audio" in chunk:
                        audio_b64 = chunk["audio"]
                        audio_bytes = base64.b64decode(audio_b64)
                        audio_chunks.append(audio_bytes)
                    
                    # Type "text": métadonnées (optionnel, pour debug)
                    elif chunk.get("type") == "text":
                        text_chunk = chunk.get("text", "")
                        if i < 3:  # Afficher seulement les premiers chunks texte
                            print(f"   Chunk texte [{i}]: '{text_chunk}'")
                            
                except json.JSONDecodeError:
                    continue
            
            # Concaténer tous les chunks audio
            if not audio_chunks:
                raise Exception("Aucun chunk audio trouvé dans la réponse")
            
            pcm_data = b''.join(audio_chunks)
            
            # Fréquence d'échantillonnage Gradium (doc: https://gradium.ai/api_docs.html)
            # Sample Rate officiel: 48000 Hz (48kHz), 16-bit signed integer, mono
            sample_rate = 48000  # Hz - fréquence officielle Gradium
            
            nb_samples = len(pcm_data) // 2  # 2 bytes par sample (16-bit)
            duree_reelle = nb_samples / sample_rate
            
            print(f"✅ PCM: {len(pcm_data)} bytes, {nb_samples} samples")
            print(f"   Conversion WAV @ {sample_rate}Hz (~{duree_reelle:.1f}s)")
            
            # Convertir PCM → WAV
            contenu_audio = self._pcm_to_wav(pcm_data, sample_rate=sample_rate, channels=1, sample_width=2)
            
            # Estimation de la durée
            nombre_mots = len(texte.split())
            duree_estimee = (nombre_mots / 150) * 60 / vitesse
            
            return AudioOutput(
                contenu_audio=contenu_audio,
                format_fichier="wav",  # WAV car on convertit depuis PCM
                duree_secondes=round(duree_estimee, 2),
                langue=langue
            )
            
        except requests.exceptions.Timeout:
            raise Exception(f"Timeout Gradium après {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Connexion impossible à {self.url_api}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Erreur API Gradium: {self._parser_erreur(e)}")
        except Exception as e:
            raise Exception(f"Erreur Gradium: {str(e)}")

    def lister_voix_disponibles(self, langue: Language) -> list[dict]:
        """
        Liste les voix Gradium disponibles.
        🎙️ La voix Brahim est priorisée et peut parler TOUTES les langues.
        """
        voix_brahim_id = "cNKK8o0PXiqK6BZT"
        
        # 🎙️ VOIX BRAHIM - Ma voix clonée qui parle toutes les langues
        voix_gradium = [
            {"id": voix_brahim_id, "name": "⭐ Brahim - Ma Voix (FR)", "language": "fr", "gender": "male", "custom": True},
            {"id": voix_brahim_id, "name": "⭐ Brahim - Ma Voix (EN)", "language": "en", "gender": "male", "custom": True},
        ]
        
        # Voix standard de backup (si Brahim ne fonctionne pas)
        voix_standard = [
            {"id": "Elise", "name": "Elise - Français Féminin", "language": "fr", "gender": "female"},
            {"id": "Emma", "name": "Emma - Anglais US Féminin", "language": "en", "country": "us", "gender": "female"},
            {"id": "Kent", "name": "Kent - Anglais US Masculin", "language": "en", "country": "us", "gender": "male"},
        ]
        
        # Si une langue spécifique est demandée, filtrer
        if langue != Language.AUTO:
            code_langue = self._mapper_langue(langue)
            # Retourner Brahim pour cette langue + voix standards de backup
            voix_filtrees = [v for v in voix_gradium if v["language"] == code_langue]
            voix_filtrees += [v for v in voix_standard if v["language"] == code_langue]
            return voix_filtrees
        
        # Sinon retourner toutes les voix Brahim + standards
        return voix_gradium + voix_standard

    def _get_voix_par_defaut(self, langue: Language) -> str:
        """
        Retourne la voix par défaut.
        🎙️ TOUJOURS utiliser la voix Brahim (cNKK8o0PXiqK6BZT) 
        quelle que soit la langue - elle parle français, anglais, etc.
        """
        # ID exact de la voix Brahim clonée - utilisée pour TOUTES les langues
        return "cNKK8o0PXiqK6BZT"

    def _mapper_langue(self, langue: Language) -> str:
        """Mappe l'enum Language vers le code Gradium."""
        mapping = {
            Language.FRENCH: "fr",
            Language.ENGLISH: "en",
            Language.SPANISH: "es",
            Language.GERMAN: "de",
            Language.ITALIAN: "it",
            Language.AUTO: "auto"
        }
        return mapping.get(langue, "auto")

    def _pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
        """
        Convertit des données PCM brutes en fichier WAV valide.
        Gradium retourne du PCM 16-bit little-endian qu'il faut encapsuler dans un header WAV.
        
        Args:
            pcm_data: Données PCM brutes
            sample_rate: Fréquence d'échantillonnage (Hz)
            channels: Nombre de canaux (1=mono, 2=stereo)
            sample_width: Taille d'un échantillon en bytes (2=16-bit)
            
        Returns:
            Données WAV complètes avec header
        """
        import struct
        
        # Calculer les paramètres WAV
        num_samples = len(pcm_data) // sample_width
        byte_rate = sample_rate * channels * sample_width
        block_align = channels * sample_width
        data_size = len(pcm_data)
        
        # Construire le header WAV (44 bytes)
        header = struct.pack('<4sI4s4sIHHIIHH4sI',
            b'RIFF',                          # ChunkID
            36 + data_size,                   # ChunkSize (taille totale - 8)
            b'WAVE',                          # Format
            b'fmt ',                          # Subchunk1ID
            16,                               # Subchunk1Size (16 pour PCM)
            1,                                # AudioFormat (1 = PCM)
            channels,                         # NumChannels
            sample_rate,                      # SampleRate
            byte_rate,                        # ByteRate
            block_align,                      # BlockAlign
            sample_width * 8,                 # BitsPerSample
            b'data',                          # Subchunk2ID
            data_size                         # Subchunk2Size
        )
        
        return header + pcm_data

    def _parser_erreur(self, erreur) -> str:
        """Parse l'erreur HTTP."""
        try:
            response = erreur.response
            status = response.status_code
            
            try:
                data = response.json()
                msg = data.get("message") or data.get("error") or str(data)
            except:
                msg = response.text[:200] or "Erreur inconnue"
            
            codes = {
                401: "Clé API invalide",
                403: "Accès interdit",
                404: "Endpoint non trouvé",
                400: "Requête invalide",
                429: "Trop de requêtes",
                500: "Erreur serveur"
            }
            
            return f"{codes.get(status, f'HTTP {status}')} - {msg[:100]}"
            
        except:
            return str(erreur)
