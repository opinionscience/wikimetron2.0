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
  'Featured article': 'Quality article status recognized by the community, if available for the language',
  'Citation gaps': 'Number of missing or needed citations',
  'Staleness': 'Content age, indicator of information freshness',
  'Source concentration': 'Diversity of sources used in the article',
  'Contributor add/delete ratio': 'Balance between content additions and deletions in the contributions of each contributor of the page',
  'Add/delete ratio': 'Balance between content additions and deletions',
  'Anonymity': 'Proportion of edits by anonymous users',
  'Contributors concentration': 'Share of the most active user in the latest modifications',
  'Sporadicity': 'Irregularity in contributor editing frequency',
  'Sockpuppets': 'Presence of sockpuppet accounts, indicating potential manipulation',
};

// Categories of metrics with descriptions - Compatible with your existing code
const METRIC_CATEGORIES = {
  heat: {
    metrics: ['Views spikes', 'Edits spikes', 'Edits revert probability', 'Protection', 'Discussion intensity'],
    title: 'Heat risk',
    description: 'Indicators of controversy and abnormal activity',
    color: '#ef4444'
  },
  risk: {
    metrics: ["Sockpuppets", 'Anonymity', 'Contributors concentration', 'Sporadicity', 'Contributor add/delete ratio'],
    title: 'Behaviour risk',
    description: 'Indicators of suspicious editing behaviors',
    color: '#f59e0b'
  },

  quality: {
    metrics: ["Suspicious sources", 'Featured article', 'Citation gaps', 'Staleness', 'Source concentration', 'Add/delete ratio'],
    title: 'Quality risk',
    description: 'Indicators of content quality and reliability',
    color: '#3b82f6'
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
  // État pour gérer l'expansion des sockpuppets par index de page
  const [expandedSockpuppets, setExpandedSockpuppets] = useState({});
  // État pour gérer l'expansion des sources suspectes par index de page
  const [expandedSuspiciousSources, setExpandedSuspiciousSources] = useState({});

  // Toggle l'affichage des sockpuppets pour une page donnée
  const toggleSockpuppets = (pageIndex) => {
    setExpandedSockpuppets(prev => ({
      ...prev,
      [pageIndex]: !prev[pageIndex]
    }));
  };

  // Toggle l'affichage des sources suspectes pour une page donnée
  const toggleSuspiciousSources = (pageIndex) => {
    setExpandedSuspiciousSources(prev => ({
      ...prev,
      [pageIndex]: !prev[pageIndex]
    }));
  };

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

    // Vérifier si cette métrique a des détails détectés
    const hasDetailsInAnyPage = pages.some(page => {
      if (metricKey === 'Sockpuppets') {
        return page.detected_sockpuppets && page.detected_sockpuppets.length > 0;
      } else if (metricKey === 'Suspicious sources') {
        return page.detected_suspicious_sources && page.detected_suspicious_sources.length > 0;
      }
      return false;
    });

    return (
      <div className="metric-item-horizontal">
        <div className="metric-name-horizontal">
          <Tooltip text={METRIC_TOOLTIPS[metricKey] || 'Information sur cette métrique'}>
            <span style={{
              paddingBottom: '1px'
            }}>
              {metricKey}
              {hasDetailsInAnyPage && (
                <span style={{
                  fontSize: '0.65em',
                  marginLeft: '6px',
                  opacity: 0.6,
                  fontWeight: '400',
                  fontStyle: 'italic',
                  color: metricKey === 'Sockpuppets' ? '#52cd08' : '#52cd08'
                }}>
                  click below to see details
                </span>
              )}
            </span>
          </Tooltip>
        </div>
        <div className="metric-values-horizontal">
          {comparisonMode && pages.length > 1 ? (
            pages.map((page, index) => {
              const value = page.metrics?.[metricKey] || 0;
              const pageColor = PAGE_COLORS[index % PAGE_COLORS.length];

              // Gérer les sockpuppets
              const detectedSockpuppets = metricKey === 'Sockpuppets' ? page.detected_sockpuppets : null;
              const hasSockpuppets = detectedSockpuppets && detectedSockpuppets.length > 0;
              const isSockpuppetsExpanded = expandedSockpuppets[index];

              // Gérer les sources suspectes
              const detectedSuspiciousSources = metricKey === 'Suspicious sources' ? page.detected_suspicious_sources : null;
              const hasSuspiciousSources = detectedSuspiciousSources && detectedSuspiciousSources.length > 0;
              const isSuspiciousSourcesExpanded = expandedSuspiciousSources[index];

              const hasDetails = hasSockpuppets || hasSuspiciousSources;
              const isExpanded = hasSockpuppets ? isSockpuppetsExpanded : isSuspiciousSourcesExpanded;

              return (
                <div key={index} className="metric-page-value" style={{color: pageColor}}>
                  <span
                    className="page-value"
                    onClick={() => {
                      if (hasSockpuppets) toggleSockpuppets(index);
                      else if (hasSuspiciousSources) toggleSuspiciousSources(index);
                    }}
                    style={{
                      cursor: hasDetails ? 'pointer' : 'default',
                      userSelect: 'none',
                      position: 'relative',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    {renderMetricValue(value)}
                    {hasDetails && (
                      <span style={{
                        fontSize: '0.7em',
                        opacity: 0.7,
                        transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s ease'
                      }}>
                        ▼
                      </span>
                    )}
                  </span>
                  {/* Afficher les sockpuppets détectés au clic */}
                  {hasSockpuppets && isSockpuppetsExpanded && (
                    <div className="detected-sockpuppets" style={{
                      marginTop: '8px',
                      padding: '10px 12px',
                      background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                      borderRadius: '8px',
                      fontSize: '0.75em',
                      animation: 'slideDown 0.2s ease-out',
                      boxShadow: '0 2px 8px rgba(245, 158, 11, 0.15)'
                    }}>
                      <div style={{
                        fontWeight: '700',
                        color: '#92400e',
                        marginBottom: '6px',
                        fontSize: '0.85em',
                        letterSpacing: '0.3px',
                        textTransform: 'uppercase'
                      }}>
                        Detected Users
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {detectedSockpuppets.map((username, idx) => (
                          <a
                            key={idx}
                            href={`https://${page.language}.wikipedia.org/wiki/User:${encodeURIComponent(username)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              display: 'inline-block',
                              padding: '4px 10px',
                              background: 'linear-gradient(135deg, #ffffff 0%, #fef9f3 100%)',

                              borderRadius: '14px',
                              color: '#92400e',
                              fontSize: '0.9em',
                              fontWeight: '600',
                              textDecoration: 'none',
                              cursor: 'pointer',
                              transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                              boxShadow: '0 1px 3px rgba(245, 158, 11, 0.2)'
                            }}
                            onMouseEnter={(e) => {
                              e.target.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
                              e.target.style.color = '#ffffff';
                              e.target.style.transform = 'translateY(-2px)';
                              e.target.style.boxShadow = '0 4px 12px rgba(245, 158, 11, 0.4)';
                            }}
                            onMouseLeave={(e) => {
                              e.target.style.background = 'linear-gradient(135deg, #ffffff 0%, #fef9f3 100%)';
                              e.target.style.color = '#92400e';
                              e.target.style.transform = 'translateY(0)';
                              e.target.style.boxShadow = '0 1px 3px rgba(245, 158, 11, 0.2)';
                            }}
                          >
                            {username}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* Afficher les sources suspectes détectées au clic */}
                  {hasSuspiciousSources && isSuspiciousSourcesExpanded && (
                    <div className="detected-suspicious-sources" style={{
                      marginTop: '8px',
                      padding: '10px 12px',
                      background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',

                      borderRadius: '8px',
                      fontSize: '0.75em',
                      animation: 'slideDown 0.2s ease-out',
                      boxShadow: '0 2px 8px rgba(220, 38, 38, 0.15)'
                    }}>
                      <div style={{
                        fontWeight: '700',
                        color: '#7f1d1d',
                        marginBottom: '6px',
                        fontSize: '0.85em',
                        letterSpacing: '0.3px',
                        textTransform: 'uppercase'
                      }}>
                         Detected Sources
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {detectedSuspiciousSources.map((domain, idx) => (
                          <a
                            key={idx}
                            href={`https://${domain}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              display: 'inline-block',
                              padding: '4px 10px',
                              background: 'linear-gradient(135deg, #ffffff 0%, #fef9f9 100%)',

                              borderRadius: '14px',
                              color: '#7f1d1d',
                              fontSize: '0.9em',
                              fontWeight: '600',
                              textDecoration: 'none',
                              cursor: 'pointer',
                              transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                              boxShadow: '0 1px 3px rgba(220, 38, 38, 0.2)'
                            }}
                            onMouseEnter={(e) => {
                              e.target.style.background = 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)';
                              e.target.style.color = '#ffffff';
                              e.target.style.transform = 'translateY(-2px)';
                              e.target.style.boxShadow = '0 4px 12px rgba(220, 38, 38, 0.4)';
                            }}
                            onMouseLeave={(e) => {
                              e.target.style.background = 'linear-gradient(135deg, #ffffff 0%, #fef9f9 100%)';
                              e.target.style.color = '#7f1d1d';
                              e.target.style.transform = 'translateY(0)';
                              e.target.style.boxShadow = '0 1px 3px rgba(220, 38, 38, 0.2)';
                            }}
                          >
                            {domain}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <div className="metric-single-value-horizontal">
              <span
                className="page-value"
                onClick={() => {
                  const hasSockpuppets = metricKey === 'Sockpuppets' &&
                    pages[0]?.detected_sockpuppets &&
                    pages[0].detected_sockpuppets.length > 0;
                  const hasSuspiciousSources = metricKey === 'Suspicious sources' &&
                    pages[0]?.detected_suspicious_sources &&
                    pages[0].detected_suspicious_sources.length > 0;

                  if (hasSockpuppets) toggleSockpuppets(0);
                  else if (hasSuspiciousSources) toggleSuspiciousSources(0);
                }}
                style={{
                  cursor: (
                    (metricKey === 'Sockpuppets' && pages[0]?.detected_sockpuppets && pages[0].detected_sockpuppets.length > 0) ||
                    (metricKey === 'Suspicious sources' && pages[0]?.detected_suspicious_sources && pages[0].detected_suspicious_sources.length > 0)
                  ) ? 'pointer' : 'default',
                  userSelect: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                {renderMetricValue(stats.values[0])}
                {metricKey === 'Sockpuppets' && pages[0]?.detected_sockpuppets && pages[0].detected_sockpuppets.length > 0 && (
                  <span style={{
                    fontSize: '0.8em',
                    opacity: 0.7,
                    transform: expandedSockpuppets[0] ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s ease'
                  }}>
                    ▼
                  </span>
                )}
                {metricKey === 'Suspicious sources' && pages[0]?.detected_suspicious_sources && pages[0].detected_suspicious_sources.length > 0 && (
                  <span style={{
                    fontSize: '0.8em',
                    opacity: 0.7,
                    transform: expandedSuspiciousSources[0] ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s ease'
                  }}>
                    ▼
                  </span>
                )}
              </span>
              {/* Afficher les sockpuppets détectés au clic en mode single page */}
              {metricKey === 'Sockpuppets' &&
                pages[0]?.detected_sockpuppets &&
                pages[0].detected_sockpuppets.length > 0 &&
                expandedSockpuppets[0] && (
                <div className="detected-sockpuppets" style={{
                  marginTop: '10px',
                  padding: '12px 14px',
                  background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',

                  borderRadius: '8px',
                  fontSize: '0.9em',
                  animation: 'slideDown 0.2s ease-out',
                  boxShadow: '0 2px 8px rgba(245, 158, 11, 0.15)'
                }}>
                  <div style={{
                    fontWeight: '700',
                    color: '#92400e',
                    marginBottom: '8px',
                    fontSize: '0.9em',
                    letterSpacing: '0.3px',
                    textTransform: 'uppercase'
                  }}>
                     Detected Users
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {pages[0].detected_sockpuppets.map((username, idx) => (
                      <a
                        key={idx}
                        href={`https://${pages[0].language}.wikipedia.org/wiki/User:${encodeURIComponent(username)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-block',
                          padding: '6px 12px',
                          background: 'linear-gradient(135deg, #ffffff 0%, #fef9f3 100%)',

                          borderRadius: '14px',
                          color: '#92400e',
                          fontSize: '0.95em',
                          fontWeight: '600',
                          textDecoration: 'none',
                          cursor: 'pointer',
                          transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                          boxShadow: '0 1px 3px rgba(245, 158, 11, 0.2)'
                        }}
                        onMouseEnter={(e) => {
                          e.target.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
                          e.target.style.color = '#ffffff';
                          e.target.style.transform = 'translateY(-2px)';
                          e.target.style.boxShadow = '0 4px 12px rgba(245, 158, 11, 0.4)';
                        }}
                        onMouseLeave={(e) => {
                          e.target.style.background = 'linear-gradient(135deg, #ffffff 0%, #fef9f3 100%)';
                          e.target.style.color = '#92400e';
                          e.target.style.transform = 'translateY(0)';
                          e.target.style.boxShadow = '0 1px 3px rgba(245, 158, 11, 0.2)';
                        }}
                      >
                        {username}
                      </a>
                    ))}
                  </div>
                </div>
              )}
              {/* Afficher les sources suspectes détectées au clic en mode single page */}
              {metricKey === 'Suspicious sources' &&
                pages[0]?.detected_suspicious_sources &&
                pages[0].detected_suspicious_sources.length > 0 &&
                expandedSuspiciousSources[0] && (
                <div className="detected-suspicious-sources" style={{
                  marginTop: '10px',
                  padding: '12px 14px',
                  background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',

                  borderRadius: '8px',
                  fontSize: '0.9em',
                  animation: 'slideDown 0.2s ease-out',
                  boxShadow: '0 2px 8px rgba(220, 38, 38, 0.15)'
                }}>
                  <div style={{
                    fontWeight: '700',
                    color: '#7f1d1d',
                    marginBottom: '8px',
                    fontSize: '0.9em',
                    letterSpacing: '0.3px',
                    textTransform: 'uppercase'
                  }}>
                     Detected Sources
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {pages[0].detected_suspicious_sources.map((domain, idx) => (
                      <a
                        key={idx}
                        href={`https://${domain}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-block',
                          padding: '6px 12px',
                          background: 'linear-gradient(135deg, #ffffff 0%, #fef9f9 100%)',

                          borderRadius: '14px',
                          color: '#7f1d1d',
                          fontSize: '0.95em',
                          fontWeight: '600',
                          textDecoration: 'none',
                          cursor: 'pointer',
                          transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                          boxShadow: '0 1px 3px rgba(220, 38, 38, 0.2)'
                        }}
                        onMouseEnter={(e) => {
                          e.target.style.background = 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)';
                          e.target.style.color = '#ffffff';
                          e.target.style.transform = 'translateY(-2px)';
                          e.target.style.boxShadow = '0 4px 12px rgba(220, 38, 38, 0.4)';
                        }}
                        onMouseLeave={(e) => {
                          e.target.style.background = 'linear-gradient(135deg, #ffffff 0%, #fef9f9 100%)';
                          e.target.style.color = '#7f1d1d';
                          e.target.style.transform = 'translateY(0)';
                          e.target.style.boxShadow = '0 1px 3px rgba(220, 38, 38, 0.2)';
                        }}
                      >
                        {domain}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        <style jsx>{`
          @keyframes slideDown {
            from {
              opacity: 0;
              transform: translateY(-10px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
        `}</style>
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
    {index < mainScore.length - 1 && (
      <span style={{ fontWeight: 300, opacity: 0.8 }}> VS </span>
    )}
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