const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8200';

export const apiService = {
  async startAnalysis(analysisData) {
    const response = await fetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(analysisData)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  async getTaskStatus(taskId) {
    const response = await fetch(`${API_BASE}/api/tasks/${taskId}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
  },

  // ✨ NOUVEAU : Récupérer les données pageviews pour les graphiques
  async getPageviewsData(pageviewsRequest) {
    const response = await fetch(`${API_BASE}/api/pageviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pageviewsRequest)
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorBody}`);
    }

    return response.json();
  },

  // ✨ NOUVEAU : Récupérer les données d'éditions temporelles
  async getEditTimeseriesData(editRequest) {
    const response = await fetch(`${API_BASE}/api/edit-timeseries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editRequest)
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorBody}`);
    }

    return response.json();
  },

  // ✨ HELPER : Fonction utilitaire pour formater les dates
  formatDateForAPI(date) {
    if (date instanceof Date) {
      return date.toISOString().split('T')[0]; // YYYY-MM-DD
    }
    return date; // déjà au bon format
  },

  // ✨ HELPER : Fonction pour générer une période par défaut (30 derniers jours)
  getDefaultDateRange() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    
    return {
      start_date: this.formatDateForAPI(startDate),
      end_date: this.formatDateForAPI(endDate)
    };
  },

  // ✨ VALIDATION : Vérifier les paramètres avant l'appel API
  validatePageviewsRequest(request) {
    const errors = [];
    
    if (!request.pages || !Array.isArray(request.pages) || request.pages.length === 0) {
      errors.push("Au moins une page est requise");
    }
    
    if (request.pages && request.pages.length > 20) {
      errors.push("Maximum 20 pages pour les graphiques");
    }
    
    if (!request.start_date) {
      errors.push("Date de début requise");
    }
    
    if (!request.end_date) {
      errors.push("Date de fin requise");
    }
    
    if (request.start_date && request.end_date) {
      const start = new Date(request.start_date);
      const end = new Date(request.end_date);
      
      if (start >= end) {
        errors.push("La date de début doit être antérieure à la date de fin");
      }
      
      const diffDays = (end - start) / (1000 * 60 * 60 * 24);
      if (diffDays > 365) {
        errors.push("Période maximum : 365 jours");
      }
    }
    
    return errors;
  },

  // ✨ MÉTHODE PRINCIPALE : Récupérer pageviews avec validation
  async fetchPageviewsForChart(pages, startDate, endDate, language = 'fr') {
    try {
      const request = {
        pages: Array.isArray(pages) ? pages : [pages],
        start_date: this.formatDateForAPI(startDate),
        end_date: this.formatDateForAPI(endDate),
        language
      };
      
      const validationErrors = this.validatePageviewsRequest(request);
      if (validationErrors.length > 0) {
        throw new Error(`Erreurs de validation: ${validationErrors.join(', ')}`);
      }

      const result = await this.getPageviewsData(request);
      
      if (!result.success) {
        throw new Error('Échec de récupération des données pageviews');
      }

      return result;

    } catch (error) {
      console.error('Erreur lors de la récupération des pageviews:', error);
      throw error;
    }
  },

  // ✨ MÉTHODE PRINCIPALE : Récupérer éditions avec validation
  async fetchEditTimeseriesForChart(pages, startDate, endDate, language = 'fr', editorType = 'user') {
    try {
      const request = {
        pages: Array.isArray(pages) ? pages : [pages],
        start_date: this.formatDateForAPI(startDate),
        end_date: this.formatDateForAPI(endDate),
        language,
        editor_type: editorType
      };
      
      const validationErrors = this.validatePageviewsRequest ?
        this.validatePageviewsRequest(request) :
        this.validateTimeseriesRequest(request);
        
      if (validationErrors.length > 0) {
        throw new Error(`Erreurs de validation: ${validationErrors.join(', ')}`);
      }

      const result = await this.getEditTimeseriesData(request);
      
      if (!result.success) {
        throw new Error('Échec de récupération des données d\'éditions');
      }

      return result;

    } catch (error) {
      console.error('Erreur lors de la récupération des éditions:', error);
      throw error;
    }
  }
};
