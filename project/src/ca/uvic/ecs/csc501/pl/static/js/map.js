// Server-rendered JSON is the only map data source. Result content needs no JS.
function drawMap() {
  const element = document.getElementById('station-map');
  const data = document.getElementById('map-data');
  if (!element || !data || !window.L) return;
  let stations;
  try { stations = JSON.parse(data.textContent); } catch { return; }
  if (!stations.length) return;
  element.replaceChildren();
  const map = L.map(element, { scrollWheelZoom: false });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  const labels = { AVAILABLE: 'Available', NEEDS_REVIEW: 'Needs review', UNAVAILABLE: 'Unavailable' };
  const colors = { AVAILABLE: '#225e47', NEEDS_REVIEW: '#85670a', UNAVAILABLE: '#b64435' };
  const bounds = [];
  for (const station of stations) {
    const lat = Number(station.latitude), lng = Number(station.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
    const popup = document.createElement('div');
    const link = document.createElement('a');
    link.textContent = station.name;
    link.href = station.url;
    popup.append(link, document.createElement('br'), document.createTextNode(labels[station.status] || 'Needs review'));
    L.circleMarker([lat, lng], { radius: 10, color: '#ffffff', weight: 3, fillColor: colors[station.status] || '#85670a', fillOpacity: 1 })
      .addTo(map).bindPopup(popup);
    bounds.push([lat, lng]);
  }
  if (bounds.length) map.fitBounds(bounds, { padding: [48, 48], maxZoom: 13 });
}
if (document.readyState === 'complete') drawMap();
else window.addEventListener('load', drawMap, { once: true });
