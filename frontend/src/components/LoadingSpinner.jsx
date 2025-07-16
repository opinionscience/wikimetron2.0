import React from 'react';

export const LoadingSpinner = ({ size = 'medium' }) => {
  const sizeClasses = {
    small: 'w-6 h-6',
    medium: 'w-8 h-8',
    large: 'w-12 h-12',
    xlarge: 'w-16 h-16'
  };

  return (
    <div className={`loading-spinner ${sizeClasses[size]}`}>
      <svg className="animate-spin" fill="none" viewBox="0 0 24 24">
        <circle 
          className="opacity-25" 
          cx="12" 
          cy="12" 
          r="10" 
          stroke="currentColor" 
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    </div>
  );
};

// Composant de chargement avec design moderne et blur
export const ModernLoadingOverlay = ({ 
  title = "Ongoing analysis...", 
  subtitle = "Please wait", 
  taskId = null,
  pagesCount = 0,
  showProgress = false,
  progress = 0 
}) => {
  return (
    <div className="modern-loading-overlay">
      {/* Arrière-plan flou */}
      <div className="loading-backdrop" />
      
      {/* Contenu de chargement */}
      <div className="loading-content">
        <div className="loading-card">
          {/* Spinner principal */}
          <div className="loading-spinner-container">
            <div className="loading-spinner-outer">
              <div className="loading-spinner-inner">
                <LoadingSpinner size="xlarge" />
              </div>
              <div className="loading-pulse-ring" />
            </div>
          </div>
          
          {/* Texte et informations */}
          <div className="loading-text">
            <h2 className="loading-title">{title}</h2>
            <p className="loading-subtitle">{subtitle}</p>
            
            {pagesCount > 0 && (
              <div className="loading-info">
                <span className="loading-pages">
                   {pagesCount} page{pagesCount > 1 ? 's' : ''} to analyze
                </span>
              </div>
            )}
            
            {taskId && (
              <div className="loading-task-id">
                <span>ID: {taskId}</span>
              </div>
            )}
          </div>
          
          {/* Barre de progression optionnelle */}
          {showProgress && (
            <div className="loading-progress">
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="progress-text">{progress}%</span>
            </div>
          )}
          
          {/* Points de chargement animés */}
          <div className="loading-dots">
            <span className="dot dot-1" />
            <span className="dot dot-2" />
            <span className="dot dot-3" />
          </div>
        </div>
      </div>
    </div>
  );
};