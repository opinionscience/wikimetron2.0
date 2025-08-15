import React, { useState } from 'react';

const renderMetricValue = (value) => {
  if (typeof value === 'number') {
    return value.toFixed(1);
  }
  return value || '0.0';
};

// Définitions des tooltips pour chaque métrique
const METRIC_TOOLTIPS = {
  'Views spikes': 'Abnormal view spikes that may indicate controversial events or media attention',
  'Edits spikes': 'Edit spikes that may signal edit wars or controversies',
  'Edits revert probability': 'Probability that an edit will be reverted, indicating controversy',
  'Protection': 'Page protection level against unauthorized modifications',
  'Discussion intensity': 'Intensity of discussions on the talk page',
  'Suspicious sources': 'Potentially unreliable or biased sources',
  'Featured article': 'Quality article status recognized by the community',
  'Citations need': 'Number of missing or needed citations',
  'Staleness': 'Content age, indicator of information freshness',
  'Sources homogeneity': 'Diversity of sources used in the article',
  'Additions/deletions balance': 'Balance between content additions and deletions in the contributions of each contributor of the page',
  'Additions/deletions balance ': 'Balance between content additions and deletions',
  'Anonymity': 'Proportion of edits by anonymous users',
  'Uniformity': 'Uniformity of contributor editing patterns',
  'Sporadicity': 'Irregularity in contributor editing frequency',
  'sockpuppet': 'Presence of sockpuppet accounts, indicating potential manipulation',
};

// Categories of metrics with descriptions - Compatible with your existing code
const METRIC_CATEGORIES = {
  heat: {
    metrics: ['Views spikes', 'Edits spikes', 'Edits revert probability', 'Protection', 'Discussion intensity'],
    title: 'Heat risk',
    description: 'Indicators of controversy and abnormal activity',
    color: '#ef4444'
  },
  quality: {
    metrics: ["Suspicious sources", 'Featured article', 'Citations need', 'Staleness', 'Sources homogeneity', 'Additions/deletions balance '],
    title: 'Quality risk',
    description: 'Indicators of content quality and reliability',
    color: '#3b82f6'
  },
  risk: {
    metrics: ["sockpuppet", 'Anonymity', 'Uniformity', 'Sporadicity', 'Additions/deletions balance'],
    title: 'Behaviour risk',
    description: 'Indicators of suspicious editing behaviors',
    color: '#f59e0b'
  }
};


// Couleurs pour les pages (palette moderne)
const PAGE_COLORS = [
  '#3b82f6', // Bleu
  '#ef4444', // Rouge
  '#10b981', // Vert
  '#f59e0b', // Orange
  '#8b5cf6', // Violet
  '#06b6d4'  // Cyan
];

// Composant Tooltip amélioré
const Tooltip = ({ children, text, position = 'top', isFirst = false }) => {
  const [isVisible, setIsVisible] = useState(false);

  // Fonction pour formater le texte avec retour à la ligne tous les 4 mots
  const formatText = (text) => {
    const words = text.split(' ');
    const lines = [];
    for (let i = 0; i < words.length; i += 7) {
      lines.push(words.slice(i, i + 7).join(' '));
    }
    return lines.join('\n');
  };

  return (
    <div 
      className="wikimetron-tooltip-container"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      style={{ 
        position: 'relative', 
        display: 'inline-block',
        cursor: 'help'
      }}
    >
      {children}
      {isVisible && (
        <div 
          className="wikimetron-tooltip"
          style={{
            position: 'absolute',
            top: '0',
            left: '120%',
            backgroundColor: '#1f2937',
            color: 'white',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            lineHeight: '1.4',
            maxWidth: '280px',
            minWidth: '120px',
            zIndex: 9999,
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.25)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            wordWrap: 'break-word',
            pointerEvents: 'none',
            opacity: 0,
            animation: 'tooltipFadeIn 0.2s ease-out forwards',
            whiteSpace: 'pre-line'
          }}
        >
          {formatText(text)}
          <div
            style={{
              position: 'absolute',
              top: '8px',
              right: '100%',
              marginRight: '3px',
              borderTop: '5px solid transparent',
              borderBottom: '5px solid transparent',
              borderRight: '5px solid #1f2937',
              width: 0,
              height: 0
            }}
          />
        </div>
      )}
      
      <style jsx>{`
        @keyframes tooltipFadeIn {
          from {
            opacity: 0;
            transform: translateX(10px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
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

  // Composant pour une métrique individuelle avec layout horizontal - compatible avec vos classes CSS
  const MetricItem = ({ metricKey, stats }) => {
    if (!stats) return null;
    
    return (
      <div className="metric-item-horizontal">
        <div className="metric-name-horizontal">
          <Tooltip text={METRIC_TOOLTIPS[metricKey] || 'Information sur cette métrique'}>
            <span style={{ 
              borderBottom: '1px dotted #9ca3af',
              paddingBottom: '1px'
            }}>
              {metricKey}
            </span>
          </Tooltip>
        </div>
        <div className="metric-values-horizontal">
          {comparisonMode && pages.length > 1 ? (
            pages.map((page, index) => {
              const value = page.metrics?.[metricKey] || 0;
              const pageColor = PAGE_COLORS[index % PAGE_COLORS.length];
              return (
                <div key={index} className="metric-page-value" style={{color: pageColor}}>
                  <span className="page-value">
                    {renderMetricValue(value)}
                  </span>
                </div>
              );
            })
          ) : (
            <div className="metric-single-value-horizontal">
              {renderMetricValue(stats.values[0])}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Composant pour une catégorie de métriques - compatible avec vos classes CSS
  const MetricCategory = ({ categoryKey }) => {
    const categoryData = METRIC_CATEGORIES[categoryKey];
    // Calcul des scores de catégorie
    const mainScore = pages.map(page => page.scores?.[categoryKey] || 0);

    return (
      <div className={`metric-category-horizontal ${categoryKey}`}>
        {/* Header avec titre et description */}
        <div className="metric-category-header-horizontal">
          <Tooltip text={categoryData.description}>
            <h5 className="metric-category-title-horizontal" style={{ cursor: 'help' }}>
              {categoryData.title}
            </h5>
          </Tooltip>
          <p className="metric-category-description-horizontal">{categoryData.description}</p>
{/* Score principal ou comparaison des scores */}
<div className="category-scores-horizontal">
  {pages.length > 1 ? (
    <div 
      className="category-single-score"
      style={{
        fontSize: mainScore.length > 2 ? '0.9em' : 'inherit',
        whiteSpace: mainScore.length > 2 ? 'nowrap' : 'normal',
        overflow: 'hidden',
        textOverflow: 'ellipsis'
      }}
    >
      {mainScore.map((score, index) => (
        <React.Fragment key={index}>
          <span style={{ color: PAGE_COLORS[index % PAGE_COLORS.length] }}>
            {renderMetricValue(score)}%
          </span>
          {index < mainScore.length - 1 && ' VS '}
        </React.Fragment>
      ))}
    </div>
  ) : (
    <div className="category-single-score">
      <span style={{ color: PAGE_COLORS[0] }}>
        {renderMetricValue(mainScore[0])}%
      </span>
    </div>
  )}
</div>
        </div>
        {/* Métriques détaillées */}
        <div className="metrics-list-horizontal">
          {categoryData.metrics.map(metricKey => {
            const stats = getComparisonStats(metricKey);
            return (
              <MetricItem
                key={metricKey}
                metricKey={metricKey}
                stats={stats}
              />
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="metrics-container-horizontal">
      <div className="metrics-categories-horizontal">
        {Object.entries(METRIC_CATEGORIES).map(([categoryKey]) => (
          <MetricCategory
            key={categoryKey}
            categoryKey={categoryKey}
          />
        ))}
      </div>
    </div>
  );
};

export default MetricsDisplay;