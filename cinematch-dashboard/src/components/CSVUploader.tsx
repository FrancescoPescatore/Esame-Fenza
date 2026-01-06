import { useState, useRef } from 'react';
import './CSVUploader.css';

interface UploadStats {
    total_watched: number;
    avg_rating: number;
    total_5_stars: number;
    total_1_stars: number;
}

interface CSVUploaderProps {
    onUploadSuccess?: (stats: UploadStats) => void;
}

export function CSVUploader({ onUploadSuccess }: CSVUploaderProps) {
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleUpload = async (file: File) => {
        if (!file.name.endsWith('.csv')) {
            setMessage({ type: 'error', text: 'Per favore carica un file CSV' });
            return;
        }

        setUploading(true);
        setMessage(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:8000/upload-csv', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                setMessage({ 
                    type: 'success', 
                    text: `✅ Caricati ${data.count} film! Media rating: ${data.stats.avg_rating}⭐` 
                });
                if (onUploadSuccess) {
                    onUploadSuccess(data.stats);
                }
            } else {
                setMessage({ type: 'error', text: data.detail || 'Errore durante il caricamento' });
            }
        } catch (err) {
            setMessage({ type: 'error', text: 'Errore di connessione al server' });
        } finally {
            setUploading(false);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleUpload(file);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleUpload(file);
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(true);
    };

    const handleDragLeave = () => {
        setDragOver(false);
    };

    return (
        <div className="csv-uploader">
            <div 
                className={`upload-zone ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                />
                
                {uploading ? (
                    <div className="upload-loading">
                        <div className="spinner"></div>
                        <p>Analizzando i tuoi film...</p>
                    </div>
                ) : (
                    <>
                        <div className="upload-icon">📁</div>
                        <h3>Carica il tuo export Letterboxd</h3>
                        <p>Trascina qui il file ratings.csv o clicca per selezionarlo</p>
                        <span className="upload-hint">Formato supportato: CSV da Letterboxd</span>
                    </>
                )}
            </div>

            {message && (
                <div className={`upload-message ${message.type}`}>
                    {message.text}
                </div>
            )}

            <div className="upload-info">
                <h4>📋 Come esportare da Letterboxd:</h4>
                <ol>
                    <li>Vai su <strong>letterboxd.com</strong> → Il tuo profilo</li>
                    <li>Clicca su <strong>Settings</strong> → <strong>Import & Export</strong></li>
                    <li>Scarica <strong>Export your data</strong></li>
                    <li>Carica qui il file <code>ratings.csv</code></li>
                </ol>
            </div>
        </div>
    );
}
