// File: src/App.js
import React, { useState, useRef } from 'react';
import ConfigurationPage from './components/ConfigurationPage';
import ResultsSection from './components/ResultsPage';
import Layout from './components/Layout';
// IMPORTANT : MainPage.css en PREMIER pour que ResultsPage.css override
import './styles/MainPage.css';


import './components/ResultsPage.css';

const WikimetronApp = () => {
  const [analysisState, setAnalysisState] = useState({
    status: 'idle', // 'idle', 'loading', 'completed', 'error'
    data: null,
    results: null,
    error: null,
    progress: 0
  });

  const resultsRef = useRef(null);

  // Fonction pour démarrer l'analyse - adaptée de votre logique existante
  const handleAnalysisStart = (analysisData) => {
    setAnalysisState({
      status: 'loading',
      data: analysisData,
      results: null,
      error: null,
      progress: 0
    });

    // Scroll vers la section résultats après un court délai
    setTimeout(() => {
      resultsRef.current?.scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
      });
    }, 100);
  };

  // Fonction pour mettre à jour les résultats
  const handleAnalysisComplete = (results) => {
    setAnalysisState(prev => ({
      ...prev,
      status: 'completed',
      results,
      progress: 100
    }));
  };

  // Fonction pour gérer les erreurs
  const handleAnalysisError = (error) => {
    setAnalysisState(prev => ({
      ...prev,
      status: 'error',
      error,
      progress: 0
    }));
  };

  // Fonction pour mettre à jour le progress
  const handleProgressUpdate = (progress) => {
    setAnalysisState(prev => ({
      ...prev,
      progress
    }));
  };

  // Fonction pour reset l'analyse (équivalent de votre goToConfig)
  const handleReset = () => {
    setAnalysisState({
      status: 'idle',
      data: null,
      results: null,
      error: null,
      progress: 0
    });
  };

  // Fonction pour refaire une analyse (scroll vers le haut)
  const handleNewAnalysis = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    // Optionnel : vous pouvez aussi reset l'état ici si souhaité
    // handleReset();
  };

  return (
    <Layout 
      pageTitle="SensiMeter Wikipedia" 
      subtitle="Wikipedia Content Intelligence Platform"
    >
      <div className="main-page-container">
        {/* Section Configuration - utilise votre ConfigurationPage existant mais modifié */}
        <div className="configuration-section">
          <ConfigurationPage
            onAnalysisStart={handleAnalysisStart}
            onAnalysisComplete={handleAnalysisComplete}
            onAnalysisError={handleAnalysisError}
            onProgressUpdate={handleProgressUpdate}
            isAnalyzing={analysisState.status === 'loading'}
            // On retire onNavigateToResults car on n'en a plus besoin
          />
        </div>

        {/* Section Résultats */}
        <div 
          ref={resultsRef}
          className={`results-section ${analysisState.status}`}
        >
          <ResultsSection 
            analysisState={analysisState}
            onNewAnalysis={handleNewAnalysis}
            onReset={handleReset}
          />
        </div>
      </div>
    </Layout>
  );
};

export default WikimetronApp;