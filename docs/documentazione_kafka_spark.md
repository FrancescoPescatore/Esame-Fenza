# Documentazione Kafka Producer e Spark Stats Processor

## Indice
1. [kafka_producer.py - Funzioni](#kafka_producerpy---funzioni)
2. [spark_stats_processor.py - Funzioni](#spark_stats_processorpy---funzioni)
3. [Funzionamento Spark: Creazione user_stats e user_affinities](#funzionamento-spark-creazione-user_stats-e-user_affinities)

---

## kafka_producer.py - Funzioni

| Funzione | Descrizione |
|----------|-------------|
| `MovieEventProducer.__init__()` | Inizializza il producer con configurazione Kafka (server bootstrap, stato connessione). |
| `MovieEventProducer._get_producer()` | **Lazy initialization** del producer Kafka con retry automatico. Configura serializzazione JSON, acknowledgment `acks='all'`, retry e timeout. Restituisce `None` se Kafka non è disponibile. |
| `MovieEventProducer.send_movie_event(event_type, user_id, movie_data)` | Pubblica un singolo evento film su Kafka. Costruisce il payload con `event_type` (ADD/UPDATE/DELETE), dati del film (nome, anno, rating, generi, attori, regista, durata, data visione) e timestamp. Chiave di partizionamento: `user_id`. Restituisce `True` se pubblicato con successo. |
| `MovieEventProducer.send_batch_event(event_type, user_id, movies)` | Pubblica **più eventi** (uno per ogni film nel batch) nel formato identico a `send_movie_event()`. Usato per import massivi o ricalcoli. Esegue `flush()` alla fine per garantire la consegna. |
| `MovieEventProducer.flush()` | Forza l'invio immediato di tutti i messaggi in coda al broker Kafka. |
| `MovieEventProducer.close()` | Chiude la connessione al producer e rilascia le risorse. |
| `get_kafka_producer()` | Restituisce l'istanza **singleton** del `MovieEventProducer`. Garantisce un'unica connessione Kafka per tutta l'applicazione. |

---

## spark_stats_processor.py - Funzioni

| Funzione | Descrizione |
|----------|-------------|
| `normalize_title(text)` | Normalizza un titolo film: rimuove accenti, caratteri speciali, converte in minuscolo. Usato per matching fuzzy tra titoli italiani e originali. |
| `create_spark_session()` | Crea la `SparkSession` configurata con connettori Kafka e MongoDB, checkpoint location e URI di connessione. |
| `process_partition_incremental(iterator)` | **(V6 - PRINCIPALE)** Processa una partizione di eventi in modo **incrementale O(1)**. Aggrega in memoria e scrive con `bulk_write()` su `user_stats` (metriche globali) e `user_affinities` (registi, attori, generi). Gestisce ADD, DELETE e UPDATE_RATING. |
| `process_partition_legacy(iterator)` | **(V3 - LEGACY)** Processa rileggendo **tutti i film** dell'utente da MongoDB e ricalcolando le statistiche complete. Usato solo per bootstrap o migrazione. Complessità O(N). |
| `process_partition(iterator)` | Wrapper/alias che chiama `process_partition_incremental()` (dopo la migrazione). |
| `process_batch(batch_df, batch_id)` | Callback per `foreachBatch`: raggruppa gli eventi per `user_id`, colleziona tutti i campi necessari (event_type, nome, rating, old/new_rating) e chiama `process_partition()` in parallelo sui worker Spark. |
| `bootstrap_global_stats()` | **Bootstrap iniziale**: legge TUTTI i film degli ultimi 30 giorni da MongoDB e inizializza `global_stats` (top_movies, trending_genres, movie_counts, genre_counts, poster_cache). Chiamato **una sola volta** all'avvio di Spark. |
| `write_global_trends_to_mongo(batch_df, batch_id)` | Callback per lo stream globale: **incrementa o decrementa** i conteggi in `global_stats` in base all'`event_type` (ADD o DELETE). Preserva i poster URL esistenti e ricalcola Top 10 film e generi. |
| `start_global_trends_stream(spark, parsed_stream)` | Avvia lo **Structured Streaming** per i trend globali: applica watermark (1 ora), raggruppa per `movie_name` + `event_type`, e scrive su MongoDB ogni 2 minuti tramite `foreachBatch`. |
| `compute_user_stats(movies, catalog_collection, prefetched_map)` | Calcola le statistiche **complete** per un utente: rating distribution, generi preferiti, registi/attori più visti e meglio votati, top rated movies, film recenti, statistiche mensili per anno. Usato dalla versione legacy. |
| `main()` | **Entry point**: esegue bootstrap, crea SparkSession, configura 2 stream (user_stats e global_trends), e attende la terminazione. |

---

## Funzionamento Spark: Creazione user_stats e user_affinities

### Architettura Generale

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  FastAPI        │      │  Kafka Topic    │      │  Spark          │
│  Backend        │─────▶│  user-movie-    │─────▶│  Streaming      │
│                 │      │  events         │      │                 │
└─────────────────┘      └─────────────────┘      └────────┬────────┘
                                                          │
                                                          ▼
                                               ┌─────────────────────┐
                                               │  MongoDB            │
                                               │  - user_stats       │
                                               │  - user_affinities  │
                                               │  - global_stats     │
                                               └─────────────────────┘
```

### Flusso di Elaborazione

1. **Evento Generato**: Quando un utente aggiunge, modifica o elimina un film, il backend chiama `send_movie_event()` che pubblica su Kafka.

2. **Spark Consuma**: Lo stream Spark legge da Kafka con `startingOffsets: latest`.

3. **Parsing JSON**: Gli eventi vengono deserializzati con lo schema definito (`event_schema`).

4. **Micro-Batch Processing** (ogni 5 secondi per user_stats):
   - Raggruppa per `user_id`
   - Chiama `process_partition_incremental()` sui worker

---

### Logica user_stats (Collezione MongoDB)

La collezione `user_stats` contiene **metriche globali** dell'utente:

```javascript
{
  "user_id": "user123",
  "total_watched": 42,           // Totale film visti
  "sum_ratings": 168,            // Somma di tutti i voti
  "watch_time_minutes": 5460,    // Tempo totale di visione
  "rating_distribution": {       // Distribuzione voti 1-5 stelle
    "1": 2, "2": 5, "3": 12, "4": 15, "5": 8
  },
  "monthly_counts": {            // Film per mese/anno
    "2024": { "01": 5, "02": 8, "03": 3 },
    "2025": { "01": 10 }
  },
  "updated_at": "2025-01-21T00:45:00+01:00",
  "stats_version": "6.0_flat_affinities"
}
```

#### Logica Incrementale O(1)

Per ogni evento:

| Event Type | Operazione |
|------------|------------|
| **ADD** | `$inc: { total_watched: +1, sum_ratings: +rating, rating_distribution.X: +1 }` |
| **DELETE** | `$inc: { total_watched: -1, sum_ratings: -rating, rating_distribution.X: -1 }` |
| **UPDATE_RATING** | `$inc: { sum_ratings: (new-old), rating_distribution.old: -1, rating_distribution.new: +1 }` |

Il codice accumula tutti i delta **in memoria** per batch, poi esegue **una sola** `bulk_write()`:

```python
user_stats_inc[user_id] = {
    "total_watched": delta,        # +1 o -1
    "sum_ratings": rating_delta,   # rating * delta
    "watch_time_minutes": duration * delta,
    f"rating_distribution.{rating}": delta,
    f"monthly_counts.{year}.{month}": delta
}

# Scrittura atomica
db.user_stats.bulk_write([
    UpdateOne({"user_id": uid}, {"$inc": aggregated_inc}, upsert=True)
    for uid, aggregated_inc in user_stats_inc.items()
])
```

---

### Logica user_affinities (Collezione MongoDB)

La collezione `user_affinities` contiene preferenze per registi, attori e generi in **struttura piatta**:

```javascript
// Documento singolo per ogni affinità
{
  "_id": "user123_director_Christopher_Nolan",
  "user_id": "user123",
  "type": "director",
  "name": "Christopher Nolan",
  "name_key": "Christopher_Nolan",
  "count": 5,        // Numero di film visti con questo regista
  "sum_voti": 23,    // Somma dei voti dati a questi film
  "updated_at": "2025-01-21T00:45:00+01:00"
}
```

#### Schema ID

L'ID è composto da: `{user_id}_{type}_{name_key}`

Dove:
- `type` = `director` | `actor` | `genre`
- `name_key` = nome normalizzato (spazi → underscore, punti rimossi)

#### Logica Incrementale

```python
# Per ogni film nel batch
for director in directors_list[:2]:  # Max 2 registi per film
    affinity_id = f"{user_id}_director_{clean_key(director)}"
    user_affinities_inc[affinity_id] = {
        "count": delta,          # +1 (ADD) o -1 (DELETE)
        "sum_voti": rating_delta # rating * delta
    }

# Bulk write
db.user_affinities.bulk_write([
    UpdateOne(
        {"_id": affinity_id},
        {
            "$inc": {"count": data["count"], "sum_voti": data["sum_voti"]},
            "$set": {"user_id": ..., "type": ..., "name": ..., "name_key": ...}
        },
        upsert=True
    )
])
```

#### Vantaggi Struttura Piatta

1. **Query efficienti**: `db.user_affinities.find({user_id: "X", type: "director"}).sort({count: -1})`
2. **Documenti piccoli**: ~200 bytes vs KB con struttura nested
3. **Indici granulari**: Indice su `{user_id: 1, type: 1, count: -1}`
4. **Scalabilità**: Nessun limite di 16MB per documento

---

### Flusso Completo: Esempio ADD

```
Utente aggiunge "Inception" (Nolan, rating 5)
    │
    ▼
Kafka: { event_type: "ADD", user_id: "u1", movie: {name: "Inception", rating: 5, ...} }
    │
    ▼
Spark process_partition_incremental():
    │
    ├── Lookup catalogo → trova director="Christopher Nolan", genres=["Sci-Fi", "Action"]
    │
    ├── Aggrega in memoria:
    │   user_stats_inc["u1"] = {
    │       "total_watched": +1,
    │       "sum_ratings": +5,
    │       "rating_distribution.5": +1
    │   }
    │
    │   user_affinities_inc = {
    │       "u1_director_Christopher_Nolan": {count: +1, sum_voti: +5},
    │       "u1_genre_Sci-Fi": {count: +1, sum_voti: 0},
    │       "u1_genre_Action": {count: +1, sum_voti: 0}
    │   }
    │
    └── bulk_write() su entrambe le collezioni
```

---

### Differenza tra User Stats e Global Stats

| Aspetto | User Stats | Global Stats |
|---------|------------|--------------|
| **Trigger** | 5 secondi | 2 minuti |
| **Scope** | Per singolo utente | Tutti gli utenti |
| **Struttura** | `user_stats` + `user_affinities` | `global_stats` |
| **Logica** | Incrementale O(1) | Bootstrap + Streaming |
| **Dati** | Metriche personali | Top 10 film, trending genres |
