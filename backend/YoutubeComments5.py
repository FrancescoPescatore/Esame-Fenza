# YoutubeComments5 - Orchestration layer for YouTube comments streaming
"""
YoutubeComments5 - Layer di orchestrazione per Kafka + Spark Structured Streaming
Questo layer gestisce il lifecycle dei processi di streaming.

Architecture:
- Ingestion: YoutubeProducer.py (Subprocess) → Kafka
- Processing: YoutubeSparkConsumer.py (Subprocess) → MongoDB
- Orchestration: This file (Spawns processes, reads from MongoDB)
"""
import re
import html
import subprocess
import sys
import os
import signal
import time
from typing import List, Dict, Optional
from pymongo import MongoClient
from datetime import datetime

# Import del modulo per il calcolo del sentiment
try:
    from YoutubeComments6 import process_pending_comments
    SENTIMENT_ENABLED = True
except ImportError:
    print("[YoutubeComments5] Modulo YoutubeComments6 non disponibile, sentiment disabilitato")
    SENTIMENT_ENABLED = False


# -----------------------------
# CONFIG
# -----------------------------
MAX_COMMENTS = 5
MIN_CHARS = 80
SPAM_KEYWORDS = ["subscribe"]

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DATABASE = "cinematch_db"
MONGODB_COLLECTION = "CommentiLive"

# Process Management
_producer_process: Optional[subprocess.Popen] = None
_consumer_process: Optional[subprocess.Popen] = None
_streaming_active = False
_current_trailer_url: Optional[str] = None


# -----------------------------
# UTILITY FUNCTIONS
# -----------------------------
def extract_video_id(youtube_url: str) -> str:
    """Estrae il video ID da un URL YouTube."""
    if "v=" in youtube_url:
        return youtube_url.split("v=")[-1].split("&")[0]
    return youtube_url


def clean_comment(text: str) -> str:
    """Pulisce il testo del commento."""
    text = html.unescape(text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\b\d{1,2}:\d{2}\b", "", text)
    text = re.sub(r"[^\w\s.,!?'\"]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_spam(text: str) -> bool:
    """Controlla se il commento è spam."""
    lower = text.lower()
    for k in SPAM_KEYWORDS:
        if k in lower: return True
    if text.count("http") > 0: return True
    if text.isupper(): return True
    words = text.split()
    if len(words) > 10 and len(set(words)) / len(words) < 0.4: return True
    return False


# -----------------------------
# MONGODB Helper
# -----------------------------
def get_mongodb_client():
    try:
        return MongoClient(MONGODB_URL)
    except Exception as e:
        print(f"[MongoDB] Errore connessione: {e}")
        return None


# -----------------------------
# PROCESS ORCHESTRATION
# -----------------------------
def start_live_comments_streaming(trailer_url: str) -> bool:
    """
    Avvia lo streaming spawnando i processi Producer e Consumer.
    
    Args:
        trailer_url: URL del trailer YouTube
        
    Returns:
        True se avviato con successo
    """
    global _producer_process, _consumer_process, _streaming_active, _current_trailer_url
    
    if not trailer_url:
        return False
        
    # Se già attivo per lo stesso URL, ignora
    if _streaming_active and _current_trailer_url == trailer_url:
        print(f"[YoutubeComments5] Streaming già attivo per {trailer_url}")
        return True
        
    # Se attivo per altro URL, ferma prima
    if _streaming_active:
        stop_live_comments_streaming()
        
    print(f"[YoutubeComments5] Avvio streaming per: {trailer_url}")
    
    try:
        # Percorsi degli script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        producer_script = os.path.join(base_dir, "YoutubeProducer.py")
        consumer_script = os.path.join(base_dir, "YoutubeSparkConsumer.py")
        
        # Environment per i sottoprocessi (eredita corrente)
        env = os.environ.copy()
        
        # -- 1. AVVIO PRODUCER --
        # Passiamo il VIDEO ID tramite variabile ambiente o argomento?
        # YoutubeProducer.py attualmente ha VIDEO_ID hardcoded nel main. 
        # Modifica necessaria: YoutubeProducer dovrebbe accettare argomenti. 
        # Per ora lo avviamo, ma nota che userà il video default se non modificato.
        # TODO: Aggiornare YoutubeProducer.py per leggere env var TARGET_VIDEO_ID
        env["TARGET_VIDEO_ID"] = extract_video_id(trailer_url)
        
        log_prod = open(os.path.join(base_dir, "producer.log"), "a")
        _producer_process = subprocess.Popen(
            [sys.executable, producer_script],
            env=env,
            stdout=log_prod,
            stderr=subprocess.STDOUT
        )
        print(f"[YoutubeComments5] Producer avviato (PID: {_producer_process.pid})")
        
        # -- 2. AVVIO CONSUMER (Spark) --
        log_cons = open(os.path.join(base_dir, "consumer.log"), "a")
        _consumer_process = subprocess.Popen(
            [sys.executable, consumer_script],
            env=env,
            stdout=log_cons,
            stderr=subprocess.STDOUT
        )
        print(f"[YoutubeComments5] Consumer avviato (PID: {_consumer_process.pid})")
        
        _streaming_active = True
        _current_trailer_url = trailer_url
        
        return True
        
    except Exception as e:
        print(f"[YoutubeComments5] Errore avvio processi: {e}")
        stop_live_comments_streaming()  # Cleanup
        return False


def stop_live_comments_streaming() -> None:
    """Ferma i processi di streaming."""
    global _producer_process, _consumer_process, _streaming_active, _current_trailer_url
    
    print("[YoutubeComments5] Arresto streaming...")
    
    # helper kill
    def kill_proc(proc):
        if proc:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                print(f"Errore kill processo: {e}")
                
    kill_proc(_producer_process)
    kill_proc(_consumer_process)
    
    _producer_process = None
    _consumer_process = None
    _streaming_active = False
    _current_trailer_url = None
    print("[YoutubeComments5] Streaming fermato")


def is_streaming_active() -> bool:
    return _streaming_active


# -----------------------------
# PUBLIC API (Lettura)
# -----------------------------
def get_live_comments() -> List[Dict]:
    try:
        client = get_mongodb_client()
        if not client: return []
        
        db = client[MONGODB_DATABASE]
        collection = db[MONGODB_COLLECTION]
        
        # Recupera ultimi commenti
        cursor = collection.find().sort("data_ora", -1).limit(MAX_COMMENTS)
        
        comments = []
        for doc in cursor:
            comments.append({
                "comment_id": doc.get("_id"),
                "author": doc.get("utente_commento", "Unknown"),
                "published_at": doc.get("data_ora", ""),
                "text": doc.get("commento", ""),
                "valore_sentiment": doc.get("valore_sentiment")
            })
        
        client.close()
        return comments
    except Exception as e:
        print(f"[YoutubeComments5] Errore get_live_comments: {e}")
        return []

def get_live_comment_at(index: int) -> Optional[Dict]:
    comments = get_live_comments()
    return comments[index] if 0 <= index < len(comments) else None

def get_live_comments_count() -> int:
    return len(get_live_comments())

def get_live_comments_for_trailer(trailer_url: str) -> Dict:
    """API entry point"""
    if not trailer_url:
        return {"status": "error", "message": "URL invalido", "comments": [], "active": False}
    
    # Auto-start streaming (Orchestration logic)
    if not _streaming_active or _current_trailer_url != trailer_url:
        start_live_comments_streaming(trailer_url)
    
    comments = get_live_comments()
    
    if SENTIMENT_ENABLED and comments:
        try:
            process_pending_comments()
        except: pass
        
    return {
        "status": "success",
        "comments": comments,
        "count": len(comments),
        "streaming_active": _streaming_active
    }
