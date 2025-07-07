// File: src/components/ResultsPage.jsx
import React, { useState, useEffect } from 'react';
import Layout from './Layout';
import { apiService } from '../services/api.js';
import PageSelector from './results/PageSelector';
import KiviatChart from './results/KiviatChart';
import PageviewsChart from './results/PageviewsChart';
import EditChart from './results/EditChart'; // ✨ NOUVEAU : Import du composant EditChart
import MetricsDisplay from './results/MetricsDisplay';
import './ResultsPage.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8200';

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

const ResultsView = ({ results, analysisConfig, onBackToConfig }) => {
  const [selectedPageIndices, setSelectedPageIndices] = useState([0]);
  const [comparisonMode, setComparisonMode] = useState(false);
  const [chartMode, setChartMode] = useState('pageviews'); // ✨ NOUVEAU : État pour le switch entre pageviews et éditions
  
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

  const handlePageSelection = (indices, isComparison) => {
    setSelectedPageIndices(indices);
    setComparisonMode(isComparison);
  };

  const selectedPages = selectedPageIndices.map(index => pages[index]);

  return (
    <div className="results-container-new">
      {/* Sélecteur de pages */}
      <div className="content-card">
        <div className="card-body">
          <PageSelector
            pages={pages}
            selectedIndices={selectedPageIndices}
            comparisonMode={comparisonMode}
            onSelectionChange={handlePageSelection}
          />
        </div>
      </div>

      {/* Section principale avec Kiviat et Pageviews/Éditions */}
      <div className="content-card">
        <div className="card-body">
          <div className="main-charts-container">
  <div className="charts-grid">
    {/* Kiviat Chart - Gauche */}
    <div className="chart-section kiviat-section">
      <KiviatChart
        pages={pages}
        selectedPageIndices={selectedPageIndices}
        comparisonMode={comparisonMode}
      />
    </div>

    {/* Section Pageviews/Éditions - Droite */}
    <div className="chart-section pageviews-section">
      {/* Switch en position absolue */}
      <div className="chart-mode-switch">
        <div className="switch-container">
          <button
            className={`switch-btn ${chartMode === 'pageviews' ? 'active' : ''}`}
            onClick={() => setChartMode('pageviews')}
            title="Afficher les pages vues"
          >
            
            <span className="switch-label">Pages vues</span>
          </button>
          <button
            className={`switch-btn ${chartMode === 'edits' ? 'active' : ''}`}
            onClick={() => setChartMode('edits')}
            title="Afficher les éditions"
          >
            
            <span className="switch-label">Éditions</span>
          </button>
        </div>
      </div>

      {/* Container pour le contenu */}
      <div className="chart-content-container">
        {chartMode === 'pageviews' ? (
          <PageviewsChart
            pages={selectedPages}
            analysisConfig={analysisConfig}
          />
        ) : (
          <EditChart
            pages={selectedPages}
            analysisConfig={analysisConfig}
          />
        )}
      </div>
    </div>
  </div>
</div>
        </div>
      </div>

      {/* Métriques détaillées */}
      <div className="content-card">
        <div className="card-body">
          <MetricsDisplay
            pages={selectedPages}
            comparisonMode={comparisonMode}
          />
        </div>
      </div>

      {/* Actions */}
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
};

export default ResultsPage;