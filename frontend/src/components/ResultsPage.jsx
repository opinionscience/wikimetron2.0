// File: src/components/ResultsPage.jsx
import React, { useState, useEffect } from 'react';
import Layout from './Layout';
import { 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  Radar, 
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import { apiService } from '../services/api.js'; // Import du service API
import './ResultsPage.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8200';

// Fonction utilitaire pour rendre les valeurs métriques
const renderMetricValue = (value) => {
  if (typeof value === 'number') {
    return value.toFixed(3);
  }
  return value || '0.000';
};

// ✨ NOUVEAU : Composant Graphique Pageviews
const PageviewsChart = ({ pages, analysisConfig }) => {
  const [pageviewsData, setPageviewsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPages, setSelectedPages] = useState(pages?.slice(0, 5) || []); // Max 5 pages par défaut

  // Couleurs pour les différentes pages (même palette que le KiviatChart)
  const colors = [
    '#8b5cf6', '#ef4444', '#3b82f6', '#10b981', '#f59e0b', 
    '#ec4899', '#6366f1', '#14b8a6', '#f97316', '#84cc16'
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

  // Effet pour charger les données au montage et changement de sélection
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
      if (selectedPages.length < 10) { // Max 10 pages pour lisibilité
        setSelectedPages(prev => [...prev, page]);
      }
    }
  };

  // Formatter les nombres pour le tooltip
  const formatNumber = (value) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toLocaleString();
  };

  // Composant Tooltip personnalisé
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="pageviews-tooltip">
          <p className="tooltip-date">{`Date: ${label}`}</p>
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

  return (
    <div className="pageviews-container">
      <div className="pageviews-header">
        <h4>📈 Évolution des pages vues</h4>
        <div className="pageviews-period">
          {analysisConfig?.startDate} → {analysisConfig?.endDate}
        </div>
      </div>

      {/* Sélecteur de pages */}
      {pages && pages.length > 1 && (
        <div className="pageviews-selector">
          <p className="selector-label">
            Sélectionner les pages à afficher ({selectedPages.length}/10):
          </p>
          <div className="pages-selector-grid">
            {pages.map((page, index) => {
              const isSelected = selectedPages.some(p => (p.title || p) === (page.title || page));
              return (
                <div key={index} className="page-selector-item">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handlePageToggle(index)}
                    disabled={!isSelected && selectedPages.length >= 10}
                    id={`pageview-page-${index}`}
                  />
                  <label 
                    htmlFor={`pageview-page-${index}`}
                    className={isSelected ? 'selected' : ''}
                  >
                    {page.title || page}
                  </label>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* États de chargement et erreur */}
      {loading && (
        <div className="pageviews-loading">
          <div className="mini-spinner"></div>
          <span>Récupération des données pageviews...</span>
        </div>
      )}

      {error && (
        <div className="pageviews-error">
          <span>❌ Erreur: {error}</span>
          <button onClick={fetchPageviews} className="retry-btn">
            Réessayer
          </button>
        </div>
      )}

      {/* Graphique */}
      {pageviewsData && !loading && !error && (
        <>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={pageviewsData.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 12, fill: '#666' }}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis 
                tick={{ fontSize: 12, fill: '#666' }}
                tickFormatter={formatNumber}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              
              {selectedPages.map((page, index) => {
                const pageName = page.title || page;
                return (
                  <Line
                    key={pageName}
                    type="monotone"
                    dataKey={pageName}
                    stroke={colors[index % colors.length]}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                    connectNulls={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>

          {/* Statistiques résumées */}
          <div className="pageviews-stats">
            <h5>📊 Statistiques de la période</h5>
            <div className="stats-grid">
              {Object.entries(pageviewsData.metadata.pages_stats || {}).map(([pageName, stats]) => (
                <div key={pageName} className="stat-item">
                  <div className="stat-page-name">{pageName}</div>
                  <div className="stat-values">
                    <span>Total: {formatNumber(stats.total_views)}</span>
                    <span>Moyenne: {formatNumber(Math.round(stats.avg_views))}/jour</span>
                    <span>Maximum: {formatNumber(stats.max_views)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// Catégories de métriques
const METRIC_CATEGORIES = {
  heat: ['pageview_spike', 'edit_spike', 'revert_risk', 'protection_level', 'talk_intensity'],
  quality: ['citation_gap', 'blacklist_share', 'event_imbalance', 'recency_score', 'adq_score', 'domain_dominance'],
  risk: ['anon_edit', 'mean_contributor_balance', 'monopolization_score', 'avg_activity_score']
};

// Composant Kiviat Chart avec comparaison (inchangé)
const KiviatChart = ({ pages, selectedPageIndices = [0], showComparison = false }) => {
  const colors = [
    { stroke: '#8b5cf6', fill: '#8b5cf6', name: 'purple' },
    { stroke: '#ef4444', fill: '#ef4444', name: 'red' },
    { stroke: '#3b82f6', fill: '#3b82f6', name: 'blue' },
    { stroke: '#10b981', fill: '#10b981', name: 'green' },
    { stroke: '#f59e0b', fill: '#f59e0b', name: 'yellow' },
    { stroke: '#ec4899', fill: '#ec4899', name: 'pink' }
  ];

  const metrics = ['Heat', 'Quality', 'Risk'];
  const data = metrics.map(metric => {
    const dataPoint = { metric };
    
    selectedPageIndices.forEach((pageIndex, index) => {
      const page = pages[pageIndex];
      const scores = page?.scores || {};
      const metricKey = metric.toLowerCase();
      dataPoint[`page${pageIndex}`] = scores[metricKey] || 0;
      dataPoint[`page${pageIndex}Name`] = page?.title || `Page ${pageIndex + 1}`;
    });
    
    return dataPoint;
  });

  return (
    <div className="kiviat-container">
      <h4>
        📊 {showComparison ? 'Comparaison des profils' : 'Profil de sensibilité'}
      </h4>
      
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data}>
          <PolarGrid stroke="#e5e7eb" />
          <PolarAngleAxis 
            dataKey="metric" 
            tick={{ fill: '#374151', fontSize: 14, fontWeight: 'bold' }}
          />
          <PolarRadiusAxis 
            angle={90} 
            domain={[0, 1]} 
            tick={{ fill: '#6b7280', fontSize: 12 }}
            tickCount={6}
          />
          
          {selectedPageIndices.map((pageIndex, index) => {
            const color = colors[index % colors.length];
            return (
              <Radar
                key={pageIndex}
                name={pages[pageIndex]?.title || `Page ${pageIndex + 1}`}
                dataKey={`page${pageIndex}`}
                stroke={color.stroke}
                fill={color.fill}
                fillOpacity={showComparison ? 0.1 : 0.3}
                strokeWidth={3}
                dot={{ fill: color.stroke, strokeWidth: 2, r: showComparison ? 4 : 6 }}
              />
            );
          })}
        </RadarChart>
      </ResponsiveContainer>

      <div className="kiviat-legend">
        {selectedPageIndices.map((pageIndex, index) => {
          const page = pages[pageIndex];
          const scores = page?.scores || {};
          const color = colors[index % colors.length];
          
          return (
            <div key={pageIndex} className="kiviat-legend-item">
              <div className="kiviat-legend-color"
                style={{ backgroundColor: color.fill, borderColor: color.stroke }}
              ></div>
              <span className="kiviat-legend-name">
                {page?.title || `Page ${pageIndex + 1}`}
              </span>
              <div className="kiviat-legend-score" style={{ color: color.stroke }}>
                {renderMetricValue(scores.sensitivity)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Sous-composants inchangés
const LoadingView = ({ pagesCount, taskId }) => (
  <div className="content-card">
    <div className="loading-container">
      <svg className="spinner" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <h2>Analyse en cours...</h2>
      <p>Collecte des métriques pour {pagesCount} page(s)</p>
      <div className="summary-box mt-6">
        <p className="mb-0">Tâche ID: {taskId}</p>
      </div>
    </div>
  </div>
);

const ErrorView = ({ error, onBack }) => (
  <div className="content-card">
    <div className="loading-container">
      <h2 style={{ color: '#dc2626' }}>❌ Erreur</h2>
      <p style={{ color: '#dc2626' }}>{error}</p>
      <button onClick={onBack} className="btn btn-primary mt-6">
        Retour à la configuration
      </button>
    </div>
  </div>
);

// ✨ MODIFIÉ : Composant DetailedPageResult avec graphique pageviews
const DetailedPageResult = ({ pageResult, analysisConfig, allPages, currentPageIndex }) => {
  const [showComparison, setShowComparison] = useState(false);
  const [selectedPagesForComparison, setSelectedPagesForComparison] = useState([currentPageIndex]);
  const [activeTab, setActiveTab] = useState('sensitivity'); // Nouveau: gestion des onglets
  
  const scores = pageResult.scores || {};
  const metrics = pageResult.metrics || {};

  const handlePageToggle = (pageIndex) => {
    if (selectedPagesForComparison.includes(pageIndex)) {
      setSelectedPagesForComparison(prev => prev.filter(i => i !== pageIndex));
    } else {
      setSelectedPagesForComparison(prev => [...prev, pageIndex]);
    }
  };

  const effectiveSelection = showComparison 
    ? selectedPagesForComparison 
    : [currentPageIndex];

  return (
    <div className="space-y-6">
      {/* Header avec titre */}
      <div className="page-title-section">
        <h3>
          📊 Analyse détaillée: {pageResult.title}
        </h3>
      </div>

      {/* ✨ NOUVEAU : Onglets de navigation */}
      <div className="analysis-tabs">
        <button 
          className={`tab-button ${activeTab === 'sensitivity' ? 'active' : ''}`}
          onClick={() => setActiveTab('sensitivity')}
        >
          🎯 Sensibilité
        </button>
        <button 
          className={`tab-button ${activeTab === 'pageviews' ? 'active' : ''}`}
          onClick={() => setActiveTab('pageviews')}
        >
          📈 Pages vues
        </button>
        <button 
          className={`tab-button ${activeTab === 'metrics' ? 'active' : ''}`}
          onClick={() => setActiveTab('metrics')}
        >
          📋 Métriques détaillées
        </button>
      </div>

      {/* Contenu selon l'onglet actif */}
      {activeTab === 'sensitivity' && (
        <>
          {/* Contrôles de comparaison */}
          {allPages && allPages.length > 1 && (
            <div className="comparison-controls">
              <div className="comparison-header">
                <h4>🔄 Mode comparaison</h4>
                <div className="comparison-toggle">
                  <input
                    type="checkbox"
                    checked={showComparison}
                    onChange={(e) => {
                      setShowComparison(e.target.checked);
                      if (!e.target.checked) {
                        setSelectedPagesForComparison([currentPageIndex]);
                      }
                    }}
                    id="comparison-toggle"
                  />
                  <label htmlFor="comparison-toggle">
                    Comparer avec d'autres pages
                  </label>
                </div>
              </div>
              
              {showComparison && (
                <div>
                  <p className="comparison-hint">
                    Sélectionnez les pages à comparer (max 6) :
                  </p>
                  <div className="comparison-page-grid">
                    {allPages.map((page, index) => (
                      <div key={index} className="comparison-page-item">
                        <input
                          type="checkbox"
                          checked={selectedPagesForComparison.includes(index)}
                          onChange={() => handlePageToggle(index)}
                          disabled={
                            !selectedPagesForComparison.includes(index) && 
                            selectedPagesForComparison.length >= 6
                          }
                          id={`page-${index}`}
                        />
                        <label htmlFor={`page-${index}`} className={index === currentPageIndex ? 'current-page' : ''}>
                          {page.title} {index === currentPageIndex ? '(actuelle)' : ''}
                        </label>
                      </div>
                    ))}
                  </div>
                  <p className="comparison-hint">
                    {selectedPagesForComparison.length} page(s) sélectionnée(s)
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Section avec Kiviat à gauche et scores à droite */}
          <div className="bg-white border rounded-lg p-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="flex flex-col justify-center">
                <KiviatChart 
                  pages={allPages || [pageResult]}
                  selectedPageIndices={effectiveSelection}
                  showComparison={showComparison}
                />
              </div>
              
              <div className="flex flex-col justify-center">
                <h4>🎯 Scores détaillés</h4>
                <div className="score-cards-grid">
                  <div className="score-card heat">
                    <div className="score-card-info">
                      <h5>🔥 HEAT</h5>
                      <p>Activité et attention</p>
                    </div>
                    <div className="score-card-value">
                      {renderMetricValue(scores.heat)}
                    </div>
                  </div>
                  
                  <div className="score-card quality">
                    <div className="score-card-info">
                      <h5>⭐ QUALITY</h5>
                      <p>Fiabilité du contenu</p>
                    </div>
                    <div className="score-card-value">
                      {renderMetricValue(scores.quality)}
                    </div>
                  </div>
                  
                  <div className="score-card risk">
                    <div className="score-card-info">
                      <h5>⚠️ RISK</h5>
                      <p>Controverses et conflits</p>
                    </div>
                    <div className="score-card-value">
                      {renderMetricValue(scores.risk)}
                    </div>
                  </div>
                  
                  <div className="score-card sensitivity">
                    <div className="score-card-info">
                      <h5>🎯 SENSITIVITY</h5>
                      <p>Score global de sensibilité</p>
                    </div>
                    <div className="score-card-value">
                      {renderMetricValue(scores.sensitivity)}
                    </div>
                  </div>
                </div>
                
                {showComparison && selectedPagesForComparison.length > 1 && (
                  <div className="comparison-tip">
                    💡 <strong>Astuce:</strong> Comparez les formes sur le radar chart pour identifier 
                    les profils de sensibilité distincts entre les pages.
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* ✨ NOUVEAU : Onglet Pageviews */}
      {activeTab === 'pageviews' && (
        <div className="bg-white border rounded-lg p-6">
          <PageviewsChart 
            pages={allPages || [pageResult]} 
            analysisConfig={analysisConfig}
          />
        </div>
      )}

      {/* Onglet Métriques détaillées */}
      {activeTab === 'metrics' && (
        <div className="metrics-grid">
          <div className="metrics-category heat">
            <h4>🔥 Métriques HEAT</h4>
            <div className="metrics-list">
              {METRIC_CATEGORIES.heat.map(metric => (
                metrics[metric] !== undefined && (
                  <div key={metric} className="metric-item">
                    <span className="metric-name">{metric}:</span>
                    <span className="metric-value">
                      {renderMetricValue(metrics[metric])}
                    </span>
                  </div>
                )
              ))}
            </div>
          </div>

          <div className="metrics-category quality">
            <h4>⭐ Métriques QUALITY</h4>
            <div className="metrics-list">
              {METRIC_CATEGORIES.quality.map(metric => (
                metrics[metric] !== undefined && (
                  <div key={metric} className="metric-item">
                    <span className="metric-name">{metric}:</span>
                    <span className="metric-value">
                      {renderMetricValue(metrics[metric])}
                    </span>
                  </div>
                )
              ))}
            </div>
          </div>

          <div className="metrics-category risk">
            <h4>⚠️ Métriques RISK</h4>
            <div className="metrics-list">
              {METRIC_CATEGORIES.risk.map(metric => (
                metrics[metric] !== undefined && (
                  <div key={metric} className="metric-item">
                    <span className="metric-name">{metric}:</span>
                    <span className="metric-value">
                      {renderMetricValue(metrics[metric])}
                    </span>
                  </div>
                )
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Informations de l'analyse */}
      <div className="analysis-info">
        <h4>📋 Détails de l'analyse</h4>
        <div className="analysis-info-grid">
          <div className="analysis-info-item">
            <span>Langue:</span> {analysisConfig?.language || 'N/A'}
          </div>
          <div className="analysis-info-item">
            <span>Période:</span> {analysisConfig?.startDate} → {analysisConfig?.endDate}
          </div>
          <div className="analysis-info-item">
            <span>Statut:</span> 
            <span className="status-success">{pageResult.status || 'completed'}</span>
          </div>
          <div className="analysis-info-item">
            <span>Temps:</span> 
            {pageResult.processing_time ? `${pageResult.processing_time}s` : 'N/A'}
          </div>
        </div>
      </div>
    </div>
  );
};

// Le reste du code reste inchangé...
const SummaryCard = ({ page, index }) => (
  <div className="page-summary-card">
    <h4>{page.title}</h4>
    <div className="page-summary-scores">
      <div className="page-summary-score heat">
        <span className="score-label">Heat:</span>
        <span className="score-value">
          {renderMetricValue(page.scores?.heat)}
        </span>
      </div>
      <div className="page-summary-score quality">
        <span className="score-label">Quality:</span>
        <span className="score-value">
          {renderMetricValue(page.scores?.quality)}
        </span>
      </div>
      <div className="page-summary-score risk">
        <span className="score-label">Risk:</span>
        <span className="score-value">
          {renderMetricValue(page.scores?.risk)}
        </span>
      </div>
      <div className="page-summary-score sensitivity">
        <span className="score-label">Sensitivity:</span>
        <span className="score-value">
          {renderMetricValue(page.scores?.sensitivity)}
        </span>
      </div>
    </div>
  </div>
);

const ResultsView = ({ results, analysisConfig, onBackToConfig }) => {
  const [selectedPageIndex, setSelectedPageIndex] = useState(0);
  const pages = results.pages || [];
  
  if (pages.length === 0) {
    return (
      <div className="content-card">
        <div className="loading-container">
          <h2>❌ Aucun résultat</h2>
          <p>Aucune page n'a pu être analysée</p>
          <button onClick={onBackToConfig} className="btn btn-primary mt-6">
            Retour à la configuration
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="results-container">
      {pages.length === 1 ? (
        <div className="content-card">
          <div className="card-body">
            <DetailedPageResult 
              pageResult={pages[0]} 
              analysisConfig={analysisConfig}
              allPages={pages}
              currentPageIndex={0}
            />
          </div>
        </div>
      ) : (
        <div className="results-container">
          <div className="content-card">
            <div className="card-header">
              <h3>📊 Vue d'ensemble</h3>
              <p>Cliquez sur une page pour voir les détails</p>
            </div>
            <div className="card-body">
              <div className="pages-overview-grid">
                {pages.map((page, index) => (
                  <div
                    key={index}
                    onClick={() => setSelectedPageIndex(index)}
                    className={`page-summary-card ${
                      selectedPageIndex === index ? 'selected' : ''
                    }`}
                  >
                    <SummaryCard page={page} index={index} />
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="content-card">
            <div className="card-header">
              <h3>🔍 Analyse détaillée</h3>
              <p>Page {selectedPageIndex + 1} sur {pages.length}</p>
            </div>
            <div className="card-body">
              <DetailedPageResult 
                pageResult={pages[selectedPageIndex]} 
                analysisConfig={analysisConfig}
                allPages={pages}
                currentPageIndex={selectedPageIndex}
              />
            </div>
          </div>
        </div>
      )}

      <div className="content-card">
        <div className="results-actions">
          <button
            onClick={onBackToConfig}
            className="btn btn-action"
          >
             Nouvelle analyse
          </button>
          <button
            onClick={() => {
              console.log('Export results:', results);
              alert('Fonctionnalité d\'export à venir');
            }}
            className="btn btn-action"
          >
             Exporter les résultats
          </button>
        </div>
      </div>
    </div>
  );
};

const ResultsPage = ({ analysisData, onBackToConfig }) => {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!analysisData?.taskId) return;
    
    const pollResults = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/tasks/${analysisData.taskId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const taskData = await response.json();

        if (taskData.status === 'completed' && taskData.results) {
          setResults(taskData.results);
          setLoading(false);
        } else if (taskData.status === 'error') {
          setError('Erreur lors de l\'analyse');
          setLoading(false);
        } else {
          setTimeout(pollResults, 2000);
        }
      } catch (err) {
        console.error('Erreur polling:', err);
        setTimeout(pollResults, 3000);
      }
    };

    pollResults();
  }, [analysisData?.taskId]);

  return (
    <Layout
      pageTitle="SensiMeter Wikipedia"
      subtitle="Wikipedia Content Intelligence Platform"
      onBackToConfig={onBackToConfig}
    >
      {loading && (
        <LoadingView 
          pagesCount={analysisData?.pages?.length || 0} 
          taskId={analysisData?.taskId} 
        />
      )}
      
      {error && (
        <ErrorView error={error} onBack={onBackToConfig} />
      )}
      
      {results && (
        <ResultsView 
          results={results} 
          analysisConfig={analysisData}
          onBackToConfig={onBackToConfig} 
        />
      )}
    </Layout>
  );
}

export default ResultsPage;