(() => {
  const initializeHelpSearch = () => {
    const input = document.querySelector("#help-search");
    if (!input) return;

    const cards = [...document.querySelectorAll("[data-help-card]")];
    const groups = [...document.querySelectorAll("[data-help-group]")];
    const empty = document.querySelector("#help-empty");
    const status = document.querySelector("#help-search-status");
    const clear = document.querySelector("#help-search-clear");
    const normalize = (value) =>
      value
        .normalize("NFKD")
        .replace(/[\u0300-\u036f]/g, "")
        .trim()
        .toLocaleLowerCase();

    const filterGuides = () => {
      const rawQuery = input.value.trim();
      const query = normalize(rawQuery);
      let visible = 0;

      cards.forEach((card) => {
        const match = !query || normalize(card.dataset.search || "").includes(query);
        card.hidden = !match;
        if (match) visible += 1;
      });
      groups.forEach((group) => {
        group.hidden = !group.querySelector("[data-help-card]:not([hidden])");
      });

      if (empty) empty.hidden = visible !== 0;
      if (clear) clear.hidden = !rawQuery;
      if (status) {
        status.textContent = rawQuery
          ? `${visible} guide${visible === 1 ? "" : "s"} matched \u201c${rawQuery}\u201d.`
          : `Showing all ${cards.length} guides.`;
      }
    };

    input.addEventListener("input", filterGuides);
    input.addEventListener("search", filterGuides);
    clear?.addEventListener("click", () => {
      input.value = "";
      filterGuides();
      input.focus();
    });
    document.addEventListener("keydown", (event) => {
      const target = event.target;
      const isEditing =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target?.isContentEditable;
      if (
        event.key === "/" &&
        !event.altKey &&
        !event.ctrlKey &&
        !event.metaKey &&
        !isEditing
      ) {
        event.preventDefault();
        input.focus();
      }
      if (event.key === "Escape" && document.activeElement === input && input.value) {
        input.value = "";
        filterGuides();
      }
    });

    filterGuides();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeHelpSearch, { once: true });
  } else {
    initializeHelpSearch();
  }
})();
