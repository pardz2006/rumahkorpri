import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { rupiah } from "../lib/api";

const CITY_COORDS = {
  bekasi: [-6.2383, 106.9756], depok: [-6.4025, 106.7942], bogor: [-6.5971, 106.806],
  "tangerang selatan": [-6.2889, 106.718], tangerang: [-6.1783, 106.6319],
  jakarta: [-6.2088, 106.8456], bandung: [-6.9175, 107.6191],
  sleman: [-7.7167, 110.3556], bantul: [-7.8887, 110.33], yogyakarta: [-7.7956, 110.3695],
  semarang: [-6.9932, 110.4203], malang: [-7.9666, 112.6326], surabaya: [-7.2575, 112.7521],
  "palangka raya": [-2.21, 113.92], "bandar lampung": [-5.3971, 105.2668],
  lampung: [-5.3971, 105.2668], medan: [3.5952, 98.6722],
};

const cityCoord = (city) => {
  if (!city) return null;
  const c = city.trim().toLowerCase();
  if (CITY_COORDS[c]) return CITY_COORDS[c];
  const hit = Object.keys(CITY_COORDS).find((k) => k.includes(c) || c.includes(k));
  return hit ? CITY_COORDS[hit] : null;
};

const haversine = (a, b) => {
  const R = 6371, toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(b[0] - a[0]), dLng = toRad(b[1] - a[1]);
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[0])) * Math.cos(toRad(b[0])) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
};

const pinIcon = (color) => L.divIcon({
  className: "",
  html: `<div style="filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))"><svg width="30" height="40" viewBox="0 0 24 32" xmlns="http://www.w3.org/2000/svg"><path d="M12 0C5.4 0 0 5.4 0 12c0 8.5 12 20 12 20s12-11.5 12-20C24 5.4 18.6 0 12 0z" fill="${color}"/><circle cx="12" cy="12" r="5" fill="#fff"/></svg></div>`,
  iconSize: [30, 40], iconAnchor: [15, 40], popupAnchor: [0, -38],
});

const PRIMARY = "#0F5132";
const ACCENT = "#C2410C";

export function ProjectsMap({ projects, userCity }) {
  const elRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (mapRef.current || !elRef.current) return;
    const map = L.map(elRef.current, { scrollWheelZoom: false }).setView([-2.5, 118], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; OpenStreetMap contributors', maxZoom: 19,
    }).addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    setTimeout(() => map.invalidateSize(), 200);
  }, []);

  useEffect(() => {
    const map = mapRef.current, layer = layerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();

    const pts = (projects || []).filter((p) => p.lat != null && p.lng != null);
    if (pts.length === 0) return;

    const home = cityCoord(userCity);
    let nearestId = null;
    if (home) {
      let best = Infinity;
      pts.forEach((p) => { const d = haversine(home, [p.lat, p.lng]); if (d < best) { best = d; nearestId = p.id; } });
    }

    const markers = [];
    pts.forEach((p) => {
      const isNearest = p.id === nearestId;
      const m = L.marker([p.lat, p.lng], { icon: pinIcon(isNearest ? ACCENT : PRIMARY) });
      m.bindPopup(
        `<div style="min-width:170px;font-family:inherit">
          ${isNearest ? `<div style="font-size:11px;font-weight:700;color:${ACCENT};margin-bottom:2px">★ Terdekat dari ${userCity}</div>` : ""}
          <div style="font-weight:700;color:#1e293b;font-size:14px">${p.name}</div>
          <div style="font-size:12px;color:#64748b;margin:2px 0">${p.location || ""}</div>
          <div style="font-size:12px;color:#334155">${p.program === "FLPP" ? "FLPP Subsidi" : "Komersial"} · <b>${p.available_count ?? 0}</b>/${p.total_units ?? 0} unit</div>
          <button data-goto="${p.id}" style="margin-top:8px;width:100%;background:${PRIMARY};color:#fff;border:none;border-radius:8px;padding:7px 0;font-size:12px;font-weight:600;cursor:pointer">Lihat Unit</button>
        </div>`
      );
      m.addTo(layer);
      markers.push(m);
    });

    if (home) {
      L.circleMarker(home, { radius: 8, color: "#2563eb", weight: 3, fillColor: "#3b82f6", fillOpacity: 0.9 })
        .bindPopup(`<div style="font-weight:600;color:#1e293b">📍 Domisili Anda${userCity ? ` — ${userCity}` : ""}</div>`)
        .addTo(layer);
    }

    const all = home ? [...markers.map((m) => m.getLatLng()), L.latLng(home)] : markers.map((m) => m.getLatLng());
    map.fitBounds(L.latLngBounds(all).pad(0.2));

    map.off("popupopen");
    map.on("popupopen", (e) => {
      const btn = e.popup.getElement()?.querySelector("[data-goto]");
      if (btn) btn.onclick = () => navigate(`/proyek/${btn.getAttribute("data-goto")}`);
    });
  }, [projects, userCity, navigate]);

  return <div ref={elRef} data-testid="projects-map" className="h-[420px] w-full rounded-xl overflow-hidden border border-slate-200/80 shadow-sm z-0" />;
}
