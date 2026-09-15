(function () {
  "use strict";

  var CATEGORY_ORDER = ["verified", "scouted", "secluded"];
  var CATEGORY_LABEL = { verified: "Verified", scouted: "Scouted", secluded: "Secluded / private" };

  var SESSION_TAGS = ["Wedding", "Engagement", "Senior", "Family", "Couples", "Portraits"];
  var SESSION_KEYWORDS = {
    Wedding: /wedding/i,
    Engagement: /engagement/i,
    Senior: /senior/i,
    Family: /family/i,
    Couples: /couples?/i,
    Portraits: /portrait/i
  };

  var CONFIDENCE_ORDER = ["Confirmed", "Probable", "Possible", "Unverified", "Client request only"];

  var FAVORITES_KEY = "bmls_favorites_v1";

  var state = {
    all: [],
    favorites: loadFavorites(),
    filters: {
      search: "",
      category: new Set(),
      session: new Set(),
      confidence: new Set(),
      favoritesOnly: false
    },
    userPos: null,
    sort: "name",
    currentView: "map"
  };

  var map, markerLayer, markerById = {};
  var mapAvailable = true;

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    try {
      if (typeof L === "undefined") throw new Error("Leaflet did not load");
      initMap();
    } catch (e) {
      mapAvailable = false;
      document.getElementById("map").innerHTML =
        '<div style="padding:24px;text-align:center;color:var(--ink-soft);">' +
        "Map couldn't load (no connection yet). Your saved location data still works &mdash; " +
        'switch to the <strong>List</strong> tab.</div>';
      console.error(e);
    }
    wireUpUI();
    fetch("data/locations.csv")
      .then(function (res) {
        if (!res.ok) throw new Error("Failed to load location data (" + res.status + ")");
        return res.text();
      })
      .then(function (text) {
        state.all = parseCsv(text).map(toLocation);
        buildFilterChips();
        renderAll();
      })
      .catch(function (err) {
        document.getElementById("result-count").textContent = "Could not load locations.";
        document.getElementById("location-list").innerHTML =
          '<p style="padding:16px;color:#b3261e;">' + escapeHtml(err.message) + "</p>";
        console.error(err);
      });

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("service-worker.js").catch(function () {});
    }
  }

  // ---------------------------------------------------------------------
  // CSV parsing (handles quoted fields, embedded commas, escaped quotes)
  // ---------------------------------------------------------------------
  function parseCsv(text) {
    var rows = [];
    var row = [];
    var field = "";
    var inQuotes = false;
    var i = 0;
    var len = text.length;

    function pushField() { row.push(field); field = ""; }
    function pushRow() { pushField(); rows.push(row); row = []; }

    while (i < len) {
      var c = text[i];
      if (inQuotes) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
          inQuotes = false; i++; continue;
        }
        field += c; i++; continue;
      } else {
        if (c === '"') { inQuotes = true; i++; continue; }
        if (c === ",") { pushField(); i++; continue; }
        if (c === "\r") { i++; continue; }
        if (c === "\n") { pushRow(); i++; continue; }
        field += c; i++; continue;
      }
    }
    if (field.length || row.length) pushRow();

    var header = rows.shift();
    return rows
      .filter(function (r) { return r.length === header.length && r.some(function (v) { return v !== ""; }); })
      .map(function (r) {
        var obj = {};
        header.forEach(function (h, idx) { obj[h.trim()] = r[idx]; });
        return obj;
      });
  }

  function toLocation(raw, idx) {
    var lat = parseFloat(raw.latitude);
    var lng = parseFloat(raw.longitude);
    var sessionText = raw.session_types || "";
    var sessionTags = SESSION_TAGS.filter(function (tag) {
      return SESSION_KEYWORDS[tag].test(sessionText);
    });
    var confidenceRaw = raw.confidence || "Unverified";
    var confidenceGroup = confidenceRaw.indexOf(" (") > -1
      ? confidenceRaw.split(" (")[0]
      : confidenceRaw;

    return {
      id: "loc-" + idx,
      name: raw.name,
      lat: isNaN(lat) ? null : lat,
      lng: isNaN(lng) ? null : lng,
      coordinateQuality: raw.coordinate_quality || "unknown",
      category: raw.category || "scouted",
      city: raw.city || "",
      sessionText: sessionText,
      sessionTags: sessionTags,
      confidenceRaw: confidenceRaw,
      confidenceGroup: confidenceGroup,
      notes: raw.notes || ""
    };
  }

  // ---------------------------------------------------------------------
  // Favorites (localStorage)
  // ---------------------------------------------------------------------
  function loadFavorites() {
    try {
      var raw = window.localStorage.getItem(FAVORITES_KEY);
      return raw ? new Set(JSON.parse(raw)) : new Set();
    } catch (e) { return new Set(); }
  }
  function saveFavorites() {
    try {
      window.localStorage.setItem(FAVORITES_KEY, JSON.stringify(Array.from(state.favorites)));
    } catch (e) { /* private mode etc: shortlist just won't persist */ }
  }
  function toggleFavorite(id) {
    if (state.favorites.has(id)) state.favorites.delete(id);
    else state.favorites.add(id);
    saveFavorites();
    document.getElementById("fav-count").textContent = state.favorites.size;
  }

  // ---------------------------------------------------------------------
  // Map
  // ---------------------------------------------------------------------
  function initMap() {
    map = L.map("map", { zoomControl: true }).setView([46.815, -100.835], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    markerLayer = L.markerClusterGroup({ maxClusterRadius: 45 });
    map.addLayer(markerLayer);
  }

  function pinIcon(loc) {
    var cls = "pin pin-" + loc.category + (state.favorites.has(loc.id) ? " is-favorite" : "");
    return L.divIcon({
      className: "",
      html: '<div class="' + cls + '"></div>',
      iconSize: [26, 26],
      iconAnchor: [13, 26],
      popupAnchor: [0, -26]
    });
  }

  function rebuildMarkers(list) {
    if (!mapAvailable) return;
    markerLayer.clearLayers();
    markerById = {};
    list.forEach(function (loc) {
      if (loc.lat === null || loc.lng === null) return;
      var marker = L.marker([loc.lat, loc.lng], { icon: pinIcon(loc) });
      marker.on("click", function () { openDetail(loc); });
      markerById[loc.id] = marker;
      markerLayer.addLayer(marker);
    });
  }

  function focusOnMap(loc) {
    if (loc.lat === null || loc.lng === null) return;
    if (!mapAvailable) { alert("The map couldn't load without a connection. Try again once you're back online."); return; }
    switchView("map");
    map.setView([loc.lat, loc.lng], 15, { animate: true });
    var marker = markerById[loc.id];
    if (marker) {
      if (markerLayer.zoomToShowLayer) {
        markerLayer.zoomToShowLayer(marker, function () { marker.openPopup && marker.fire("click"); });
      }
    }
  }

  // ---------------------------------------------------------------------
  // Filtering
  // ---------------------------------------------------------------------
  function applyFilters() {
    var f = state.filters;
    var q = f.search.trim().toLowerCase();
    var result = state.all.filter(function (loc) {
      if (f.category.size && !f.category.has(loc.category)) return false;
      if (f.confidence.size && !f.confidence.has(loc.confidenceGroup)) return false;
      if (f.session.size) {
        var hasAny = loc.sessionTags.some(function (t) { return f.session.has(t); });
        if (!hasAny) return false;
      }
      if (f.favoritesOnly && !state.favorites.has(loc.id)) return false;
      if (q) {
        var hay = (loc.name + " " + loc.city + " " + loc.notes + " " + loc.sessionText).toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });

    if (state.userPos) {
      result.forEach(function (loc) {
        loc.distanceMi = (loc.lat === null) ? null : haversineMiles(state.userPos, { lat: loc.lat, lng: loc.lng });
      });
    }

    result.sort(function (a, b) {
      if (state.sort === "distance" && state.userPos) {
        var da = a.distanceMi === null ? Infinity : a.distanceMi;
        var db = b.distanceMi === null ? Infinity : b.distanceMi;
        return da - db;
      }
      if (state.sort === "confidence") {
        return CONFIDENCE_ORDER.indexOf(a.confidenceGroup) - CONFIDENCE_ORDER.indexOf(b.confidenceGroup);
      }
      return a.name.localeCompare(b.name);
    });

    return result;
  }

  function renderAll() {
    var filtered = applyFilters();
    rebuildMarkers(filtered);
    renderList(filtered);
    var countText = filtered.length + " of " + state.all.length + " location" + (state.all.length === 1 ? "" : "s");
    document.getElementById("result-count").textContent = countText;
    document.getElementById("list-count").textContent = countText;
    document.getElementById("fav-count").textContent = state.favorites.size;
    updateFilterBadge();
  }

  function updateFilterBadge() {
    var f = state.filters;
    var n = f.category.size + f.session.size + f.confidence.size + (f.favoritesOnly ? 1 : 0) + (f.search ? 1 : 0);
    var badge = document.getElementById("filter-badge");
    if (n > 0) { badge.hidden = false; badge.textContent = n; }
    else { badge.hidden = true; }
  }

  // ---------------------------------------------------------------------
  // List rendering
  // ---------------------------------------------------------------------
  function renderList(list) {
    var container = document.getElementById("location-list");
    if (!list.length) {
      container.innerHTML = '<p style="padding:20px;color:var(--ink-soft);">No locations match those filters. Try clearing a few.</p>';
      return;
    }
    container.innerHTML = list.map(cardHtml).join("");
    container.querySelectorAll(".loc-card").forEach(function (card) {
      var id = card.getAttribute("data-id");
      var loc = state.all.find(function (l) { return l.id === id; });
      card.addEventListener("click", function (e) {
        if (e.target.closest(".star-btn")) return;
        openDetail(loc);
      });
    });
    container.querySelectorAll(".star-btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        toggleFavorite(btn.getAttribute("data-id"));
        renderAll();
      });
    });
  }

  function cardHtml(loc) {
    var isFav = state.favorites.has(loc.id);
    var distance = (loc.distanceMi !== undefined && loc.distanceMi !== null)
      ? '<span class="distance">' + loc.distanceMi.toFixed(1) + " mi</span>" : "";
    var approx = (loc.coordinateQuality && loc.coordinateQuality !== "exact")
      ? '<span class="tag tag-approx">' + escapeHtml(loc.coordinateQuality) + "</span>" : "";
    return (
      '<article class="loc-card" data-id="' + loc.id + '">' +
        '<div class="loc-card-top">' +
          "<div>" +
            "<h3>" + escapeHtml(loc.name) + "</h3>" +
            '<p class="city">' + escapeHtml(loc.city) + "</p>" +
          "</div>" +
          '<button class="star-btn' + (isFav ? " active" : "") + '" data-id="' + loc.id + '" aria-label="Save to shortlist">' + (isFav ? "★" : "☆") + "</button>" +
        "</div>" +
        '<p class="notes-preview">' + escapeHtml(loc.notes) + "</p>" +
        '<div class="badges">' +
          '<span class="tag tag-' + loc.category + '">' + CATEGORY_LABEL[loc.category] + "</span>" +
          '<span class="tag tag-confidence">' + escapeHtml(loc.confidenceRaw) + "</span>" +
          approx + distance +
        "</div>" +
      "</article>"
    );
  }

  // ---------------------------------------------------------------------
  // Detail sheet
  // ---------------------------------------------------------------------
  function openDetail(loc) {
    var el = document.getElementById("detail-content");
    var approx = (loc.coordinateQuality && loc.coordinateQuality !== "exact")
      ? '<span class="tag tag-approx">' + escapeHtml(loc.coordinateQuality) + " location</span>" : "";
    var hasCoords = loc.lat !== null && loc.lng !== null;
    var directions = hasCoords
      ? '<a class="btn btn-primary" target="_blank" rel="noopener" href="https://www.google.com/maps/dir/?api=1&destination=' + loc.lat + "," + loc.lng + '">Directions</a>'
      : "";
    var viewOnMap = hasCoords
      ? '<button class="btn btn-ghost" id="detail-view-map">View on map</button>' : "";
    var isFav = state.favorites.has(loc.id);

    el.innerHTML =
      "<h2>" + escapeHtml(loc.name) + "</h2>" +
      '<p class="city">' + escapeHtml(loc.city) + "</p>" +
      '<div class="badges">' +
        '<span class="tag tag-' + loc.category + '">' + CATEGORY_LABEL[loc.category] + "</span>" +
        '<span class="tag tag-confidence">' + escapeHtml(loc.confidenceRaw) + "</span>" +
        approx +
      "</div>" +
      '<p class="session-types"><strong>Good for:</strong> ' + escapeHtml(loc.sessionText || "Not specified") + "</p>" +
      '<p class="notes">' + escapeHtml(loc.notes) + "</p>" +
      '<div class="detail-actions">' +
        '<button class="btn btn-ghost" id="detail-fav">' + (isFav ? "★ On shortlist" : "☆ Add to shortlist") + "</button>" +
        viewOnMap + directions +
      "</div>" +
      (hasCoords ? "" : '<p style="margin-top:12px;color:var(--danger);font-size:0.8rem;">No coordinates recorded for this spot yet &mdash; see notes.</p>');

    document.getElementById("detail-fav").addEventListener("click", function () {
      toggleFavorite(loc.id);
      renderAll();
      openDetail(loc);
    });
    var vm = document.getElementById("detail-view-map");
    if (vm) vm.addEventListener("click", function () { closeDetail(); focusOnMap(loc); });

    document.getElementById("detail-sheet").classList.add("open");
    document.getElementById("detail-sheet").setAttribute("aria-hidden", "false");
    document.getElementById("detail-scrim").hidden = false;
  }

  function closeDetail() {
    document.getElementById("detail-sheet").classList.remove("open");
    document.getElementById("detail-sheet").setAttribute("aria-hidden", "true");
    document.getElementById("detail-scrim").hidden = true;
  }

  // ---------------------------------------------------------------------
  // Filter chips / panel
  // ---------------------------------------------------------------------
  function buildFilterChips() {
    var catCounts = {};
    var confCounts = {};
    state.all.forEach(function (loc) {
      catCounts[loc.category] = (catCounts[loc.category] || 0) + 1;
      confCounts[loc.confidenceGroup] = (confCounts[loc.confidenceGroup] || 0) + 1;
    });

    renderChipGroup("chips-category", CATEGORY_ORDER.filter(function (c) { return catCounts[c]; }), state.filters.category, function (v) { return CATEGORY_LABEL[v] + " (" + catCounts[v] + ")"; });
    renderChipGroup("chips-session", SESSION_TAGS, state.filters.session, function (v) { return v; });
    var confList = CONFIDENCE_ORDER.filter(function (c) { return confCounts[c]; });
    renderChipGroup("chips-confidence", confList, state.filters.confidence, function (v) { return v + " (" + confCounts[v] + ")"; });
  }

  function renderChipGroup(containerId, values, selectedSet, labelFn) {
    var container = document.getElementById(containerId);
    container.innerHTML = values.map(function (v) {
      return '<button type="button" class="chip' + (selectedSet.has(v) ? " selected" : "") + '" data-value="' + escapeHtml(v) + '">' + escapeHtml(labelFn(v)) + "</button>";
    }).join("");
    container.querySelectorAll(".chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        var val = chip.getAttribute("data-value");
        if (selectedSet.has(val)) selectedSet.delete(val);
        else selectedSet.add(val);
        chip.classList.toggle("selected");
      });
    });
  }

  // ---------------------------------------------------------------------
  // UI wiring
  // ---------------------------------------------------------------------
  function switchView(view) {
    state.currentView = view;
    document.querySelectorAll(".tab").forEach(function (t) {
      var active = t.getAttribute("data-view") === view;
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    document.getElementById("view-map").classList.toggle("active", view === "map");
    document.getElementById("view-list").classList.toggle("active", view === "list");
    if (view === "map" && mapAvailable) setTimeout(function () { map.invalidateSize(); }, 50);
  }

  function openFilterPanel() {
    document.getElementById("filter-panel").classList.add("open");
    document.getElementById("filter-panel").setAttribute("aria-hidden", "false");
    document.getElementById("filter-scrim").hidden = false;
    document.getElementById("btn-filters").setAttribute("aria-expanded", "true");
  }
  function closeFilterPanel() {
    document.getElementById("filter-panel").classList.remove("open");
    document.getElementById("filter-panel").setAttribute("aria-hidden", "true");
    document.getElementById("filter-scrim").hidden = true;
    document.getElementById("btn-filters").setAttribute("aria-expanded", "false");
  }

  function wireUpUI() {
    document.querySelectorAll(".tab").forEach(function (tab) {
      tab.addEventListener("click", function () { switchView(tab.getAttribute("data-view")); });
    });

    document.getElementById("btn-filters").addEventListener("click", openFilterPanel);
    document.getElementById("btn-close-filters").addEventListener("click", closeFilterPanel);
    document.getElementById("filter-scrim").addEventListener("click", closeFilterPanel);

    document.getElementById("btn-close-detail").addEventListener("click", closeDetail);
    document.getElementById("detail-scrim").addEventListener("click", closeDetail);

    document.getElementById("search-input").addEventListener("input", function (e) {
      state.filters.search = e.target.value;
    });

    document.getElementById("chk-favorites").addEventListener("change", function (e) {
      state.filters.favoritesOnly = e.target.checked;
    });

    document.getElementById("btn-apply").addEventListener("click", function () {
      closeFilterPanel();
      renderAll();
    });

    document.getElementById("btn-reset").addEventListener("click", function () {
      state.filters.search = "";
      state.filters.category.clear();
      state.filters.session.clear();
      state.filters.confidence.clear();
      state.filters.favoritesOnly = false;
      document.getElementById("search-input").value = "";
      document.getElementById("chk-favorites").checked = false;
      buildFilterChips();
      renderAll();
    });

    document.getElementById("sort-select").addEventListener("change", function (e) {
      state.sort = e.target.value;
      if (state.sort === "distance" && !state.userPos) {
        requestLocation(function () { renderAll(); });
      } else {
        renderAll();
      }
    });

    document.getElementById("btn-locate").addEventListener("click", function () {
      requestLocation(function () {
        state.sort = "distance";
        document.getElementById("sort-select").value = "distance";
        renderAll();
        document.getElementById("btn-locate").classList.add("active");
      });
    });
  }

  function requestLocation(cb) {
    if (!navigator.geolocation) {
      alert("Your browser doesn't support location. You can still sort by name.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        state.userPos = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        cb();
      },
      function () {
        alert("Couldn't get your location. Check your browser's location permission and try again.");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  // ---------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------
  function haversineMiles(a, b) {
    var R = 3958.8;
    var dLat = toRad(b.lat - a.lat);
    var dLng = toRad(b.lng - a.lng);
    var lat1 = toRad(a.lat);
    var lat2 = toRad(b.lat);
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.sin(dLng / 2) * Math.sin(dLng / 2) * Math.cos(lat1) * Math.cos(lat2);
    return R * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
  }
  function toRad(deg) { return deg * Math.PI / 180; }

  function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
})();
