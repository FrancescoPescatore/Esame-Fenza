// ============================================
// CINEMATCH - API SERVICE
// ============================================

const API_BASE_URL = 'http://localhost:8000';

// Interfacce per i dati
export interface UserStats {
  filmsWatched: number;
  averageRating: number;
  totalRatings: number;
  ratingDistribution: Record<number, number>;
  topRatedMovies: MovieRating[];
  recentMovies: MovieRating[];
}

export interface MovieRating {
  name: string;
  year: number;
  rating: number;
  date: string;
  letterboxdUri?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface SentimentResult {
  movie: string;
  sentiment_score: number;
  timestamp: string;
  type: string;
}

// Helper per le richieste autenticate
const getAuthHeaders = (): HeadersInit => {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` })
  };
};

// ============================================
// AUTH API
// ============================================

export const authAPI = {
  async login(username: string, password: string): Promise<AuthResponse> {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login fallito');
    }
    
    const data = await response.json();
    localStorage.setItem('token', data.access_token);
    return data;
  },

  async register(username: string, password: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registrazione fallita');
    }
    
    return response.json();
  },

  logout(): void {
    localStorage.removeItem('token');
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  }
};

// ============================================
// DATA API
// ============================================

export const dataAPI = {
  async uploadCSV(file: File): Promise<UserStats> {
    const token = localStorage.getItem('token');
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/upload-csv`, {
      method: 'POST',
      headers: {
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload fallito');
    }
    
    return response.json();
  },

  async getUserStats(): Promise<UserStats | null> {
    const response = await fetch(`${API_BASE_URL}/user-stats`, {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error('Errore nel recupero delle statistiche');
    }
    
    return response.json();
  },

  async getUserHistory(): Promise<SentimentResult[]> {
    const response = await fetch(`${API_BASE_URL}/user-history`, {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      throw new Error('Errore nel recupero della cronologia');
    }
    
    const data = await response.json();
    return data.history || [];
  }
};

// ============================================
// SENTIMENT API
// ============================================

export const sentimentAPI = {
  async analyzeMovie(title: string): Promise<SentimentResult> {
    const response = await fetch(`${API_BASE_URL}/analyze-movie-sentiment/${encodeURIComponent(title)}`, {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      throw new Error('Errore nell\'analisi del sentiment');
    }
    
    const data = await response.json();
    return data.result;
  }
};

export default { authAPI, dataAPI, sentimentAPI };
