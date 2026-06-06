window.JobIntelApi = (function () {
  async function request(path, params) {
    const url = new URL(path, window.location.origin);
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        url.searchParams.set(key, value);
      }
    });

    const response = await fetch(url);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(payload.message || "Backend request failed.");
      error.payload = payload;
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  return {
    searchJobs: (params) => request("/jobs/search", params),
    facets: () => request("/jobs/search/facets"),
    jobDetail: (jobId) => request(`/jobs/${encodeURIComponent(jobId)}`),
    similarJobs: (jobId) => request(`/jobs/${encodeURIComponent(jobId)}/similar`, { limit: 4 }),
    applyHandoff: (jobId) => request(`/jobs/${encodeURIComponent(jobId)}/apply`, { redirect: "false" }),
  };
})();
