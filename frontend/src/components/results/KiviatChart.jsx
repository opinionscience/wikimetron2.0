// File: src/components/results/KiviatChart.jsx
import React from 'react';
import { 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  Radar, 
  ResponsiveContainer,
  Legend,
  Tooltip
} from 'recharts';

const renderMetricValue = (value) => {
  if (typeof value === 'number') {
    return value.toFixed(1);
  }
  return value || '0.0';
};

// Composant pour le tooltip personnalisé qui affiche aussi les descriptions des métriques
const CustomTooltip = ({ active, payload, label }) => {
  const metricDescriptions = {
    'Heat risk': 'Indicators of controversy and abnormal activity',
    'Quality risk': 'Indicators of content quality and reliability',
    'Behaviour risk': 'Indicators of suspicious editing behaviors'
  };

  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 sm:p-4 border border-gray-300 rounded-lg shadow-lg max-w-xs">
        <p className="font-semibold text-gray-800 mb-1 text-sm sm:text-base">{label}</p>
        <p className="text-xs sm:text-sm text-gray-600 mb-2 sm:mb-3 italic">
          {metricDescriptions[label]}
        </p>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center mb-1">
            <div 
              className="w-3 h-3 rounded-full mr-2" 
              style={{ backgroundColor: entry.color }}
            ></div>
            <span className="text-xs sm:text-sm text-gray-700">
              {entry.name}: <span className="font-medium">{renderMetricValue(entry.value)}</span>
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

const KiviatChart = ({ pages, selectedPageIndices = [0], comparisonMode = false }) => {
  const colors = [
    { stroke: '#3b82f6', fill: '#3b82f6', name: 'blue' },
    { stroke: '#ef4444', fill: '#ef4444', name: 'red' },
    { stroke: '#10b981', fill: '#10b981', name: 'green' },
    { stroke: '#f59e0b', fill: '#f59e0b', name: 'orange' },
    { stroke: '#8b5cf6', fill: '#8b5cf6', name: 'purple' },
    { stroke: '#06b6d4', fill: '#06b6d4', name: 'cyan' }
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

  // Fonction pour formater le label des axes avec tooltip
  const formatAxisLabel = (value) => {
    return value;
  };

  // Configuration responsive pour mobile
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  const chartHeight = isMobile ? 700 : 600;
  const marginConfig = isMobile 
    ? { top: 30, right: 20, bottom: 30, left: 20 }
    : { top: 20, right: 80, bottom: 20, left: 80 };

  return (
    <div className="kiviat-chart-container w-full">
      {/* Graphique radar */}
      <div className="kiviat-chart-wrapper w-full">
        <ResponsiveContainer width="100%" height={chartHeight}>
          <RadarChart 
            data={data} 
            margin={marginConfig}
            className="w-full"
          >
            <PolarGrid stroke="#e5e7eb" radialLines={true} />
            <PolarAngleAxis
              dataKey="metric"
              tick={{
                fill: '#374151',
                fontSize: isMobile ? 14 : 16,
                fontWeight: 'bold'
              }}
              tickFormatter={(value) => {
                // Raccourcir les labels sur mobile
                if (isMobile) {
                  return value.replace(' risk', '');
                }
                return value;
              }}
              radius={isMobile ? 110 : 120}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={false}
              tickCount={6}
              axisLine={false}
            />

            {/* Tooltip personnalisé avec descriptions des métriques */}
            <Tooltip 
              content={<CustomTooltip />}
              cursor={{ strokeDasharray: '3 3' }}
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
                  strokeWidth={comparisonMode ? 3 : 4}
                  dot={{
                    fill: color.stroke,
                    strokeWidth: 2,
                    r: comparisonMode ? (isMobile ? 4 : 3) : (isMobile ? 6 : 5),
                    fillOpacity: 1
                  }}
                />
              );
            })}

            {comparisonMode && (
              <Legend 
                wrapperStyle={{
                  fontSize: isMobile ? '12px' : '14px',
                  paddingTop: '10px'
                }}
              />
            )}
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default KiviatChart;