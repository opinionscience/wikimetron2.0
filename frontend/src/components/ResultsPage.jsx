// File: src/components/ResultsSection.jsx - Version avec infobulle sur le score de sensibilité
import React, { useState } from 'react';
import { ModernLoadingOverlay } from './LoadingSpinner';
import KiviatChart from './results/KiviatChart';
import PageviewsChart from './results/PageviewsChart';
import EditChart from './results/EditChart';
import MetricsDisplay from './results/MetricsDisplay';
import './ResultsPage.css';

// Utilitaire pour formatter les valeurs
const formatMetricValue = (value) => {
  if (typeof value === 'number') {
    return value.toFixed(1);
  }
  return value || '0.0';
};

// Composant infobulle
const Tooltip = ({ content, children, position = 'top' }) => {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div 
      className="tooltip-container"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      style={{ position: 'relative', display: 'inline-block' }}
    >
      {children}
      {isVisible && (
        <div 
          className={`tooltip-content tooltip-${position}`}
          style={{
            position: 'absolute',
            zIndex: 1000,
            background: '#1a1a1a',
            color: 'white',
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '13px',
            lineHeight: '1.4',
            maxWidth: '300px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
            border: '1px solid #333',
            ...(position === 'top' && {
              bottom: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginBottom: '8px'
            }),
            ...(position === 'bottom' && {
              top: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              marginTop: '8px'
            }),
            ...(position === 'left' && {
              right: '100%',
              top: '50%',
              transform: 'translateY(-50%)',
              marginRight: '8px'
            }),
            ...(position === 'right' && {
              left: '100%',
              top: '50%',
              transform: 'translateY(-50%)',
              marginLeft: '8px'
            })
          }}
        >
          {content}
          <div 
            className="tooltip-arrow"
            style={{
              position: 'absolute',
              width: '0',
              height: '0',
              borderStyle: 'solid',
              ...(position === 'top' && {
                top: '100%',
                left: '50%',
                marginLeft: '-5px',
                borderWidth: '5px 5px 0 5px',
                borderColor: '#1a1a1a transparent transparent transparent'
              }),
              ...(position === 'bottom' && {
                bottom: '100%',
                left: '50%',
                marginLeft: '-5px',
                borderWidth: '0 5px 5px 5px',
                borderColor: 'transparent transparent #1a1a1a transparent'
              }),
              ...(position === 'left' && {
                left: '100%',
                top: '50%',
                marginTop: '-5px',
                borderWidth: '5px 0 5px 5px',
                borderColor: 'transparent transparent transparent #1a1a1a'
              }),
              ...(position === 'right' && {
                right: '100%',
                top: '50%',
                marginTop: '-5px',
                borderWidth: '5px 5px 5px 0',
                borderColor: 'transparent #1a1a1a transparent transparent'
              })
            }}
          />
        </div>
      )}
    </div>
  );
};

// Composants réutilisés de ResultsPage
const ModernPageSelector = ({ pages, selectedIndices, comparisonMode, onSelectionChange }) => {
  const handlePageClick = (pageIndex) => {
    if (comparisonMode) {
      const newSelection = selectedIndices.includes(pageIndex)
        ? selectedIndices.filter(i => i !== pageIndex)
        : [...selectedIndices, pageIndex].slice(0, 6);
      onSelectionChange(newSelection, comparisonMode);
    } else {
      onSelectionChange([pageIndex], false);
    }
  };

  const handleComparisonToggle = () => {
    const newComparisonMode = !comparisonMode;
    if (newComparisonMode && selectedIndices.length < 2) {
      onSelectionChange([0, 1].slice(0, pages.length), true);
    } else {
      onSelectionChange(selectedIndices, newComparisonMode);
    }
  };

  return (
    <div className="page-selector-modern">
      <div className="pages-comparison-row">
        <div className="pages-buttons-container">
          {pages.map((page, index) => (
            <button
              key={index}
              className={`page-button-modern ${selectedIndices.includes(index) ? 'selected' : ''}`}
              onClick={() => handlePageClick(index)}
              title={page.title}
            >
              {page.title}
            </button>
          ))}
        </div>
        
        {pages.length > 1 && (
          <div className="comparison-toggle-container">
            <span className="comparison-toggle-label">Comparison</span>
            <button
              className={`comparison-toggle ${comparisonMode ? 'active' : ''}`}
              onClick={handleComparisonToggle}
              aria-label="Toggle comparison mode"
            />
          </div>
        )}
      </div>
    </div>
  );
};

const SensitivityScoresHeader = ({ pages, selectedIndices }) => {
  const selectedPages = selectedIndices.map(index => pages[index]);

  // Fonction pour obtenir le texte d'explication du score
  const getSensitivityExplanation = (score) => {
    const numScore = parseFloat(score);
    if (numScore >= 80) {
      return "Score très élevé : Cette page est extrêmement sensible aux changements. Les modifications peuvent avoir un impact significatif sur la perception et la crédibilité du contenu.";
    } else if (numScore >= 60) {
      return "Score élevé : Cette page présente une sensibilité notable. Les modifications doivent être effectuées avec prudence et vérification.";
    } else if (numScore >= 40) {
      return "Score modéré : Cette page a une sensibilité moyenne. Les changements sont généralement bien tolérés mais nécessitent une attention raisonnable.";
    } else if (numScore >= 20) {
      return "Score faible : Cette page a une faible sensibilité. Les modifications sont généralement peu controversées.";
    } else {
      return "Score très faible : Cette page est très peu sensible aux changements. Les modifications sont rarement problématiques.";
    }
  };

  return (
    <div className="sensitivity-scores-header">
      <div className="sensitivity-scores-grid">
        {selectedPages.map((page, index) => (
          <Tooltip
            key={index}
            content={
              <div>
                <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                  Score de sensibilité : {formatMetricValue(page.scores?.sensitivity)}%
                </div>
                <div style={{ marginBottom: '8px' }}>
                  {getSensitivityExplanation(page.scores?.sensitivity)}
                </div>
                <div style={{ fontSize: '12px', opacity: '0.8' }}>
                  Basé sur l'analyse de l'activité éditoriale, des vues et des métriques de qualité.
                </div>
              </div>
            }
            position="bottom"
          >
            <div className="sensitivity-score-card">
              <div className="sensitivity-score-number">
                {formatMetricValue(page.scores?.sensitivity)}%
              </div>
              <div className="sensitivity-score-label">
                {page.title?.length > 15 
                  ? `${page.title.substring(0, 15)}...` 
                  : page.title}
              </div>
              
            </div>
          </Tooltip>
        ))}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
// 🆕 NOUVELLES VUES DESIGN AVEC PREVIEW FLOUTÉ
// ═══════════════════════════════════════════════════════════════════════

// Vue d'état initial avec preview des résultats flouté
const IdleView = () => (
  <div className="results-container">
    {/* Contenu de preview flouté en arrière-plan */}
    <div className="results-preview-background">
      <div className="preview-header">
        <div className="preview-breadcrumb">
          <span>Analysis Results</span>
          <span className="breadcrumb-separator">›</span>
          <span>Ready to analyze</span>
        </div>
        <div className="preview-actions">
          <div className="preview-button">↑ New Analysis</div>
          <div className="preview-button">Export Results</div>
        </div>
      </div>

      <div className="preview-content">
        {/* Section des scores principaux */}
        <div className="preview-scores-section">
          <h2 className="preview-section-title">Sensitivity Scores</h2>
          <div className="preview-scores-grid">
            <div className="preview-score-card heat">
              <div className="score-icon">🔥</div>
              <div className="score-value">72.5</div>
              <div className="score-label">Heat Score</div>
              <div className="score-trend">High Activity</div>
            </div>
            <div className="preview-score-card quality">
              <div className="score-icon">⭐</div>
              <div className="score-value">85.2</div>
              <div className="score-label">Quality Score</div>
              <div className="score-trend">Excellent</div>
            </div>
            <div className="preview-score-card risk">
              <div className="score-icon">⚠️</div>
              <div className="score-value">34.1</div>
              <div className="score-label">Risk Score</div>
              <div className="score-trend">Low Risk</div>
            </div>
            <div className="preview-score-card sensitivity">
              <div className="score-icon">📊</div>
              <div className="score-value">63.9</div>
              <div className="score-label">Sensitivity</div>
              <div className="score-trend">Moderate</div>
            </div>
          </div>
        </div>

        

        {/* Section graphiques */}
        <div className="preview-charts-section">
          <div className="preview-chart-container">
            <h3 className="chart-title">Sensitivity Profile</h3>
            <div className="preview-radar-chart">
              <div className="radar-center">
                <div className="radar-value">63.9</div>
                <div className="radar-label">Overall</div>
              </div>
            </div>
          </div>

          <div className="preview-chart-container">
            <h3 className="chart-title">Page Views Timeline</h3>
            <div className="preview-chart">
              <div className="chart-bars">
                <div className="chart-bar" style={{height: '60%'}}></div>
                <div className="chart-bar" style={{height: '80%'}}></div>
                <div className="chart-bar" style={{height: '45%'}}></div>
                <div className="chart-bar" style={{height: '90%'}}></div>
                <div className="chart-bar" style={{height: '75%'}}></div>
                <div className="chart-bar" style={{height: '65%'}}></div>
                <div className="chart-bar" style={{height: '85%'}}></div>
                <div className="chart-bar" style={{height: '70%'}}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Section métriques détaillées */}
        <div className="preview-metrics-section">
          <h2 className="preview-section-title">Detailed Metrics</h2>
          <div className="preview-metrics-grid">
            <div className="metric-item">
              <div className="metric-label">Views Spikes</div>
              <div className="metric-value">8.2</div>
            </div>
            <div className="metric-item">
              <div className="metric-label">Edit Activity</div>
              <div className="metric-value">15.7</div>
            </div>
            <div className="metric-item">
              <div className="metric-label">Protection Level</div>
              <div className="metric-value">3.1</div>
            </div>
            <div className="metric-item">
              <div className="metric-label">Source Quality</div>
              <div className="metric-value">7.9</div>
            </div>
            <div className="metric-item">
              <div className="metric-label">Anonymous Edits</div>
              <div className="metric-value">23%</div>
            </div>
            <div className="metric-item">
              <div className="metric-label">Revert Risk</div>
              <div className="metric-value">4.2</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    {/* Overlay avec message d'état */}
    <div className="results-overlay">
      <div className="overlay-content">
        <div className="overlay-icon">📊</div>
        <h3>Your results will appear here</h3>
        <p>Configure your analysis parameters above and click "Analyze" to see detailed Wikipedia insights like these</p>
        <div className="preview-features">
          <div className="feature-item">
            <span className="feature-icon">🎯</span>
            <span>Sensitivity Profiles</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">📈</span>
            <span>Interactive Charts</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🔍</span>
            <span>Detailed Metrics</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">⚖️</span>
            <span>Comparison Mode</span>
          </div>
        </div>
      </div>
    </div>
  </div>
);

// Vue de chargement avec preview partiellement visible
const LoadingView = ({ analysisData, progress = 0 }) => {
  // Déterminer l'étape actuelle basée sur le progrès
  const getCurrentStep = (progress) => {
    if (progress < 20) return "Collecting Wikipedia data...";
    if (progress < 50) return "Processing metrics...";
    if (progress < 80) return "Calculating scores...";
    if (progress < 95) return "Generating charts...";
    return "Finalizing results...";
  };

  const currentStep = getCurrentStep(progress);

  return (
    <div className="results-container">
      {/* Même contenu de preview mais moins flouté */}
      <div className="results-preview-background loading">
        <div className="preview-header">
          <div className="preview-breadcrumb">
            <span>Analysis Results</span>
            <span className="breadcrumb-separator">›</span>
            <span>Analysis in progress...</span>
          </div>
          <div className="preview-actions">
            <div className="preview-button disabled">↑ New Analysis</div>
            <div className="preview-button disabled">Export Results</div>
          </div>
        </div>

        <div className="preview-content">
          <div className="preview-scores-section">
            <h2 className="preview-section-title">Sensitivity Scores</h2>
            <div className="preview-scores-grid">
              <div className="preview-score-card heat loading-shimmer">
                <div className="score-icon">🔥</div>
                <div className="score-value">--</div>
                <div className="score-label">Heat Score</div>
                <div className="score-trend">Loading...</div>
              </div>
              <div className="preview-score-card quality loading-shimmer">
                <div className="score-icon">⭐</div>
                <div className="score-value">--</div>
                <div className="score-label">Quality Score</div>
                <div className="score-trend">Loading...</div>
              </div>
              <div className="preview-score-card risk loading-shimmer">
                <div className="score-icon">⚠️</div>
                <div className="score-value">--</div>
                <div className="score-label">Risk Score</div>
                <div className="score-trend">Loading...</div>
              </div>
              <div className="preview-score-card sensitivity loading-shimmer">
                <div className="score-icon">📊</div>
                <div className="score-value">--</div>
                <div className="score-label">Sensitivity</div>
                <div className="score-trend">Loading...</div>
              </div>
            </div>
          </div>

          <div className="preview-pages-section">
            <h2 className="preview-section-title">Page Selection</h2>
            <div className="preview-pages-list">
              {analysisData?.pages?.slice(0, 3).map((page, index) => (
                <div key={index} className="preview-page-item loading-shimmer">
                  <div className="page-title">{page}</div>
                  <div className="page-scores">
                    <span className="mini-score heat">--</span>
                    <span className="mini-score quality">--</span>
                    <span className="mini-score risk">--</span>
                  </div>
                  <div className="page-status">Processing...</div>
                </div>
              )) || (
                <div className="preview-page-item loading-shimmer">
                  <div className="page-title">Loading...</div>
                  <div className="page-scores">
                    <span className="mini-score heat">--</span>
                    <span className="mini-score quality">--</span>
                    <span className="mini-score risk">--</span>
                  </div>
                  <div className="page-status">Processing...</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Overlay de chargement */}
      <div className="results-overlay loading-overlay">
        <div className="overlay-content">
          
<div className="loading-logo">
  <img 
    src="/opsci.png" 
    alt="Wikimetron Loading..." 
    className="rotating-logo "
    style={{
      filter: 'drop-shadow(0 0 15px rgba(59, 130, 246, 0.6))'
    }}
  />
</div>
          <h3>Analyzing {analysisData?.pages?.length || 0} Wikipedia page{(analysisData?.pages?.length || 0) !== 1 ? 's' : ''}...</h3>
          <p>{currentStep}</p>
          
          <div className="progress-container">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <span className="progress-text">{Math.round(progress)}%</span>
          </div>

          <div className="loading-steps">
            <div className={`step ${progress > 20 ? 'completed' : progress > 0 ? 'active' : ''}`}>
              <span className="step-icon">🔍</span>
              <span>Collecting data</span>
            </div>
            <div className={`step ${progress > 50 ? 'completed' : progress > 20 ? 'active' : ''}`}>
              <span className="step-icon">⚙️</span>
              <span>Processing metrics</span>
            </div>
            <div className={`step ${progress > 80 ? 'completed' : progress > 50 ? 'active' : ''}`}>
              <span className="step-icon">📊</span>
              <span>Calculating scores</span>
            </div>
            <div className={`step ${progress > 95 ? 'completed' : progress > 80 ? 'active' : ''}`}>
              <span className="step-icon">✨</span>
              <span>Finalizing results</span>
            </div>
          </div>

          {analysisData?.pages && analysisData.pages.length > 0 && (
            <div className="analysis-info">
              <div className="info-item">
                <span className="info-label">Pages:</span>
                <span className="info-value">{analysisData.pages.join(', ')}</span>
              </div>
              {analysisData.detectedLanguage && (
                <div className="info-item">
                  <span className="info-label">Language:</span>
                  <span className="info-value">🌐 {analysisData.detectedLanguage.toUpperCase()}</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Vue d'erreur améliorée
const ErrorView = ({ error, onReset }) => (
  <div className="results-container">
    <div className="results-preview-background error">
      <div className="preview-content">
        <div className="preview-scores-section">
          <div className="preview-scores-grid">
            <div className="preview-score-card error-card">
              <div className="score-icon">❌</div>
              <div className="score-value">Error</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div className="results-overlay error-overlay">
      <div className="overlay-content">
        <div className="overlay-icon error-icon">⚠️</div>
        <h3>Analysis Error</h3>
        <p className="error-message">{error}</p>
        <div className="error-actions">
          <button onClick={onReset} className="btn btn-primary">
            Try Again
          </button>
        </div>
      </div>
    </div>
  </div>
);

// Vue des résultats (inchangée)
const ResultsView = ({ results, analysisConfig, onNewAnalysis }) => {
  const [selectedPageIndices, setSelectedPageIndices] = useState([0]);
  const [comparisonMode, setComparisonMode] = useState(false);
  
  const pages = results.pages || [];
  
  if (pages.length === 0) {
    return (
      <div className="results-empty-view">
        <div className="empty-content">
          <div className="empty-icon">📋</div>
          <h3>No Results</h3>
          <p>No pages could be analyzed</p>
          <button onClick={onNewAnalysis} className="btn btn-primary">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const handlePageSelection = (indices, isComparison) => {
    setSelectedPageIndices(indices);
    setComparisonMode(isComparison);
  };
  
  const selectedPages = selectedPageIndices.map(index => pages[index]);

  // Export function: download results as JSON file
  const handleExportResults = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(results, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "wikimetron_results.json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  return (
    <div className="results-container-new">
      <div className="results-header">
        <h2>Analysis Results</h2>
        <div className="results-actions">
          <button
            onClick={onNewAnalysis}
            className="action-button-modern secondary"
          >
            ↑ New Analysis
          </button>
          <button
            onClick={handleExportResults}
            className="action-button-modern primary"
          >
            Export Results
          </button>
        </div>
      </div>

      <div className="results-main-content">
        <ModernPageSelector
          pages={pages}
          selectedIndices={selectedPageIndices}
          comparisonMode={comparisonMode}
          onSelectionChange={handlePageSelection}
        />

        <div className="results-grid-modern">
          <div className="results-card-modern kiviat-card">
            <h4 className="chart-title-modern">Sensitivity Profile</h4>
            <div className="kiviat-container-modern">
              <SensitivityScoresHeader 
                pages={pages}
                selectedIndices={selectedPageIndices}
              />
              <div className="kiviat-chart-section">
                <div className="kiviat-chart-wrapper">
                  <KiviatChart
                    pages={pages}
                    selectedPageIndices={selectedPageIndices}
                    comparisonMode={comparisonMode}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="results-card-modern pageviews-card">
            <div className="chart-container-modern">
              <div className="chart-header-modern">
                <h4 className="chart-title-modern">Page Views</h4>
              </div>
              <div className="chart-wrapper-modern">
                <PageviewsChart
                  pages={selectedPages}
                  analysisConfig={analysisConfig}
                />
              </div>
            </div>
          </div>

          <div className="results-card-modern metrics-card">
            <MetricsDisplay
              pages={selectedPages}
              comparisonMode={comparisonMode}
            />
          </div>
          
          <div className="results-card-modern edits-card">
            <div className="chart-container-modern">
              <div className="chart-header-modern">
                <h4 className="chart-title-modern">Edits</h4>
              </div>
              <div className="chart-wrapper-modern">
                <EditChart
                  pages={selectedPages}
                  analysisConfig={analysisConfig}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Composant principal avec les nouvelles vues
const ResultsSection = ({ analysisState, onNewAnalysis, onReset }) => {
  const { status, data, results, error, progress } = analysisState;

  return (
    <div className={`results-section-container ${status}`}>
      {status === 'idle' && <IdleView />}
      {status === 'loading' && <LoadingView analysisData={data} progress={progress} />}
      {status === 'error' && <ErrorView error={error} onReset={onReset} />}
      {status === 'completed' && results && (
        <ResultsView 
          results={results} 
          analysisConfig={data}
          onNewAnalysis={onNewAnalysis}
        />
      )}
    </div>
  );
};

export default ResultsSection;