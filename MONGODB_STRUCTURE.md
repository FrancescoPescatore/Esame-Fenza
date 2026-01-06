# 📊 Struttura Database MongoDB - CineMatch

## Database: `cinematch_db`

---

## 📁 Collections

### 1. `users` - Utenti del sistema

```javascript
{
  "_id": ObjectId,
  "username": "pasquale.langellotti",      // Unique, usato per login
  "email": "langellotti19@live.it",        // Unique, opzionale
  "password": "$2b$12$...",                // Hash bcrypt
  "user_id": "pasquale.langellotti",       // Unique, usato come riferimento
  "full_name": "Pasquale Langellotti",     // Nome completo
  "created_at": "2026-01-06T15:30:00Z",    // ISO timestamp
  "last_login": "2026-01-06T16:45:00Z",    // Ultimo accesso
  "is_active": true,                        // Account attivo
  "has_data": true,                         // Ha caricato dati
  "movies_count": 116,                      // Numero film caricati
  "data_updated_at": "2026-01-06T15:35:00Z" // Ultimo aggiornamento dati
}
```

**Indici:**
- `username` (unique)
- `email` (unique, sparse)
- `user_id` (unique)

---

### 2. `movies` - Film degli utenti

```javascript
{
  "_id": ObjectId,
  "user_id": "pasquale.langellotti",       // Riferimento all'utente
  "name": "The Devil Wears Prada",          // Titolo del film
  "year": 2006,                             // Anno di uscita
  "rating": 5,                              // Rating utente (1-5)
  "date": "2025-12-05",                     // Data di visione
  "letterboxd_uri": "https://boxd.it/2awE", // Link Letterboxd
  "added_at": "2026-01-06T15:35:00Z"        // Quando è stato aggiunto
}
```

**Indici:**
- `user_id`
- `[user_id, name]` (compound)

---

### 3. `user_stats` - Statistiche processate

```javascript
{
  "_id": ObjectId,
  "user_id": "pasquale.langellotti",
  "total_watched": 116,                     // Film totali
  "avg_rating": 3.68,                       // Media rating
  "rating_distribution": {                   // Distribuzione per stelle
    "1": 2,
    "2": 5,
    "3": 35,
    "4": 40,
    "5": 34
  },
  "top_rated_movies": [                     // Top 10 film (4-5 stelle)
    {"Name": "The Devil Wears Prada", "Year": 2006, "Rating": 5},
    {"Name": "Anyone But You", "Year": 2023, "Rating": 5},
    // ...
  ],
  "recent_movies": [                        // Ultimi 10 film visti
    {"Name": "Zootopia", "Year": 2016, "Rating": 4, "Date": "2025-12-05"},
    // ...
  ],
  "monthly_data": [                         // Film per mese
    {"month": "Gen", "films": 0},
    {"month": "Feb", "films": 0},
    // ... tutti i mesi
    {"month": "Dic", "films": 116}          // Tutti a dicembre nel CSV
  ],
  "genre_data": [                           // Distribuzione generi
    {"name": "Drama", "value": 28, "color": "#E50914"},
    {"name": "Comedy", "value": 22, "color": "#FF6B35"},
    {"name": "Action", "value": 18, "color": "#00529B"},
    {"name": "Thriller", "value": 15, "color": "#8B5CF6"},
    {"name": "Sci-Fi", "value": 10, "color": "#06B6D4"},
    {"name": "Romance", "value": 7, "color": "#EC4899"}
  ],
  "favorite_genre": "Drama",
  "total_5_stars": 34,
  "total_4_stars": 40,
  "total_3_stars": 35,
  "total_2_stars": 5,
  "total_1_stars": 2,
  "watch_time_hours": 232,                  // Stima (film * 2h)
  "source_file": "ratings.csv",
  "updated_at": "2026-01-06T15:35:00Z"
}
```

**Indici:**
- `user_id` (unique)

---

### 4. `sentiment_history` - Cronologia analisi sentiment

```javascript
{
  "_id": ObjectId,
  "user_id": "pasquale.langellotti",
  "movie": "Inception",                     // Film analizzato
  "sentiment_score": 0.78,                  // Score 0-1
  "sentiment_label": "positive",            // positive/neutral/negative
  "comments_analyzed": 5,                   // Numero commenti analizzati
  "timestamp": "2026-01-06T16:00:00Z"
}
```

**Indici:**
- `user_id`
- `[user_id, movie]` (compound)
- `[user_id, timestamp]` (compound, descending)

---

### 5. `activity_log` - Log attività utente

```javascript
{
  "_id": ObjectId,
  "user_id": "pasquale.langellotti",
  "action": "search",                       // Tipo azione
  "details": {                              // Dettagli specifici
    "query": "Inception",
    "results": 5
  },
  "timestamp": "2026-01-06T16:05:00Z"
}
```

**Indici:**
- `user_id`
- `[user_id, timestamp]` (compound, descending)

---

## 🔗 Relazioni tra Collections

```
users (1) ──────┬────── (N) movies
               │
               ├────── (1) user_stats
               │
               ├────── (N) sentiment_history
               │
               └────── (N) activity_log
```

---

## 👤 Account Pre-configurato

| Campo | Valore |
|-------|--------|
| Username | `pasquale.langellotti` |
| Email | `langellotti19@live.it` |
| Password | `Pasquale19!` |
| Full Name | Pasquale Langellotti |
| Film Caricati | 114 |
| Rating Medio | 3.38 |

---

## 📂 Dati Caricati

- **File sorgente**: `Dati-prova-letterbox/ratings.csv`
- **Film totali**: 114
- **Formato**: Export Letterboxd standard
- **Colonne**: Date, Name, Year, Letterboxd URI, Rating

### Statistiche Processate:
- ⭐ 5 stelle: 20 film
- ⭐ 4 stelle: 34 film  
- ⭐ 3 stelle: 25 film
- ⭐ 2 stelle: 16 film
- ⭐ 1 stella: 7 film
- ⏱️ Ore stimate: 228h

---

## 🔧 Comandi MongoDB Utili

```bash
# Connetti al database
docker exec -it cinematch_db mongosh

# Seleziona database
use cinematch_db

# Visualizza collections
show collections

# Conta utenti
db.users.countDocuments()

# Visualizza utente
db.users.findOne({username: "pasquale.langellotti"}, {password: 0})

# Visualizza statistiche
db.user_stats.findOne({user_id: "pasquale.langellotti"})

# Conta film utente
db.movies.countDocuments({user_id: "pasquale.langellotti"})

# Top 5 film per rating
db.movies.find({user_id: "pasquale.langellotti"}).sort({rating: -1}).limit(5)
```

---

## 🚀 Flusso Dati

1. **Registrazione**: Utente si registra → documento in `users`
2. **Upload CSV**: File caricato → 
   - Film salvati in `movies`
   - Statistiche calcolate e salvate in `user_stats`
   - `users.has_data` = true
3. **Analisi Sentiment**: Risultato → `sentiment_history`
4. **Navigazione**: Azioni loggati → `activity_log`

---

## ⚡ Auto-inizializzazione

Al primo avvio del backend:
1. Crea indici su tutte le collections
2. Crea utente `pasquale.langellotti` se non esiste
3. Se `/data/ratings.csv` esiste e l'utente non ha dati:
   - Processa il CSV
   - Salva film in `movies`
   - Calcola e salva statistiche in `user_stats`
   - Aggiorna `users.has_data = true`
