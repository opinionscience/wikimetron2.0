import React, { useState } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8200';

const SimpleWikimetronInterface = () => {
  const [page, setPage] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [taskId, setTaskId] = useState(null);

  // Configuration prédéfinie
  const defaultConfig = {
    language: 'fr',
    start_date: '2024-01-01',
    end_date: '2024-12-31'
  };

  const analyzeePage = async () => {
    if (!page.trim()) {
      setError('Veuillez entrer un nom de page');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      // 1. Lancer l'analyse
      const analyzeResponse = await axios.post(`${API_BASE}/api/analyze`, {
        pages: [page.trim()],
        start_date: defaultConfig.start_date,
        end_date: defaultConfig.end_date,
        language: defaultConfig.language
      });

      const newTaskId = analyzeResponse.data.task_id;
      setTaskId(newTaskId);

      // 2. Polling pour récupérer les résultats
      const pollResults = async () => {
        try {
          const statusResponse = await axios.get(`${API_BASE}/api/tasks/${newTaskId}`);
          const taskData = statusResponse.data;

          if (taskData.status === 'completed' && taskData.results) {
            setResults(taskData.results);
            setLoading(false);
          } else if (taskData.status === 'error') {
            setError('Erreur lors de l\'analyse');
            setLoading(false);
          } else {
            // Continuer le polling
            setTimeout(pollResults, 1000);
          }
        } catch (err) {
          console.error('Erreur polling:', err);
          setTimeout(pollResults, 2000); // Retry plus lentement
        }
      };

      // Attendre un peu puis commencer le polling
      setTimeout(pollResults, 2000);

    } catch (err) {
      setError(`Erreur API: ${err.response?.data?.detail || err.message}`);
      setLoading(false);
    }
  };

  const resetAnalysis = () => {
    setResults(null);
    setError(null);
    setTaskId(null);
    setPage('');
  };

  const renderMetricValue = (value) => {
    if (typeof value === 'number') {
      return value.toFixed(3);
    }
    return value || '0.000';
  };

  const renderResults = () => {
    if (!results || !results.pages || results.pages.length === 0) {
      return null;
    }

    const pageResult = results.pages[0];
    const scores = pageResult.scores || {};
    const metrics = pageResult.metrics || {};

    // Organiser les métriques par catégorie
    const heatMetrics = ['pageview_spike', 'edit_spike', 'revert_risk', 'protection_level', 'talk_intensity'];
    const qualityMetrics = ['citation_gap', 'blacklist_share', 'event_imbalance', 'recency_score', 'adq_score', 'domain_dominance'];
    const riskMetrics = ['anon_edit', 'mean_contributor_balance', 'monopolization_score', 'avg_activity_score'];

    return (
      <div className="mt-8 space-y-6">
        {/* Scores principaux */}
        <div className="bg-white border rounded-lg p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">
            Scores pour: {pageResult.title}
          </h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-red-600">
                {renderMetricValue(scores.heat)}
              </div>
              <div className="text-sm text-red-700 font-medium">HEAT</div>
            </div>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-600">
                {renderMetricValue(scores.quality)}
              </div>
              <div className="text-sm text-blue-700 font-medium">QUALITY</div>
            </div>
            
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-orange-600">
                {renderMetricValue(scores.risk)}
              </div>
              <div className="text-sm text-orange-700 font-medium">RISK</div>
            </div>
            
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-purple-600">
                {renderMetricValue(scores.sensitivity)}
              </div>
              <div className="text-sm text-purple-700 font-medium">SENSITIVITY</div>
            </div>
          </div>
        </div>

        {/* Détail des métriques par catégorie */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* HEAT Metrics */}
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <h4 className="font-bold text-red-800 mb-3">Métriques HEAT</h4>
            <div className="space-y-2">
              {heatMetrics.map(metric => (
                metrics[metric] !== undefined && (
                  <div key={metric} className="flex justify-between text-sm">
                    <span className="text-red-700">{metric}:</span>
                    <span className="font-mono text-red-900">
                      {renderMetricValue(metrics[metric])}
                    </span>
                  </div>
                )
              ))}
            </div>
          </div>

          {/* QUALITY Metrics */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-bold text-blue-800 mb-3">Métriques QUALITY</h4>
            <div className="space-y-2">
              {qualityMetrics.map(metric => (
                metrics[metric] !== undefined && (
                  <div key={metric} className="flex justify-between text-sm">
                    <span className="text-blue-700">{metric}:</span>
                    <span className="font-mono text-blue-900">
                      {renderMetricValue(metrics[metric])}
                    </span>
                  </div>
                )
              ))}
            </div>
          </div>

          {/* RISK Metrics */}
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <h4 className="font-bold text-orange-800 mb-3">Métriques RISK</h4>
            <div className="space-y-2">
              {riskMetrics.map(metric => (
                metrics[metric] !== undefined && (
                  <div key={metric} className="flex justify-between text-sm">
                    <span className="text-orange-700">{metric}:</span>
                    <span className="font-mono text-orange-900">
                      {renderMetricValue(metrics[metric])}
                    </span>
                  </div>
                )
              ))}
            </div>
          </div>
        </div>

        {/* Informations de l'analyse */}
        <div className="bg-gray-50 border rounded-lg p-4">
          <h4 className="font-bold text-gray-800 mb-2">Détails de l'analyse</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
            <div>
              <span className="font-medium">Langue:</span> {defaultConfig.language}
            </div>
            <div>
              <span className="font-medium">Période:</span> {defaultConfig.start_date} → {defaultConfig.end_date}
            </div>
            <div>
              <span className="font-medium">Statut:</span> 
              <span className="text-green-600 ml-1">{pageResult.status}</span>
            </div>
            <div>
              <span className="font-medium">Temps:</span> 
              {results.summary?.processing_time ? `${results.summary.processing_time}s` : 'N/A'}
            </div>
          </div>
        </div>

        {/* Bouton reset */}
        <div className="text-center">
          <button
            onClick={resetAnalysis}
            className="bg-gray-600 text-white px-6 py-2 rounded hover:bg-gray-700"
          >
            Nouvelle analyse
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-100 py-6">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🛡️ Wikimetron
          </h1>
          <p className="text-gray-600">
            Analyse de sensibilité Wikipedia
          </p>
        </div>

        {/* Formulaire d'analyse */}
        {!results && (
          <div className="bg-white border rounded-lg p-6 max-w-2xl mx-auto">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Analyser une page Wikipedia
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nom de la page Wikipedia
                </label>
                <input
                  type="text"
                  value={page}
                  onChange={(e) => setPage(e.target.value)}
                  placeholder="Ex: France, Paris, Lyon..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  onKeyPress={(e) => e.key === 'Enter' && analyzeePage()}
                />
              </div>

              <div className="bg-gray-50 p-3 rounded text-sm text-gray-600">
                <strong>Configuration prédéfinie:</strong><br/>
                📅 Période: {defaultConfig.start_date} → {defaultConfig.end_date}<br/>
                🌍 Langue: {defaultConfig.language} (Français)
              </div>

              <button
                onClick={analyzeePage}
                disabled={loading || !page.trim()}
                className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
              >
                {loading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Analyse en cours...
                  </span>
                ) : 'Analyser la page'}
              </button>
            </div>

            {/* Statut du polling */}
            {loading && taskId && (
              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-700">
                📊 Tâche créée: {taskId}<br/>
                ⏳ Collecte des métriques en cours... Cela peut prendre quelques secondes.
              </div>
            )}

            {/* Erreurs */}
            {error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                ❌ {error}
              </div>
            )}
          </div>
        )}

        {/* Résultats */}
        {renderResults()}
      </div>
    </div>
  );
};

export default SimpleWikimetronInterface;