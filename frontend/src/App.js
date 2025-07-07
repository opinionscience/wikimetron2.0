import React, { useState } from 'react';
import ConfigurationPage from './components/ConfigurationPage';
import ResultsPage from './components/ResultsPage';

const WikimetronApp = () => {
  const [currentPage, setCurrentPage] = useState('config');
  const [analysisData, setAnalysisData] = useState(null);

  const handleAnalysisStart = (data) => setAnalysisData(data);
  const goToResults = () => setCurrentPage('results');
  const goToConfig = () => {
    setCurrentPage('config');
    setAnalysisData(null);
  };

  return currentPage === 'config' ? (
    <ConfigurationPage
      onAnalysisStart={handleAnalysisStart}
      onNavigateToResults={goToResults}
    />
  ) : (
    <ResultsPage
      analysisData={analysisData}
      onBackToConfig={goToConfig}
    />
  );
};

export default WikimetronApp;
