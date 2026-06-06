(function () {
  const form = document.getElementById("search-form");
  const queryInput = document.getElementById("query");
  const locationInput = document.getElementById("location");

  function openResults(query, location) {
    const params = new URLSearchParams();
    if (query) {
      params.set("q", query);
    }
    if (location) {
      params.set("location", location);
    }
    window.location.href = `/results?${params.toString()}`;
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    openResults(queryInput.value.trim(), locationInput.value.trim());
  });

  document.querySelectorAll("[data-query]").forEach((button) => {
    button.addEventListener("click", () => {
      queryInput.value = button.dataset.query || "";
      openResults(queryInput.value.trim(), locationInput.value.trim());
    });
  });
})();
