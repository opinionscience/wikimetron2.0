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
    return value.toFixed(1);
  }
  return value || '0.0';
};

const KiviatChart = ({ pages, selectedPageIndices = [0], comparisonMode = false }) => {
  const colors = [
    { stroke: '#3b82f6', fill: '#3b82f6', name: 'purple' },
    { stroke: '#ef4444', fill: '#ef4444', name: 'red' },
    { stroke: '#10b981', fill: '#10b981', name: 'green' },
    { stroke: '#f59e0b', fill: '#f59e0b', name: 'green' },
    { stroke: '#8b5cf6', fill: '#8b5cf6', name: 'yellow' },
    { stroke: '#06b6d4', fill: '#06b6d4', name: 'pink' }
  ];

  const metrics = ['Heat', 'Quality', 'Risk']; // Utilisé pour accéder aux données
  const metricDisplayNames = ['Heat risk', 'Quality risk', 'Behaviour risk']; // Noms à afficher

  // Préparer les données pour le radar chart
  const data = metrics.map((metric, index) => {
    const dataPoint = { metric: metricDisplayNames[index] };

    selectedPageIndices.forEach((pageIndex) => {
      const page = pages[pageIndex];
      const scores = page?.scores || {};
      const metricKey = metric.toLowerCase();
      dataPoint[`page${pageIndex}`] = scores[metricKey] || 0;
      dataPoint[`page${pageIndex}Name`] = page?.title || `Page ${pageIndex + 1}`;
    });

    return dataPoint;
  });

  // Calculer les statistiques pour chaque métrique (si nécessaire)
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
      {/* Graphique radar */}
      <div className="kiviat-chart-wrapper">
        <ResponsiveContainer width="100%" height={600}>
          <RadarChart data={data} margin={{ top: 20, right: 80, bottom: 20, left: 80 }}>
            <PolarGrid stroke="#e5e7eb" radialLines={true} />
            <PolarAngleAxis
              dataKey="metric"
              tick={{
                fill: '#374151',
                fontSize: 16,
                fontWeight: 'bold'
              }}
              tickFormatter={(value) => value}
              radius={120}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={false}
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
    </div>
  );
};

export default KiviatChart;
