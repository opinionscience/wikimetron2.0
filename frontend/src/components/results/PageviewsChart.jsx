// File: src/components/results/PageviewsChart.jsx
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
  const [selectedPages, setSelectedPages] = useState(pages?.slice(0, 5) || []);

  // Couleurs pour les différentes pages
  const colors = [
      '#3b82f6', // Bleu
  '#ef4444', // Rouge
  '#10b981', // Vert
  '#f59e0b', // Orange
  '#8b5cf6', // Violet
  '#06b6d4'  // Cyan
  ];

  // Récupérer les données pageviews
  const fetchPageviews = async () => {
    if (!selectedPages.length || !analysisConfig) return;

    setLoading(true);
    setError(null);

    try {
      const pageNames = selectedPages.map(page => page.title || page);
      
      const data = await apiService.fetchPageviewsForChart(
        pageNames,
        analysisConfig.startDate,
        analysisConfig.endDate,
        analysisConfig.language || 'fr'
      );

      setPageviewsData(data);
    } catch (err) {
      console.error('Erreur récupération pageviews:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Effet pour charger les données
  useEffect(() => {
    setSelectedPages(pages?.slice(0, 5) || []);
  }, [pages]);

  useEffect(() => {
    fetchPageviews();
  }, [selectedPages, analysisConfig]);

  // Gérer la sélection des pages
  const handlePageToggle = (pageIndex) => {
    const page = pages[pageIndex];
    const isSelected = selectedPages.some(p => (p.title || p) === (page.title || page));
    
    if (isSelected) {
      setSelectedPages(prev => prev.filter(p => (p.title || p) !== (page.title || page)));
    } else {
      if (selectedPages.length < 10) {
        setSelectedPages(prev => [...prev, page]);
      }
    }
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
          <p className="tooltip-date">{`${label}`}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color }}>
              {`${entry.dataKey}: ${formatNumber(entry.value)} vues`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Calculer les totaux pour l'en-tête
  const getTotalViews = () => {
    if (!pageviewsData?.metadata?.pages_stats) return 0;
    return Object.values(pageviewsData.metadata.pages_stats)
      .reduce((sum, stats) => sum + (stats.total_views || 0), 0);
  };

  return (
    <div className="pageviews-chart-simple">
      {/* Sélecteur de pages compact si nécessaire */}
      {pages && pages.length > 1 && (
        <div className="chart-pages-selector-minimal">
          <div className="pages-selector-chips">
            {pages.map((page, index) => {
              const isSelected = selectedPages.some(p => (p.title || p) === (page.title || page));
              const color = colors[index % colors.length];
              
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
                >
                  <span className="chip-title">
                    {(page.title || page).length > 15 
                      ? `${(page.title || page).substring(0, 15)}...` 
                      : (page.title || page)
                    }
                  </span>
                  {isSelected && <span className="chip-check">✓</span>}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Graphique seulement */}
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
              
              {selectedPages.map((page, index) => {
                const pageName = page.title || page;
                return (
                  <Line
                    key={pageName}
                    type="monotone"
                    dataKey={pageName}
                    stroke={colors[index % colors.length]}
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
          <span>Chargement...</span>
        </div>
      )}

      {error && (
        <div className="chart-error-minimal">
          <span>❌ {error}</span>
          <button onClick={fetchPageviews} className="retry-btn-minimal">
            Réessayer
          </button>
        </div>
      )}
    </div>
  );
};
export default PageviewsChart;