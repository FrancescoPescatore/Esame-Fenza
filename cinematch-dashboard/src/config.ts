// API Configuration
// In Docker, il frontend comunica con il backend tramite il nome del servizio
// Dal browser dell'utente, invece, si usa localhost perché il browser è sulla macchina host

// Determina l'URL base in base all'ambiente
const isDocker = typeof window !== 'undefined' && window.location.hostname !== 'localhost';
export const API_BASE_URL = isDocker 
    ? 'http://localhost:8000'  // Quando il browser accede da localhost
    : 'http://localhost:8000'; // Stesso URL per sviluppo locale

// In futuro si può usare una variabile d'ambiente:
// export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
