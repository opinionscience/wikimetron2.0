const API_BASE = process.env.REACT_APP_API_URL || 'http://37.59.112.214:8200';

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

  // ═══════════════════════════════════════════════════════════════════════
  // 🆕 NOUVEAUX ENDPOINTS POUR LA DÉTECTION AUTOMATIQUE
  // ═══════════════════════════════════════════════════════════════════════

  // 🆕 Détecter automatiquement la langue d'une liste de pages
  async detectLanguage(pages) {
    const response = await fetch(`${API_BASE}/api/detect-language`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Array.isArray(pages) ? pages : [pages])
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorBody}`);
    }

    return response.json();
  },

  // 🆕 Récupérer les langues supportées
  async getSupportedLanguages() {
    const response = await fetch(`${API_BASE}/api/supported-languages`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
  },

  // ═══════════════════════════════════════════════════════════════════════
  // ENDPOINTS EXISTANTS ADAPTÉS POUR LA DÉTECTION AUTOMATIQUE
  // ═══════════════════════════════════════════════════════════════════════

  // ✨ Récupérer les données pageviews avec détection automatique
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

  // ✨ Récupérer les données d'éditions temporelles avec détection automatique
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

  // ═══════════════════════════════════════════════════════════════════════
  // HELPERS ET UTILITAIRES
  // ═══════════════════════════════════════════════════════════════════════

  // ✨ Fonction utilitaire pour formater les dates
  formatDateForAPI(date) {
    if (date instanceof Date) {
      return date.toISOString().split('T')[0]; // YYYY-MM-DD
    }
    return date; // déjà au bon format
  },

  // ✨ Fonction pour générer une période par défaut (30 derniers jours)
  getDefaultDateRange() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    
    return {
      start_date: this.formatDateForAPI(startDate),
      end_date: this.formatDateForAPI(endDate)
    };
  },

  // 🆕 Extraire le titre propre depuis une URL Wikipedia
  extractCleanTitle(input) {
    try {
      if (input.startsWith('http')) {
        const url = new URL(input);
        if (url.hostname.includes('wikipedia.org') && url.pathname.includes('/wiki/')) {
          const rawTitle = url.pathname.split('/wiki/')[1];
          return decodeURIComponent(rawTitle.replace(/_/g, ' '));
        }
      }
    } catch (e) {
      console.warn('Erreur extraction titre:', e);
    }
    return input; // fallback
  },

  // 🆕 Extraire la langue depuis une URL Wikipedia
  extractLanguageFromUrl(input) {
    try {
      if (input.startsWith('http')) {
        const url = new URL(input);
        if (url.hostname.includes('wikipedia.org')) {
          return url.hostname.split('.')[0]; // ex: "fr" depuis "fr.wikipedia.org"
        }
      }
    } catch (e) {
      console.warn('Erreur extraction langue:', e);
    }
    return null;
  },

  // 🆕 Détecter la langue côté client (rapide, sans appel API)
  detectLanguageLocally(pages) {
    const languages = [];
    
    for (const page of pages) {
      const lang = this.extractLanguageFromUrl(page);
      if (lang) languages.push(lang);
    }
    
    if (languages.length === 0) return 'fr'; // défaut
    
    // Trouver la langue la plus fréquente
    const counts = {};
    languages.forEach(lang => counts[lang] = (counts[lang] || 0) + 1);
    
    return Object.entries(counts)
      .sort(([,a], [,b]) => b - a)[0][0]; // langue la plus fréquente
  },

  // ═══════════════════════════════════════════════════════════════════════
  // VALIDATION AMÉLIORÉE
  // ═══════════════════════════════════════════════════════════════════════

  // ✨ Validation pour pageviews ET éditions
  validateTimeseriesRequest(request) {
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

  // 🔄 Validation pageviews (alias pour compatibilité)
  validatePageviewsRequest(request) {
    return this.validateTimeseriesRequest(request);
  },

  // 🆕 Validation spécifique pour l'analyse complète
  validateAnalysisRequest(request) {
    const errors = [];
    
    if (!request.pages || !Array.isArray(request.pages) || request.pages.length === 0) {
      errors.push("Au moins une page est requise");
    }
    
    if (request.pages && request.pages.length > 50) {
      errors.push("Maximum 50 pages par analyse");
    }
    
    if (!request.start_date) {
      errors.push("Date de début requise");
    }
    
    if (!request.end_date) {
      errors.push("Date de fin requise");
    }
    
    return errors;
  },

  // ═══════════════════════════════════════════════════════════════════════
  // MÉTHODES PRINCIPALES AVEC DÉTECTION AUTOMATIQUE
  // ═══════════════════════════════════════════════════════════════════════

  // 🔄 Analyse complète avec détection automatique optionnelle
  async startAnalysisWithAutoDetection(pages, startDate, endDate, options = {}) {
    try {
      // Préparer la requête de base
      const analysisData = {
        pages: Array.isArray(pages) ? pages : [pages],
        start_date: this.formatDateForAPI(startDate),
        end_date: this.formatDateForAPI(endDate)
      };

      // Gestion de la langue
      if (options.language) {
        // Langue forcée
        analysisData.language = options.language;
      } else if (options.autoDetect !== false) {
        // Détection automatique (par défaut)
        // On peut soit détecter côté client, soit laisser l'API le faire
        if (options.detectLocally) {
          analysisData.language = this.detectLanguageLocally(analysisData.pages);
        }
        // Sinon on laisse language undefined pour que l'API détecte automatiquement
      }

      // Validation
      const validationErrors = this.validateAnalysisRequest(analysisData);
      if (validationErrors.length > 0) {
        throw new Error(`Erreurs de validation: ${validationErrors.join(', ')}`);
      }

      return await this.startAnalysis(analysisData);

    } catch (error) {
      console.error('Erreur lors du démarrage de l\'analyse:', error);
      throw error;
    }
  },

  // 🔄 Pageviews avec détection automatique optionnelle
  async fetchPageviewsForChart(pages, startDate, endDate, options = {}) {
    try {
      const request = {
        pages: Array.isArray(pages) ? pages : [pages],
        start_date: this.formatDateForAPI(startDate),
        end_date: this.formatDateForAPI(endDate)
      };

      // Gestion de la langue
      if (options.language) {
        request.language = options.language;
      } else if (options.autoDetect !== false) {
        // Détection automatique par défaut
        if (options.detectLocally) {
          request.language = this.detectLanguageLocally(request.pages);
        }
        // Sinon on laisse language undefined pour l'API
      } else {
        // Fallback explicite
        request.language = 'fr';
      }
      
      const validationErrors = this.validateTimeseriesRequest(request);
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

  // 🔄 Éditions avec détection automatique optionnelle
  async fetchEditTimeseriesForChart(pages, startDate, endDate, options = {}) {
    try {
      const request = {
        pages: Array.isArray(pages) ? pages : [pages],
        start_date: this.formatDateForAPI(startDate),
        end_date: this.formatDateForAPI(endDate),
        editor_type: options.editorType || 'user'
      };

      // Gestion de la langue
      if (options.language) {
        request.language = options.language;
      } else if (options.autoDetect !== false) {
        // Détection automatique par défaut
        if (options.detectLocally) {
          request.language = this.detectLanguageLocally(request.pages);
        }
        // Sinon on laisse language undefined pour l'API
      } else {
        // Fallback explicite
        request.language = 'fr';
      }
        
      const validationErrors = this.validateTimeseriesRequest(request);
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
  },

  // ═══════════════════════════════════════════════════════════════════════
  // 🆕 MÉTHODES UTILITAIRES AVANCÉES
  // ═══════════════════════════════════════════════════════════════════════

  // 🆕 Prévisualiser la détection de langue avant l'analyse
  async previewLanguageDetection(pages) {
    try {
      // Détection locale rapide
      const localDetection = this.detectLanguageLocally(pages);
      
      // Détection serveur précise (si nécessaire)
      let serverDetection = null;
      try {
        const result = await this.detectLanguage(pages);
        serverDetection = result.detected_language;
      } catch (e) {
        console.warn('Détection serveur échouée, utilisation locale:', e);
      }

      return {
        local: localDetection,
        server: serverDetection,
        recommended: serverDetection || localDetection,
        pages_analysis: pages.map(page => ({
          original: page,
          clean_title: this.extractCleanTitle(page),
          detected_language: this.extractLanguageFromUrl(page),
          is_url: page.startsWith('http')
        }))
      };

    } catch (error) {
      console.error('Erreur preview détection:', error);
      return {
        local: 'fr',
        server: null,
        recommended: 'fr',
        error: error.message
      };
    }
  },

  // 🆕 Vérifier si des pages sont d'origines linguistiques mixtes
  checkLanguageConsistency(pages) {
    const languages = pages
      .map(page => this.extractLanguageFromUrl(page))
      .filter(lang => lang !== null);

    const uniqueLanguages = [...new Set(languages)];
    
    return {
      isConsistent: uniqueLanguages.length <= 1,
      languages: uniqueLanguages,
      mixedLanguages: uniqueLanguages.length > 1,
      urlCount: languages.length,
      titleCount: pages.length - languages.length
    };
  }
};

// ═══════════════════════════════════════════════════════════════════════
// 🆕 EXEMPLES D'UTILISATION
// ═══════════════════════════════════════════════════════════════════════

/*
// Exemples d'utilisation avec détection automatique :

// 1. Analyse avec détection automatique (défaut)
const result1 = await apiService.startAnalysisWithAutoDetection([
  "https://fr.wikipedia.org/wiki/Emmanuel_Macron",
  "https://fr.wikipedia.org/wiki/Marine_Le_Pen"
], "2024-01-01", "2024-12-31");

// 2. Analyse avec langue forcée
const result2 = await apiService.startAnalysisWithAutoDetection([
  "Emmanuel Macron", "Marine Le Pen"
], "2024-01-01", "2024-12-31", { language: "fr" });

// 3. Pageviews avec détection automatique
const pageviews = await apiService.fetchPageviewsForChart([
  "https://en.wikipedia.org/wiki/Barack_Obama"
], "2024-01-01", "2024-12-31");

// 4. Prévisualiser la détection avant l'analyse
const preview = await apiService.previewLanguageDetection([
  "https://fr.wikipedia.org/wiki/France",
  "https://en.wikipedia.org/wiki/Barack_Obama"
]);
console.log("Langue recommandée:", preview.recommended);

// 5. Vérifier la cohérence linguistique
const consistency = apiService.checkLanguageConsistency([
  "https://fr.wikipedia.org/wiki/France",
  "https://fr.wikipedia.org/wiki/Paris"
]);
console.log("Langues cohérentes:", consistency.isConsistent);
*/