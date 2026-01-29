# Capitolo 1: Ampliamento dati iniziali

## 1.1 Introduzione al DataSet

Il DataSet originale “IMDB_Movies”, preso da GitHub, presentava circa 80.000 film diversi, a partire dal 1900 circa fino al 2020. Le principali informazioni disponibili per ogni film sono:
- Codice IMDB
- Titolo
- Anno di Uscita
- Genere/i
- Regista
- Attori
- Descrizione

La prima task del progetto è stata ampliare il dataset includendo anche i principali film usciti negli anni 2021 - 2025. Ciò è stato svolto attraverso:

- Web Scraping: per ottenere la lista dei film con i rispettivi codici
- Libreria Python: IMDBinfo

## 1.2 Web Scraping

Abbiamo scelto di ottenere le informazioni di 50 film per ogni anno, dal 2021 al 2025. Per fare ciò, abbiamo utilizzato il web scraping per ottenere la lista dei film con i rispettivi codici IMDB. Successivamente, abbiamo utilizzato la libreria Python IMDBinfo per ottenere le informazioni dei film.

```python
# Configura le opzioni del browser
options = webdriver.ChromeOptions()
options.add_argument('--lang=en-US')
options.add_argument('--accept-lang=en-US,en;q=0.9')

# Setup Chrome driver
driver = webdriver.Chrome(options=options)
driver.maximize_window()

'''
url_list=["https://www.imdb.com/search/title/?title_type=feature&release_date=2021-01-01,2021-12-31&sort=num_votes,desc",
          "https://www.imdb.com/search/title/?title_type=feature&release_date=2022-01-01,2022-12-31&sort=num_votes,desc",
          "https://www.imdb.com/search/title/?title_type=feature&release_date=2023-01-01,2023-12-31&sort=num_votes,desc",
          "https://www.imdb.com/search/title/?title_type=feature&release_date=2024-01-01,2024-12-31&sort=num_votes,desc",
          "https://www.imdb.com/search/title/?title_type=feature&release_date=2025-01-01,2025-12-31&sort=num_votes,desc"] # Lista di URL per i film del 2021, 2022, 2023, 2024, 2025
'''
          
# URL della pagina
url = "https://www.imdb.com/search/title/?title_type=feature&release_date=2025-01-01,2025-12-31&sort=num_votes,desc"
driver.get(url)

# Attendi il caricamento iniziale
time.sleep(3)
print("Pagina caricata")
```

## 1.3 Estrazione dei collegamenti alle pagine dei Film
Una volta caricata la pagina interessata, è stato possibile estrarre i link alle singole pagine dei film

```
# Estrai i link dei 50 film
film_links = []

try:
    # Trova tutti i link con class="ipc-title-link-wrapper"
    link_elements = driver.find_elements(By.CSS_SELECTOR, 'a.ipc-title-link-wrapper')
    
    # Estrai i primi 50 link
    for i, element in enumerate(link_elements[:50]):
        href = element.get_attribute('href')
        if href:
            # Converti il link relativo in assoluto
            full_url = href.split('?')[0]  # Rimuovi i parametri di tracking
            if not href.startswith('http'):
                full_url = "https://www.imdb.com" + full_url
            film_links.append(full_url)
            print(f"{i+1}. {full_url}")
    
    print(f"\n✓ Totale film trovati: {len(film_links)}")
    
except Exception as e:
    print(f"Errore nell'estrazione dei link: {e}")
```

Un collegamento ottenuto da questo scraping ha questa struttura:
https://www.imdb.com/title/tt6208148/
Successivamente, è possibile estrarre la parte numerica del codice. Questa servirà per l'estrazione delle informazioni del film attraverso la libreria IMDBinfo

## 1.4 Estrazione delle informazioni del film e creazione del Dataframe

```
#Creazione DataFrame
#Voglio creare un Dataframe, avrà la colonna Titolo, Anno, Genere (conterrà una lista dei generi del film), Attori (Sezione TOP Cast della pagina IMDB), IMDB Rating

import pandas as pd
df = pd.DataFrame(columns=["title", "year", "genre", "cast", "plot", "rating", "duration", "directors", "imdb_title_id", "link_imdb", "poster_url"])

# Ciclo per inserire ogni titolo
# for i in range(5):
#     tit = titoli[i].text.strip()
#     tit = tit[3:]

n = 0
for i in (chiavi):
    movie = get_movie(i)
    time.sleep(2)

    print(f"Titolo: {movie.title}")
    titolo = movie.title
    print(f"Anno: {movie.year}")
    year = movie.year
    print(f"Rating: {movie.rating}")
    rating = movie.rating
    print(f"Generi: {movie.genres}")
    genre = movie.genres
    print(f"Trama: {movie.plot}")
    plot = movie.plot
    print(f"Url: {movie.cover_url}")
    poster_url = movie.cover_url
    print(f"Durata: {movie.duration}")
    duration = movie.duration
    print(f"Cast:")
    attori = []
    for actor in movie.stars:
        attori.append(actor.name)
    print(attori)
    print(f"Regista/i:")
    registi = []
    for director in movie.directors:
        registi.append(director.name)
    print(registi)

    
    # Creo una nuova riga con i dati
    nuova_riga = {
        "title": titolo,
        "year": year,
        "genre": genre,
        "cast": attori,
        "plot": plot,
        "rating": rating,
        "duration": duration,
        "directors": registi,
        "imdb_title_id": chiavi[n],
        "link_imdb":film_links[n],
        "poster_url": poster_url
    }
    n = n+1
    # Aggiungo la riga al DataFrame
```
Questa operazione ha permesso la costruzione dei file CSV per ogni anno dal 2021 al 2025. I singoli CSV sono stati poi uniti al DataSet iniziale per formare un unico DataSet contenente i film dal 1900 al 2025.
