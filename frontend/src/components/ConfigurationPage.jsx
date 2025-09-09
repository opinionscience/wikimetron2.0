// File: src/components/ConfigurationPage.jsx — Multi-lang (per-page) ready
import React, { useState, useEffect } from 'react';
import { LoadingSpinner } from './LoadingSpinner';

const API_BASE =
  process.env.NODE_ENV === "development"
    ? process.env.REACT_APP_API_URL || "http://localhost:8200"
    : "";

/** Étends la liste au besoin ; fallback prévu si code inconnu */
const LANGUAGE_OPTIONS = [
  { value: 'fr', label: '🇫🇷 Français' },
  { value: 'en', label: '🇬🇧 English' },
  { value: 'de', label: '🇩🇪 Deutsch' },
  { value: 'it', label: '🇮🇹 Italiano' },
  { value: 'es', label: '🇪🇸 Español' },
  { value: 'ca', label: '🏳️ Català' },
  { value: 'pt', label: '🇵🇹 Português' },
  { value: 'et', label: '🇪🇪 Eesti' },
  { value: 'lv', label: '🇱🇻 Latviešu' },
  { value: 'lt', label: '🇱🇹 Lietuvių' },
  { value: 'ro', label: '🇷🇴 Română' },
  { value: 'uk', label: '🇺🇦 Українська' },
  { value: 'be', label: '🇧🇾 Беларуская' },
  { value: 'ru', label: '🇷🇺 Русский' },
  { value: 'nl', label: '🇳🇱 Nederlands' },
  { value: 'da', label: '🇩🇰 Dansk' },
  { value: 'sv', label: '🇸🇪 Svenska' },
  { value: 'no', label: '🇳🇴 Norsk' },
  { value: 'fi', label: '🇫🇮 Suomi' },
  { value: 'is', label: '🇮🇸 Íslenska' },
  { value: 'pl', label: '🇵🇱 Polski' },
  { value: 'hu', label: '🇭🇺 Magyar' },
  { value: 'cs', label: '🇨🇿 Čeština' },
  { value: 'sk', label: '🇸🇰 Slovenčina' },
  { value: 'bg', label: '🇧🇬 Български' },
  { value: 'sr', label: '🇷🇸 Српски' },
  { value: 'sh', label: '🏳️ Srpskohrvatski' },
  { value: 'hr', label: '🇭🇷 Hrvatski' },
  { value: 'bs', label: '🇧🇦 Bosanski' },
  { value: 'mk', label: '🇲🇰 Македонски' },
  { value: 'sl', label: '🇸🇮 Slovenščina' },
  { value: 'sq', label: '🇦🇱 Shqip' },
  { value: 'el', label: '🇬🇷 Ελληνικά' },
  { value: 'tr', label: '🇹🇷 Türkçe' },
  { value: 'ka', label: '🇬🇪 ქართული' },
  { value: 'hy', label: '🇦🇲 Հայերեն' },
  { value: 'he', label: '🇮🇱 עברית' },
  { value: 'ar', label: '🇸🇦 العربية' },
  { value: 'arz', label: '🇪🇬 مصرى' },
  { value: 'fa', label: '🇮🇷 فارسی' },
  { value: 'hi', label: '🇮🇳 हिन्दी' },
  { value: 'id', label: '🇮🇩 Bahasa Indonesia' },
  { value: 'ceb', label: '🇵🇭 Cebuano' },
  { value: 'zh', label: '🇨🇳 中文' },
  { value: 'ja', label: '🇯🇵 日本語' },
];


const QUICK_DATE_RANGES = [
  { label: 'Last week', days: 7 },
  { label: 'Last month', days: 30 },
  { label: 'Last 3 months', days: 90 },
  { label: 'Last 6 months', days: 180 },
  { label: 'This year', months: 'year' },
  { label: 'Last 12 months', months: 'last 12 months' }
];

// ─────────────────────────────────────────────────────────────────────
// Utils
// ─────────────────────────────────────────────────────────────────────
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

const detectLanguageFromInput = (urlInput) => {
  if (!urlInput || typeof urlInput !== 'string') return null;
  return extractLanguageFromUrl(urlInput.trim());
};

const toWikiUrl = (title, lang) => {
  const cleaned = (title || '').trim().replace(/\s+/g, ' ');
  const encoded = encodeURIComponent(cleaned.replace(/ /g, '_'));
  const safeLang = (lang || 'fr').trim().toLowerCase();
  return `https://${safeLang}.wikipedia.org/wiki/${encoded}`;
};

const langLabel = (code) => {
  const found = LANGUAGE_OPTIONS.find(o => o.value === code);
  if (found) return found.label.replace(/^[^\s]+\s*/, '').trim(); // retire emoji, garde libellé
  return (code || '').toUpperCase() || '—';
};

// ─────────────────────────────────────────────────────────────────────
// Sous-composants
// ─────────────────────────────────────────────────────────────────────
const PagesInput = ({
  urlValue,
  pageNameValue,
  selectedLanguage,
  onUrlChange,
  onPageNameChange,
  onLanguageChange,
  additionalPages,
  onAdditionalPagesChange
}) => {
  const [detectedLanguage, setDetectedLanguage] = useState(null);

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

  useEffect(() => {
    setDetectedLanguage(detectLanguageFromInput(urlValue));
  }, [urlValue]);

  const totalPages = getTotalPagesCount();

  return (
    <div className="form-section">
      <div className="form-section-header">
        <h3>Pages to analyze</h3>
      </div>

      {/* URL principale */}
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
              {langLabel(detectedLanguage)}
            </span>
          )}
        </div>
      </div>

      <div className="input-separator">
        <span>OR</span>
      </div>

      {/* Titre + langue principale */}
      <div className="page-name-group">
        <div className="page-name-section">
          <span className="input-label">Page name:</span>
          <input
            type="text"
            value={pageNameValue || ''}
            onChange={(e) => onPageNameChange(e.target.value)}
            placeholder="  Type the title of a page"
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
        const additionalDetectedLang = detectLanguageFromInput(page.url || '');
        return (
          <div key={index} className="additional-page-group">
            {/* URL */}
            <div className="page-input-group">
              <span className="input-label">Page URL:</span>
              <div style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                <input
                  type="text"
                  value={page.url || ''}
                  onChange={(e) => {
                    const newPages = [...additionalPages];
                    newPages[index] = {
                      ...newPages[index],
                      url: e.target.value,
                      ...(e.target.value ? { pageName: '', language: '' } : {})
                    };
                    onAdditionalPagesChange(newPages);
                  }}
                  placeholder="  https://en.wikipedia.org/wiki/the_page_title"
                  className="form-input page-url-input"
                />
                {additionalDetectedLang && (
                  <span className="detected-language-badge" style={{ marginLeft: 8 }}>
                    {langLabel(additionalDetectedLang)}
                  </span>
                )}
              </div>
            </div>

            <div className="input-separator">
              <span>OR</span>
            </div>

            {/* Titre + langue */}
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
                    ...(e.target.value ? { url: '' } : {})
                  };
                  onAdditionalPagesChange(newPages);
                }}
                placeholder="  Type the title of a page"
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

            {/* Supprimer */}
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

      {/* Ajouter une page */}
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
          <span>
            Enter Wikipedia URLs for automatic language detection, or page titles with manual language selection. Maximum 5 pages per analysis.
          </span>
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

      <div className="input-separator">
        <span>OR</span>
      </div>

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

const ErrorAlert = ({ message }) => (
  <div className="alert alert-error">
    <span>⚠️ {message}</span>
  </div>
);

const SubmitButton = ({ onClick, disabled, loading }) => (
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

// ─────────────────────────────────────────────────────────────────────
// Composant principal
// ─────────────────────────────────────────────────────────────────────
const ConfigurationPage = ({
  onAnalysisStart,
  onAnalysisComplete,
  onAnalysisError,
  onProgressUpdate,
  isAnalyzing = false
}) => {
  const [urlInput, setUrlInput] = useState('');
  const [pageNameInput, setPageNameInput] = useState('');
  const [manualLanguage, setManualLanguage] = useState('');
  const [additionalPages, setAdditionalPages] = useState([]);
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [error, setError] = useState(null);
  const [taskLanguages, setTaskLanguages] = useState(null); // languages dict renvoyé par /api/analyze

  const detectedLanguage = detectLanguageFromInput(urlInput);

  // Construit la liste des pages visibles pour compteur
  const getTotalPages = () => {
    const pages = [];
    if (urlInput && urlInput.trim()) pages.push(urlInput.trim());
    if (pageNameInput && pageNameInput.trim() && manualLanguage) pages.push(pageNameInput.trim());
    if (additionalPages) {
      additionalPages.forEach(p => {
        if (p.url && p.url.trim()) pages.push(p.url.trim());
        else if (p.pageName && p.pageName.trim() && p.language) pages.push(p.pageName.trim());
      });
    }
    return pages;
  };

  // Construit la liste **pour l'API** : convertit (titre+langue) → URL wiki
  const buildPagesForApi = () => {
    const dest = [];

    if (urlInput && urlInput.trim()) {
      dest.push(urlInput.trim());
    }
    if (pageNameInput && pageNameInput.trim() && manualLanguage) {
      dest.push(toWikiUrl(pageNameInput.trim(), manualLanguage));
    }
    if (additionalPages) {
      additionalPages.forEach(p => {
        if (p.url && p.url.trim()) {
          dest.push(p.url.trim());
        } else if (p.pageName && p.pageName.trim() && p.language) {
          dest.push(toWikiUrl(p.pageName.trim(), p.language));
        }
      });
    }
    return dest;
  };

  const allPages = getTotalPages();
  const totalPages = allPages.length;

  const handleSubmit = async () => {
    if (totalPages === 0) {
      setError('Please enter at least one Wikipedia page');
      return;
    }
    if (totalPages > 5) {
      setError('Maximum 5 pages per analysis');
      return;
    }

    const hasUrlWithDetection = urlInput && urlInput.trim() && detectedLanguage;
    const hasPageWithLanguage = pageNameInput && pageNameInput.trim() && manualLanguage;

    if (!hasUrlWithDetection && !hasPageWithLanguage) {
      setError('Please provide either a Wikipedia URL (for auto-detection) or a page name with language selection');
      return;
    }

    setError(null);
    setTaskLanguages(null);

    // Toujours envoyer des URLs pour préserver la langue par page
    const pagesForApi = buildPagesForApi();

    const analysisDataLocal = {
      taskId: 'pending',
      pages: pagesForApi,
      startDate,
      endDate,
      estimatedTime: Math.ceil(totalPages * 30)
    };
    onAnalysisStart(analysisDataLocal);

    const progressInterval = setInterval(() => {
      onProgressUpdate(prev => Math.min(prev + Math.random() * 10, 90));
    }, 500);

    try {
      const requestData = {
        pages: pagesForApi,
        start_date: startDate,
        end_date: endDate
        // NOTE: on NE PASSE PAS default_language car chaque titre a été converti en URL (avec sa langue)
      };

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

      // languages = dict {"fr": n, "en": m}
      if (data?.languages) {
        setTaskLanguages(data.languages);
      }

      const updatedLocal = {
        ...analysisDataLocal,
        taskId: data.task_id,
        estimatedTime: data.estimated_time || analysisDataLocal.estimatedTime
      };
      onAnalysisStart(updatedLocal);

      const pollResults = async () => {
        try {
          const r = await fetch(`${API_BASE}/api/tasks/${data.task_id}`);
          if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
          const taskData = await r.json();

          if (taskData?.languages && !taskLanguages) {
            setTaskLanguages(taskData.languages);
          }

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

        {error && <ErrorAlert message={error} />}

        <SubmitButton
          onClick={handleSubmit}
          disabled={isSubmitDisabled}
          loading={isAnalyzing}
        />
      </div>
    </div>
  );
};

export default ConfigurationPage;