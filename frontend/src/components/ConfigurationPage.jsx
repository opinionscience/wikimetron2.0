// File: src/components/ConfigurationPage.jsx - Version corrigée et simplifiée
import React, { useState, useEffect } from 'react';
import { LoadingSpinner } from './LoadingSpinner';

const API_BASE =
  process.env.NODE_ENV === "development"
    ? process.env.REACT_APP_API_URL || "http://localhost:8200"
    : "";

const LANGUAGE_OPTIONS = [
  { value: 'fr', label: '🇫🇷 Français' },
  { value: 'en', label: '🇺🇸 English' },

];

const QUICK_DATE_RANGES = [
  { label: 'Last week', days: 7 },
  { label: 'Last month', days: 30 },
  { label: 'Last 3 months', days: 90 },
  { label: 'Last 6 months', days: 180 },
  { label: 'This year', months: 'year' },
  { label: 'Last 12 months', months: 'last 12 months' }
];

// Fonction pour calculer les dates
const calculateDateRange = (option) => {
  const today = new Date();
  const endDate = today.toISOString().split('T')[0];
  let startDate;

  if (option.months === 'year') {
    startDate = new Date(today.getFullYear(), 0, 1).toISOString().split('T')[0];
  } else if (option.months === 'last 12 months') {
    const start = new Date(today);
    start.setFullYear(today.getFullYear() - 1);
    startDate = start.toISOString().split('T')[0];
  } else if (option.days) {
    const start = new Date(today);
    start.setDate(start.getDate() - option.days);
    startDate = start.toISOString().split('T')[0];
  }

  return { startDate, endDate };
};

// Fonction pour extraire la langue depuis une URL Wikipedia
const extractLanguageFromUrl = (url) => {
  try {
    if (url && typeof url === 'string' && url.startsWith('http') && url.includes('wikipedia.org')) {
      const hostname = new URL(url).hostname;
      return hostname.split('.')[0]; // ex: "fr" depuis "fr.wikipedia.org"
    }
  } catch (e) {
    console.warn('Erreur extraction langue:', e);
  }
  return null;
};

// Détection locale rapide de langue depuis la première URL
const detectLanguageFromInput = (urlInput) => {
  if (!urlInput || typeof urlInput !== 'string') return null;
  return extractLanguageFromUrl(urlInput.trim());
};

// 🔧 Composant d'input simplifié
const PagesInput = ({ urlValue, pageNameValue, selectedLanguage, onUrlChange, onPageNameChange, onLanguageChange, additionalPages, onAdditionalPagesChange }) => {
  const [detectedLanguage, setDetectedLanguage] = useState(null);
  
  // Calcul du nombre total de pages
  const getTotalPagesCount = () => {
    let count = 0;
    if (urlValue && urlValue.trim()) count++;
    if (pageNameValue && pageNameValue.trim() && selectedLanguage) count++;
    if (additionalPages) {
      additionalPages.forEach(page => {
        if (page.url && page.url.trim()) count++;
        else if (page.pageName && page.pageName.trim() && page.language) count++;
      });
    }
    return count;
  };

  // Détection de langue depuis l'URL
  useEffect(() => {
    const detected = detectLanguageFromInput(urlValue);
    setDetectedLanguage(detected);
  }, [urlValue]);
  
  const totalPages = getTotalPagesCount();
  
  return (
    <div className="form-section">
      <div className="form-section-header">
        <h3>Pages to analyze</h3>
      </div>
      
      {/* Input principal pour URL */}
      <div className="page-input-group full-width">
        <span className="input-label">Page URL:</span>
        <div className="url-input-row" style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
          <input
            type="text"
            value={urlValue || ''}
            onChange={(e) => onUrlChange(e.target.value)}
            placeholder="  https://en.wikipedia.org/wiki/the_page_title"
            className="form-input page-url-input"
            style={{ backgroundColor: '#f5f5f5', flex: 1 }}
          />
          {detectedLanguage && (
            <span className="detected-language-badge" style={{ marginLeft: 8 }}>
              {LANGUAGE_OPTIONS.find(opt => opt.value === detectedLanguage)?.label?.replace(/🇫🇷|🇺🇸|🇩🇪|🇪🇸|🇮🇹/, '').trim() || detectedLanguage.charAt(0).toUpperCase() + detectedLanguage.slice(1)}
            </span>
          )}
        </div>
      </div>
      <div className="input-separator">
        <span>OR</span>
      </div>
      
      <div className="page-name-group">
    <div className="page-name-section">
        <span className="input-label">Page name:</span>
        <input
            type="text"
            value={pageNameValue || ''}
            onChange={(e) => onPageNameChange(e.target.value)}
            placeholder="Type the title of a page"
            className="form-input page-name-input"
            style={{ backgroundColor: '#f5f5f5' }}
        />
    </div>
    <div className="language-section">
        <span className="and-language">Language:</span>
        <select
            value={selectedLanguage || ''}
            onChange={(e) => onLanguageChange(e.target.value)}
            className="form-select language-select"
            style={{ backgroundColor: '#f5f5f5' }}
        >
            <option value="">Choose</option>
            {LANGUAGE_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                    {option.label}
                </option>
            ))}
        </select>
    </div>
</div>
      
      {/* Pages supplémentaires */}
      {additionalPages && additionalPages.length > 0 && additionalPages.map((page, index) => {
        // Détection de langue pour cette page supplémentaire
        const additionalDetectedLang = detectLanguageFromInput(page.url || '');
        
        return (
          <div key={index} className="additional-page-group">
            {/* URL pour page supplémentaire */}
            <div className="page-input-group">
              <span className="input-label">Page URL:</span>
              <input
                type="text"
                value={page.url || ''}
                onChange={(e) => {
                  const newPages = [...additionalPages];
                  newPages[index] = { 
                    ...newPages[index], 
                    url: e.target.value,
                    // Reset page name if URL is provided
                    ...(e.target.value ? { pageName: '', language: '' } : {})
                  };
                  onAdditionalPagesChange(newPages);
                }}
                placeholder="  https://en.wikipedia.org/wiki/the_page_title"
                className="form-input page-url-input"
                style={{ display: 'flex', alignItems: 'center', width: '100%' }}
              />
              {additionalDetectedLang && (
                <span className="detected-language-badge">
                   {LANGUAGE_OPTIONS.find(opt => opt.value === additionalDetectedLang)?.label?.replace(/🇫🇷|🇺🇸|🇩🇪|🇪🇸|🇮🇹/, '').trim() || additionalDetectedLang.charAt(0).toUpperCase() + additionalDetectedLang.slice(1)}
                </span>
              )}
            </div>
            
            {/* Séparateur OR pour page supplémentaire */}
            <div className="input-separator">
        <span>OR</span>
      </div>
      
            
            {/* Nom de page + langue pour page supplémentaire */}
            <div className="page-name-group">
              <span className="input-label">Page name:</span>
              <input
                type="text"
                value={page.pageName || ''}
                onChange={(e) => {
                  const newPages = [...additionalPages];
                  newPages[index] = { 
                    ...newPages[index], 
                    pageName: e.target.value,
                    // Reset URL if page name is provided
                    ...(e.target.value ? { url: '' } : {})
                  };
                  onAdditionalPagesChange(newPages);
                }}
                placeholder="Type the title of a page"
                className="form-input page-name-input"
              />
              <span className="and-language">Language:</span>
              <select 
                value={page.language || ''} 
                onChange={(e) => {
                  const newPages = [...additionalPages];
                  newPages[index] = { ...newPages[index], language: e.target.value };
                  onAdditionalPagesChange(newPages);
                }}
                className="form-select language-select"
                style={{ backgroundColor: '#ffffffff' }}
              >
                <option value="">Choose</option>
                {LANGUAGE_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Bouton de suppression repositionné en bas à droite */}
            <button
              type="button"
              onClick={() => {
                const newPages = additionalPages.filter((_, i) => i !== index);
                onAdditionalPagesChange(newPages);
              }}
              className="remove-page-btn remove-page-btn-bottom"
              title="Remove this page"
            >
              ×
            </button>
          </div>
        );
      })}

      {/* Bouton pour ajouter une autre page - maintenant toujours en bas */}
      <div className="add-page-section">
        <button 
          type="button" 
          className="add-page-btn"
          onClick={() => {
            const newPages = [...(additionalPages || []), { url: '', pageName: '', language: '' }];
            onAdditionalPagesChange(newPages);
          }}
        >
          <span className="plus-icon">+</span>
          Compare with another page (optional)
        </button>
      </div>
      
      <div className="form-bottom-section">
  <div className="form-help">
    <span>Enter Wikipedia URLs for automatic language detection, or page titles with manual language selection. Maximum 5 pages per analysis.</span>
  </div>
  <div className="page-counter-badge">
    <span className="page-count">{totalPages}</span>
    <span className="page-label">
      {totalPages <= 1 ? 'page' : 'pages'}
    </span>
  </div>
</div>

    </div>
  );
};

// 🔄 Sélecteur de période adapté
const DateRangeSelector = ({ startDate, endDate, onStartChange, onEndChange }) => {
  const [selectedQuickRange, setSelectedQuickRange] = useState('');

  const handleQuickRange = (range) => {
    const dates = calculateDateRange(range);
    onStartChange(dates.startDate);
    onEndChange(dates.endDate);
    setSelectedQuickRange(range.label);
  };

  const handleCustomDate = () => {
    setSelectedQuickRange('');
  };

  return (
    <div className="form-section">
      <div className="form-section-header">
        <h3>Timeframe</h3>
      </div>
      
      {/* Boutons de période rapide */}
      <div className="quick-dates">
        <div className="quick-dates-grid">
          {QUICK_DATE_RANGES.map(range => (
            <button
              key={range.label}
              onClick={() => handleQuickRange(range)}
              className={`quick-date-btn ${selectedQuickRange === range.label ? 'active' : ''}`}
              type="button"
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {/* Séparateur */}
      <div className="input-separator">
        <span>OR</span>
      </div>

      {/* Sélection de dates personnalisées */}
<div className="custom-dates">
  <div className="date-inputs">
    <span className="date-label">From:</span>
    <input 
      type="date" 
      value={startDate} 
      onChange={(e) => {
        onStartChange(e.target.value);
        handleCustomDate();
      }}
      className="form-input date-input"
    />
    <span className="date-label">to:</span>
    <input 
      type="date" 
      value={endDate} 
      onChange={(e) => {
        onEndChange(e.target.value);
        handleCustomDate();
      }}
      className="form-input date-input"
    />
  </div>

      </div>
    </div>
  );
};

// Résumé d'analyse simplifié
const AnalysisSummary = ({ totalPages, startDate, endDate, detectedLanguage, manualLanguage }) => {
  if (totalPages === 0) return null;

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getLanguageDisplay = () => {
    if (detectedLanguage) {
      return `Auto (${detectedLanguage.toUpperCase()})`;
    }
    if (manualLanguage) {
      return manualLanguage.toUpperCase();
    }
    return 'Not specified';
  };

  return (
    <div className="analysis-preview">
      <h3>🚀 Ready to analyze</h3>
      <div className="preview-stats">
        <div className="stat">
          <span className="stat-number">{totalPages}</span>
          <span className="stat-label">page{totalPages > 1 ? 's' : ''}</span>
        </div>
        <div className="stat">
          <span className="stat-number">{getLanguageDisplay()}</span>
          <span className="stat-label">language</span>
        </div>
        <div className="stat">
          <span className="stat-number">{formatDate(startDate)}</span>
          <span className="stat-label">from</span>
        </div>
        <div className="stat">
          <span className="stat-number">{formatDate(endDate)}</span>
          <span className="stat-label">to</span>
        </div>
      </div>
    </div>
  );
};

const ErrorAlert = ({ message }) => (
  <div className="alert alert-error">
    <span>⚠️ {message}</span>
  </div>
);

const SubmitButton = ({ onClick, disabled, loading, totalPages }) => (
  <div className="submit-section">
    <button 
      onClick={onClick} 
      disabled={disabled} 
      className={`btn btn-primary btn-large submit-btn analyze-btn${loading ? ' hover' : ''}`}
      type="button"
    >
      {loading ? (
        <span style={{ margin: '0 auto', alignItems: 'center' }}>
          <LoadingSpinner />
        </span>
      ) : (
        'ANALYZE'
      )}
    </button>
  </div>
);

// COMPOSANT PRINCIPAL SIMPLIFIÉ
const ConfigurationPage = ({ 
  onAnalysisStart, 
  onAnalysisComplete, 
  onAnalysisError, 
  onProgressUpdate,
  isAnalyzing = false 
}) => {
  // États séparés pour chaque input
  const [urlInput, setUrlInput] = useState('');
  const [pageNameInput, setPageNameInput] = useState('');
  const [manualLanguage, setManualLanguage] = useState('');
  const [additionalPages, setAdditionalPages] = useState([]);
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [error, setError] = useState(null);

  // Détection de langue depuis l'URL
  const detectedLanguage = detectLanguageFromInput(urlInput);

  // Calcul du nombre total de pages valides
  const getTotalPages = () => {
    const pages = [];
    
    // URL principale
    if (urlInput && urlInput.trim()) {
      pages.push(urlInput.trim());
    }
    
    // Page nommée (seulement si langue sélectionnée)
    if (pageNameInput && pageNameInput.trim() && manualLanguage) {
      pages.push(pageNameInput.trim());
    }
    
    // Pages supplémentaires
    if (additionalPages) {
      additionalPages.forEach(page => {
        if (page.url && page.url.trim()) {
          pages.push(page.url.trim());
        } else if (page.pageName && page.pageName.trim() && page.language) {
          pages.push(page.pageName.trim());
        }
      });
    }
    
    return pages;
  };

  const allPages = getTotalPages();
  const totalPages = allPages.length;

  const handleSubmit = async () => {
    console.log('handleSubmit called', { totalPages, isAnalyzing });
    
    if (totalPages === 0) {
      setError('Please enter at least one Wikipedia page');
      return;
    }
    
    if (totalPages > 5) {
      setError('Maximum 5 pages per analysis');
      return;
    }

    // Vérifier qu'on a au moins une source avec langue
    const hasUrlWithDetection = urlInput && urlInput.trim() && detectedLanguage;
    const hasPageWithLanguage = pageNameInput && pageNameInput.trim() && manualLanguage;
    
    if (!hasUrlWithDetection && !hasPageWithLanguage) {
      setError('Please provide either a Wikipedia URL (for auto-detection) or a page name with language selection');
      return;
    }
    
    setError(null);
    
    // Créer les données d'analyse
    const analysisData = {
      taskId: 'pending',
      pages: allPages,
      detectedLanguage: detectedLanguage,
      manualLanguage: manualLanguage,
      startDate,
      endDate,
      estimatedTime: Math.ceil(totalPages * 30)
    };
    
    // Démarrer l'analyse
    onAnalysisStart(analysisData);
    
    // Simulation de progression
    const progressInterval = setInterval(() => {
      onProgressUpdate(prev => Math.min(prev + Math.random() * 10, 90));
    }, 500);
    
    try {
      // Préparer la requête API
      const requestData = {
        pages: allPages,
        start_date: startDate,
        end_date: endDate
      };
      
      // Ajouter la langue seulement si on force manuellement
      // Sinon laisser l'API détecter automatiquement
      if (manualLanguage && !detectedLanguage) {
        requestData.language = manualLanguage;
      }
      
      console.log('Sending request:', requestData);
      
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }
      
      const data = await response.json();
      console.log('API response:', data);
      
      // Mettre à jour avec le vrai taskId
      const updatedAnalysisData = {
        ...analysisData,
        taskId: data.task_id,
        estimatedTime: data.estimated_time || analysisData.estimatedTime,
        detectedLanguage: data.detected_language || detectedLanguage
      };
      
      onAnalysisStart(updatedAnalysisData);
      
      // Polling des résultats
      const pollResults = async () => {
        try {
          const response = await fetch(`${API_BASE}/api/tasks/${data.task_id}`);
          if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
          const taskData = await response.json();

          if (taskData.status === 'completed' && taskData.results) {
            clearInterval(progressInterval);
            onProgressUpdate(100);
            setTimeout(() => {
              onAnalysisComplete(taskData.results);
            }, 500);
          } else if (taskData.status === 'error') {
            clearInterval(progressInterval);
            onAnalysisError(taskData.error || 'Erreur lors de l\'analyse');
          } else {
            setTimeout(pollResults, 2000);
          }
        } catch (err) {
          console.error('Erreur polling:', err);
          setTimeout(pollResults, 5000);
        }
      };

      pollResults();
      
    } catch (err) {
      console.error('Error starting analysis:', err);
      clearInterval(progressInterval);
      onAnalysisError(`Erreur lors du démarrage de l'analyse: ${err.message}`);
    }
  };

  const isSubmitDisabled = totalPages === 0 || isAnalyzing;

  return (
    <div className="config-container">
      <div className="config-form">
        <PagesInput 
          urlValue={urlInput}
          pageNameValue={pageNameInput}
          selectedLanguage={manualLanguage}
          onUrlChange={setUrlInput}
          onPageNameChange={setPageNameInput}
          onLanguageChange={setManualLanguage}
          additionalPages={additionalPages}
          onAdditionalPagesChange={setAdditionalPages}
        />
        
        <DateRangeSelector 
          startDate={startDate}
          endDate={endDate}
          onStartChange={setStartDate}
          onEndChange={setEndDate}
        />
        
        <AnalysisSummary 
          totalPages={totalPages}
          startDate={startDate} 
          endDate={endDate} 
          detectedLanguage={detectedLanguage}
          manualLanguage={manualLanguage}
        />
        
        {error && <ErrorAlert message={error} />}
        
        <SubmitButton 
          onClick={handleSubmit} 
          disabled={isSubmitDisabled} 
          loading={isAnalyzing}
          totalPages={totalPages}
        />
      </div>
    </div>
  );
};

export default ConfigurationPage;