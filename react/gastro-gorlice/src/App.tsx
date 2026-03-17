import React, { useState, useEffect } from 'react';

// --- Interfejsy danych ---
interface Post {
  content: string;
  images: string[];
}

interface RestaurantData {
  restaurant_name: string;
  restaurant_url: string;
  posts: Post[];
  scraped_at: string;
}

interface FlattenedPost extends Post {
  restaurantName: string;
  restaurantUrl: string;
  scrapedAt: string;
}

const App: React.FC = () => {
  const [allPosts, setAllPosts] = useState<FlattenedPost[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isGalleryOpen, setIsGalleryOpen] = useState(false);

  // --- Pobieranie i filtrowanie danych ---
  useEffect(() => {
    fetch('/gastro_data.json')
      .then((res) => res.json())
      .then((data: RestaurantData[]) => {
        const uniquePosts: FlattenedPost[] = [];
        const seenFingerprints = new Set<string>();

        data.forEach((restaurant) => {
          restaurant.posts.forEach((post) => {
            // --- 1. NAPRAWA ZDUBLOWANEJ TREŚCI WEWNĄTRZ POSTA ---
            const lines = post.content.split('\n');
            const uniqueLines: string[] = [];
            const seenLines = new Set<string>();

            lines.forEach(line => {
              const trimmedLine = line.trim();
              if (trimmedLine === "" || !seenLines.has(trimmedLine)) {
                uniqueLines.push(line);
                if (trimmedLine !== "") seenLines.add(trimmedLine);
              }
            });

            const cleanContent = uniqueLines.join('\n').trim();

            // --- 2. FILTROWANIE DUPLIKATÓW MIĘDZY POSTAMI ---
            const fingerprint = cleanContent
              .toLowerCase()
              .replace(/[^a-z0-9]/g, "");

            if (fingerprint.length > 10 && !seenFingerprints.has(fingerprint)) {
              seenFingerprints.add(fingerprint);
              uniquePosts.push({
                ...post,
                content: cleanContent,
                restaurantName: restaurant.restaurant_name,
                restaurantUrl: restaurant.restaurant_url,
                scrapedAt: restaurant.scraped_at,
              });
            }
          });
        });

        setAllPosts(uniquePosts);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error("Błąd ładowania danych:", err);
        setIsLoading(false);
      });
  }, []);

  // --- Nawigacja ---
  const handleNext = () => {
    setIsGalleryOpen(false);
    setCurrentIndex((prev) => (prev + 1) % allPosts.length);
  };

  const handlePrev = () => {
    setIsGalleryOpen(false);
    setCurrentIndex((prev) => (prev - 1 + allPosts.length) % allPosts.length);
  };

  // --- Renderowanie ---
  if (isLoading) return <div style={fullScreenCenter}>Ładowanie danych...</div>;
  if (allPosts.length === 0) return <div style={fullScreenCenter}>Brak postów.</div>;

  const current = allPosts[currentIndex];

  return (
    <div style={containerStyle}>
      {/* 20% szerokości - Lewy margines */}
      <div style={sideColumn}></div>

      {/* 60% szerokości - Główna treść */}
      <div style={mainColumn}>
        <div style={cardStyle}>
          <div style={{ marginBottom: '20px' }}>
            <h2 style={{ margin: 0 }}>
              <a href={current.restaurantUrl} target="_blank" rel="noreferrer" style={linkStyle}>
                {decodeURIComponent(current.restaurantName).replace(/-/g, ' ')}
              </a>
            </h2>
            <small style={{ color: '#888' }}>📅 {current.scrapedAt}</small>
          </div>

          <div style={contentBoxStyle}>{current.content}</div>

          <div style={imageContainerStyle}>
            {current.images.length === 1 ? (
              <img src={current.images[0]} alt="Post" style={singleImageStyle} />
            ) : current.images.length > 1 ? (
              <button onClick={() => setIsGalleryOpen(true)} style={galleryBtnStyle}>
                📸 Zobacz galerię ({current.images.length})
              </button>
            ) : null}
          </div>
        </div>

        {/* Nawigacja */}
        <div style={navStyle}>
          <button onClick={handlePrev} style={navBtnStyle}>Poprzedni</button>
          <span style={{ fontWeight: 'bold', fontSize: '1.2rem' }}>{currentIndex + 1} / {allPosts.length}</span>
          <button onClick={handleNext} style={navBtnStyle}>Następny</button>
        </div>
      </div>

      {/* 20% szerokości - Prawy margines */}
      <div style={sideColumn}></div>

      {/* MODAL GALERII z przyciskiem zamykania */}
      {isGalleryOpen && (
        <div style={modalOverlayStyle} onClick={() => setIsGalleryOpen(false)}>
          {/* Przycisk ZAMKNIJ w prawym górnym rogu ekranu */}
          <button 
            style={closeBtnStyle} 
            onClick={(e) => {
              e.stopPropagation(); // Zapobiega zamknięciu przez kliknięcie w nakładkę
              setIsGalleryOpen(false);
            }}
          >
            ZAMKNIJ
          </button>
          <div style={modalContentStyle} onClick={e => e.stopPropagation()}>
            {current.images.map((img, i) => (
              <img key={i} src={img} alt="Galeria" style={galleryImageStyle} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// --- Style ---
const containerStyle: React.CSSProperties = {
  display: 'flex',
  minHeight: '100vh',
  backgroundColor: '#353839', // Tło onyxowe dla całości
  color: '#eee',
  fontFamily: 'system-ui, sans-serif',
};

const fullScreenCenter: React.CSSProperties = {
  height: '100vh',
  backgroundColor: '#353839',
  color: 'white',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
};

const sideColumn: React.CSSProperties = { width: '20%', backgroundColor: 'transparent' };

const mainColumn: React.CSSProperties = {
  width: '60%',
  padding: '40px 15px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
};

const cardStyle: React.CSSProperties = {
  width: '100%',
  maxWidth: '700px',
  backgroundColor: 'rgba(255,255,255,0.05)',
  padding: '30px',
  borderRadius: '15px',
  border: '1px solid rgba(255,255,255,0.1)',
  boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
};

const contentBoxStyle: React.CSSProperties = { whiteSpace: 'pre-line', fontSize: '1.1rem', lineHeight: '1.6' };

const linkStyle: React.CSSProperties = { color: '#4db8ff', textDecoration: 'none' };

const imageContainerStyle: React.CSSProperties = { textAlign: 'center', marginTop: '20px' };

const singleImageStyle: React.CSSProperties = { maxWidth: '100%', maxHeight: '500px', borderRadius: '10px' };

const galleryBtnStyle: React.CSSProperties = {
  padding: '12px 24px',
  backgroundColor: '#4db8ff',
  color: 'white',
  border: 'none',
  borderRadius: '25px',
  cursor: 'pointer',
  fontWeight: 'bold',
  fontSize: '1rem',
};

const navStyle: React.CSSProperties = { display: 'flex', gap: '25px', alignItems: 'center', marginTop: '30px' };

const navBtnStyle: React.CSSProperties = {
  padding: '12px 28px',
  cursor: 'pointer',
  borderRadius: '8px',
  border: 'none',
  fontWeight: 'bold',
  backgroundColor: '#f0f0f0',
  color: '#333',
};

const modalOverlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0, left: 0, right: 0, bottom: 0,
  backgroundColor: 'rgba(0,0,0,0.9)',
  zIndex: 1000,
  padding: '40px',
  overflowY: 'auto',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'flex-start', // Zaczyna od góry, aby umożliwić przewijanie
};

const closeBtnStyle: React.CSSProperties = {
  position: 'absolute',
  top: '20px',
  right: '20px',
  padding: '10px 20px',
  backgroundColor: '#fff',
  color: '#333',
  border: 'none',
  borderRadius: '5px',
  cursor: 'pointer',
  fontWeight: 'bold',
  zIndex: 1010, // Nad nakładką i obrazami
  fontSize: '1rem',
};

const modalContentStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '20px',
  maxWidth: '800px',
  paddingTop: '60px', // Odstęp od góry, aby przycisk go nie zasłaniał
};

const galleryImageStyle: React.CSSProperties = {
  width: '100%',
  borderRadius: '8px',
  boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
};

export default App;