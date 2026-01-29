# Documentazione Architettura Streaming YouTube: Kafka + Spark

## 1. Panoramica del Sistema: Event-Driven Architecture

Il sistema è progettato secondo i principi della **Event-Driven Architecture (EDA)**. Invece di eseguire un'elaborazione monolitica (scarico -> elaboro -> salvo tutto in una volta), il sistema reagisce a flussi continui di "eventi". Ogni nuovo commento su YouTube è un evento che attraversa una pipeline di trasformazione.

Il flusso dati segue il modello **Producer-Consumer**:
1.  **Producer**: Genera gli eventi (scarica dati da YouTube).
2.  **Broker (Kafka)**: Canale di trasporto persistente e buffer.
3.  **Consumer (Spark)**: Elabora gli eventi e produce risultati.

---

## 2. Ingestion Layer: YoutubeProducer.py (Dettagli)

Il `YoutubeProducer.py` funge da ponte tra il mondo esterno (API YouTube) e il sistema interno.

### Meccanismo di Polling Intelligente
Nonostante Kafka sia orientato agli eventi, le API di YouTube sono REST (quindi richiesta/risposta). Il Producer simula uno stream continuo effettuando un **polling periodico** (ogni 30s).
- **Perché 30 secondi?** È un compromesso per rispettare le quote limiti delle API di YouTube (Quota Cost) pur mantenendo una sembianza di "tempo reale".
- **Serializzazione**: I dati vengono convertiti in JSON (`json.dumps`). Kafka accetta solo byte, quindi il Producer si occupa di questa traduzione (`.encode("utf-8")`), garantendo che qualsiasi consumer possa leggere i dati standardizzati.

### Riferimento Codice: Configurazione Kafka
```python
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,  # Indirizzo del Cluster Kafka
    value_serializer=lambda v: json.dumps(v).encode("utf-8")  # Serializzazione automatica
)
```
La variabile d'ambiente `TARGET_VIDEO_ID` permette all'Orchestrator di cambiare il bersaglio del polling senza riavviare il container o modificare il codice sorgente.

---

## 3. Message Broker: Apache Kafka

Kafka non è solo una "coda", ma un **Distributed Commit Log**.

### Ruolo Chiave: Il Buffer Persistente
Kafka agisce come "cuscinetto" tra l'ingestione e l'elaborazione.
- **Disaccoppiamento**: Se Spark (il consumer) si ferma per un errore o per manutenzione, il Producer **continua a scaricare** i commenti e a salvarli in Kafka. Nessun dato viene perso.
- **Rielaborazione**: I messaggi in Kafka persistono per un tempo configurato (retention). Se si vuole riprocessare gli ultimi 100 commenti con una logica diversa, Spark può semplicemente "riavvolgere il nastro" (reset offset) e rileggerli.

---

## 4. Processing Layer: YoutubeSparkConsumer.py (Approfondimento)

Qui avviene la vera magia di **Spark Structured Streaming**.

### Concetto: Unbounded Table
Spark Structured Streaming tratta il flusso di dati da Kafka come una tabella infinita ("Unbounded Table"). Ogni nuovo messaggio Kafka è una nuova riga aggiunta (`append`) a questa tabella.

### Micro-Batch Processing
Spark non elabora i messaggi uno alla volta (che sarebbe inefficiente), ma accumula dati per piccoli intervalli di tempo (es. 1 secondo) creando dei **micro-batch**.
1.  Legge tutti i messaggi arrivati negli ultimi X millisecondi.
2.  Li trasforma in un DataFrame.
3.  Applica le trasformazioni (filtri, calcoli).
4.  Scrive il risultato su MongoDB.

### Fault Tolerance & Checkpointing
Il sistema è resiliente ai guasti grazie al meccanismo di **Checkpointing**.
```python
.option("checkpointLocation", "/tmp/youtube_checkpoint")
```
Spark salva periodicamente su disco (o HDFS/S3) lo "stato" dell'elaborazione (es. "ho letto fino all'offset 1054 del topic youtube-comments").
- **Scenario di Guasto**: Se il processo Spark crasha mentre elabora il messaggio 1060.
- **Recovery**: Al riavvio, Spark legge il checkpoint ("ero arrivato al 1054"), richiede a Kafka i messaggi dal 1055 in poi e riprende esattamente da dove si era interrotto. Questo garantisce la semantica **At-Least-Once** (o Exactly-Once con sink idonei).

### Scrittura su MongoDB (`foreachBatch`)
La funzione `foreachBatch` permette di applicare logica custom per ogni micro-batch. Qui viene usata per ottimizzare la connessione verso MongoDB, aprendola una volta per batch invece che per ogni singolo record.

---

## 5. Orchestration Layer: YoutubeComments5.py

Questo layer trasforma i due script indipendenti in un **servizio gestito**.

### Gestione del Ciclo di Vita (Lifecycle Management)
Senza questo layer, l'amministratore dovrebbe lanciare manualmente da terminale:
1. `python YoutubeProducer.py`
2. `python YoutubeSparkConsumer.py`

Il `YoutubeComments5.py` automatizza questo processo utilizzando `subprocess`.
- **Environment Isolation**: Crea una copia delle variabili d'ambiente (`os.environ.copy()`) e inietta `TARGET_VIDEO_ID` specifica per la richiesta corrente.
- **Process Supervision**: Mantiene i PID (Process ID) in memoria. Quando viene chiamato `stop_live_comments_streaming`, invia segnali di terminazione (`SIGTERM`) pulita ai processi figli, evitando processi orfani ("zombie processes") che consumerebbero memoria inutilmente.

---

## Conclusione: Perché questa architettura?

Questa architettura è sovradimensionata per 5 commenti, ma è **perfetta** per dimostrare come si gestiscono i **Big Data**:
1.  **Scalabilità**: Se domani arrivassero 1 milione di commenti al secondo, basterebbe aggiungere più nodi Kafka e più worker Spark, senza cambiare una riga di codice.
2.  **Resilienza**: Il fallimento di un componente non blocca l'intero sistema.
3.  **Manutenibilità**: Ogni script fa una cosa sola e la fa bene (Separation of Concerns).
