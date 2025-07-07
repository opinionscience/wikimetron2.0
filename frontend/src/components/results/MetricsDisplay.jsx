// File: src/components/results/MetricsDisplay.jsx
import React from 'react';

const renderMetricValue = (value) => {
  if (typeof value === 'number') {
    return value.toFixed(3);
  }
  return value || '0.000';
};

// Catégories de métriques avec descriptions
const METRIC_CATEGORIES = {
  heat: {
    metrics: ['pageview_spike', 'edit_spike', 'revert_risk', 'protection_level', 'talk_intensity'],
    title: '🔥 HEAT - Activité et Attention',
    description: 'Mesure l\'intensité de l\'activité et de l\'attention portée à la page',
    color: '#ef4444'
  },
  quality: {
    metrics: ['citation_gap', 'blacklist_share', 'event_imbalance', 'recency_score', 'adq_score', 'domain_dominance'],
    title: '⭐ QUALITY - Fiabilité du Contenu',
    description: 'Évalue la qualité et la fiabilité du contenu de la page',
    color: '#3b82f6'
  },
  risk: {
    metrics: ['anon_edit', 'mean_contributor_balance', 'monopolization_score', 'avg_activity_score'],
    title: '⚠️ RISK - Controverses et Conflits',
    description: 'Identifie les risques de controverses et de conflits d\'édition',
    color: '#f59e0b'
  }
};

const MetricsDisplay = ({ pages, comparisonMode }) => {
  // Fonction pour calculer les statistiques de comparaison
  const getComparisonStats = (metricKey) => {
    const values = pages.map(page => page.metrics?.[metricKey] || 0);
    const validValues = values.filter(v => v !== null && v !== undefined);
    
    if (validValues.length === 0) return null;
    
    return {
      min: Math.min(...validValues),
      max: Math.max(...validValues),
      avg: validValues.reduce((sum, val) => sum + val, 0) / validValues.length,
      range: Math.max(...validValues) - Math.min(...validValues),
      values: values
    };
  };

  // Composant pour une métrique individuelle
  const MetricItem = ({ metricKey, categoryColor, stats }) => {
    if (!stats) return null;

    return (
      <div className="metric-detail-item">
        <div className="metric-name-section">
          <span className="metric-name">{metricKey}</span>
        </div>
        
        {comparisonMode && pages.length > 1 ? (
          <div className="metric-comparison-values">
            {pages.map((page, index) => {
              const value = page.metrics?.[metricKey];
              const isMax = value === stats.max;
              const isMin = value === stats.min;
              
              return (
                <div 
                  key={index} 
                  className={`comparison-value ${isMax ? 'max-value' : ''} ${isMin ? 'min-value' : ''}`}
                  style={{ borderLeftColor: categoryColor }}
                >
                  <span className="page-indicator">#{index + 1}</span>
                  <span className="value">{renderMetricValue(value)}</span>
                </div>
              );
            })}
            <div className="stats-summary">
              <span>Δ {renderMetricValue(stats.range)}</span>
            </div>
          </div>
        ) : (
          <div className="metric-single-value">
            <span className="value" style={{ color: categoryColor }}>
              {renderMetricValue(stats.values[0])}
            </span>
          </div>
        )}
      </div>
    );
  };

  // Composant pour une catégorie de métriques
  const MetricCategory = ({ categoryKey, category }) => {
    const categoryData = METRIC_CATEGORIES[categoryKey];
    const mainScore = comparisonMode && pages.length > 1 
      ? pages.map(page => page.scores?.[categoryKey] || 0)
      : [pages[0]?.scores?.[categoryKey] || 0];

    const avgScore = mainScore.reduce((sum, score) => sum + score, 0) / mainScore.length;
    const maxScore = Math.max(...mainScore);
    const minScore = Math.min(...mainScore);

    return (
      <div className={`metrics-category-new ${categoryKey}`}>
        {/* Header avec score principal */}
        <div className="category-header">
          <div className="category-title-section">
            <h4 style={{ color: categoryData.color }}>
              {categoryData.title}
            </h4>
            <p className="category-description">
              {categoryData.description}
            </p>
          </div>
          
          <div className="category-main-score">
            {comparisonMode && pages.length > 1 ? (
              <div className="comparison-main-scores">
                <div className="main-score-primary" style={{ color: categoryData.color }}>
                  {renderMetricValue(avgScore)}
                </div>
                <div className="main-score-details">
                  <span>Moyenne</span>
                  <div className="score-range">
                    {renderMetricValue(minScore)} - {renderMetricValue(maxScore)}
                  </div>
                </div>
              </div>
            ) : (
              <div className="single-main-score">
                <div className="main-score-primary" style={{ color: categoryData.color }}>
                  {renderMetricValue(mainScore[0])}
                </div>
                <div className="main-score-label">Score {categoryKey}</div>
              </div>
            )}
          </div>
        </div>

        {/* Métriques détaillées */}
        <div className="metrics-details">
          <h5>Métriques détaillées</h5>
          <div className="metrics-list-new">
            {categoryData.metrics.map(metricKey => {
              const stats = getComparisonStats(metricKey);
              return (
                <MetricItem
                  key={metricKey}
                  metricKey={metricKey}
                  categoryColor={categoryData.color}
                  stats={stats}
                />
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="metrics-display-container">
      {/* Header */}
      <div className="metrics-header">
        <h3>
          📋 {comparisonMode && pages.length > 1 
            ? `Métriques détaillées - Comparaison de ${pages.length} pages`
            : 'Métriques détaillées'
          }
        </h3>
        {comparisonMode && pages.length > 1 && (
          <div className="comparison-legend">
            <div className="legend-item">
              <div className="legend-indicator max"></div>
              <span>Valeur maximale</span>
            </div>
            <div className="legend-item">
              <div className="legend-indicator min"></div>
              <span>Valeur minimale</span>
            </div>
            <div className="legend-item">
              <div className="legend-indicator delta"></div>
              <span>Écart (Δ)</span>
            </div>
          </div>
        )}
      </div>

      {/* Grille des catégories */}
      <div className="metrics-categories-grid">
        {Object.entries(METRIC_CATEGORIES).map(([categoryKey, category]) => (
          <MetricCategory
            key={categoryKey}
            categoryKey={categoryKey}
            category={category}
          />
        ))}
      </div>

      {/* Résumé de sensibilité */}
      <div className="sensitivity-summary">
        <h4>🎯 Résumé de sensibilité</h4>
        {comparisonMode && pages.length > 1 ? (
          <div className="sensitivity-comparison">
            <div className="sensitivity-grid">
              {pages.map((page, index) => {
                const sensitivity = page.scores?.sensitivity || 0;
                const getSensitivityLevel = (score) => {
                  if (score >= 0.7) return { label: 'Très élevée', color: '#ef4444' };
                  if (score >= 0.5) return { label: 'Élevée', color: '#f59e0b' };
                  if (score >= 0.3) return { label: 'Modérée', color: '#3b82f6' };
                  return { label: 'Faible', color: '#10b981' };
                };
                
                const level = getSensitivityLevel(sensitivity);
                
                return (
                  <div key={index} className="sensitivity-item">
                    <div className="sensitivity-page">
                      <span className="page-number">#{index + 1}</span>
                      <span className="page-title" title={page.title}>
                        {page.title?.length > 20 
                          ? `${page.title.substring(0, 20)}...` 
                          : page.title
                        }
                      </span>
                    </div>
                    <div className="sensitivity-score" style={{ color: level.color }}>
                      <span className="score-value">{renderMetricValue(sensitivity)}</span>
                      <span className="score-level">{level.label}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="sensitivity-single">
            <div className="sensitivity-main">
              <span className="sensitivity-score-large">
                {renderMetricValue(pages[0]?.scores?.sensitivity)}
              </span>
              <span className="sensitivity-label">Score de sensibilité global</span>
            </div>
            <div className="sensitivity-breakdown">
              <div className="breakdown-item">
                <span>Heat:</span>
                <span>{renderMetricValue(pages[0]?.scores?.heat)}</span>
              </div>
              <div className="breakdown-item">
                <span>Quality:</span>
                <span>{renderMetricValue(pages[0]?.scores?.quality)}</span>
              </div>
              <div className="breakdown-item">
                <span>Risk:</span>
                <span>{renderMetricValue(pages[0]?.scores?.risk)}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MetricsDisplay;