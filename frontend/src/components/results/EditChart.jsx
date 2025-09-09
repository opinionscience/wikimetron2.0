import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { apiService } from '../../services/api.js';

const EditChart = ({ pages, analysisConfig }) => {
  const [editData, setEditData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPages, setSelectedPages] = useState([]);
  const [editorType, setEditorType] = useState('user');
  const [pageLabelsMap, setPageLabelsMap] = useState(new Map());

  // Couleurs pour les différentes pages (cohérent avec PageviewsChart)
  const colors = [
    '#3b82f6', // Bleu
    '#ef4444', // Rouge
    '#10b981', // Vert
    '#f59e0b', // Orange
    '#8b5cf6', // Violet
    '#06b6d4'  // Cyan
  ];

  // Normaliser une page (peut être un objet d'analyse ou une string)
  const normalizePage = (page) => {
    if (typeof page === 'object' && page !== null) {
      return page.original_input || page.title || String(page);
    }
    return String(page);
  };

  // Créer un label d'affichage user-friendly
  const createUserLabel = (page) => {
    const normalizedPage = normalizePage(page);
    
    if (typeof normalizedPage === 'string' && normalizedPage.startsWith('http') && normalizedPage.includes('wikipedia.org')) {
      try {
        const url = new URL(normalizedPage);
        const hostname = url.hostname;
        const lang = hostname.split('.')[0];
        
        if (url.pathname.includes('/wiki/')) {
          const rawTitle = url.pathname.split('/wiki/')[1];
          const cleanTitle = decodeURIComponent(rawTitle.replace(/_/g, ' '));
          return { label: cleanTitle, lang: lang, original: normalizedPage };
        }
      } catch (e) {
        console.warn('Erreur parsing URL:', e);
      }
    }
    
    // Pour les objets d'analyse, essayer d'utiliser le titre
    if (typeof page === 'object' && page !== null && page.title) {
      return { 
        label: page.title, 
        lang: page.language || null, 
        original: page.original_input || normalizedPage 
      };
    }
    
    return { label: normalizedPage, lang: null, original: normalizedPage };
  };

  // Initialiser le mapping des labels et pages sélectionnées
  useEffect(() => {
    if (pages && pages.length > 0) {
      const labelMap = new Map();
      const normalizedPages = [];
      
      pages.forEach((page) => {
        const pageInfo = createUserLabel(page);
        const normalizedPage = normalizePage(page);
        
        labelMap.set(normalizedPage, pageInfo.label);
        normalizedPages.push(normalizedPage);
      });
      
      setPageLabelsMap(labelMap);
      
      // Sélectionner les premières pages normalisées par défaut
      const initialSelection = normalizedPages.slice(0, Math.min(5, normalizedPages.length));
      setSelectedPages(initialSelection);
      
      console.log('EditChart - Pages analysées:', pages.map(p => {
        const normalized = normalizePage(p);
        return { 
          original: p,
          normalized: normalized,
          label: labelMap.get(normalized),
          info: createUserLabel(p)
        };
      }));
    }
  }, [pages]);

  // Récupérer les données d'éditions (version multi-langues simplifiée)
  const fetchEditData = async () => {
    if (!selectedPages.length || !analysisConfig?.startDate || !analysisConfig?.endDate) {
      console.log('Conditions manquantes pour récupérer les éditions:', {
        selectedPages: selectedPages.length,
        startDate: analysisConfig?.startDate,
        endDate: analysisConfig?.endDate
      });
      return;
    }

    setLoading(true);
    setError(null);

    try {
      console.log('🚀 Requête éditions multi-langues:');
      console.log('- Pages sélectionnées:', selectedPages);
      console.log('- Type éditeur:', editorType);
      console.log('- Période:', analysisConfig.startDate, 'à', analysisConfig.endDate);
      
      // IMPORTANT: Envoyer les pages telles quelles (URLs complètes)
      // L'API se charge de la détection de langue per-page
      const requestData = {
        pages: selectedPages,
        start_date: analysisConfig.startDate,
        end_date: analysisConfig.endDate,
        editor_type: editorType,
        // On ne spécifie PAS default_language car toutes nos pages sont des URLs
      };
      
      console.log('📤 Données de requête éditions:', JSON.stringify(requestData, null, 2));
      
      const data = await apiService.fetchEditTimeseriesForChart(
        selectedPages,
        analysisConfig.startDate,
        analysisConfig.endDate,
        { editorType: editorType } // Pas d'options de langue, détection auto
      );

      console.log('📥 Données éditions reçues:', data);
      
      if (data.metadata?.languages_summary) {
        console.log('🌍 Langues détectées par l\'API:', data.metadata.languages_summary);
      }
      
      // Vérifier la correspondance des données
      if (data.data && data.data.length > 0) {
        const dataKeys = Object.keys(data.data[0]).filter(key => key !== 'date');
        console.log('📊 Clés de données reçues:', dataKeys);
        console.log('🔍 Pages demandées:', selectedPages);
        
        const missingPages = selectedPages.filter(page => !dataKeys.includes(page));
        if (missingPages.length > 0) {
          console.warn('⚠️ Pages manquantes dans les données:', missingPages);
        }
      }
      
      setEditData(data);
    } catch (err) {
      console.error('❌ Erreur récupération éditions:', err);
      setError(`Erreur: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Récupérer les données quand la sélection ou config change
  useEffect(() => {
    if (selectedPages.length > 0 && analysisConfig) {
      console.log('🔄 Déclenchement fetchEditData - pages:', selectedPages.length, 'config:', !!analysisConfig);
      fetchEditData();
    }
  }, [selectedPages, analysisConfig, editorType]);

  // Gérer la sélection/déselection des pages
  const handlePageToggle = (pageIndex) => {
    const originalPage = pages[pageIndex];
    const normalizedPage = normalizePage(originalPage);
    const isSelected = selectedPages.includes(normalizedPage);
    
    if (isSelected) {
      setSelectedPages(prev => prev.filter(p => p !== normalizedPage));
    } else {
      if (selectedPages.length < 10) {
        setSelectedPages(prev => [...prev, normalizedPage]);
      }
    }
  };

  // Obtenir la couleur pour une page
  const getPageColor = (normalizedPage) => {
    const originalIndex = pages?.findIndex(p => normalizePage(p) === normalizedPage) ?? 0;
    return colors[originalIndex % colors.length];
  };

  // Formatter les nombres
  const formatNumber = (value) => {
    if (value >= 1000) {
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
            const normalizedUrl = entry.dataKey;
            const userLabel = pageLabelsMap.get(normalizedUrl) || normalizedUrl;
            
            // Retrouver la page originale pour extraire les infos de langue
            const originalPage = pages?.find(p => normalizePage(p) === normalizedUrl);
            const pageInfo = createUserLabel(originalPage || normalizedUrl);
            
            return (
              <p key={index} style={{ color: entry.color }}>
                {userLabel}
                {pageInfo.lang && <span className="lang-indicator"> ({pageInfo.lang.toUpperCase()})</span>}
                : {formatNumber(entry.value)} éditions
              </p>
            );
          })}
          {editData?.metadata?.languages_summary && Object.keys(editData.metadata.languages_summary).length > 1 && (
            <p className="languages-summary">
              Langues: {Object.entries(editData.metadata.languages_summary)
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
    <div className="pageviews-chart-container">
      

      {/* Sélecteur de pages */}
      {pages && pages.length > 1 && (
        <div className="chart-pages-selector-minimal">
          <div className="pages-selector-chips">
            {pages.map((page, index) => {
              const normalizedPage = normalizePage(page);
              const isSelected = selectedPages.includes(normalizedPage);
              const color = colors[index % colors.length];
              const pageInfo = createUserLabel(page);
              const displayLabel = pageLabelsMap.get(normalizedPage) || pageInfo.label;
              
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

      {/* États de chargement */}
      {loading && (
        <div className="chart-loading-minimal">
          <div className="mini-spinner"></div>
          <span>Chargement des données d'éditions...</span>
        </div>
      )}

      {error && (
        <div className="chart-error-minimal">
          <span>{error}</span>
          <button onClick={fetchEditData} className="retry-btn-minimal">
            Réessayer
          </button>
        </div>
      )}

      {/* Graphique */}
      {editData && !loading && !error && (
        <div className="chart-wrapper-simple">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={editData.data}>
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
              
              {selectedPages.map((normalizedPage) => {
                const lineColor = getPageColor(normalizedPage);
                
                return (
                  <Line
                    key={normalizedPage}
                    type="monotone"
                    dataKey={normalizedPage}
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

      {/* État vide */}
      {!editData && !loading && !error && selectedPages.length === 0 && (
        <div className="chart-empty-state">
          <span>Sélectionnez au moins une page pour voir le graphique</span>
        </div>
      )}
    </div>
  );
};

export default EditChart;