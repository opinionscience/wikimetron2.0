// File: src/components/results/KiviatChart.jsx
import React from 'react';
import { 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  Radar, 
  ResponsiveContainer,
  Legend
} from 'recharts';

const renderMetricValue = (value) => {
  if (typeof value === 'number') {
    return value.toFixed(3);
  }
  return value || '0.000';
};

const KiviatChart = ({ pages, selectedPageIndices = [0], comparisonMode = false }) => {
  const colors = [
    { stroke: '#8b5cf6', fill: '#8b5cf6', name: 'purple' },
    { stroke: '#ef4444', fill: '#ef4444', name: 'red' },
    { stroke: '#3b82f6', fill: '#3b82f6', name: 'blue' },
    { stroke: '#10b981', fill: '#10b981', name: 'green' },
    { stroke: '#f59e0b', fill: '#f59e0b', name: 'yellow' },
    { stroke: '#ec4899', fill: '#ec4899', name: 'pink' }
  ];

  const metrics = ['Heat', 'Quality', 'Risk'];
  
  // Préparer les données pour le radar chart
  const data = metrics.map(metric => {
    const dataPoint = { metric };
    
    selectedPageIndices.forEach((pageIndex, index) => {
      const page = pages[pageIndex];
      const scores = page?.scores || {};
      const metricKey = metric.toLowerCase();
      dataPoint[`page${pageIndex}`] = scores[metricKey] || 0;
      dataPoint[`page${pageIndex}Name`] = page?.title || `Page ${pageIndex + 1}`;
    });
    
    return dataPoint;
  });

  // Calculer les statistiques pour chaque métrique
  const getMetricStats = (metricKey) => {
    const values = selectedPageIndices.map(idx => pages[idx]?.scores?.[metricKey] || 0);
    return {
      min: Math.min(...values),
      max: Math.max(...values),
      avg: values.reduce((sum, val) => sum + val, 0) / values.length,
      range: Math.max(...values) - Math.min(...values)
    };
  };

  return (
    <div className="kiviat-chart-container">
      {/* Header */}
      <div className="kiviat-header">
        <h4>
          🎯 {comparisonMode ? 'Comparaison des profils de sensibilité' : 'Profil de sensibilité'}
        </h4>
        {comparisonMode && selectedPageIndices.length > 1 && (
          <p className="kiviat-subtitle">
            Comparaison de {selectedPageIndices.length} pages
          </p>
        )}
      </div>

      {/* Graphique radar */}
      <div className="kiviat-chart-wrapper">
        <ResponsiveContainer width="100%" height={500}>
          <RadarChart data={data} margin={{ top: 20, right: 80, bottom: 20, left: 80 }}>
            <PolarGrid stroke="#e5e7eb" radialLines={true} />
            <PolarAngleAxis 
              dataKey="metric" 
              tick={{ fill: '#374151', fontSize: 14, fontWeight: 'bold' }}
            />
            <PolarRadiusAxis 
              angle={90} 
              domain={[0, 1]} 
              tick={{ fill: '#6b7280', fontSize: 12 }}
              tickCount={6}
              axisLine={false}
            />
            
            {selectedPageIndices.map((pageIndex, index) => {
              const color = colors[index % colors.length];
              return (
                <Radar
                  key={pageIndex}
                  name={pages[pageIndex]?.title || `Page ${pageIndex + 1}`}
                  dataKey={`page${pageIndex}`}
                  stroke={color.stroke}
                  fill={color.fill}
                  fillOpacity={comparisonMode ? 0.1 : 0.25}
                  strokeWidth={comparisonMode ? 2 : 3}
                  dot={{ 
                    fill: color.stroke, 
                    strokeWidth: 2, 
                    r: comparisonMode ? 3 : 5,
                    fillOpacity: 1
                  }}
                />
              );
            })}
            
            {comparisonMode && <Legend />}
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Légende personnalisée et scores */}
      <div className="kiviat-details">
        {/* Légende avec scores de sensibilité */}
        <div className="kiviat-legend">
          <h5>📊 Scores de sensibilité</h5>
          <div className="legend-items">
            {selectedPageIndices.map((pageIndex, index) => {
              const page = pages[pageIndex];
              const scores = page?.scores || {};
              const color = colors[index % colors.length];
              
              return (
                <div key={pageIndex} className="legend-item">
                  <div className="legend-visual">
                    <div 
                      className="legend-color"
                      style={{ 
                        backgroundColor: color.fill, 
                        borderColor: color.stroke 
                      }}
                    />
                    <span className="legend-number">#{pageIndex + 1}</span>
                  </div>
                  <div className="legend-content">
                    <div className="legend-title" title={page?.title}>
                      {page?.title || `Page ${pageIndex + 1}`}
                    </div>
                    <div className="legend-score" style={{ color: color.stroke }}>
                      {renderMetricValue(scores.sensitivity)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Statistiques de comparaison */}
        {comparisonMode && selectedPageIndices.length > 1 && (
          <div className="kiviat-stats">
            <h5>📈 Statistiques de comparaison</h5>
            <div className="stats-grid">
              {metrics.map(metric => {
                const metricKey = metric.toLowerCase();
                const stats = getMetricStats(metricKey);
                
                return (
                  <div key={metric} className={`stat-item ${metricKey}`}>
                    <div className="stat-header">
                      <span className="stat-name">{metric}</span>
                    </div>
                    <div className="stat-values">
                      <div className="stat-row">
                        <span>Écart:</span>
                        <span>{renderMetricValue(stats.range)}</span>
                      </div>
                      <div className="stat-row">
                        <span>Moyenne:</span>
                        <span>{renderMetricValue(stats.avg)}</span>
                      </div>
                      <div className="stat-row">
                        <span>Min/Max:</span>
                        <span>{renderMetricValue(stats.min)} / {renderMetricValue(stats.max)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      
    </div>
  );
};

export default KiviatChart;