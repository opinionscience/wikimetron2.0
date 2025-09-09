import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { apiService } from '../../services/api.js';

const PageviewsChart = ({ pages, analysisConfig }) => {
  const [pageviewsData, setPageviewsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPages, setSelectedPages] = useState([]);
  const [pageLabelsMap, setPageLabelsMap] = useState(new Map()); // Map: original_input -> user_label

  // Couleurs pour les différentes pages
  const colors = [
    '#3b82f6', // Bleu
    '#ef4444', // Rouge
    '#10b981', // Vert
    '#f59e0b', // Orange
    '#8b5cf6', // Violet
    '#06b6d4'  // Cyan
  ];

  // Créer un label d'affichage user-friendly
  const createUserLabel = (page, index) => {
    if (typeof page === 'string' && page.startsWith('http') && page.includes('wikipedia.org')) {
      try {
        const url = new URL(page);
        const hostname = url.hostname;
        const lang = hostname.split('.')[0];
        
        if (url.pathname.includes('/wiki/')) {
          const rawTitle = url.pathname.split('/wiki/')[1];
          const cleanTitle = decodeURIComponent(rawTitle.replace(/_/g, ' '));
          return { label: cleanTitle, lang: lang, original: page };
        }
      } catch (e) {
        console.warn('Erreur parsing URL:', e);
      }
    }
    
    // Fallback pour les pages non-URL
    return { label: String(page), lang: null, original: page };
  };

  // Initialiser le mapping des labels et pages sélectionnées
  useEffect(() => {
    if (pages && pages.length > 0) {
      const labelMap = new Map();
      
      pages.forEach((page) => {
        const pageInfo = createUserLabel(page);
        labelMap.set(page, pageInfo.label);
      });
      
      setPageLabelsMap(labelMap);
      
      // Sélectionner les premières pages par défaut
      const initialSelection = pages.slice(0, Math.min(5, pages.length));
      setSelectedPages(initialSelection);
      
      console.log('Pages analysées:', pages.map(p => ({ 
        original: p, 
        label: labelMap.get(p),
        info: createUserLabel(p)
      })));
    }
  }, [pages]);

  // Récupérer les données pageviews (version multi-langues simplifiée)
  const fetchPageviews = async () => {
    if (!selectedPages.length || !analysisConfig?.startDate || !analysisConfig?.endDate) {
      console.log('Conditions manquantes pour récupérer les pageviews:', {
        selectedPages: selectedPages.length,
        startDate: analysisConfig?.startDate,
        endDate: analysisConfig?.endDate
      });
      return;
    }

    setLoading(true);
    setError(null);

    try {
      console.log('🚀 Requête pageviews multi-langues:');
      console.log('- Pages sélectionnées:', selectedPages);
      console.log('- Période:', analysisConfig.startDate, 'à', analysisConfig.endDate);
      
      // IMPORTANT: Envoyer les pages telles quelles (URLs complètes)
      // L'API se charge de la détection de langue per-page
      const requestData = {
        pages: selectedPages, // Pas de transformation, on garde les URLs originales
        start_date: analysisConfig.startDate,
        end_date: analysisConfig.endDate,
        // On ne spécifie PAS default_language car toutes nos pages sont des URLs
      };
      
      console.log('📤 Données de requête:', JSON.stringify(requestData, null, 2));
      
      const data = await apiService.fetchPageviewsForChart(
        selectedPages,
        analysisConfig.startDate,
        analysisConfig.endDate,
        {} // Pas d'options, détection auto
      );

      console.log('📥 Données pageviews reçues:', data);
      
      if (data.metadata?.languages_summary) {
        console.log('🌍 Langues détectées par l\'API:', data.metadata.languages_summary);
      }
      
      // Vérifier que les données correspondent aux pages demandées
      if (data.data && data.data.length > 0) {
        const dataKeys = Object.keys(data.data[0]).filter(key => key !== 'date');
        console.log('📊 Clés de données reçues:', dataKeys);
        console.log('🔍 Pages demandées:', selectedPages);
        
        // Vérifier la correspondance
        const missingPages = selectedPages.filter(page => !dataKeys.includes(page));
        if (missingPages.length > 0) {
          console.warn('⚠️ Pages manquantes dans les données:', missingPages);
        }
      }
      
      setPageviewsData(data);
    } catch (err) {
      console.error('❌ Erreur récupération pageviews:', err);
      setError(`Erreur: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Récupérer les données quand la sélection ou config change
  useEffect(() => {
    if (selectedPages.length > 0 && analysisConfig) {
      console.log('🔄 Déclenchement fetchPageviews - pages:', selectedPages.length, 'config:', !!analysisConfig);
      fetchPageviews();
    }
  }, [selectedPages, analysisConfig]);

  // Gérer la sélection/déselection des pages
  const handlePageToggle = (pageIndex) => {
    const page = pages[pageIndex];
    const isSelected = selectedPages.includes(page);
    
    if (isSelected) {
      setSelectedPages(prev => prev.filter(p => p !== page));
    } else {
      if (selectedPages.length < 10) {
        setSelectedPages(prev => [...prev, page]);
      }
    }
  };

  // Obtenir la couleur pour une page
  const getPageColor = (page) => {
    const originalIndex = pages?.indexOf(page) ?? 0;
    return colors[originalIndex % colors.length];
  };

  // Formatter les nombres
  const formatNumber = (value) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toLocaleString();
  };

  // Tooltip personnalisé
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="pageviews-tooltip">
          <p className="tooltip-date">{label}</p>
          {payload.map((entry, index) => {
            // entry.dataKey est l'URL originale
            const originalUrl = entry.dataKey;
            const userLabel = pageLabelsMap.get(originalUrl) || originalUrl;
            const pageInfo = createUserLabel(originalUrl);
            
            return (
              <p key={index} style={{ color: entry.color }}>
                {userLabel}
                {pageInfo.lang && <span className="lang-indicator"> ({pageInfo.lang.toUpperCase()})</span>}
                : {formatNumber(entry.value)} vues
              </p>
            );
          })}
          {pageviewsData?.metadata?.languages_summary && Object.keys(pageviewsData.metadata.languages_summary).length > 1 && (
            <p className="languages-summary">
              Langues: {Object.entries(pageviewsData.metadata.languages_summary)
                .map(([lang, count]) => `${lang}(${count})`)
                .join(', ')}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="pageviews-chart-simple">
    

      {/* Sélecteur de pages */}
      {pages && pages.length > 1 && (
        <div className="chart-pages-selector-minimal">
          <div className="pages-selector-chips">
            {pages.map((page, index) => {
              const isSelected = selectedPages.includes(page);
              const color = colors[index % colors.length];
              const pageInfo = createUserLabel(page);
              const displayLabel = pageLabelsMap.get(page) || pageInfo.label;
              
              return (
                <button
                  key={index}
                  className={`page-chip-minimal ${isSelected ? 'selected' : ''}`}
                  onClick={() => handlePageToggle(index)}
                  style={isSelected ? { 
                    borderColor: color, 
                    backgroundColor: `${color}15`,
                    color: color
                  } : {}}
                  disabled={!isSelected && selectedPages.length >= 10}
                >
                  <span className="chip-title">
                    {displayLabel.length > 15 
                      ? `${displayLabel.substring(0, 15)}...` 
                      : displayLabel
                    }
                  </span>
                  {pageInfo.lang && (
                    <span className="chip-lang-indicator">
                      &nbsp;{pageInfo.lang.toUpperCase()}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          {selectedPages.length >= 10 && (
            <div className="selection-limit-info">
              Maximum 10 pages sélectionnées
            </div>
          )}
        </div>
      )}

      {/* Graphique */}
      {pageviewsData && !loading && !error && (
        <div className="chart-wrapper-simple">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={pageviewsData.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 11, fill: '#666' }}
                angle={-45}
                textAnchor="end"
                height={60}
                interval="preserveStartEnd"
              />
              <YAxis 
                tick={{ fontSize: 11, fill: '#666' }}
                tickFormatter={formatNumber}
              />
              <Tooltip content={<CustomTooltip />} />
              
              {selectedPages.map((page) => {
                const lineColor = getPageColor(page);
                
                return (
                  <Line
                    key={page} // Utilise l'URL originale comme clé
                    type="monotone"
                    dataKey={page} // L'API retourne les données indexées par URL originale
                    stroke={lineColor}
                    strokeWidth={2}
                    dot={{ r: 2 }}
                    activeDot={{ r: 4 }}
                    connectNulls={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* États de chargement */}
      {loading && (
        <div className="chart-loading-minimal">
          <div className="mini-spinner"></div>
          <span>Chargement des données pageviews...</span>
        </div>
      )}

      {error && (
        <div className="chart-error-minimal">
          <span>{error}</span>
          <button onClick={fetchPageviews} className="retry-btn-minimal">
            Réessayer
          </button>
        </div>
      )}

      {/* État vide */}
      {!pageviewsData && !loading && !error && selectedPages.length === 0 && (
        <div className="chart-empty-state">
          <span>Sélectionnez au moins une page pour voir le graphique</span>
        </div>
      )}
    </div>
  );
};

export default PageviewsChart;