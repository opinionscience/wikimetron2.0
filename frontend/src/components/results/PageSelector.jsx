// File: src/components/results/PageSelector.jsx
import React, { useState } from 'react';

const renderMetricValue = (value) => {
  if (typeof value === 'number') {
    return value.toFixed(3);
  }
  return value || '0.000';
};

const PageSelector = ({ pages, selectedIndices, comparisonMode, onSelectionChange }) => {
  const [tempSelectedIndices, setTempSelectedIndices] = useState(selectedIndices);

  const handleToggleComparison = () => {
    if (comparisonMode) {
      // Sortir du mode comparaison - garder seulement la première page
      onSelectionChange([selectedIndices[0] || 0], false);
      setTempSelectedIndices([selectedIndices[0] || 0]);
    } else {
      // Entrer en mode comparaison - garder la sélection actuelle
      onSelectionChange(selectedIndices.length > 1 ? selectedIndices : [selectedIndices[0], 1].filter(i => i < pages.length), true);
    }
  };

  const handlePageToggle = (pageIndex) => {
    if (!comparisonMode) {
      // Mode page unique
      onSelectionChange([pageIndex], false);
      setTempSelectedIndices([pageIndex]);
    } else {
      // Mode comparaison
      let newSelection;
      if (tempSelectedIndices.includes(pageIndex)) {
        newSelection = tempSelectedIndices.filter(i => i !== pageIndex);
        if (newSelection.length === 0) {
          newSelection = [0]; // Toujours garder au moins une page
        }
      } else {
        if (tempSelectedIndices.length < 6) { // Max 6 pages en comparaison
          newSelection = [...tempSelectedIndices, pageIndex].sort((a, b) => a - b);
        } else {
          return; // Ne rien faire si déjà 6 pages sélectionnées
        }
      }
      setTempSelectedIndices(newSelection);
      onSelectionChange(newSelection, true);
    }
  };

  const getSensitivityColor = (sensitivity) => {
    const value = parseFloat(sensitivity) || 0;
    if (value >= 0.7) return '#ef4444'; // Rouge - haute sensibilité
    if (value >= 0.5) return '#f59e0b'; // Orange - sensibilité moyenne
    if (value >= 0.3) return '#3b82f6'; // Bleu - sensibilité modérée
    return '#10b981'; // Vert - faible sensibilité
  };

  const currentSelection = comparisonMode ? tempSelectedIndices : selectedIndices;

  return (
    <div className="page-selector-container">
      {/* Header avec contrôles */}
      <div className="page-selector-header">
        <div className="header-left">
          <h3>📊 Pages analysées ({pages.length})</h3>
          <p className="header-subtitle">
            {comparisonMode 
              ? `${currentSelection.length} page(s) sélectionnée(s) pour comparaison`
              : `Page ${currentSelection[0] + 1} sélectionnée`
            }
          </p>
        </div>
        
        {pages.length > 1 && (
          <div className="header-right">
            <div className="comparison-toggle-container">
              <label className="comparison-toggle">
                <input
                  type="checkbox"
                  checked={comparisonMode}
                  onChange={handleToggleComparison}
                />
                <span className="toggle-slider"></span>
                <span className="toggle-label">Mode comparaison</span>
              </label>
              {comparisonMode && (
                <span className="comparison-hint">
                  Sélectionnez jusqu'à 6 pages à comparer
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Grille des pages */}
      <div className={`pages-grid ${comparisonMode ? 'comparison-mode' : 'single-mode'}`}>
        {pages.map((page, index) => {
          const isSelected = currentSelection.includes(index);
          const sensitivity = page.scores?.sensitivity;
          const sensitivityColor = getSensitivityColor(sensitivity);
          const isDisabled = comparisonMode && !isSelected && currentSelection.length >= 6;

          return (
            <div
              key={index}
              className={`page-card ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
              onClick={() => !isDisabled && handlePageToggle(index)}
            >
              {/* Badge de sélection */}
              {comparisonMode && (
                <div className="selection-badge">
                  <div className={`selection-checkbox ${isSelected ? 'checked' : ''}`}>
                    {isSelected && <span>✓</span>}
                  </div>
                </div>
              )}

              {/* Header de la carte */}
              <div className="page-card-header">
                <div className="page-number">#{index + 1}</div>
                <div 
                  className="sensitivity-indicator"
                  style={{ backgroundColor: sensitivityColor }}
                >
                  {renderMetricValue(sensitivity)}
                </div>
              </div>

              {/* Titre de la page */}
              <div className="page-card-title">
                <h4 title={page.title}>{page.title}</h4>
              </div>

              {/* Scores en mini */}
              <div className="page-card-scores">
                <div className="mini-score heat">
                  <span className="score-label">Heat</span>
                  <span className="score-value">
                    {renderMetricValue(page.scores?.heat)}
                  </span>
                </div>
                <div className="mini-score quality">
                  <span className="score-label">Quality</span>
                  <span className="score-value">
                    {renderMetricValue(page.scores?.quality)}
                  </span>
                </div>
                <div className="mini-score risk">
                  <span className="score-label">Risk</span>
                  <span className="score-value">
                    {renderMetricValue(page.scores?.risk)}
                  </span>
                </div>
              </div>

              {/* Indicateur de statut */}
              <div className="page-card-status">
                <span className="status-dot success"></span>
                <span>Analysée</span>
              </div>
            </div>
          );
        })}
      </div>

      
    </div>
  );
};

export default PageSelector;