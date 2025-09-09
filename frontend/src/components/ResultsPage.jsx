// File: src/components/ResultsSection.jsx
import React, { useState } from 'react';
import { ModernLoadingOverlay } from './LoadingSpinner';
import KiviatChart from './results/KiviatChart';
import PageviewsChart from './results/PageviewsChart';
import EditChart from './results/EditChart';
import MetricsDisplay from './results/MetricsDisplay';
import './ResultsPage.css';

// Palette de couleurs pour les scores de sensibilité
const PAGE_COLORS = [
  '#3b82f6', // Bleu
  '#ef4444', // Rouge
  '#10b981', // Vert
  '#f59e0b', // Orange
  '#8b5cf6', // Violet
  '#06b6d4'  // Cyan
];

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

  const getSensitivityExplanation = (score) => {
  const numScore = parseFloat(score);
  if (numScore >= 80) {
    return "Very high score: This page is extremely sensitive";
  } else if (numScore >= 60) {
    return "High score: This page shows notable sensitivity.";
  } else if (numScore >= 40) {
    return "Moderate score: This page has average sensitivity.";
  } else if (numScore >= 15) {
    return "Low score: This page has low sensitivity.";
  } else {
    return "Very low score: This page has very little sensitivity.";
  }
};

  return (
    <div className="sensitivity-scores-header">
      <div className="sensitivity-scores-grid">
        {selectedPages.map((page, i) => {
          const pageIndex = selectedIndices[i];
          const bg = PAGE_COLORS[pageIndex % PAGE_COLORS.length];

          return (
            <Tooltip
              key={pageIndex}
              content={
                <div>
                  <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                    sensitivity score : {formatMetricValue(page.scores?.sensitivity)}%
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    {getSensitivityExplanation(page.scores?.sensitivity)}
                  </div>
                  
                </div>
              }
              position="bottom"
            >
              <div
                className="sensitivity-score-card"
                style={{
                  backgroundColor: bg,
                  color: 'white',
                  boxShadow: '0 6px 18px rgba(0,0,0,0.18)'
                }}
              >
                <div className="sensitivity-score-label">
                  {page.title?.length > 15 
                    ? `${page.title.substring(0, 15)}...` 
                    : page.title}
                </div>
                <div className="sensitivity-score-number">
                  {formatMetricValue(page.scores?.sensitivity)}%
                </div>
              </div>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
};

// Vue de chargement avec preview partiellement visible et espacement footer
const LoadingView = ({ analysisData, progress = 0 }) => {
  const getCurrentStep = (progress) => {
    if (progress < 20) return "Collecting Wikipedia data...";
    if (progress < 50) return "Processing metrics...";
    if (progress < 80) return "Calculating scores...";
    if (progress < 95) return "Generating charts...";
  };

  const currentStep = getCurrentStep(progress);

  return (
    <div className="results-container" style={{ minHeight: '100vh', paddingBottom: '200px' }}>
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
          </div>
        </div>
      </div>
    </div>
  );
};

// Vue d'erreur améliorée avec espacement footer
const ErrorView = ({ error, onReset }) => (
  <div className="results-container" style={{ minHeight: '100vh', paddingBottom: '200px' }}>
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

// Vue des résultats
const ResultsView = ({ results, analysisConfig, originalPages }) => {
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
        </div>
      </div>
    );
  }

  const handlePageSelection = (indices, isComparison) => {
    setSelectedPageIndices(indices);
    setComparisonMode(isComparison);
  };
  
  const selectedPages = selectedPageIndices.map(index => pages[index]);

  return (
    <div className="results-container-new">
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
  pages={selectedPageIndices.map(index => originalPages[index])}
  analysisConfig={analysisConfig}
/>
              </div>
            </div>
          </div>

          <div className="results-card-modern2 metrics-card">
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
  pages={selectedPageIndices.map(index => originalPages[index])}
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

// Composant principal
const ResultsSection = ({ 
  analysisState, 
  originalPages,    // AJOUT
  analysisConfig,   // AJOUT 
  onNewAnalysis, 
  onReset 
}) => {

  const { status, data, results, error, progress } = analysisState;

  if (status === 'idle') {
    return null;
  }

  const handleExportResults = () => {
    if (results) {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(results, null, 2));
      const downloadAnchorNode = document.createElement('a');
      downloadAnchorNode.setAttribute("href", dataStr);
      downloadAnchorNode.setAttribute("download", "wikimetron_results.json");
      document.body.appendChild(downloadAnchorNode);
      downloadAnchorNode.click();
      downloadAnchorNode.remove();
    }
  };

  return (
    <>
      <header className="wikimetron-header minimal-header">
  <div className="minimal-container">
    <div className="header-content">
      {/* Section logo et titre */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center',
        flex: '1',
        minWidth: '0' // Permet le text-overflow
      }}>
        <a 
          href="https://disinfo-prompt.eu/" 
          target="_blank" 
          rel="noopener noreferrer" 
          className="header-logo-link"
        >
          <img src="/prompt.png" alt="Logo 1" className="header-logo" />
        </a>
        <h1 className="minimal-title">Wikipedia Sensitivity Meter</h1>
      </div>
      
      {/* Section boutons - s'adapte automatiquement en mobile */}
      {status === 'completed' && results && (
        <div style={{ 
          display: 'flex',
          gap: '12px',
          alignItems: 'center',
          flexShrink: 0,
          // Sur mobile, les boutons passeront en pleine largeur grâce au CSS
        }}>
          <button
            onClick={handleExportResults}
            className="action-button-modern primary"
          >
            Export Results
          </button>
          <button
            onClick={onNewAnalysis}
            className="action-button-modern secondary"
          >
            ↑ New Analysis
          </button>
        </div>
      )}
    </div>
  </div>
</header>
      
      <div className={`results-section-container ${status}`}>
        {status === 'loading' && <LoadingView analysisData={data} progress={progress} />}
        {status === 'error' && <ErrorView error={error} onReset={onReset} />}
        {status === 'completed' && results && (
  <ResultsView 
    results={results} 
    analysisConfig={analysisConfig}  // Utilisez analysisConfig au lieu de data
    originalPages={originalPages}    // AJOUT
  />
)}
      </div>
    </>
  );
};

export default ResultsSection;
