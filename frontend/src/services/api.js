// apiService.js

const API_BASE =
  process.env.NODE_ENV === "development"
    ? process.env.REACT_APP_API_URL || "http://localhost:8200"
    : "";

export const apiService = {
  // ─────────────────────────────────────────────────────────────
  // CORE CALLS
  // ─────────────────────────────────────────────────────────────

  async startAnalysis(analysisData) {
    const response = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(analysisData),
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

  // ─────────────────────────────────────────────────────────────
  // 🆕 DÉTECTION AUTOMATIQUE & META
  // ─────────────────────────────────────────────────────────────

  // Renvoie:
  // {
  //   languages_summary: {"fr":2,"en":1},
  //   pages: [{ original, clean_title, detected_language, unique_key, is_url }],
  //   summary: {...}
  // }
  async detectLanguage(pages) {
    const response = await fetch(`${API_BASE}/api/detect-language`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Array.isArray(pages) ? pages : [pages]),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(
        `HTTP error! status: ${response.status}, message: ${errorBody}`
      );
    }

    return response.json();
  },

  async getSupportedLanguages() {
    const response = await fetch(`${API_BASE}/api/supported-languages`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  // ─────────────────────────────────────────────────────────────
  // TIMESERIES (PAGEVIEWS & EDITS)
  // ─────────────────────────────────────────────────────────────

  async getPageviewsData(pageviewsRequest) {
    const response = await fetch(`${API_BASE}/api/pageviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(pageviewsRequest),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(
        `HTTP error! status: ${response.status}, message: ${errorBody}`
      );
    }

    return response.json();
  },

  async getEditTimeseriesData(editRequest) {
    const response = await fetch(`${API_BASE}/api/edit-timeseries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(editRequest),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(
        `HTTP error! status: ${response.status}, message: ${errorBody}`
      );
    }

    return response.json();
  },

  // ─────────────────────────────────────────────────────────────
  // HELPERS & UTILITAIRES
  // ─────────────────────────────────────────────────────────────

  formatDateForAPI(date) {
    if (date instanceof Date) {
      return date.toISOString().split("T")[0]; // YYYY-MM-DD
    }
    return date; // déjà au bon format
  },

  getDefaultDateRange() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);

    return {
      start_date: this.formatDateForAPI(startDate),
      end_date: this.formatDateForAPI(endDate),
    };
  },

  extractCleanTitle(input) {
    try {
      if (typeof input === "string" && input.startsWith("http")) {
        const url = new URL(input);
        if (url.hostname.includes("wikipedia.org") && url.pathname.includes("/wiki/")) {
          const rawTitle = url.pathname.split("/wiki/")[1];
          return decodeURIComponent(rawTitle.replace(/_/g, " "));
        }
      }
    } catch (e) {
      console.warn("Erreur extraction titre:", e);
    }
    return input; // fallback
  },

  extractLanguageFromUrl(input) {
    try {
      if (typeof input === "string" && input.startsWith("http")) {
        const url = new URL(input);
        if (url.hostname.includes("wikipedia.org")) {
          return url.hostname.split(".")[0]; // ex: "fr" depuis "fr.wikipedia.org"
        }
      }
    } catch (e) {
      console.warn("Erreur extraction langue:", e);
    }
    return null;
  },

  detectLanguageLocally(pages) {
    const languages = [];

    for (const page of pages) {
      const lang = this.extractLanguageFromUrl(page);
      if (lang) languages.push(lang);
    }

    if (languages.length === 0) return "fr"; // défaut

    // Trouver la langue la plus fréquente
    const counts = {};
    languages.forEach((lang) => (counts[lang] = (counts[lang] || 0) + 1));

    return Object.entries(counts).sort(([, a], [, b]) => b - a)[0][0];
  },

  // ─────────────────────────────────────────────────────────────
  // VALIDATION
  // ─────────────────────────────────────────────────────────────

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

  validatePageviewsRequest(request) {
    return this.validateTimeseriesRequest(request);
  },

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

  // ─────────────────────────────────────────────────────────────
  // MÉTHODES PRINCIPALES (avec auto-détection adaptée au backend v2)
  // ─────────────────────────────────────────────────────────────

  /**
   * Démarre l’analyse complète.
   * Ne PAS envoyer `language` (le backend détecte par page).
   * Optionnel: envoyer `default_language` pour aider sur les TITRES sans URL.
   */
  async startAnalysisWithAutoDetection(pages, startDate, endDate, options = {}) {
    try {
      const analysisData = {
        pages: Array.isArray(pages) ? pages : [pages],
        start_date: this.formatDateForAPI(startDate),
        end_date: this.formatDateForAPI(endDate),
      };

      // Optionnel: fournir une langue par défaut (pour titres nus)
      if (options?.defaultLanguage) {
        analysisData.default_language = options.defaultLanguage;
      } else if (options.detectLocally === true) {
        analysisData.default_language = this.detectLanguageLocally(analysisData.pages);
      }

      const validationErrors = this.validateAnalysisRequest(analysisData);
      if (validationErrors.length > 0) {
        throw new Error(`Erreurs de validation: ${validationErrors.join(", ")}`);
      }

      return await this.startAnalysis(analysisData);
    } catch (error) {
      console.error("Erreur lors du démarrage de l'analyse:", error);
      throw error;
    }
  },

  /**
   * Récupère les pageviews pour graphiques.
   * Ne PAS envoyer `language`. (Le backend groupe par langue automatiquement.)
   * Optionnel: `default_language` pour titres nus.
   */
// Dans apiService.js - Remplacer la méthode fetchPageviewsForChart

/**
 * Récupère les pageviews pour graphiques (version multi-langues).
 * Le backend détecte automatiquement la langue de chaque page.
 */
async fetchPageviewsForChart(pages, startDate, endDate, options = {}) {
  try {
    const request = {
      pages: Array.isArray(pages) ? pages : [pages],
      start_date: this.formatDateForAPI(startDate),
      end_date: this.formatDateForAPI(endDate),
    };

    // Seule la langue par défaut peut être spécifiée (pour les titres sans URL)
    if (options?.defaultLanguage) {
      request.default_language = options.defaultLanguage;
    }

    console.log('API Service - Requête pageviews multi-langues:', request);

    const validationErrors = this.validateTimeseriesRequest(request);
    if (validationErrors.length > 0) {
      throw new Error(`Erreurs de validation: ${validationErrors.join(", ")}`);
    }

    const result = await this.getPageviewsData(request);

    if (!result.success) {
      throw new Error("Échec de récupération des données pageviews");
    }

    console.log('API Service - Réponse pageviews multi-langues:', result);
    console.log('Langues détectées:', result.metadata?.languages_summary);
    
    return result;
  } catch (error) {
    console.error("Erreur lors de la récupération des pageviews:", error);
    throw error;
  }
},
  /**
   * Récupère les séries d’éditions pour graphiques.
   * Ne PAS envoyer `language`. (Détection par page côté API.)
   * Optionnel: `default_language` pour titres nus.
   */
  async fetchEditTimeseriesForChart(pages, startDate, endDate, options = {}) {
    try {
      const request = {
        pages: Array.isArray(pages) ? pages : [pages],
        start_date: this.formatDateForAPI(startDate),
        end_date: this.formatDateForAPI(endDate),
        editor_type: options.editorType || "user",
      };

      // Optionnel: langue par défaut pour titres sans URL
      if (options?.defaultLanguage) {
        request.default_language = options.defaultLanguage;
      } else if (options.detectLocally === true) {
        request.default_language = this.detectLanguageLocally(request.pages);
      }

      const validationErrors = this.validateTimeseriesRequest(request);
      if (validationErrors.length > 0) {
        throw new Error(`Erreurs de validation: ${validationErrors.join(", ")}`);
      }

      const result = await this.getEditTimeseriesData(request);

      if (!result.success) {
        throw new Error("Échec de récupération des données d'éditions");
      }

      return result;
    } catch (error) {
      console.error("Erreur lors de la récupération des éditions:", error);
      throw error;
    }
  },

  // ─────────────────────────────────────────────────────────────
  // OUTILS AVANCÉS (UI / cohérence)
  // ─────────────────────────────────────────────────────────────

  /**
   * Prévisualise la détection de langue (local + serveur).
   * Le serveur renvoie `languages_summary` et `pages[]`.
   */
  async previewLanguageDetection(pages) {
    try {
      const localDetection = this.detectLanguageLocally(pages);

      let serverDetection = null;
      let serverPagesAnalysis = null;

      try {
        const result = await this.detectLanguage(pages);
        const langs = result?.languages_summary || {};
        const majority = Object.entries(langs).sort(([, a], [, b]) => b - a)[0]?.[0] || null;
        serverDetection = majority;
        serverPagesAnalysis = Array.isArray(result?.pages) ? result.pages : null;
      } catch (e) {
        console.warn("Détection serveur échouée, utilisation locale:", e);
      }

      return {
        local: localDetection,
        server: serverDetection,
        recommended: serverDetection || localDetection,
        pages_analysis:
          serverPagesAnalysis ||
          pages.map((page) => ({
            original: page,
            clean_title: this.extractCleanTitle(page),
            detected_language: this.extractLanguageFromUrl(page),
            unique_key: null,
            is_url: typeof page === "string" && page.startsWith("http"),
          })),
      };
    } catch (error) {
      console.error("Erreur preview détection:", error);
      return {
        local: "fr",
        server: null,
        recommended: "fr",
        error: error.message,
      };
    }
  },

  /**
   * Vérifie rapidement si la liste mélange plusieurs langues (basé sur URLs).
   */
  checkLanguageConsistency(pages) {
    const languages = pages
      .map((page) => this.extractLanguageFromUrl(page))
      .filter((lang) => lang !== null);

    const uniqueLanguages = [...new Set(languages)];

    return {
      isConsistent: uniqueLanguages.length <= 1,
      languages: uniqueLanguages,
      mixedLanguages: uniqueLanguages.length > 1,
      urlCount: languages.length,
      titleCount: pages.length - languages.length,
    };
  },

  /**
   * Affiche joliment le résumé des langues (ex: "fr: 2 · en: 1")
   */
  formatLanguagesSummary(langs) {
    if (!langs) return "—";
    return Object.entries(langs)
      .map(([k, v]) => `${k}: ${v}`)
      .join(" · ");
  },
};

export default apiService;
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