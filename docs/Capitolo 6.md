# Capitolo 6: Commenti Youtube

## YoutubeComments.py

## Introduzione
La sezione "Commenti Youtube" è basata su diversi moduli, il primo dei quali `YoutubeComments.py` ha lo scopo di automatizzare il recupero di informazioni sui film in prossima uscita. Nello specifico, il suo obiettivo è identificare il primo film che verrà rilasciato nel mese successivo alla data corrente e recuperarne il relativo trailer ufficiale da YouTube tramite le API di The Movie Database (TMDB).

Il flusso logico è progettato per garantire che l'applicazione mostri sempre contenuti aggiornati e pertinenti alle future uscite cinematografiche.

## Architettura del Modulo
Il modulo è strutturato in tre funzioni principali che cooperano sequenzialmente:

1.  **`get_first_upcoming_movie_next_month`**: Identificazione del film target.
2.  **`get_youtube_trailer`**: Recupero della risorsa video.
3.  **`get_upcoming_movie_with_trailer`**: Orchestrazione del processo.

Di seguito viene presentata un'analisi dettagliata di ciascun componente.

---

### 1. Identificazione del Film (`get_first_upcoming_movie_next_month`)
Questa funzione è responsabile della logica temporale e della ricerca nel database TMDB.

**Logica di funzionamento:**
1.  **Calcolo Temporale**: Determina dinamicamente quale sia il "mese prossimo" rispetto alla data di esecuzione (`date.today()`). Gestisce correttamente il cambio anno (es. se siamo a Dicembre, il mese prossimo è Gennaio dell'anno successivo).
2.  **Interrogazione API**: Effettua chiamate paginate all'endpoint `movie/upcoming` di TMDB.
3.  **Filtraggio**: Itera sui risultati ricevuti e verifica la data di rilascio (`release_date`) di ogni film.
4.  **Selezione**: Il primo film trovato che corrisponde esattamente al mese e anno target viene selezionato e restituito.

```python
def get_first_upcoming_movie_next_month():
    # ... calcolo target_month e target_year ...
    
    while True:
        # ... richiesta API ...
        
        for film in results:
            # Parsing della data di rilascio
            release = datetime.strptime(release_date, "%Y-%m-%d").date()

            # Verifica corrispondenza temporale
            if release.year == target_year and release.month == target_month:
                return {
                    "movie_id": film["id"],
                    "title": film.get("title"),
                    "release_date": release_date
                }
```

### 2. Recupero del Trailer (`get_youtube_trailer`)
Una volta ottenuto l'ID univoco del film, questa funzione interroga l'API per ottenere le risorse video associate.

**Logica di funzionamento:**
1.  Effettua una chiamata all'endpoint `/movie/{movie_id}/videos`.
2.  Scansiona la lista dei video restituiti cercando un oggetto che soddisfi due condizioni:
    *   `site`: deve essere "YouTube".
    *   `type`: deve essere "Trailer".
3.  Restituisce l'URL completo e l'ID del video per l'embedding.

```python
def get_youtube_trailer(movie_id: int):
    # ... richiesta API ...
    
    for video in data.get("results", []):
        if video["site"] == "YouTube" and video["type"] == "Trailer":
            return {
                "url": f"https://www.youtube.com/watch?v={video['key']}",
                "embed_id": video['key']
            }
```

### 3. Orchestrazione (`get_upcoming_movie_with_trailer`)
Questa è la funzione di interfaccia principale che viene richiamata dall'esterno (es. dal controller API).

**Flusso:**
1.  Invoca `get_first_upcoming_movie_next_month()` per ottenere un candidato valido.
2.  Se nessun film viene trovato, termina restituendo `None`.
3.  Se un film è presente, invoca `get_youtube_trailer()` passando l'ID del film.
4.  Aggrega i dati del film e del trailer in un unico dizionario di risposta.

```python
def get_upcoming_movie_with_trailer():
    film = get_first_upcoming_movie_next_month()
    
    if not film:
        return None
    
    trailer_data = get_youtube_trailer(film["movie_id"])
    
    return {
        "title": film["title"],
        "release_date": film["release_date"],
        "trailer_url": trailer_data["url"] if trailer_data else None,
        "embed_id": trailer_data["embed_id"] if trailer_data else None
    }
```

## Conclusione
Il modulo `YoutubeComments.py` incapsula interamente la logica necessaria per la funzionalità "Trailer in Anteprima". Separando la responsabilità della selezione del film da quella del recupero del media, il codice mantiene un'elevata modularità e leggibilità, facilitando eventuali manutenzioni future o l'estensione a nuove fonti di dati.

---

## YoutubeComments3.py

## Introduzione
Il modulo `YoutubeComments3.py` è dedicato all'acquisizione massiva (limitata a 5 commenti per questioni didattiche) e pulita dei commenti da video YouTube, alla loro persistenza su database MongoDB e all'integrazione con il sistema di analisi del sentiment. A differenza di un semplice scraper, questo componente implementa logiche avanzate di filtraggio anti-spam e garantisce l'idempotenza dei salvataggi per prevenire duplicati.
I commenti acquisti possono essere considerati i "commenti più popolari" in quanto vengono proposti i commenti con maggiore rilevanza in base all'algoritmo di YouTube e al numero di like.

## Architettura del Modulo
Il flusso di lavoro si articola attraverso diverse fasi operative:

1.  **Estrazione e Connessione API**: Interfacciamento con YouTube Data API v3.
2.  **Filtraggio e Pulizia**: Pre-processing del testo grezzo.
3.  **Filtraggio Spam**: Analisi euristica per scartare contenuti di bassa qualità.
4.  **Persistenza Dati**: Salvataggio sicuro su MongoDB con gestione dei duplicati.
5.  **Integrazione Sentiment**: Trigger automatico per l'analisi emotiva dei commenti.

### 1. Acquisizione e Pulizia (`get_multiple_comments`)
Questa funzione principale coordina il processo di estrazione. Utilizza l'API `commentThreads` di YouTube per scaricare i commenti in ordine di rilevanza.

Ogni commento scaricato viene sottoposto alla funzione `clean_comment`, che esegue le seguenti operazioni di sanitizzazione tramite espressioni regolari (Regex):
*   Rimoziome tag HTML (`<.*?>`).
*   Rimozione URL (`http\S+`).
*   Rimozione timestamp video (es. "1:23").
*   Normalizzazione caratteri speciali e spazi multipli.

```python
def clean_comment(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<.*?>", "", text)        # HTML
    text = re.sub(r"http\S+", "", text)      # URL
    text = re.sub(r"[^\w\s.,!?'\"]", "", text) # Caratteri speciali
    return text.strip()
```

### 2. Filtraggio Anti-Spam (`is_spam`)
Prima di essere accettato, ogni commento viene validato da un filtro che scarta:
*   Commenti contenenti parole chiave proibite (es. "subscribe") o altre stringhe non desiderate. L'elenco delle parole da considerare spam può essere ampliato con le dovute modifiche.
*   Testi con eccessivi link o composti interamente da maiuscole (CAPSLOCK).
*   Commenti con eccessiva ripetizione di parole (indice di bassa entropia lessicale).

```python
def is_spam(text: str) -> bool:
    if "subscribe" in text.lower(): return True
    if text.count("http") > 0: return True
    if text.isupper(): return True
    # Controllo ripetizioni
    words = text.split()
    if len(words) > 10 and len(set(words)) / len(words) < 0.4:
        return True
    return False
```

### 3. Persistenza dei dati (`save_comments_to_mongodb`)
Una caratteristica critica di questo modulo è la gestione dell'unicità dei commenti. Per evitare duplicati nel database ("CommentiVotati"), viene generato un ID deterministico per ogni commento utilizzando l'hash MD5 del contenuto testuale e dell'autore.

```python
# Generazione ID deterministico
text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
comment_id = f"yt3_{author}_{text_hash}"
```

Il salvataggio utilizza l'operazione `update_one` con flag `upsert=True`, garantendo che se un commento esiste già, venga aggiornato (o ignorato se identico) anziché duplicato.

```python
collection.update_one(
    {"_id": doc["_id"]}, # Chiave di ricerca
    {"$set": doc},       # Dati da scrivere
    upsert=True          # Crea se non esiste
)
```

### 4. Integrazione Sentiment Analysis
Al termine del salvataggio, il modulo invoca `process_pending_comments` dal modulo `YoutubeComments6`. Questo design a "trigger" assicura che i nuovi commenti vengano analizzati (positivi/negativi) immediatamente dopo l'acquisizione, arricchendo il dataset in tempo reale.

## Conclusione
`YoutubeComments3.py` rappresenta un componente robusto per l'ingestione dati. La combinazione di pulizia regex, filtraggio spam euristico e gestione transazionale con ID deterministici assicura che il database "CommentiVotati" contenga solo dati di alta qualità, pronti per l'analisi semantica successiva.

---

## YoutubeComments5.py

## Introduzione
Il modulo `YoutubeComments5.py` introduce un cambio di paradigma rispetto ai precedenti script, passando da un'esecuzione batch a un'architettura **Real-Time Streaming**. Lo scopo di questo componente è monitorare costantemente un trailer YouTube, catturando i nuovi commenti non appena vengono pubblicati e visualizzandoli "live" nell'interfaccia utente.

## Architettura del Modulo
Il sistema è progettato attorno al pattern *Producer-Consumer* e utilizza **Apache Spark Structured Streaming** (simulato per contesti didattici) per l'elaborazione dei dati.

Le componenti chiave sono:

1.  **`CommentsBuffer`**: Un buffer thread-safe circolare (Deque) che mantiene in memoria solo gli ultimi N commenti (configurato a 5).
2.  **`YouTubeCommentsStreaming`**: Il gestore del ciclo di vita dello streaming.
3.  **`_polling_worker`**: Un thread che interroga periodicamente l'API di YouTube.

### 1. Gestione dello Stato (`CommentsBuffer`)
Poiché l'ambiente è multithread (il polling avviene in background mentre l'API Flask legge i dati), è necessario un meccanismo di sincronizzazione.

```python
class CommentsBuffer:
    def __init__(self, max_size: int = 5):
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.RLock()

    def add_comment(self, comment: Dict) -> None:
        with self._lock:
            # Logica di deduplica e inserimento
            self._buffer.append(comment)
```

### 2. Il Motore di Streaming (`YouTubeCommentsStreaming`)
Questa classe incapsula la Sessione Spark e gestisce il thread di acquisizione dati.

**Loop di Polling:**
Il worker esegue un ciclo continuo che:
1.  Scarica i nuovi commenti dall'API.
2.  Aggiorna il buffer condiviso.
3.  Persiste i dati su MongoDB (`CommentiLive`).
4.  Invoca l'elaborazione Spark.

### 3. Integrazione con Spark
All'interno del metodo `_process_with_spark`, i dati grezzi (dizionari Python) vengono convertiti in **Spark DataFrame**. Questo passaggio è fondamentale perché trasforma dati non strutturati in una tabella relazionale in-memory, permettendo di applicare operazioni SQL-like complesse.

```python
def _process_with_spark(self, comments: List[Dict]):
    # Creazione del DataFrame Spark
    rows = [Row(...) for c in comments]
    df = self._spark.createDataFrame(rows)
    
    # Esempio di trasformazione streaming
    df_sorted = df.orderBy(desc("published_at"))
```

### 4. Persistenza su MongoDB (`save_comments_to_mongodb`)
Ogni ciclo di polling non si limita ad aggiornare il buffer in memoria, ma esegue anche la persistenza dei dati sulla collezione MongoDB `CommentiLive`.
Questa operazione svolge un ruolo cruciale nell'architettura del sistema:
*   **Trigger per l'Analisi**: I nuovi commenti vengono salvati con il campo `valore_sentiment` impostato a `None`. La presenza di questo valore nullo viene rilevata dal modulo di analisi semantica (`YoutubeComments6.py`), che procederà asincronamente al calcolo del punteggio.
*   **Fonte Dati per il Frontend**: L'interfaccia utente attinge i dati da questa collezione persistente, garantendo che i commenti visualizzati siano sempre sincronizzati e storicizzati.

Come per gli altri moduli, l'inserimento utilizza l'opzione `upsert=True` per gestire correttamente eventuali duplicati in fase di ricezione.

## Analisi Architetturale: Perché Spark?
L'utilizzo di **Apache Spark** per gestire un flusso limitato di 5 commenti potrebbe apparire, a una prima analisi, sovradimensionato (*overkill*). Tuttavia, questa scelta architetturale risponde a precisi requisiti di **progettazione software scalabile**:

1.  **Astrazione del Data Processing**: Spark astrae la complessità della manipolazione dati. Se domani i requisiti cambiassero da "mostra gli ultimi 5" a "calcola la media mobile del sentiment sugli ultimi 10.000 commenti raggruppati per nazionalità dell'autore", con Spark basterebbe modificare una riga di codice SQL/DataFrame (`df.groupBy(...).agg(...)`), mentre con Python puro richiederebbe la riscrittura dell'intero motore di aggregazione.
2.  **Unificazione Batch/Streaming**: Spark Structured Streaming permette di trattare i dati in arrivo come se fossero una tabella statica infinita. Questo significa che lo stesso codice usato per analizzare lo storico dei commenti può essere riutilizzato per i dati live senza modifiche.
3.  **Robustezza e Tipizzazione**: L'uso di Schemi (`StructType`) impone un rigore nella struttura dei dati che Python, essendo dinamicamente tipizzato, non garantisce nativamente.

In sintesi, Spark è stato introdotto non per la *mole* attuale dei dati, ma per predisporre un'architettura pronta all'evoluzione ("Future-Proof").

## Evoluzione e Scalabilità: Il ruolo di Kafka
Nell'attuale implementazione, l'acquisizione dei dati avviene tramite **Polling attivo** (il sistema chiede ripetutamente a YouTube "ci sono novità?").
In uno scenario di produzione ad alto traffico (es. monitoraggio di migliaia di video contemporaneamente), questo approccio presenterebbe limiti evidenti:
*   **Rate Limiting**: Rischio di saturare le quote API di YouTube.
*   **Latenza**: I dati vengono visti solo all'intervallo di polling.

### L'integrazione di Apache Kafka
Per scalare orizzontalmente, l'architettura ideale prevederebbe l'introduzione di **Apache Kafka** come message broker intermedio:

1.  **Produttori Disaccoppiati**: Un fleet di agenti leggeri invierebbe i commenti a un topic Kafka (`youtube-comments-firehose`) senza preoccuparsi di chi li elaborerà.
2.  **Kafka come Buffer**: Kafka gestirebbe i picchi di traffico, accumulando i messaggi se Spark rallenta, prevenendo la perdita di dati.
3.  **Spark come Consumatore**: Spark Structured Streaming consumerebbe gradualmente quanto accumulato da Kafka, elaborando i micro-batch ad alta velocità.

### Perché non è stato implementato Kafka?
Nel contesto specifico di questo progetto, Kafka non è stato introdotto principalmente per complessità
Dato che il requisito è monitorare un singolo video per volta e visualizzare pochi commenti, la complessità infrastrutturale di gestire un cluster Kafka avrebbe introdotto una difficoltà maggiore rispetto al beneficio immediato. L'architettura attuale (Polling + Buffer in memoria) rappresenta il compromesso ottimale tra prestazioni e complessità implementativa.

### Considerazioni Finali

L’uso di Apache Spark in questo progetto ha una finalità prevalentemente didattica e dimostrativa. Spark è inizializzato e utilizzato per l’elaborazione dei dati sotto forma di DataFrame, eseguendo trasformazioni e azioni reali sui commenti raccolti, ma non viene impiegato come motore di ingestione streaming nativo. Lo streaming dei dati è simulato tramite un meccanismo di polling periodico delle API di YouTube, che rappresenta un limite intrinseco in termini di scalabilità e parallelismo, poiché la sorgente dei dati è pull-based e soggetta a rate limiting. In questo contesto, Spark opera come motore di elaborazione batch su micro-lotti generati dall’applicazione, consentendo di studiare l’integrazione tra sistemi di raccolta dati, persistenza e analisi distribuita, pur senza sfruttare appieno le funzionalità di Spark Structured Streaming come watermarking, gestione degli offset e fault tolerance end-to-end. In un reale scenario big data e streaming, l’architettura dovrebbe prevedere un sistema di messaggistica distribuita (ad esempio Kafka o un servizio di streaming equivalente) come livello intermedio di ingestione, permettendo a Spark di consumare direttamente uno stream continuo di eventi, garantendo scalabilità orizzontale, resilienza e una separazione più netta tra produzione e consumo dei dati.

---

## YoutubeComments6.py

## Introduzione
Il modulo `YoutubeComments6.py` è responsabile dell'analisi "emotiva" dei commenti, assegnando a ciascuno un punteggio di sentiment (positivo, negativo o neutro) utilizzando tecnologie di **Natural Language Processing (NLP)**.

## Architettura del Modulo
Il sistema è basato su **RoBERTa** (Robustly optimized BERT approach), specificamente il modello `cardiffnlp/twitter-roberta-base-sentiment-latest`, addestrato su milioni di tweet. Questa scelta garantisce un'elevata precisione anche su testi informali, pieni di slang o sgrammaticati, tipici dei commenti social.

### Design Pattern: Singleton
Caricare un modello di Deep Learning in memoria è un'operazione costosa in termini di tempo e risorse (RAM). Per evitare di ricaricare il modello per ogni singolo commento, il modulo implementa il pattern **Singleton**.

```python
class SentimentAnalyzer:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Caricamento thread-safe del modello
                cls._instance = super().__new__(cls)
        return cls._instance
```
Questo garantisce che esista **una e una sola istanza** del modello in memoria per l'intero ciclo di vita dell'applicazione.

### Flusso di Analisi
1.  **Preprocessing**: Il testo viene pulito e normalizzato (es. sostituendo gli username con `@user`).
2.  **Tokenizzazione**: Il testo viene convertito in vettori numerici compatibili con la rete neurale.
3.  **Inferenza**: Il modello calcola la probabilità per le tre classi (Negativo, Neutro, Positivo).
4.  **Score Finale**: Viene calcolato un punteggio normalizzato tra -1 (molto negativo) e +1 (molto positivo).

```python
def analyze(self, text: str) -> float:
    # Calcolo score come differenza tra probabilità positiva e negativa
    sentiment_value = positive_score - negative_score
    return round(sentiment_value, 4)
```

### Integrazione Asincrona con MongoDB
Il modulo agisce come un "worker" che processa i commenti in background. La funzione `process_pending_comments` scansiona periodicamente le collezioni `CommentiLive` e `CommentiVotati` alla ricerca di documenti che non hanno ancora un campo `valore_sentiment`.

Questa architettura disaccoppiata permette di:
1.  Salvare immediatamente il commento (bassa latenza per l'utente).
2.  Calcolare il sentiment in un secondo momento (elaborazione pesante) senza bloccare l'interfaccia.

## Conclusione
L'adozione di un modello Transformer pre-addestrato come RoBERTa, incapsulato in un Singleton per l'efficienza, eleva la qualità dell'analisi ben oltre i semplici approcci basati su dizionari di parole, permettendo al sistema di comprendere sfumature, ironia e contesto.

---

## YoutubeComments7.py

## Introduzione
Il modulo `YoutubeComments7.py` funge da layer di **Aggregazione dei Dati** dell'applicazione. Mentre gli altri moduli si occupano di acquisizione (ETL) e analisi puntuale, questo componente ha il compito di aggregare i dati grezzi per estrarre metriche di alto livello, specificamente la media del sentiment per le collezioni `CommentiLive` e `CommentiVotati`.

## Architettura del Modulo
Il modulo interroga direttamente il database MongoDB per calcolare statistiche in tempo reale. Non storicizza i risultati, ma li calcola "on-demand" ogni volta che vengono richiesti (es. quando il frontend aggiorna la dashboard).

### Algoritmo di Aggregazione
La funzione principale `calculate_collection_sentiment_average` implementa la logica di calcolo:

1.  **Filtraggio**: Seleziona solo i documenti che possiedono un campo `valore_sentiment` valido (escludendo quindi i commenti non ancora processati dal modulo 6).
2.  **Calcolo Media**: Esegue la media aritmetica dei punteggi.
3.  **Etichettatura (Labeling)**: Converte il valore numerico (range -1.0 a +1.0) in una classe semantica leggibile secondo soglie prefissate:
    *   **Positive**: Media > 0.2
    *   **Negative**: Media < -0.2
    *   **Neutral**: Valori intermedi

```python
def calculate_collection_sentiment_average(collection_name: str) -> Dict:
    # Query MongoDB filtrata
    comments_with_sentiment = list(collection.find({
        "valore_sentiment": {"$ne": None, "$exists": True}
    }, {"valore_sentiment": 1})) # Projection per efficienza
    
    # Calcolo della media
    sentiment_sum = sum(c.get("valore_sentiment", 0) for c in comments_with_sentiment)
    average = sentiment_sum / sentiment_count
    
    # Assegnazione Label
    if average > 0.2: label = "positive"
    elif average < -0.2: label = "negative"
    else: label = "neutral"
```

### Ottimizzazione delle Performance
Per ridurre il carico di rete e memoria, la query MongoDB utilizza una **Projection** (`{"valore_sentiment": 1}`), istruendo il database a restituire *solo* il campo necessario al calcolo, ignorando il testo del commento, l'autore e altri metadati pesanti.

## Conclusione
`YoutubeComments7.py` chiude il cerchio dell'elaborazione dati, trasformando i singoli giudizi (calcolati dal modello BERT) in una metrica di tendenza complessiva (Sentiment Analysis Aggregata), fornendo all'utente una visione sintetica immediata della percezione del film.
