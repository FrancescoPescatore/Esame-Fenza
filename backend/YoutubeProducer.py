from googleapiclient.discovery import build
from kafka import KafkaProducer
import json
import time
import re
import html
import os

YOUTUBE_API_KEY = "AIzaSyCWgR9xeE3H2arlD_M8twh82WJ8cc2g6WQ"
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:29092")
TOPIC = "youtube-comments"
POLLING_INTERVAL = 30

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def clean_comment(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def fetch_comments(video_id: str):
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=20,
            order="time",
            textFormat="plainText"
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            yield {
                "comment_id": item["id"],
                "author": snippet["authorDisplayName"],
                "text": clean_comment(snippet["textDisplay"]),
                "published_at": snippet["publishedAt"]
            }
    except Exception as e:
        print(f"[Producer] Errore API YouTube: {e}")

if __name__ == "__main__":
    # Legge l'ID video da variabile ambiente (impostata da YoutubeComments5.py)
    # Default: Rick Roll
    VIDEO_ID = os.getenv("TARGET_VIDEO_ID", "dQw4w9WgXcQ")
    
    print(f"[Producer] Avvio polling per video ID: {VIDEO_ID}")
    print(f"[Producer] Kafka Broker: {KAFKA_BROKER}")

    while True:
        try:
            count = 0
            for comment in fetch_comments(VIDEO_ID):
                producer.send(TOPIC, comment)
                count += 1
            print(f"[Producer] Ciclo completato: inviati {count} commenti.")
        except Exception as e:
            print(f"[Producer] Loop error: {e}")
            
        time.sleep(POLLING_INTERVAL)
