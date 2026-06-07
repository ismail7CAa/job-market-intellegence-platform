(function () {
  const api = window.JobIntelApi;
  const resultsKey = "jobIntel.searchResults";
  const stateKey = "jobIntel.searchState";
  const form = document.getElementById("search-form");
  const queryInput = document.getElementById("query");
  const locationInput = document.getElementById("location");
  const statusMessage = document.getElementById("search-status");
  const suggestionsPanel = document.getElementById("suggestions");
  const submitButton = form.querySelector("button[type='submit']");
  let suggestions = [];
  let activeSuggestionIndex = -1;
  let suggestionTimer = null;
  const germanTerms = [
    "pflege",
    "buchhaltung",
    "logistik",
    "vertrieb",
    "ingenieur",
    "ingenieurwesen",
    "verwaltung",
    "erzieher",
    "lehrer",
    "einkauf",
    "handwerk",
    "bau",
    "koch",
    "hotel",
    "personal",
  ];
  const suggestionLabels = {
    Nurse: "Pflegefachkraft",
    Accountant: "Buchhalter",
    "Warehouse Worker": "Lagermitarbeiter",
    "Dispatch Coordinator": "Disponent",
    "Sales Representative": "Vertriebsmitarbeiter",
    "Mechanical Engineer": "Maschinenbauingenieur",
    "Electrical Engineer": "Elektroingenieur",
    "Administrative Officer": "Verwaltungsmitarbeiter",
  };
  const categoryLabels = {
    title: "Beruf",
    company: "Unternehmen",
    location: "Ort",
    skill: "Kompetenz",
    occupation: "Berufsfeld",
    role_type: "Rolle",
  };

  function detectLanguage(query) {
    const normalized = String(query || "").toLowerCase();
    if (/[äöüß]/.test(normalized)) {
      return "de";
    }
    return germanTerms.some((term) => normalized.includes(term)) ? "de" : "en";
  }

  function setBusy(isBusy) {
    submitButton.disabled = isBusy;
    submitButton.textContent = isBusy ? "Suche laeuft..." : "Jobs suchen";
  }

  function showStatus(message, isError) {
    statusMessage.hidden = !message;
    statusMessage.textContent = message || "";
    statusMessage.classList.toggle("error", Boolean(isError));
    statusMessage.classList.toggle("loading", Boolean(message) && !isError);
  }

  function hideSuggestions() {
    suggestions = [];
    activeSuggestionIndex = -1;
    suggestionsPanel.hidden = true;
    suggestionsPanel.innerHTML = "";
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function renderSuggestions(rows) {
    const language = detectLanguage(queryInput.value);
    suggestions = rows || [];
    activeSuggestionIndex = -1;
    if (!suggestions.length) {
      hideSuggestions();
      return;
    }

    suggestionsPanel.innerHTML = suggestions.map((item, index) => `
      <button class="suggestion-button" type="button" data-suggestion-index="${index}">
        <span class="suggestion-value">${escapeHtml(language === "de" ? suggestionLabels[item.value] || item.value : item.value)}</span>
        <span class="suggestion-category">${escapeHtml(language === "de" ? categoryLabels[item.category] || item.category : item.category.replace("_", " "))}</span>
      </button>
    `).join("");
    suggestionsPanel.hidden = false;
    suggestionsPanel.querySelectorAll("[data-suggestion-index]").forEach((button) => {
      button.addEventListener("mousedown", (event) => {
        event.preventDefault();
        chooseSuggestion(Number(button.dataset.suggestionIndex));
      });
    });
  }

  function setActiveSuggestion(index) {
    activeSuggestionIndex = index;
    suggestionsPanel.querySelectorAll(".suggestion-button").forEach((button, buttonIndex) => {
      button.classList.toggle("active", buttonIndex === activeSuggestionIndex);
    });
  }

  function chooseSuggestion(index) {
    const suggestion = suggestions[index];
    if (!suggestion) {
      return;
    }
    const language = detectLanguage(queryInput.value);
    queryInput.value = language === "de" ? suggestionLabels[suggestion.value] || suggestion.value : suggestion.value;
    queryInput.dataset.searchValue = suggestion.value;
    queryInput.dataset.language = language;
    hideSuggestions();
    queryInput.focus();
  }

  async function loadSuggestions() {
    const query = queryInput.value.trim();
    if (query.length < 2) {
      hideSuggestions();
      return;
    }
    try {
      const payload = await api.suggestions({ q: query, limit: 8 });
      renderSuggestions(payload.suggestions || []);
    } catch (_error) {
      hideSuggestions();
    }
  }

  async function searchAndOpenResults(query, location) {
    const actualQuery = queryInput.dataset.searchValue || query;
    const displayQuery = query;
    const language = queryInput.dataset.language || detectLanguage(displayQuery);
    setBusy(true);
    showStatus("Gepruefte Stellen werden durchsucht...", false);
    try {
      const searchState = {
        q: actualQuery,
        display_q: displayQuery,
        location,
        language,
        sort: "relevance",
        page: 1,
        per_page: 10,
      };
      const data = await api.searchJobs({
        q: searchState.q,
        location: searchState.location,
        sort: searchState.sort,
        page: searchState.page,
        per_page: searchState.per_page,
      });
      sessionStorage.setItem(resultsKey, JSON.stringify(data));
      sessionStorage.setItem(stateKey, JSON.stringify(searchState));
      window.location.href = "/results";
    } catch (error) {
      showStatus(error.message || "Suche fehlgeschlagen. Bitte versuchen Sie es erneut.", true);
      setBusy(false);
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await searchAndOpenResults(queryInput.value.trim(), locationInput.value.trim());
  });

  queryInput.addEventListener("input", () => {
    delete queryInput.dataset.searchValue;
    delete queryInput.dataset.language;
    clearTimeout(suggestionTimer);
    suggestionTimer = setTimeout(loadSuggestions, 180);
  });

  queryInput.addEventListener("keydown", (event) => {
    if (suggestionsPanel.hidden || !suggestions.length) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveSuggestion((activeSuggestionIndex + 1) % suggestions.length);
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveSuggestion((activeSuggestionIndex - 1 + suggestions.length) % suggestions.length);
    }
    if (event.key === "Enter" && activeSuggestionIndex >= 0) {
      event.preventDefault();
      chooseSuggestion(activeSuggestionIndex);
    }
    if (event.key === "Escape") {
      hideSuggestions();
    }
  });

  queryInput.addEventListener("blur", () => {
    setTimeout(hideSuggestions, 120);
  });

  document.querySelectorAll("[data-query]").forEach((button) => {
    button.addEventListener("click", async () => {
      queryInput.value = button.dataset.query || "";
      delete queryInput.dataset.searchValue;
      queryInput.dataset.language = detectLanguage(queryInput.value);
      await searchAndOpenResults(queryInput.value.trim(), locationInput.value.trim());
    });
  });
})();
