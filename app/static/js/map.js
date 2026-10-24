/**
 * CIVICFIX — NATIONWIDE INTERACTIVE MAP & GPS GEOLOCATION
 * Pan-India OpenStreetMap, Indian States & UTs Search, Geocoding,
 * Real Database Markers, Accessible Legend, and Map/List View Toggle.
 */

// Nationwide India Center and Zoom
const INDIA_CENTER = [22.5937, 78.9629];
const INDIA_ZOOM = 5;

// Default local reporting coordinates (Hyderabad corridor fallback)
const DEFAULT_REPORTING_COORDS = [17.4435, 78.3820];

let reportingMap = null;
let reportingMarker = null;
let exploreMap = null;
let markersLayer = null;
let hotspotLayer = null;
let currentMarkersData = [];

document.addEventListener('DOMContentLoaded', () => {
  initReportingMap();
  initExploreMap();
  initMiniDetailMap();
});

// ==========================================
// 1. CITIZEN REPORTING FORM MAP
// ==========================================
function initReportingMap() {
  const mapElem = document.getElementById('leaflet-map');
  if (!mapElem) return;

  const latInput = document.getElementById('input-latitude');
  const lonInput = document.getElementById('input-longitude');
  
  const initLat = parseFloat(latInput?.value) || DEFAULT_REPORTING_COORDS[0];
  const initLon = parseFloat(lonInput?.value) || DEFAULT_REPORTING_COORDS[1];

  reportingMap = L.map('leaflet-map').setView([initLat, initLon], 14);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors | CivicFix India',
    maxZoom: 19
  }).addTo(reportingMap);

  const customPin = L.divIcon({
    html: `
      <div style="background:linear-gradient(135deg, #22D3EE, #8B5CF6); width:28px; height:28px; border-radius:50%; border:3px solid #FFFFFF; box-shadow:0 0 12px rgba(34,211,238,0.6); display:flex; align-items:center; justify-content:center;">
        <div style="width:8px; height:8px; border-radius:50%; background:#0B1020;"></div>
      </div>
    `,
    className: 'reporting-map-pin',
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });

  reportingMarker = L.marker([initLat, initLon], {
    draggable: true,
    icon: customPin,
    title: 'Drag or click to position civic hazard'
  }).addTo(reportingMap);

  reportingMarker.on('dragend', (e) => {
    const pos = e.target.getLatLng();
    updateCoordinates(pos.lat, pos.lng);
  });

  reportingMap.on('click', (e) => {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    reportingMarker.setLatLng([lat, lng]);
    updateCoordinates(lat, lng);
  });

  // "USE MY LOCATION" Geolocation Button
  const gpsBtn = document.getElementById('use-gps-btn');
  const gpsStatus = document.getElementById('gps-status-indicator');

  if (gpsBtn) {
    gpsBtn.addEventListener('click', (e) => {
      e.preventDefault();
      if (!navigator.geolocation) {
        if (gpsStatus) gpsStatus.textContent = 'Geolocation is not supported by your browser. Please tap the map to position the pin.';
        return;
      }

      if (gpsStatus) {
        gpsStatus.textContent = 'Acquiring GPS coordinates with high accuracy...';
        gpsStatus.style.color = 'var(--accent-cyan)';
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          const accuracy = Math.round(position.coords.accuracy);

          reportingMap.setView([lat, lng], 16);
          reportingMarker.setLatLng([lat, lng]);
          updateCoordinates(lat, lng);

          if (gpsStatus) {
            gpsStatus.textContent = `GPS Located! (Accurate to ±${accuracy}m). Drag pin to adjust exact location.`;
            gpsStatus.style.color = 'var(--accent-emerald)';
          }
        },
        (error) => {
          let msg = 'Unable to acquire GPS automatically. Please tap anywhere on the map to set location.';
          if (error.code === error.PERMISSION_DENIED) {
            msg = 'GPS permission was denied. You can manually tap or drag the pin anywhere in India.';
          } else if (error.code === error.TIMEOUT) {
            msg = 'GPS request timed out. Please tap the map to place the location pin.';
          }
          if (gpsStatus) {
            gpsStatus.textContent = msg;
            gpsStatus.style.color = 'var(--accent-amber)';
          }
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    });
  }

  function updateCoordinates(lat, lng) {
    const latInp = document.getElementById('input-latitude');
    const lonInp = document.getElementById('input-longitude');
    const coordDisplay = document.getElementById('coords-display-text');

    if (latInp) latInp.value = lat.toFixed(6);
    if (lonInp) lonInp.value = lng.toFixed(6);
    if (coordDisplay) {
      coordDisplay.textContent = `Coordinates: ${lat.toFixed(5)}° N, ${lng.toFixed(5)}° E`;
    }

    // Trigger duplicate check with updated coords
    if (window.triggerDuplicateCheck) {
      window.triggerDuplicateCheck();
    }
  }
}

// ==========================================
// 2. NATIONWIDE EXPLORE MAP & LIST VIEW
// ==========================================
function initExploreMap() {
  const exploreMapElem = document.getElementById('explore-map');
  if (!exploreMapElem) return;

  // Initialized with nationwide view of India
  exploreMap = L.map('explore-map', {
    center: INDIA_CENTER,
    zoom: INDIA_ZOOM,
    minZoom: 4,
    maxZoom: 19
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors | CivicFix India',
    maxZoom: 19
  }).addTo(exploreMap);

  markersLayer = L.layerGroup().addTo(exploreMap);
  hotspotLayer = L.layerGroup().addTo(exploreMap);

  // Load Initial Nationwide Data
  loadExploreData();
  loadHotspots();

  // Reset to India View Button
  const resetBtn = document.getElementById('reset-india-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      exploreMap.setView(INDIA_CENTER, INDIA_ZOOM);
    });
  }

  // Use My Location on Explore Map
  const mapLocateBtn = document.getElementById('map-locate-btn');
  if (mapLocateBtn) {
    mapLocateBtn.addEventListener('click', () => {
      if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser.');
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          exploreMap.setView([pos.coords.latitude, pos.coords.longitude], 14);
        },
        () => {
          alert('Could not access your location. Please check browser permissions.');
        }
      );
    });
  }

  // Search Button & Enter Key in Search Input
  const searchInput = document.getElementById('filter-search-input');
  const searchBtn = document.getElementById('filter-search-btn');

  if (searchBtn) {
    searchBtn.addEventListener('click', () => {
      const q = searchInput?.value.trim();
      if (q) {
        geocodeAndPan(q);
      }
      loadExploreData();
    });
  }

  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        searchBtn?.click();
      }
    });
  }

  // Dropdown filter changes
  ['filter-state', 'filter-category', 'filter-status', 'filter-severity'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        // If state changed, pan to that state
        if (id === 'filter-state' && el.value) {
          panToState(el.value);
        }
        loadExploreData();
      });
    }
  });

  // City filter change
  const cityInput = document.getElementById('filter-city');
  if (cityInput) {
    let debounceTimer;
    cityInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        loadExploreData();
      }, 400);
    });
  }

  // Clear Filters Button
  const clearBtn = document.getElementById('clear-filters-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (cityInput) cityInput.value = '';
      ['filter-state', 'filter-category', 'filter-status', 'filter-severity'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      exploreMap.setView(INDIA_CENTER, INDIA_ZOOM);
      loadExploreData();
    });
  }

  // Map / List View Toggle
  const toggleMapBtn = document.getElementById('toggle-view-map');
  const toggleListBtn = document.getElementById('toggle-view-list');
  const mapViewWrapper = document.getElementById('map-view-wrapper');
  const listViewWrapper = document.getElementById('list-view-wrapper');

  if (toggleMapBtn && toggleListBtn && mapViewWrapper && listViewWrapper) {
    toggleMapBtn.addEventListener('click', () => {
      toggleMapBtn.classList.add('active');
      toggleMapBtn.classList.replace('btn-secondary', 'btn-primary');
      toggleListBtn.classList.remove('active');
      toggleListBtn.classList.replace('btn-primary', 'btn-secondary');
      mapViewWrapper.style.display = 'block';
      listViewWrapper.style.display = 'none';
      exploreMap.invalidateSize();
    });

    toggleListBtn.addEventListener('click', () => {
      toggleListBtn.classList.add('active');
      toggleListBtn.classList.replace('btn-secondary', 'btn-primary');
      toggleMapBtn.classList.remove('active');
      toggleMapBtn.classList.replace('btn-primary', 'btn-secondary');
      mapViewWrapper.style.display = 'none';
      listViewWrapper.style.display = 'block';
      renderListView(currentMarkersData);
    });
  }

  // Hotspots Toggle
  const hotspotToggle = document.getElementById('toggle-hotspots-btn');
  if (hotspotToggle) {
    let visible = true;
    hotspotToggle.addEventListener('click', () => {
      visible = !visible;
      if (visible) {
        exploreMap.addLayer(hotspotLayer);
        hotspotToggle.classList.add('active');
      } else {
        exploreMap.removeLayer(hotspotLayer);
        hotspotToggle.classList.remove('active');
      }
    });
  }
}

// Fetch nationwide markers and update Map & List view
function loadExploreData() {
  if (!markersLayer) return;

  const state = document.getElementById('filter-state')?.value || '';
  const city = document.getElementById('filter-city')?.value || '';
  const category = document.getElementById('filter-category')?.value || '';
  const status = document.getElementById('filter-status')?.value || '';
  const severity = document.getElementById('filter-severity')?.value || '';
  const query = document.getElementById('filter-search-input')?.value || '';

  const params = new URLSearchParams({
    state: state,
    city: city,
    category: category,
    status: status,
    severity: severity,
    q: query
  });

  const countElem = document.getElementById('results-count-text');
  if (countElem) countElem.textContent = 'Searching nationwide issues...';

  fetch(`/api/issues/map-data?${params.toString()}`)
    .then(res => res.json())
    .then(data => {
      markersLayer.clearLayers();
      currentMarkersData = data.markers || [];

      if (countElem) {
        countElem.textContent = `Found ${currentMarkersData.length} active issue reports across India`;
      }

      // Render markers on map
      currentMarkersData.forEach(issue => {
        const markerColor = getStatusColor(issue.status);
        const priorityBadge = issue.priority === 'Critical' ? '🚨' : '';

        const iconHtml = `
          <div style="background:${markerColor}; width:28px; height:28px; border-radius:50%; border:2px solid #FFFFFF; box-shadow:0 0 12px ${markerColor}; display:flex; align-items:center; justify-content:center; font-size:12px; color:#FFFFFF;">
            ${priorityBadge || getCategoryIconGlyph(issue.category)}
          </div>
        `;

        const customIcon = L.divIcon({
          html: iconHtml,
          className: 'custom-map-pin',
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });

        const marker = L.marker([issue.latitude, issue.longitude], { icon: customIcon });

        const popupContent = `
          <div style="font-family:'Inter',system-ui,sans-serif; min-width:240px; max-width:280px; color:#0F172A;">
            <div style="position:relative; margin-bottom:8px;">
              <img src="${issue.image_url}" alt="${escapeHtml(issue.title)}" style="width:100%; height:120px; object-fit:cover; border-radius:8px; border:1px solid #E2E8F0;" onerror="this.src='/static/images/placeholder_issue.svg'">
              <span style="position:absolute; top:6px; right:6px; font-size:0.68rem; font-weight:700; padding:2px 8px; border-radius:9999px; background:${markerColor}; color:#0B1020; text-transform:uppercase;">${issue.status}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <span style="font-size:0.75rem; font-weight:700; color:#0284C7;">${issue.id}</span>
              <span style="font-size:0.72rem; font-weight:600; color:#64748B;">${issue.priority} Priority</span>
            </div>
            <div style="font-weight:700; font-size:0.92rem; line-height:1.25; margin-bottom:4px; color:#0F172A;">${escapeHtml(issue.title)}</div>
            <div style="font-size:0.78rem; color:#475569; margin-bottom:6px;">
              📍 ${escapeHtml(issue.landmark || issue.address || 'India')}
            </div>
            <div style="font-size:0.72rem; color:#94A3B8; margin-bottom:8px;">
              Reported: ${issue.created_at}
            </div>
            <a href="/issues/${issue.id}" style="display:block; text-align:center; padding:6px 12px; background:linear-gradient(135deg, #0B1020 0%, #171A3A 100%); color:#22D3EE; border-radius:6px; font-size:0.82rem; font-weight:700; text-decoration:none; border:1px solid rgba(34,211,238,0.3);">
              View Complete Verification Proof &rarr;
            </a>
          </div>
        `;

        marker.bindPopup(popupContent);
        markersLayer.addLayer(marker);
      });

      // Update List view if active
      const listViewWrapper = document.getElementById('list-view-wrapper');
      if (listViewWrapper && listViewWrapper.style.display !== 'none') {
        renderListView(currentMarkersData);
      }
    })
    .catch(() => {
      if (countElem) countElem.textContent = 'Error loading map reports.';
    });
}

// Render dynamic card grid for List View
function renderListView(items) {
  const grid = document.getElementById('list-view-grid');
  if (!grid) return;

  if (!items || items.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 0.75rem;">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="8" y1="12" x2="16" y2="12"></line>
        </svg>
        <div style="font-weight: 600; font-size: 1.1rem; color: var(--text-main);">No civic issues match your current filters.</div>
        <div style="font-size: 0.85rem; margin-top: 4px;">Try clearing filters or zooming out to view reports across India.</div>
      </div>
    `;
    return;
  }

  grid.innerHTML = items.map(issue => `
    <div class="glass-card" style="padding: 1rem; display: flex; flex-direction: column;">
      <div style="position: relative; margin-bottom: 0.75rem;">
        <img src="${issue.image_url}" alt="${escapeHtml(issue.title)}" style="width: 100%; height: 160px; object-fit: cover; border-radius: 8px;" onerror="this.src='/static/images/placeholder_issue.svg'">
        <span class="badge badge-${issue.status.toLowerCase().replace(' ', '-')}" style="position: absolute; top: 8px; right: 8px;">
          ${issue.status}
        </span>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <span style="font-size: 0.76rem; font-weight: 700; color: var(--accent-cyan);">${issue.id}</span>
        <span class="badge badge-${issue.severity.toLowerCase()}" style="font-size: 0.7rem;">${issue.priority}</span>
      </div>
      <h4 style="font-size: 0.98rem; font-weight: 700; margin-bottom: 4px; line-height: 1.3;">
        ${escapeHtml(issue.title)}
      </h4>
      <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 6px;">
        📍 ${escapeHtml(issue.landmark || issue.address || 'India')}
      </div>
      <div style="font-size: 0.75rem; color: var(--text-dim); margin-bottom: 1rem; margin-top: auto;">
        ${issue.category} • ${issue.created_at}
      </div>
      <a href="/issues/${issue.id}" class="btn btn-secondary btn-sm" style="width: 100%; justify-content: center;">
        View Report Details
      </a>
    </div>
  `).join('');
}

// Pan to Indian State Center Coordinates
function panToState(stateName) {
  const STATE_COORDS = {
    'Delhi': [28.6139, 77.2090],
    'Maharashtra': [19.7515, 75.7139],
    'Karnataka': [15.3173, 75.7139],
    'Tamil Nadu': [11.1271, 78.6569],
    'Telangana': [17.8749, 78.1008],
    'West Bengal': [22.9868, 87.8550],
    'Uttar Pradesh': [26.8467, 80.9462],
    'Rajasthan': [27.0238, 74.2179],
    'Gujarat': [22.2587, 71.1924],
    'Kerala': [10.8505, 76.2711],
    'Punjab': [31.1471, 75.3412],
    'Haryana': [29.0588, 76.0856],
    'Bihar': [25.0961, 85.3131],
    'Madhya Pradesh': [22.9734, 78.6569],
    'Odisha': [20.9517, 85.0985],
    'Andhra Pradesh': [15.9129, 79.7400]
  };

  const coords = STATE_COORDS[stateName];
  if (coords && exploreMap) {
    exploreMap.setView(coords, 7);
  }
}

// Nominatim OpenStreetMap Geocoding Place Search
function geocodeAndPan(placeName) {
  if (!exploreMap) return;
  const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(placeName + ', India')}&limit=1`;
  fetch(url, { headers: { 'Accept': 'application/json' } })
    .then(res => res.json())
    .then(results => {
      if (results && results.length > 0) {
        const lat = parseFloat(results[0].lat);
        const lon = parseFloat(results[0].lon);
        exploreMap.setView([lat, lon], 12);
      }
    })
    .catch(() => {});
}

// Load Hotspots
function loadHotspots() {
  if (!hotspotLayer) return;
  hotspotLayer.clearLayers();
  fetch('/api/issues/hotspots?radius=300')
    .then(res => res.json())
    .then(data => {
      if (!data.hotspots) return;
      data.hotspots.forEach(spot => {
        const circle = L.circle([spot.center_lat, spot.center_lon], {
          color: '#FB7185',
          fillColor: '#FB7185',
          fillOpacity: 0.2,
          radius: spot.radius_meters || 250,
          weight: 2
        });
        circle.bindPopup(`
          <div style="font-family:'Inter',system-ui,sans-serif; color:#0F172A;">
            <strong>Urban Clustered Hotspot</strong><br>
            ${spot.count} municipal reports recorded in this 250m radius zone.<br>
            <em>Dominant Category: ${escapeHtml(spot.dominant_category)}</em>
          </div>
        `);
        hotspotLayer.addLayer(circle);
      });
    })
    .catch(() => {});
}

// Mini Detail Map for Issue Page
function initMiniDetailMap() {
  const miniMapElem = document.getElementById('mini-map');
  if (!miniMapElem) return;

  const lat = parseFloat(miniMapElem.dataset.lat);
  const lng = parseFloat(miniMapElem.dataset.lng);
  if (isNaN(lat) || isNaN(lng)) return;

  const miniMap = L.map('mini-map', { zoomControl: false }).setView([lat, lng], 15);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
  }).addTo(miniMap);

  L.marker([lat, lng]).addTo(miniMap)
    .bindPopup('Reported Issue Location')
    .openPopup();
}

function getStatusColor(status) {
  switch (status) {
    case 'Resolved': return '#34D399';
    case 'In Progress': return '#2DD4BF';
    case 'Assigned': return '#FBBF24';
    case 'Verified': return '#22D3EE';
    case 'Under Review': return '#8B5CF6';
    case 'Rejected': return '#FB7185';
    case 'Reopened': return '#F43F5E';
    default: return '#94A3B8';
  }
}

function getCategoryIconGlyph(cat) {
  const map = {
    'Pothole or damaged road': '🛣️',
    'Streetlight failure': '💡',
    'Overflowing garbage bin': '🗑️',
    'Drainage blockage': '🌊',
    'Water leakage': '💧',
    'Broken footpath': '🚶',
    'Damaged public property': '🏛️'
  };
  return map[cat] || '📍';
}

function escapeHtml(text) {
  if (!text) return '';
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.toString().replace(/[&<>"']/g, m => map[m]);
}
