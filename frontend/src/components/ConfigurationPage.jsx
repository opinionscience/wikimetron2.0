import React, { useState } from 'react';
import Layout from './Layout';
import { LoadingSpinner } from './LoadingSpinner';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8200';
const LANGUAGE_OPTIONS = [
  { value: 'fr', label: '🇫🇷 Français' },
  { value: 'en', label: '🇺🇸 English' },
];

const QUICK_DATE_RANGES = [
  { label: 'Last 30 days', months: 1 }, // Approximativement 7 jours
  { label: 'Last 3 months', months: 3 },
  { label: 'Last 6 months', months: 6 },
  { label: 'This year', months: 'year' },
  
];

// Fonction pour calculer les dates
const calculateDateRange = (option) => {
  const today = new Date();
  const endDate = today.toISOString().split('T')[0];
  let startDate;

  if (option === 'year') {
    startDate = new Date(today.getFullYear(), 0, 1).toISOString().split('T')[0];
  } else if (option === 'lastYear') {
    startDate = new Date(today.getFullYear() - 1, 0, 1).toISOString().split('T')[0];
    const lastYearEnd = new Date(today.getFullYear() - 1, 11, 31).toISOString().split('T')[0];
    return { startDate, endDate: lastYearEnd };
  } else {
    const start = new Date(today);
    start.setMonth(start.getMonth() - option);
    startDate = start.toISOString().split('T')[0];
  }

  return { startDate, endDate };
};

// Fonction utilitaire pour calculer le nombre de pages
const calculatePagesCount = (pagesText) => {
  if (!pagesText || typeof pagesText !== 'string') return 0;
  return pagesText.split('\n').map(p => p.trim()).filter(p => p.length > 0).length;
};

// Composants améliorés
const PagesInput = ({ value, onChange }) => {
  const pagesCount = calculatePagesCount(value);
  
  return (
    <div className="form-section">
      <div className="form-section-header">
        <h3>📄 Wikipedia Pages</h3>
        <p>Enter the pages you want to analyze</p>
      </div>
      <textarea
        value={value}
        onChange={onChange}
        placeholder="Enter one page per line&#10;Example:&#10;Climate change&#10;Global warming&#10;Renewable energy"
        className="form-textarea pages-input"
      />
      <div className="form-help-row">
        <span className="form-help">Maximum 50 pages per analysis</span>
        <span className="page-counter">{pagesCount} page(s)</span>
      </div>
    </div>
  );
};

const LanguageSelector = ({ value, onChange }) => (
  <div className="form-section">
    <div className="form-section-header">
      <h3>🌍 Language</h3>
      <p>Choose Wikipedia language</p>
    </div>
    <div className="language-grid">
      {LANGUAGE_OPTIONS.map(option => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={`language-option ${value === option.value ? 'active' : ''}`}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  </div>
);

const DateRangeSelector = ({ startDate, endDate, onStartChange, onEndChange }) => {
  const [selectedQuickRange, setSelectedQuickRange] = useState('');

  const handleQuickRange = (range) => {
    const dates = calculateDateRange(range.months);
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
        <h3>📅 Analysis Period</h3>
        <p>Select the time range for your analysis</p>
      </div>
      
      <div className="quick-dates">
        <h4>Quick selection:</h4>
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

      <div className="custom-dates">
        <h4>Or choose custom dates:</h4>
        <div className="date-inputs">
          <div className="date-input-group">
            <label>From</label>
            <input 
              type="date" 
              value={startDate} 
              onChange={(e) => {
                onStartChange(e.target.value);
                handleCustomDate();
              }}
              className="form-input date-input"
            />
          </div>
          <div className="date-separator">→</div>
          <div className="date-input-group">
            <label>To</label>
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
    </div>
  );
};

const AnalysisSummary = ({ pagesCount, startDate, endDate, language }) => {
  if (pagesCount === 0) return null;

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="analysis-preview">
      <h3>🚀 Ready to analyze</h3>
      <div className="preview-stats">
        <div className="stat">
          <span className="stat-number">{pagesCount}</span>
          <span className="stat-label">page{pagesCount > 1 ? 's' : ''}</span>
        </div>
        <div className="stat">
          <span className="stat-number">{language.toUpperCase()}</span>
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

const SubmitButton = ({ onClick, disabled, loading, pagesCount }) => (
  <div className="submit-section">
    <button 
      onClick={onClick} 
      disabled={disabled} 
      className="btn btn-primary btn-large submit-btn"
      type="button"
    >
      {loading ? (
        <>
          <LoadingSpinner />
          Analyzing...
        </>
      ) : (
        <>
          Start Analysis
        </>
      )}
    </button>
    {pagesCount > 0 && !loading && (
      <p className="submit-help">
        This will analyze {pagesCount} Wikipedia page{pagesCount > 1 ? 's' : ''} and may take a few minutes.
      </p>
    )}
  </div>
);

const ConfigurationPage = ({ onAnalysisStart, onNavigateToResults }) => {
  const [pages, setPages] = useState('');
  const [language, setLanguage] = useState('en');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Utiliser la fonction utilitaire pour calculer le nombre de pages
  const pagesCount = calculatePagesCount(pages);

  const handleSubmit = async () => {
    console.log('handleSubmit called', { pagesCount, loading }); // Debug
    
    if (!pages.trim()) {
      setError('Please enter at least one Wikipedia page');
      return;
    }
    
    const pageList = pages.split('\n').map(p => p.trim()).filter(p => p.length > 0);
    
    if (pageList.length === 0) {
      setError('Please enter a valid page');
      return;
    }
    
    if (pageList.length > 50) {
      setError('Maximum 50 pages per analysis');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          pages: pageList, 
          start_date: startDate, 
          end_date: endDate, 
          language 
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      onAnalysisStart({
        taskId: data.task_id,
        pages: pageList,
        language,
        startDate,
        endDate,
        estimatedTime: data.estimated_time
      });
      
      onNavigateToResults();
    } catch (err) {
      setError(`Error starting analysis: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const isSubmitDisabled = pagesCount === 0 || loading;

  console.log('Render state:', { pagesCount, loading, isSubmitDisabled }); // Debug

  return (
    <Layout pageTitle="SensiMeter Wikipedia" subtitle="Wikipedia Content Intelligence Platform">
      <div className="config-container">
        <div className="config-intro">
          
        </div>

        <div className="config-form">
          <PagesInput 
            value={pages} 
            onChange={(e) => setPages(e.target.value)} 
          />
          
          <LanguageSelector 
            value={language} 
            onChange={setLanguage}
          />
          
          <DateRangeSelector 
            startDate={startDate}
            endDate={endDate}
            onStartChange={setStartDate}
            onEndChange={setEndDate}
          />
          
          <AnalysisSummary 
            pagesCount={pagesCount} 
            startDate={startDate} 
            endDate={endDate} 
            language={language}
          />
          
          {error && <ErrorAlert message={error} />}
          
          <SubmitButton 
            onClick={handleSubmit} 
            disabled={isSubmitDisabled} 
            loading={loading}
            pagesCount={pagesCount}
          />
        </div>
      </div>
    </Layout>
  );
};

export default ConfigurationPage;