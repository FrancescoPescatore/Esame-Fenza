"""
Script di inizializzazione del database MongoDB per CineMatch.
Crea l'account di default e carica i dati di prova.
"""
import os
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from passlib.context import CryptContext
import random

# Configurazione
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
CSV_PATH = os.getenv("CSV_PATH", "/data/ratings.csv")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def process_letterboxd_csv(csv_path: str) -> dict:
    """Processa un CSV di Letterboxd e restituisce i dati strutturati."""
    df = pd.read_csv(csv_path)
    
    # Pulizia dati
    df = df.dropna(subset=['Rating'])
    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
    df = df.dropna(subset=['Rating'])
    
    # Prepara lista film
    movies = []
    for _, row in df.iterrows():
        movie = {
            "name": row['Name'],
            "year": int(row['Year']) if pd.notna(row.get('Year')) else None,
            "rating": int(row['Rating']),
            "date": str(row.get('Date', '')) if pd.notna(row.get('Date')) else None,
            "letterboxd_uri": row.get('Letterboxd URI', None),
            "processed_at": datetime.utcnow().isoformat()
        }
        movies.append(movie)
    
    # Calcola distribuzione rating
    rating_distribution = df['Rating'].value_counts().to_dict()
    rating_distribution = {int(k): int(v) for k, v in rating_distribution.items()}
    
    # Top rated movies
    top_rated = df[df['Rating'] >= 4].nlargest(10, 'Rating')[['Name', 'Year', 'Rating']].to_dict('records')
    
    # Film per anno
    if 'Year' in df.columns:
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        yearly_counts = df.groupby('Year').size().to_dict()
        yearly_data = [{"year": int(y), "count": int(c)} for y, c in sorted(yearly_counts.items()) if pd.notna(y)]
    else:
        yearly_data = []
    
    # Film per mese (se c'è la data)
    months = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    if 'Date' in df.columns:
        df['DateParsed'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Month'] = df['DateParsed'].dt.month
        monthly_counts = df.groupby('Month').size().to_dict()
        monthly_data = [{"month": months[i], "films": int(monthly_counts.get(i+1, 0))} for i in range(12)]
        
        recent = df.nlargest(10, 'DateParsed')[['Name', 'Year', 'Rating', 'Date']].to_dict('records')
    else:
        monthly_data = [{"month": m, "films": 0} for m in months]
        recent = df.head(10)[['Name', 'Year', 'Rating']].to_dict('records')
    
    # Generi (mock per ora - in futuro TMDB API)
    genre_colors = {
        "Drama": "#E50914", "Comedy": "#FF6B35", "Action": "#00529B",
        "Thriller": "#8B5CF6", "Sci-Fi": "#06B6D4", "Romance": "#EC4899",
        "Animation": "#10B981", "Horror": "#1F2937"
    }
    # Distribuzione realistica basata sui film
    total = len(movies)
    genre_data = []
    remaining = 100
    for i, (name, color) in enumerate(list(genre_colors.items())[:6]):
        if i == 5:
            value = remaining
        else:
            value = random.randint(10, min(35, remaining - (5-i)*5))
            remaining -= value
        genre_data.append({"name": name, "value": value, "color": color})
    
    # Statistiche complete
    stats = {
        "total_watched": len(movies),
        "avg_rating": round(float(df['Rating'].mean()), 2),
        "rating_distribution": rating_distribution,
        "top_rated_movies": top_rated,
        "recent_movies": recent,
        "monthly_data": monthly_data,
        "yearly_data": yearly_data,
        "genre_data": genre_data,
        "favorite_genre": "Drama",
        "total_5_stars": int(df[df['Rating'] == 5].shape[0]),
        "total_4_stars": int(df[df['Rating'] == 4].shape[0]),
        "total_3_stars": int(df[df['Rating'] == 3].shape[0]),
        "total_2_stars": int(df[df['Rating'] == 2].shape[0]),
        "total_1_stars": int(df[df['Rating'] == 1].shape[0]),
        "watch_time_hours": len(movies) * 2,  # Stima 2h per film
        "processed_at": datetime.utcnow().isoformat()
    }
    
    return {
        "movies": movies,
        "stats": stats,
        "raw_count": len(df)
    }

def init_database():
    """Inizializza il database con l'utente di default e i dati di prova."""
    print("🚀 Inizializzazione database CineMatch...")
    
    client = MongoClient(MONGO_URL)
    db = client.cinematch_db
    
    # ============================================
    # COLLEZIONE: users
    # ============================================
    users = db.users
    
    # Crea indici
    users.create_index("username", unique=True)
    users.create_index("email", unique=True, sparse=True)
    users.create_index("user_id", unique=True)
    
    # Dati utente di default
    default_user = {
        "username": "pasquale.langellotti",
        "email": "langellotti19@live.it",
        "password": get_password_hash("Pasquale19!"),
        "user_id": "pasquale.langellotti",
        "full_name": "Pasquale Langellotti",
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None,
        "is_active": True,
        "preferences": {
            "theme": "netflix",
            "language": "it",
            "notifications": True
        }
    }
    
    # Verifica se l'utente esiste già
    existing_user = users.find_one({"username": default_user["username"]})
    
    if existing_user:
        print(f"✅ Utente {default_user['username']} già esistente")
        user_id = existing_user["user_id"]
    else:
        users.insert_one(default_user)
        print(f"✅ Creato utente: {default_user['username']}")
        user_id = default_user["user_id"]
    
    # ============================================
    # COLLEZIONE: movies (film dell'utente)
    # ============================================
    movies_collection = db.movies
    movies_collection.create_index([("user_id", 1), ("name", 1)])
    movies_collection.create_index("user_id")
    
    # ============================================
    # COLLEZIONE: user_stats (statistiche processate)
    # ============================================
    stats_collection = db.user_stats
    stats_collection.create_index("user_id", unique=True)
    
    # ============================================
    # COLLEZIONE: sentiment_history
    # ============================================
    sentiment_collection = db.sentiment_history
    sentiment_collection.create_index("user_id")
    sentiment_collection.create_index([("user_id", 1), ("movie", 1)])
    
    # ============================================
    # COLLEZIONE: activity_log
    # ============================================
    activity_collection = db.activity_log
    activity_collection.create_index("user_id")
    activity_collection.create_index([("user_id", 1), ("timestamp", -1)])
    
    # ============================================
    # CARICA DATI CSV SE ESISTONO
    # ============================================
    if os.path.exists(CSV_PATH):
        print(f"📂 Trovato file CSV: {CSV_PATH}")
        
        # Verifica se i dati sono già stati processati
        existing_stats = stats_collection.find_one({"user_id": user_id})
        
        if existing_stats:
            print("✅ Dati già processati, skip del caricamento")
        else:
            print("🔄 Processing dati CSV...")
            processed = process_letterboxd_csv(CSV_PATH)
            
            # Salva i film
            for movie in processed["movies"]:
                movie["user_id"] = user_id
            
            # Elimina vecchi film dell'utente e inserisci i nuovi
            movies_collection.delete_many({"user_id": user_id})
            if processed["movies"]:
                movies_collection.insert_many(processed["movies"])
            
            # Salva le statistiche
            stats_doc = {
                "user_id": user_id,
                **processed["stats"],
                "source_file": os.path.basename(CSV_PATH)
            }
            stats_collection.update_one(
                {"user_id": user_id},
                {"$set": stats_doc},
                upsert=True
            )
            
            # Aggiorna riferimento nell'utente
            users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "has_data": True,
                    "data_processed_at": datetime.utcnow().isoformat(),
                    "movies_count": len(processed["movies"])
                }}
            )
            
            print(f"✅ Caricati {len(processed['movies'])} film")
            print(f"✅ Media rating: {processed['stats']['avg_rating']}")
    else:
        print(f"⚠️ File CSV non trovato: {CSV_PATH}")
    
    print("\n📊 Struttura Database:")
    print("=" * 50)
    for coll_name in db.list_collection_names():
        count = db[coll_name].count_documents({})
        print(f"  📁 {coll_name}: {count} documenti")
    
    print("\n✅ Inizializzazione completata!")
    return True

if __name__ == "__main__":
    init_database()
