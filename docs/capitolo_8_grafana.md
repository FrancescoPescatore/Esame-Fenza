# Capitolo 8: Dashboard Analitica con Grafana

Grafana rappresenta il livello di visualizzazione ("Presentation Layer") dell'architettura Big Data di CineMatch. Attraverso una connessione diretta alle sorgenti dati (MongoDB via plugin Infinity/MongoDB e API Backend), offre una panoramica in tempo reale dello stato del sistema e dei trend cinematografici.

Il dashboard configurato è suddiviso in tre sezioni logiche principali, progettate per monitorare sia le metriche di business (film, utenti) che quelle tecniche (sentiment, performance).

---

## 8.1 Sezione Global Trends (Analisi Mercato)

Questa sezione visualizza i dati calcolati da Spark Streaming e persistiti nella collezione `global_stats`. Serve per comprendere quali contenuti stanno performando meglio sulla piattaforma.

### 1. Top 10 Movies (Bar Chart)
*   **Descrizione**: Visualizza i 10 film con il maggior numero di interazioni (visualizzazioni/voti) accumulate.
*   **Sorgente Dati**: MongoDB (`global_stats` -> `top_movies`).
*   **Visualizzazione**: Grafico a barre orizzontali. Sull'asse Y i titoli dei film, sull'asse X il numero di interazioni.
*   **Insight**: Permette di identificare istantaneamente i "Blockbuster" del momento.

### 2. Trending Genres (Pie Chart)
*   **Descrizione**: Mostra la distribuzione percentuale dei generi più popolari basata sull'attività recente degli utenti.
*   **Sorgente Dati**: MongoDB (`global_stats` -> `trending_genres`).
*   **Visualizzazione**: Grafico a torta (Donut Chart) con legenda laterale e percentuali.
*   **Insight**: Utile per capire se l'utenza preferisce generi specifici (es. Drama vs Sci-Fi) in un determinato periodo.

---

## 8.2 Sezione Analisi Sentiment (Real-Time YouTube)

Questa sezione è dedicata all'analisi in tempo reale dei feedback provenienti dai social (YouTube), processati dai nuovi moduli di ingestion.

### 3. Live Sentiment Gauge
*   **Descrizione**: Un indicatore a "tachimetro" che mostra il sentiment medio attuale dei commenti analizzati (scala da -1 a +1 o da 0 a 100).
*   **Sorgente Dati**: API Backend (`/sentiment-averages`).
*   **Visualizzazione**: Gauge Chart con soglie colorate (Rosso=Negativo, Giallo=Neutro, Verde=Positivo).
*   **Insight**: Fornisce un feedback immediato sulla percezione del pubblico verso i trailer in uscita.

### 4. Sentiment Trend Over Time (Time Series)
*   **Descrizione**: Grafico a linee che traccia l'evoluzione del sentiment nel tempo.
*   **Sorgente Dati**: MongoDB (`sentiment_history` o aggregazione live).
*   **Visualizzazione**: Line chart con area sottesa.
*   **Insight**: Permette di correlare picchi di sentiment (positivo o negativo) a eventi specifici (es. rilascio di un nuovo trailer).

---

## 8.3 Sezione Monitoraggio Utenti e Sistema

Questa sezione offre metriche operative sulla base utenti e sullo stato del sistema.

### 5. Nuovi Utenti Giornalieri (Stat)
*   **Descrizione**: Visualizza il numero di nuovi utenti registrati nelle ultime 24 ore.
*   **Sorgente Dati**: MongoDB (`users` collection).
*   **Visualizzazione**: Stat panel (Single Value).

### 6. Distribuzione Rating (Histogram)
*   **Descrizione**: Un istogramma che mostra come gli utenti distribuiscono i loro voti (da 1 a 5 stelle).
*   **Sorgente Dati**: MongoDB (`user_stats` aggregate o `global_stats`).
*   **Visualizzazione**: Istogramma verticale.
*   **Insight**: Evidenzia se la community è tendenzialmente generosa (molti 4-5) o critica (molti 1-2).

---

## 8.4 Architettura di Collegamento

Grafana non si collega direttamente a Spark, ma legge i risultati "cristallizzati" che Spark scrive su MongoDB. L'architettura utilizza il plugin **Infinity Datasource** (per chiamate API JSON al backend) o un connettore MongoDB nativo.

*   **Vantaggio**: Disaccoppiamento totale. Se Spark è sotto carico pesante per il processing, la dashboard Grafana continua a leggere velocemente l'ultimo stato valido dal database, senza rallentamenti.
