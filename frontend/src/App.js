// File: src/App.js
import React, { useState, useRef } from 'react';
import ConfigurationPage from './components/ConfigurationPage';
import ResultsSection from './components/ResultsPage';
import Layout from './components/Layout';
import './components/MainPage.css';

const WikimetronApp = () => {
  const [analysisState, setAnalysisState] = useState({
    status: 'idle', // 'idle', 'loading', 'completed', 'error'
    data: null,
    results: null,
    error: null,
    progress: 0,
    originalPages: null, // AJOUT : conserver les pages originales
    analysisConfig: null // AJOUT : conserver la config d'analyse
  });

  const resultsRef = useRef(null);

  // Fonction pour démarrer l'analyse - modifiée pour conserver les pages originales
  const handleAnalysisStart = (analysisData) => {
    setAnalysisState({
      status: 'loading',
      data: analysisData,
      results: null,
      error: null,
      progress: 0,
      originalPages: analysisData.pages, // AJOUT : conserver les URLs originales
      analysisConfig: { // AJOUT : conserver la config pour les charts
        startDate: analysisData.startDate,
        endDate: analysisData.endDate
      }
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

  // Fonction pour reset l'analyse
  const handleReset = () => {
    setAnalysisState({
      status: 'idle',
      data: null,
      results: null,
      error: null,
      progress: 0,
      originalPages: null, // AJOUT
      analysisConfig: null // AJOUT
    });
  };

  // Fonction pour refaire une analyse (scroll vers le haut)
  const handleNewAnalysis = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <Layout 
      pageTitle="SensiMeter Wikipedia" 
      subtitle="Wikipedia Content Intelligence Platform"
    >
      <div className="main-page-container">
        {/* Section Configuration */}
        <div className="configuration-section">
          <ConfigurationPage
            onAnalysisStart={handleAnalysisStart}
            onAnalysisComplete={handleAnalysisComplete}
            onAnalysisError={handleAnalysisError}
            onProgressUpdate={handleProgressUpdate}
            isAnalyzing={analysisState.status === 'loading'}
          />
        </div>

        {/* Section Résultats */}
        <div 
          ref={resultsRef}
          className={`results-section ${analysisState.status}`}
        >
          <ResultsSection 
            analysisState={analysisState}
            originalPages={analysisState.originalPages} // AJOUT : passer les pages originales
            analysisConfig={analysisState.analysisConfig} // AJOUT : passer la config
            onNewAnalysis={handleNewAnalysis}
            onReset={handleReset}
          />
        </div>
      </div>
    </Layout>
  );
};

export default WikimetronApp;