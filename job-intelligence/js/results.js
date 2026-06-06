(function () {
  const api = window.JobIntelApi;
  const state = {
    page: 1,
    perPage: 10,
    totalPages: 1,
    selectedJobId: null,
  };

  const params = new URLSearchParams(window.location.search);
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

  queryInput.value = params.get("q") || "";
  locationInput.value = params.get("location") || "";

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
    return Math.round(Number(value)).toLocaleString("en-US");
  }

  function showStatus(message, isError) {
    statusMessage.hidden = !message;
    statusMessage.textContent = message || "";
    statusMessage.classList.toggle("error", Boolean(isError));
  }

  function buildSearchParams() {
    return {
      q: queryInput.value.trim(),
      location: locationInput.value.trim(),
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

  function setUrlFromState() {
    const next = new URLSearchParams();
    const searchParams = buildSearchParams();
    Object.entries(searchParams).forEach(([key, value]) => {
      if (value && !["page", "per_page"].includes(key)) {
        next.set(key, value);
      }
    });
    window.history.replaceState({}, "", `/results?${next.toString()}`);
  }

  function fillSelect(select, rows, label) {
    const currentValue = select.value;
    select.innerHTML = `<option value="">${label}</option>`;
    (rows || []).forEach((row) => {
      const option = document.createElement("option");
      option.value = row.value;
      option.textContent = `${row.value} (${row.count})`;
      select.appendChild(option);
    });
    select.value = currentValue;
  }

  function renderSummary(payload) {
    document.getElementById("search-label").textContent = payload.query ? "Search results" : "All jobs";
    document.getElementById("results-title").textContent = payload.query
      ? `"${payload.query}"`
      : "Indexed German jobs";
    document.getElementById("total-matches").textContent = formatNumber(payload.total);
    document.getElementById("average-salary").textContent = payload.summary.average_salary
      ? `${formatNumber(payload.summary.average_salary)} EUR`
      : "-";
    document.getElementById("listed-salaries").textContent = formatNumber(payload.summary.listed_salary_sample_size);
    document.getElementById("apply-links").textContent = formatNumber(payload.summary.apply_links_available);
    document.getElementById("governance-note").textContent = payload.data_governance.legal_position;
    state.totalPages = payload.total_pages || 1;
    pageLabel.textContent = `Page ${payload.page} of ${state.totalPages}`;
    previousPageButton.disabled = payload.page <= 1;
    nextPageButton.disabled = payload.page >= state.totalPages;
  }

  function renderJobs(jobs) {
    if (!jobs.length) {
      jobList.innerHTML = '<div class="status-message">No matching jobs found. Try a broader term or remove filters.</div>';
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
      ].filter(Boolean).slice(0, 5);
      return `
        <article class="job-card ${job.id === state.selectedJobId ? "active" : ""}" data-job-id="${escapeHtml(job.id)}">
          <div class="job-head">
            <div>
              <h2 class="job-title">${escapeHtml(job.title)}</h2>
              <div class="job-meta">${escapeHtml(job.company)} · ${escapeHtml(job.location)}</div>
            </div>
            <div class="salary-block">
              <span class="salary-label">${escapeHtml(job.salary_label)}</span>
              <span class="salary-type">${escapeHtml(job.salary_type)}</span>
            </div>
          </div>
          <p class="job-description">${escapeHtml(job.description || "No description available.")}</p>
          <div class="tags">${tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
          <div class="match-reasons">${escapeHtml(reasons || "Matched against indexed role, company, and market context.")}</div>
          <div class="job-actions">
            <span class="salary-note">Score ${formatNumber((job.relevance_score || 0) * 100)}</span>
            <button class="job-open" type="button" data-open-job="${escapeHtml(job.id)}">Inspect</button>
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
    detailContent.innerHTML = '<div class="detail-card"><p class="eyebrow">Loading</p><h2>Job detail</h2></div>';

    try {
      const [job, similar, apply] = await Promise.all([
        api.jobDetail(jobId),
        api.similarJobs(jobId),
        api.applyHandoff(jobId),
      ]);
      renderDetail(job, similar.jobs || [], apply);
    } catch (error) {
      detailContent.innerHTML = `<div class="detail-card"><p class="eyebrow">Error</p><h2>Could not load detail</h2><p>${escapeHtml(error.message)}</p></div>`;
    }
  }

  function renderDetail(job, similarJobs, apply) {
    const skills = (job.required_skills || []).slice(0, 8);
    detailContent.innerHTML = `
      <div class="detail-card">
        <p class="eyebrow">${escapeHtml(job.company)}</p>
        <h2>${escapeHtml(job.title)}</h2>
        <p class="job-meta">${escapeHtml(job.location)} · ${escapeHtml(job.employment_type || job.job_type || "Employment type unknown")}</p>
        <div class="detail-actions">
          <a class="apply-link" href="${escapeHtml(apply.apply_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(apply.button_label)}</a>
        </div>

        <section class="detail-section">
          <h3>Salary</h3>
          <div class="detail-row"><span>Range</span><strong>${escapeHtml(job.salary.label)}</strong></div>
          <div class="detail-row"><span>Type</span><strong>${escapeHtml(job.salary.type)}</strong></div>
          <div class="detail-row"><span>Confidence</span><strong>${job.salary.confidence ? `${Math.round(job.salary.confidence * 100)}%` : "-"}</strong></div>
        </section>

        <section class="detail-section">
          <h3>Market context</h3>
          <div class="detail-row"><span>Same role</span><strong>${formatNumber(job.market_context.same_role_count)}</strong></div>
          <div class="detail-row"><span>Same location</span><strong>${formatNumber(job.market_context.same_location_count)}</strong></div>
          <div class="detail-row"><span>Role average</span><strong>${job.market_context.role_average_salary ? `${formatNumber(job.market_context.role_average_salary)} EUR` : "-"}</strong></div>
        </section>

        <section class="detail-section">
          <h3>Skills</h3>
          <div class="tags">${skills.map((skill) => `<span class="tag">${escapeHtml(skill)}</span>`).join("") || '<span class="salary-note">No skills listed.</span>'}</div>
        </section>

        <section class="detail-section">
          <h3>Source and application</h3>
          <p class="salary-note">${escapeHtml(apply.handoff_note)}</p>
          <div class="detail-row"><span>Source</span><strong>${escapeHtml(apply.source || "-")}</strong></div>
          <div class="detail-row"><span>Allowed</span><strong>${apply.source_allowed ? "Yes" : "No"}</strong></div>
        </section>

        <section class="detail-section">
          <h3>Similar jobs</h3>
          <div class="similar-list">
            ${similarJobs.map((item) => `
              <div class="similar-item">
                <strong>${escapeHtml(item.title)}</strong>
                <div class="job-meta">${escapeHtml(item.company)} · ${escapeHtml(item.location)}</div>
              </div>
            `).join("") || '<span class="salary-note">No similar jobs found.</span>'}
          </div>
        </section>
      </div>
    `;
  }

  async function loadFacets() {
    const facets = await api.facets();
    fillSelect(companyInput, facets.companies, "Any company");
    fillSelect(roleTypeInput, facets.role_types, "Any role type");
    fillSelect(employmentTypeInput, facets.job_types, "Any employment type");
  }

  async function runSearch() {
    showStatus("Loading jobs...", false);
    try {
      setUrlFromState();
      const payload = await api.searchJobs(buildSearchParams());
      showStatus("", false);
      renderSummary(payload);
      renderJobs(payload.jobs || []);
    } catch (error) {
      showStatus(error.message || "Search failed.", true);
      jobList.innerHTML = "";
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    state.page = 1;
    runSearch();
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
    .catch((error) => showStatus(error.message || "Could not load filters.", true))
    .finally(runSearch);
})();
