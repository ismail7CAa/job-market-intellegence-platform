(function () {
  const api = window.JobIntelApi;
  const resultsKey = "jobIntel.searchResults";
  const stateKey = "jobIntel.searchState";
  const form = document.getElementById("search-form");
  const queryInput = document.getElementById("query");
  const locationInput = document.getElementById("location");
  const statusMessage = document.getElementById("search-status");
  const submitButton = form.querySelector("button[type='submit']");

  function setBusy(isBusy) {
    submitButton.disabled = isBusy;
    submitButton.textContent = isBusy ? "Searching..." : "Search jobs";
  }

  function showStatus(message, isError) {
    statusMessage.hidden = !message;
    statusMessage.textContent = message || "";
    statusMessage.classList.toggle("error", Boolean(isError));
  }

  async function searchAndOpenResults(query, location) {
    setBusy(true);
    showStatus("Searching approved job data...", false);
    try {
      const searchState = {
        q: query,
        location,
        sort: "relevance",
        page: 1,
        per_page: 10,
      };
      const data = await api.searchJobs(searchState);
      sessionStorage.setItem(resultsKey, JSON.stringify(data));
      sessionStorage.setItem(stateKey, JSON.stringify(searchState));
      window.location.href = "/results";
    } catch (error) {
      showStatus(error.message || "Search failed. Please try again.", true);
      setBusy(false);
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await searchAndOpenResults(queryInput.value.trim(), locationInput.value.trim());
  });

  document.querySelectorAll("[data-query]").forEach((button) => {
    button.addEventListener("click", async () => {
      queryInput.value = button.dataset.query || "";
      await searchAndOpenResults(queryInput.value.trim(), locationInput.value.trim());
    });
  });
})();
