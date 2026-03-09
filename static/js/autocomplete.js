function initAutocomplete(input, dropdown, mode) {
  let debounceTimer = null;
  let activeIndex = -1;
  let items = [];

  const transportMode = mode || input.dataset.mode || "all";

  function fetchSuggestions(query) {
    if (!query || query.length < 1) {
      hide();
      return;
    }
    if (query.length > 100) return;

    fetch(
      `/api/suggestions?q=${encodeURIComponent(query)}&mode=${encodeURIComponent(transportMode)}`,
    )
      .then((r) => r.json())
      .then((data) => {
        items = data;
        activeIndex = -1;
        render();
      })
      .catch(() => hide());
  }

  function render() {
    if (!items.length) {
      hide();
      return;
    }

    const typeIcons = {
      flights: "flight",
      hotels: "hotel",
      trains: "train",
      buses: "directions_bus",
    };
    const icon = typeIcons[transportMode] || "place";

    let html = "";
    items.forEach((item, i) => {
      const activeClass = i === activeIndex ? "active" : "";
      html += `<li class="suggestion-item ${activeClass}" data-index="${i}">
        <span class="material-icons suggestion-icon">${icon}</span>
        <div class="suggestion-text">
          <span class="suggestion-name">${escapeHtml(item.name)}</span>
        </div>
      </li>`;
    });

    dropdown.innerHTML = html;
    dropdown.style.display = "block";

    dropdown.querySelectorAll(".suggestion-item").forEach((li) => {
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        selectItem(parseInt(li.dataset.index));
      });
    });
  }

  function hide() {
    dropdown.style.display = "none";
    dropdown.innerHTML = "";
    items = [];
    activeIndex = -1;
  }

  function selectItem(index) {
    if (index >= 0 && index < items.length) {
      input.value = items[index].name;
      hide();
      input.dispatchEvent(new Event("change"));
    }
  }

  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      fetchSuggestions(input.value.trim());
    }, 250);
  });

  input.addEventListener("keydown", (e) => {
    if (!items.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
      render();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      render();
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIndex >= 0) {
        selectItem(activeIndex);
      }
    } else if (e.key === "Escape") {
      hide();
    }
  });

  input.addEventListener("blur", () => {
    setTimeout(hide, 200);
  });

  input.addEventListener("focus", () => {
    if (input.value.trim().length >= 1) {
      fetchSuggestions(input.value.trim());
    }
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}
