(function () {
  const api = window.JobIntelApi;
  const resultsKey = "jobIntel.searchResults";
  const stateKey = "jobIntel.searchState";
  const state = {
    page: 1,
    perPage: 10,
    totalPages: 1,
    selectedJobId: null,
    language: "de",
  };
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
  const copy = {
    de: {
      allJobs: "Alle Stellen",
      searchResults: "Suchergebnisse",
      indexedJobs: "Indexierte Stellen in Deutschland",
      page: "Seite",
      of: "von",
      loadingJobs: "Stellen werden geladen...",
      noJobs: "Keine passenden Stellen gefunden. Versuchen Sie einen breiteren Begriff oder entfernen Sie Filter.",
      matchedDefault: "Passend zu Beruf, Unternehmen und Marktkontext.",
      inspect: "Ansehen",
      score: "Score",
      loading: "Laedt",
      detail: "Stellendetail",
      error: "Fehler",
      detailError: "Detail konnte nicht geladen werden",
      employmentUnknown: "Anstellungsart unbekannt",
      salary: "Gehalt",
      range: "Spanne",
      type: "Typ",
      confidence: "Sicherheit",
      marketContext: "Marktkontext",
      sameRole: "Gleiche Rolle",
      sameLocation: "Gleicher Ort",
      roleAverage: "Rollendurchschnitt",
      skills: "Kompetenzen",
      noSkills: "Keine Kompetenzen angegeben.",
      sourceApply: "Quelle und Bewerbung",
      source: "Quelle",
      allowed: "Freigegeben",
      yes: "Ja",
      no: "Nein",
      similarJobs: "Aehnliche Stellen",
      noSimilar: "Keine aehnlichen Stellen gefunden.",
      filtersAnyCompany: "Alle Unternehmen",
      filtersAnyRole: "Alle Berufsfelder",
      filtersAnyEmployment: "Alle Anstellungsarten",
      loadingPolicy: "Aktuell werden rechtlich freigegebene Seed- und Anbieterquellen genutzt. Produktive Live-Daten muessen ueber offizielle APIs, lizenzierte Anbieter oder genehmigte Unternehmensfeeds kommen.",
      searchFailed: "Suche fehlgeschlagen.",
      filterFailed: "Filter konnten nicht geladen werden.",
      apply: "Bewerben",
      listed: "ausgewiesen",
      estimated: "geschaetzt",
      salaryNotListed: "Gehalt nicht angegeben",
      estimatedPrefix: "Geschaetzt ",
    },
    en: {
      allJobs: "All jobs",
      searchResults: "Search results",
      indexedJobs: "Indexed German jobs",
      page: "Page",
      of: "of",
      loadingJobs: "Loading jobs...",
      noJobs: "No matching jobs found. Try a broader term or remove filters.",
      matchedDefault: "Matched against indexed role, company, and market context.",
      inspect: "Inspect",
      score: "Score",
      loading: "Loading",
      detail: "Job detail",
      error: "Error",
      detailError: "Could not load detail",
      employmentUnknown: "Employment type unknown",
      salary: "Salary",
      range: "Range",
      type: "Type",
      confidence: "Confidence",
      marketContext: "Market context",
      sameRole: "Same role",
      sameLocation: "Same location",
      roleAverage: "Role average",
      skills: "Skills",
      noSkills: "No skills listed.",
      sourceApply: "Source and application",
      source: "Source",
      allowed: "Allowed",
      yes: "Yes",
      no: "No",
      similarJobs: "Similar jobs",
      noSimilar: "No similar jobs found.",
      filtersAnyCompany: "Any company",
      filtersAnyRole: "Any role type",
      filtersAnyEmployment: "Any employment type",
      loadingPolicy: "This v1 uses approved seed and provider-ready sources. Production live data must use official APIs, licensed providers, or approved company feeds.",
      searchFailed: "Search failed.",
      filterFailed: "Could not load filters.",
      apply: "Apply",
      listed: "listed",
      estimated: "estimated",
      salaryNotListed: "Salary not listed",
      estimatedPrefix: "Estimated ",
    },
  };
  const titleDe = {
    "Account Manager": "Kundenbetreuer",
    Accountant: "Buchhalter",
    "Accounts Payable Clerk": "Sachbearbeiter Kreditorenbuchhaltung",
    "Administrative Officer": "Verwaltungsmitarbeiter",
    "Business Development Manager": "Business-Development-Manager",
    Carpenter: "Tischler",
    "Chef de Partie": "Chef de Partie",
    "Civil Engineer": "Bauingenieur",
    "Compensation Analyst": "Verguetungsanalyst",
    "Construction Site Supervisor": "Bauleiter",
    "Customer Service Advisor": "Kundenberater",
    "Dispatch Coordinator": "Disponent",
    "E-Commerce Coordinator": "E-Commerce-Koordinator",
    "Early Childhood Educator": "Erzieher",
    "Elderly Care Specialist": "Altenpfleger",
    "Electrical Engineer": "Elektroingenieur",
    Electrician: "Elektriker",
    "Event Coordinator": "Eventkoordinator",
    "Facilities Manager": "Facility Manager",
    "Financial Controller": "Financial Controller",
    "Fleet Operations Manager": "Flottenmanager",
    "Forklift Operator": "Gabelstaplerfahrer",
    "HR Generalist": "HR Generalist",
    "HVAC Technician": "Anlagenmechaniker SHK",
    "Hotel Receptionist": "Hotelrezeptionist",
    "Housekeeping Supervisor": "Housekeeping Supervisor",
    "Inside Sales Specialist": "Inside-Sales-Spezialist",
    "Instructional Designer": "Learning Designer",
    "Learning Coordinator": "Weiterbildungskoordinator",
    "Mechanical Engineer": "Maschinenbauingenieur",
    "Medical Assistant": "Medizinischer Fachangestellter",
    "Municipal Project Coordinator": "Kommunaler Projektkoordinator",
    Nurse: "Pflegefachkraft",
    "Office Manager": "Office Manager",
    "Operations Coordinator": "Operations-Koordinator",
    "Payroll Specialist": "Payroll Specialist",
    "People Operations Manager": "People-Operations-Manager",
    Physiotherapist: "Physiotherapeut",
    Plumber: "Installateur",
    "Policy Analyst": "Policy Analyst",
    "Primary School Teacher": "Grundschullehrer",
    "Process Improvement Specialist": "Prozessoptimierer",
    "Procurement Specialist": "Einkaufsspezialist",
    "Production Engineer": "Produktionsingenieur",
    "Public Procurement Officer": "Sachbearbeiter oeffentliche Vergabe",
    "Quality Engineer": "Qualitaetsingenieur",
    "Radiology Technician": "Radiologietechnologe",
    Recruiter: "Recruiter",
    "Restaurant Manager": "Restaurantleiter",
    "Retail Sales Associate": "Verkaeufer im Einzelhandel",
    "Sales Operations Analyst": "Sales-Operations-Analyst",
    "Sales Representative": "Vertriebsmitarbeiter",
    "Social Services Caseworker": "Sachbearbeiter Sozialdienst",
    "Store Manager": "Filialleiter",
    "Student Advisor": "Studienberater",
    "Supply Chain Planner": "Supply-Chain-Planer",
    "Tax Assistant": "Steuerassistent",
    "Visual Merchandiser": "Visual Merchandiser",
    "Vocational Trainer": "Ausbilder",
    "Warehouse Worker": "Lagermitarbeiter",
  };
  const valueDe = {
    Healthcare: "Gesundheit",
    Logistics: "Logistik",
    Retail: "Einzelhandel",
    Finance: "Finanzen",
    Sales: "Vertrieb",
    HR: "Personalwesen",
    Construction: "Bau und Handwerk",
    Hospitality: "Gastronomie und Hotel",
    Education: "Bildung",
    Operations: "Operations",
    Engineering: "Ingenieurwesen",
    "Public Sector": "Oeffentlicher Dienst",
    "Healthcare and Nursing": "Gesundheit und Pflege",
    "Warehousing and Logistics": "Lager und Logistik",
    "Business Operations": "Business Operations",
    "Engineering and Technical Services": "Ingenieurwesen und Technik",
    "Public Administration": "Oeffentliche Verwaltung",
    permanent: "Festanstellung",
    temporary: "Befristet",
    apprenticeship: "Ausbildung",
    internship: "Praktikum",
    entry: "Einstieg",
    mid: "Berufserfahren",
    senior: "Senior",
    onsite: "Vor Ort",
    hybrid: "Hybrid",
    remote: "Remote",
    yearly: "jaehrlich",
    listed: "ausgewiesen",
    estimated: "geschaetzt",
    Germany: "Deutschland",
    Cologne: "Koeln",
    Munich: "Muenchen",
    Nuremberg: "Nuernberg",
    Dusseldorf: "Duesseldorf",
    "North Rhine-Westphalia": "Nordrhein-Westfalen",
    Bavaria: "Bayern",
    Hesse: "Hessen",
    Saxony: "Sachsen",
    "Lower Saxony": "Niedersachsen",
  };
  const descriptionDe = {
    Nurse: "Patientenversorgung, Dokumentation und Schichtkoordination in einem Klinikteam.",
    "Medical Assistant": "Unterstuetzung bei Aufnahme, Terminplanung, Diagnostik und medizinischer Dokumentation.",
    Physiotherapist: "Rehabilitationsplaene, Mobilitaetstraining und Betreuung in der ambulanten Versorgung.",
    "Elderly Care Specialist": "Pflegeablaeufe, Dokumentation und Kommunikation mit Angehoerigen koordinieren.",
    "Radiology Technician": "Bildgebende Systeme bedienen und sichere diagnostische Ablaeufe unterstuetzen.",
    "Warehouse Worker": "Kommissionierung, Verpackung und Bestandsarbeit in einem regionalen Logistikzentrum.",
    "Dispatch Coordinator": "Fahrer, Lieferfenster und Transportdokumentation koordinieren.",
    "Supply Chain Planner": "Bedarf, Bestand, Nachschub und Lieferantenabstimmung planen.",
    "Forklift Operator": "Waren sicher in Lagerzonen und an Laderampen bewegen.",
    "Fleet Operations Manager": "Flottenauslastung, Wartungsplaene und Fahrerleistung steuern.",
    Accountant: "Monatsabschluesse, Kontenabstimmung und Finanzberichte unterstuetzen.",
    "Sales Representative": "Kunden betreuen, Chancen qualifizieren und Verkaufsabschluesse begleiten.",
    "Mechanical Engineer": "Mechanische Komponenten entwerfen, Tests durchfuehren und Produktion vorbereiten.",
    "Electrical Engineer": "Elektrische Systeme, Dokumentation, Tests und Lieferantenabstimmung entwickeln.",
    "Administrative Officer": "Buergeranfragen, Akten und Verwaltungsablaeufe bearbeiten.",
  };
  const skillDe = {
    "Patient Care": "Patientenversorgung",
    Documentation: "Dokumentation",
    "German B2": "Deutsch B2",
    "German C1": "Deutsch C1",
    Inventory: "Bestand",
    Forklift: "Gabelstapler",
    "Shift Work": "Schichtarbeit",
    Dispatch: "Disposition",
    "Route Planning": "Routenplanung",
    Communication: "Kommunikation",
    Recruiting: "Recruiting",
    "Employee Relations": "Mitarbeiterbetreuung",
    "HR Operations": "HR Operations",
    Procurement: "Einkauf",
    Negotiation: "Verhandlung",
    "Supplier Management": "Lieferantenmanagement",
    "Data Analysis": "Datenanalyse",
    Testing: "Tests",
    "Root Cause Analysis": "Ursachenanalyse",
  };

  const queryInput = document.getElementById("query");
  const locationInput = document.getElementById("location");
  const sortInput = document.getElementById("sort");
  const companyInput = document.getElementById("company");
  const roleTypeInput = document.getElementById("role-type");
  const employmentTypeInput = document.getElementById("employment-type");
  const salaryMinInput = document.getElementById("salary-min");
  const salaryMaxInput = document.getElementById("salary-max");
  const form = document.getElementById("top-search-form");
  const applyFiltersButton = document.getElementById("apply-filters");
  const previousPageButton = document.getElementById("previous-page");
  const nextPageButton = document.getElementById("next-page");
  const pageLabel = document.getElementById("page-label");
  const statusMessage = document.getElementById("status-message");
  const jobList = document.getElementById("job-list");
  const detailEmpty = document.getElementById("detail-empty");
  const detailContent = document.getElementById("detail-content");
  let facetsPayload = null;

  function redirectToSearch() {
    window.location.href = "/job-intelligence/";
  }

  function readStoredPayload() {
    const raw = sessionStorage.getItem(resultsKey);
    if (!raw) {
      redirectToSearch();
      return null;
    }
    try {
      return JSON.parse(raw);
    } catch (_error) {
      sessionStorage.removeItem(resultsKey);
      redirectToSearch();
      return null;
    }
  }

  function readStoredState(payload) {
    const raw = sessionStorage.getItem(stateKey);
    if (!raw) {
      return {
        q: payload.query || "",
        display_q: payload.query || "",
        location: payload.location || "",
        sort: payload.sort || "relevance",
        page: payload.page || 1,
        per_page: payload.per_page || state.perPage,
      };
    }
    try {
      return JSON.parse(raw);
    } catch (_error) {
      return {
        q: payload.query || "",
        display_q: payload.query || "",
        location: payload.location || "",
        sort: payload.sort || "relevance",
        page: payload.page || 1,
        per_page: payload.per_page || state.perPage,
      };
    }
  }

  const initialPayload = readStoredPayload();
  if (!initialPayload) {
    return;
  }

  const initialState = readStoredState(initialPayload);
  function detectLanguage(query, savedLanguage) {
    if (savedLanguage === "en" || savedLanguage === "de") {
      return savedLanguage;
    }
    const normalized = String(query || "").toLowerCase();
    if (/[äöüß]/.test(normalized)) {
      return "de";
    }
    return germanTerms.some((term) => normalized.includes(term)) ? "de" : "en";
  }

  function text(key) {
    return copy[state.language][key] || copy.en[key] || key;
  }

  function localizeValue(value) {
    if (state.language !== "de") {
      return value;
    }
    if (String(value || "").includes(",")) {
      return String(value).split(",").map((part) => localizeValue(part.trim())).join(", ");
    }
    return valueDe[value] || value;
  }

  function localizeTitle(title) {
    if (state.language !== "de") {
      return title;
    }
    return titleDe[title] || title;
  }

  function localizeDescription(job) {
    if (state.language !== "de") {
      return job.description || "No description available.";
    }
    return descriptionDe[job.title] || job.description || "Keine Beschreibung verfuegbar.";
  }

  function localizeSalaryLabel(label) {
    if (state.language !== "de") {
      return label;
    }
    const raw = String(label || "");
    if (raw === "Salary not listed") {
      return text("salaryNotListed");
    }
    return raw.replace("Estimated ", text("estimatedPrefix")).replace(" EUR", " EUR");
  }

  function localizeGovernanceNote(note) {
    if (state.language !== "de") {
      return note || copy.en.loadingPolicy;
    }
    return copy.de.loadingPolicy;
  }

  function localizeApplyNote(note) {
    if (state.language !== "de") {
      return note;
    }
    return "Die Bewerbung wird auf der freigegebenen Quellen- oder Unternehmensseite fortgesetzt.";
  }

  function setOptionLabels() {
    const labels = state.language === "de"
      ? {
        relevance: "Relevanz",
        salary_desc: "Gehalt absteigend",
        salary_asc: "Gehalt aufsteigend",
        posted_desc: "Neueste zuerst",
        company: "Unternehmen",
        title: "Berufsbezeichnung",
      }
      : {
        relevance: "Relevance",
        salary_desc: "Salary high to low",
        salary_asc: "Salary low to high",
        posted_desc: "Newest",
        company: "Company",
        title: "Title",
      };
    Array.from(sortInput.options).forEach((option) => {
      option.textContent = labels[option.value] || option.textContent;
    });
  }

  function applyLanguageToChrome() {
    const isGerman = state.language === "de";
    document.documentElement.lang = state.language;
    queryInput.placeholder = isGerman ? "Beruf, Kompetenz, Unternehmen" : "Search role, skill, company";
    locationInput.placeholder = isGerman ? "Ort" : "Location";
    document.getElementById("top-search-button").textContent = isGerman ? "Suchen" : "Search";
    document.querySelector("[data-i18n='filtersEyebrow']").textContent = isGerman ? "Filter" : "Filters";
    document.querySelector("[data-i18n='sortLabel']").textContent = isGerman ? "Sortierung" : "Sort";
    document.querySelector("[data-i18n='companyLabel']").textContent = isGerman ? "Unternehmen" : "Company";
    document.querySelector("[data-i18n='roleTypeLabel']").textContent = isGerman ? "Berufsfeld" : "Role type";
    document.querySelector("[data-i18n='employmentLabel']").textContent = isGerman ? "Anstellungsart" : "Employment type";
    document.querySelector("[data-i18n='salaryMinLabel']").textContent = isGerman ? "Mindestgehalt" : "Minimum salary";
    document.querySelector("[data-i18n='salaryMaxLabel']").textContent = isGerman ? "Maximalgehalt" : "Maximum salary";
    document.querySelector("[data-i18n='sourceEyebrow']").textContent = isGerman ? "Datenquellen" : "Data guardrails";
    document.querySelector("[data-i18n='totalMatches']").textContent = isGerman ? "Treffer" : "Total matches";
    document.querySelector("[data-i18n='averageSalary']").textContent = isGerman ? "Durchschnittsgehalt" : "Average salary";
    document.querySelector("[data-i18n='listedSalaries']").textContent = isGerman ? "Ausgewiesene Gehaelter" : "Listed salaries";
    document.querySelector("[data-i18n='applyLinks']").textContent = isGerman ? "Bewerbungslinks" : "Apply links";
    applyFiltersButton.textContent = isGerman ? "Filter anwenden" : "Apply filters";
    previousPageButton.textContent = isGerman ? "Zurueck" : "Prev";
    nextPageButton.textContent = isGerman ? "Weiter" : "Next";
    setOptionLabels();
  }

  queryInput.value = initialState.display_q || initialState.q || "";
  if (initialState.display_q && initialState.display_q !== initialState.q) {
    queryInput.dataset.searchValue = initialState.q;
  }
  locationInput.value = initialState.location || "";
  sortInput.value = initialState.sort || "relevance";
  companyInput.value = initialState.company || "";
  roleTypeInput.value = initialState.role_type || "";
  employmentTypeInput.value = initialState.employment_type || "";
  salaryMinInput.value = initialState.salary_min || "";
  salaryMaxInput.value = initialState.salary_max || "";
  state.language = detectLanguage(queryInput.value, initialState.language);
  state.page = Number(initialState.page || initialPayload.page || 1);
  state.perPage = Number(initialState.per_page || initialPayload.per_page || 10);
  applyLanguageToChrome();

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function formatNumber(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "-";
    }
    return Math.round(Number(value)).toLocaleString(state.language === "de" ? "de-DE" : "en-US");
  }

  function showStatus(message, isError) {
    statusMessage.hidden = !message;
    statusMessage.textContent = message || "";
    statusMessage.classList.toggle("error", Boolean(isError));
    statusMessage.classList.toggle("loading", Boolean(message) && !isError);
  }

  function renderLoadingSkeletons() {
    jobList.innerHTML = Array.from({ length: 4 }, () => '<article class="job-card skeleton" aria-hidden="true"></article>').join("");
    detailEmpty.hidden = true;
    detailContent.hidden = false;
    detailContent.innerHTML = '<div class="detail-card skeleton" aria-hidden="true"></div>';
  }

  function buildSearchParams() {
    return {
      q: queryInput.dataset.searchValue || queryInput.value.trim(),
      display_q: queryInput.value.trim(),
      location: locationInput.value.trim(),
      language: state.language,
      sort: sortInput.value,
      company: companyInput.value,
      role_type: roleTypeInput.value,
      employment_type: employmentTypeInput.value,
      salary_min: salaryMinInput.value,
      salary_max: salaryMaxInput.value,
      page: state.page,
      per_page: state.perPage,
    };
  }

  function fillSelect(select, rows, label) {
    const currentValue = select.value;
    select.innerHTML = `<option value="">${label}</option>`;
    (rows || []).forEach((row) => {
      const option = document.createElement("option");
      option.value = row.value;
      option.textContent = `${localizeValue(row.value)} (${row.count})`;
      select.appendChild(option);
    });
    select.value = currentValue;
  }

  function renderSummary(payload) {
    document.documentElement.lang = state.language;
    document.getElementById("search-label").textContent = payload.query ? text("searchResults") : text("allJobs");
    const displayedQuery = queryInput.value.trim() || payload.query;
    document.getElementById("results-title").textContent = displayedQuery
      ? `"${displayedQuery}"`
      : text("indexedJobs");
    document.getElementById("total-matches").textContent = formatNumber(payload.total);
    document.getElementById("average-salary").textContent = payload.summary.average_salary
      ? `${formatNumber(payload.summary.average_salary)} EUR`
      : "-";
    document.getElementById("listed-salaries").textContent = formatNumber(payload.summary.listed_salary_sample_size);
    document.getElementById("apply-links").textContent = formatNumber(payload.summary.apply_links_available);
    document.getElementById("governance-note").textContent = localizeGovernanceNote(payload.data_governance.legal_position);
    state.totalPages = payload.total_pages || 1;
    pageLabel.textContent = `${text("page")} ${payload.page} ${text("of")} ${state.totalPages}`;
    previousPageButton.disabled = payload.page <= 1;
    nextPageButton.disabled = payload.page >= state.totalPages;
  }

  function renderJobs(jobs) {
    if (!jobs.length) {
      jobList.innerHTML = `<div class="status-message">${escapeHtml(text("noJobs"))}</div>`;
      detailEmpty.hidden = false;
      detailContent.hidden = true;
      return;
    }

    jobList.innerHTML = jobs.map((job) => {
      const reasons = (job.match_reasons || []).slice(0, 2).join(" · ");
      const tags = [
        job.city || job.location,
        job.employment_type || job.job_type,
        job.experience_level,
        job.remote_status,
        job.occupation_group,
      ].filter(Boolean).map(localizeValue).slice(0, 5);
      return `
        <article class="job-card ${job.id === state.selectedJobId ? "active" : ""}" data-job-id="${escapeHtml(job.id)}">
          <div class="job-head">
            <div>
              <h2 class="job-title">${escapeHtml(localizeTitle(job.title))}</h2>
              <div class="job-meta">${escapeHtml(job.company)} · ${escapeHtml(localizeValue(job.location))}</div>
            </div>
            <div class="salary-block">
              <span class="salary-label">${escapeHtml(localizeSalaryLabel(job.salary_label))}</span>
              <span class="salary-type">${escapeHtml(localizeValue(job.salary_type))}</span>
            </div>
          </div>
          <p class="job-description">${escapeHtml(localizeDescription(job))}</p>
          <div class="tags">${tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
          <div class="match-reasons">${escapeHtml(state.language === "de" ? text("matchedDefault") : reasons || text("matchedDefault"))}</div>
          <div class="job-actions">
            <span class="salary-note">${escapeHtml(text("score"))} ${formatNumber((job.relevance_score || 0) * 100)}</span>
            <button class="job-open" type="button" data-open-job="${escapeHtml(job.id)}">${escapeHtml(text("inspect"))}</button>
          </div>
        </article>
      `;
    }).join("");

    document.querySelectorAll("[data-open-job]").forEach((button) => {
      button.addEventListener("click", () => selectJob(button.dataset.openJob));
    });

    if (!state.selectedJobId || !jobs.some((job) => job.id === state.selectedJobId)) {
      selectJob(jobs[0].id);
    }
  }

  async function selectJob(jobId) {
    state.selectedJobId = jobId;
    document.querySelectorAll(".job-card").forEach((card) => {
      card.classList.toggle("active", card.dataset.jobId === jobId);
    });

    detailEmpty.hidden = true;
    detailContent.hidden = false;
    detailContent.innerHTML = `<div class="detail-card"><p class="eyebrow">${escapeHtml(text("loading"))}</p><h2>${escapeHtml(text("detail"))}</h2></div>`;

    try {
      const [job, similar, apply] = await Promise.all([
        api.jobDetail(jobId),
        api.similarJobs(jobId),
        api.applyHandoff(jobId),
      ]);
      renderDetail(job, similar.jobs || [], apply);
    } catch (error) {
      detailContent.innerHTML = `<div class="detail-card"><p class="eyebrow">${escapeHtml(text("error"))}</p><h2>${escapeHtml(text("detailError"))}</h2><p>${escapeHtml(error.message)}</p></div>`;
    }
  }

  function renderDetail(job, similarJobs, apply) {
    const skills = (job.required_skills || []).slice(0, 8).map((skill) => state.language === "de" ? skillDe[skill] || skill : skill);
    const applyLabel = state.language === "de" ? text("apply") : apply.button_label;
    detailContent.innerHTML = `
      <div class="detail-card">
        <p class="eyebrow">${escapeHtml(job.company)}</p>
        <h2>${escapeHtml(localizeTitle(job.title))}</h2>
        <p class="job-meta">${escapeHtml(localizeValue(job.location))} · ${escapeHtml(localizeValue(job.employment_type || job.job_type || text("employmentUnknown")))}</p>
        <div class="detail-actions">
          <a class="apply-link" href="${escapeHtml(apply.apply_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(applyLabel)}</a>
        </div>

        <section class="detail-section">
          <h3>${escapeHtml(text("salary"))}</h3>
          <div class="detail-row"><span>${escapeHtml(text("range"))}</span><strong>${escapeHtml(localizeSalaryLabel(job.salary.label))}</strong></div>
          <div class="detail-row"><span>${escapeHtml(text("type"))}</span><strong>${escapeHtml(localizeValue(job.salary.type))}</strong></div>
          <div class="detail-row"><span>${escapeHtml(text("confidence"))}</span><strong>${job.salary.confidence ? `${Math.round(job.salary.confidence * 100)}%` : "-"}</strong></div>
        </section>

        <section class="detail-section">
          <h3>${escapeHtml(text("marketContext"))}</h3>
          <div class="detail-row"><span>${escapeHtml(text("sameRole"))}</span><strong>${formatNumber(job.market_context.same_role_count)}</strong></div>
          <div class="detail-row"><span>${escapeHtml(text("sameLocation"))}</span><strong>${formatNumber(job.market_context.same_location_count)}</strong></div>
          <div class="detail-row"><span>${escapeHtml(text("roleAverage"))}</span><strong>${job.market_context.role_average_salary ? `${formatNumber(job.market_context.role_average_salary)} EUR` : "-"}</strong></div>
        </section>

        <section class="detail-section">
          <h3>${escapeHtml(text("skills"))}</h3>
          <div class="tags">${skills.map((skill) => `<span class="tag">${escapeHtml(skill)}</span>`).join("") || `<span class="salary-note">${escapeHtml(text("noSkills"))}</span>`}</div>
        </section>

        <section class="detail-section">
          <h3>${escapeHtml(text("sourceApply"))}</h3>
          <p class="salary-note">${escapeHtml(localizeApplyNote(apply.handoff_note))}</p>
          <div class="detail-row"><span>${escapeHtml(text("source"))}</span><strong>${escapeHtml(apply.source || "-")}</strong></div>
          <div class="detail-row"><span>${escapeHtml(text("allowed"))}</span><strong>${apply.source_allowed ? text("yes") : text("no")}</strong></div>
        </section>

        <section class="detail-section">
          <h3>${escapeHtml(text("similarJobs"))}</h3>
          <div class="similar-list">
            ${similarJobs.map((item) => `
              <div class="similar-item">
                <strong>${escapeHtml(localizeTitle(item.title))}</strong>
                <div class="job-meta">${escapeHtml(item.company)} · ${escapeHtml(localizeValue(item.location))}</div>
              </div>
            `).join("") || `<span class="salary-note">${escapeHtml(text("noSimilar"))}</span>`}
          </div>
        </section>
      </div>
    `;
  }

  async function loadFacets() {
    facetsPayload = await api.facets();
    renderFacets();
  }

  function renderFacets() {
    if (!facetsPayload) {
      return;
    }
    fillSelect(companyInput, facetsPayload.companies, text("filtersAnyCompany"));
    fillSelect(roleTypeInput, facetsPayload.role_types, text("filtersAnyRole"));
    fillSelect(employmentTypeInput, facetsPayload.job_types, text("filtersAnyEmployment"));
  }

  async function runSearch() {
    state.language = detectLanguage(queryInput.value, null);
    applyLanguageToChrome();
    renderFacets();
    showStatus(text("loadingJobs"), false);
    renderLoadingSkeletons();
    try {
      const searchParams = buildSearchParams();
      const payload = await api.searchJobs({
        q: searchParams.q,
        location: searchParams.location,
        sort: searchParams.sort,
        company: searchParams.company,
        role_type: searchParams.role_type,
        employment_type: searchParams.employment_type,
        salary_min: searchParams.salary_min,
        salary_max: searchParams.salary_max,
        page: searchParams.page,
        per_page: searchParams.per_page,
      });
      sessionStorage.setItem(resultsKey, JSON.stringify(payload));
      sessionStorage.setItem(stateKey, JSON.stringify(searchParams));
      showStatus("", false);
      renderSummary(payload);
      renderJobs(payload.jobs || []);
    } catch (error) {
      showStatus(error.message || text("searchFailed"), true);
      jobList.innerHTML = "";
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    state.page = 1;
    runSearch();
  });

  queryInput.addEventListener("input", () => {
    delete queryInput.dataset.searchValue;
  });

  applyFiltersButton.addEventListener("click", () => {
    state.page = 1;
    runSearch();
  });

  previousPageButton.addEventListener("click", () => {
    if (state.page > 1) {
      state.page -= 1;
      runSearch();
    }
  });

  nextPageButton.addEventListener("click", () => {
    if (state.page < state.totalPages) {
      state.page += 1;
      runSearch();
    }
  });

  loadFacets()
    .catch((error) => showStatus(error.message || text("filterFailed"), true))
    .finally(() => {
      renderSummary(initialPayload);
      renderJobs(initialPayload.jobs || []);
    });
})();
