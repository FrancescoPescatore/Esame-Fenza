import pandas as pd
import requests
import time
import os
import concurrent.futures

# =================CONFIGURATION=================
# INSERISCI QUI LA TUA CHIAVE API DI TMDB
TMDB_API_KEY = "272643841dd72057567786d8fa7f8c5f" 
# ===============================================

INPUT_CSV = "Dati-prova-letterbox/movies_final.csv"
OUTPUT_CSV = "Dati-prova-letterbox/movies_final_updated.csv"

# Sessione globale per il riutilizzo delle connessioni TCP (molto più veloce)
session = requests.Session()

def get_poster_from_tmdb(imdb_id):
    """
    Cerca il poster su TMDB usando l'ID IMDb con retry automatico per Rate Limit.
    """
    if not isinstance(imdb_id, str):
        return None
        
    url = f"https://api.themoviedb.org/3/find/{imdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "external_source": "imdb_id"
    }
    
    attempts = 0
    max_attempts = 3
    
    while attempts < max_attempts:
        try:
            response = session.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("movie_results", [])
                if results:
                    poster_path = results[0].get("poster_path")
                    if poster_path:
                        return f"https://image.tmdb.org/t/p/w500{poster_path}"
                return None
            
            elif response.status_code == 429:
                # Rate limit hit - backoff dinamico o default breve
                retry_after = int(response.headers.get("Retry-After", 1))
                time.sleep(retry_after)
                attempts += 1
                continue
                
            else:
                return None

        except Exception as e:
            # Errori di rete temporanei
            time.sleep(0.5)
            attempts += 1
    
    return None

def main():
    # Controlla se esiste un file parziale da cui riprendere
    if os.path.exists(OUTPUT_CSV):
        print(f"📂 Trovato salvataggio precedente, riprendo da: {OUTPUT_CSV}")
        file_to_read = OUTPUT_CSV
    else:
        print(f"📂 Lettura file iniziale: {INPUT_CSV}")
        file_to_read = INPUT_CSV

    try:
        df = pd.read_csv(file_to_read, low_memory=False)
    except FileNotFoundError:
        print(f"❌ File non trovato: {file_to_read}")
        return

    # Conta quanti mancano
    missing_mask = df['poster_url'].isna() | (df['poster_url'] == '')
    total_missing = missing_mask.sum()
    
    print(f"📊 Totale film: {len(df)}")
    print(f"🖼️  Poster mancanti: {total_missing}")
    
    if total_missing == 0:
        print("✅ Tutti i film hanno già un poster!")
        return

    print("🚀 Inizio recupero poster da TMDB (Multi-thread Optimized)...")
    
    # Configurazione Threading - Spinto al massimo
    MAX_WORKERS = 50  # 50 thread paralleli per saturare il rate limit
    
    # Funzione helper per il thread
    def process_row(index, row):
        imdb_id = row.get('imdb_title_id')
        poster = get_poster_from_tmdb(imdb_id)
        return index, row['title'], imdb_id, poster

    count = 0
    updated_count = 0
    
    # Esecuzione parallela
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Sottometti tutti i task
        future_to_movie = {
            executor.submit(process_row, idx, r): idx 
            for idx, r in df[missing_mask].iterrows()
        }
        
        try:
            for future in concurrent.futures.as_completed(future_to_movie):
                idx, title, imdb_id, poster_url = future.result()
                count += 1
                
                if poster_url:
                    df.at[idx, 'poster_url'] = poster_url
                    updated_count += 1
                    print(f"✅ [{updated_count}/{total_missing}] Trovato per {title}")
                else:
                    print(f"❌ [{count}/{total_missing}] Non trovato per {imdb_id} - {title}")
                
                # Salvataggio intermedio ogni 100 elaborati (non richieste, ma completamenti)
                if count % 100 == 0:
                    print(f"💾 Salvataggio intermedio ({count} processati)...")
                    df.to_csv(OUTPUT_CSV, index=False)
                    
        except KeyboardInterrupt:
            print("\n🛑 Interruzione manuale rilevata! Salvataggio in corso...")
            df.to_csv(OUTPUT_CSV, index=False)
            print("✅ Salvataggio completato.")
            return

    # Salvataggio finale
    print("💾 Salvataggio finale...")
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Finito! File salvato in: {OUTPUT_CSV}")

if __name__ == "__main__":
    if TMDB_API_KEY == "LA_TUA_CHIAVE_API_MDB":
        print("⚠️  ATTENZIONE: Devi inserire la tua API KEY di TMDB nello script!")
    else:
        main()
