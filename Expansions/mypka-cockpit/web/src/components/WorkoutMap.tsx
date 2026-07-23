// WorkoutMap.tsx — the Leaflet canvas map: self-hosted PMTiles basemap (pluggable,
// DARK flavor) + additive ember-glow heat layer (all/filtered routes) + a single
// highlighted route in a cool, high-contrast selection colour. Built to Pax's lean
// spec (no MapLibre, no leaflet.heat in v1, no cloud tiles). GL-003 tokens drive
// every cockpit-owned colour; Leaflet's own chrome is re-skinned to the tokens in
// cockpit.css.
//
// PERFORMANCE (Pax's two-and-only-two levers, implemented):
//   1. Server-side RDP simplification → GeoJSON (done in gpxRoute.js). The client
//      never parses GPX and never sees raw points.
//   2. preferCanvas + ONE shared L.canvas() renderer for the glow + the route, so
//      900+ polylines are a handful of canvas draws, not 900+ SVG/DOM nodes.
//   Plus: the glow FeatureCollection is fetched once and drawn as a single GeoJSON
//   layer; selecting a workout only re-draws the one highlighted line.
//
// THREE REFINEMENTS (2026-06-02, Felix, Tom request):
//   1. SELECTION CONTRAST. The selected route renders in --status-info (cool steel
//      blue, GL-003 §2.4) — deliberately cool against the warm brass glut-glow so it
//      pops. Thicker (weight 5) with a colour-matched glow halo (canvas shadowBlur,
//      GL-003 §6.3: glow inherits source colour, never white) and start/end markers.
//      NB: GL-003 §9.1 hard-bans cyan/teal/neon "anywhere, ever", so the requested
//      "cyan" is realised as the in-palette cool token --status-info instead — same
//      cool-contrast intent, zero design-system violation. Deselect → pure heatmap.
//   2. DARK BASEMAP. protomaps-leaflet flavor: 'dark' (resolved via @protomaps/
//      basemaps namedFlavor — verified against v5.1.0 + basemaps 5.7.2). Still
//      vector, still fetch()/same-origin, no blob/wasm/worker, no new deps → Vex's
//      CSP posture untouched (img-src never engaged; vector draws to canvas).
//   3. CSS FULLSCREEN. Map fills the viewport via position:fixed (.is-fullscreen on
//      the wrap) — iOS-Safari-reliable, because Safari does NOT support the native
//      Fullscreen API for arbitrary DOM elements. Native requestFullscreen is layered
//      on as progressive enhancement on desktop only. invalidateSize() fires after
//      every fullscreen transition so Leaflet re-lays the canvas + reloads tiles.
//
// BASEMAP IS PLUGGABLE: if Mack's germany-z14.pmtiles is absent (probed via
// /api/cockpit/basemap-status), we skip the basemap layer entirely and render the
// routes/glow on the neutral surface background with a quiet "Basemap wird
// vorbereitet" hint. The panel never crashes without the file.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { leafletLayer } from 'protomaps-leaflet';
import { Maximize2, Minimize2 } from 'lucide-react';
import type { Feature, FeatureCollection, LineString } from 'geojson';
import type { HeatFeature, RouteFeature, WorkoutSummary } from '../lib/workoutTypes';
import { S } from '../lib/strings';

// Germany-ish default view (used only until we have geometry to fit to). Centered
// on the country so a basemap-less first paint still shows the right region.
const GERMANY_CENTER: L.LatLngTuple = [51.1, 10.4];
const GERMANY_ZOOM = 6;

// The brass accent + cool selection tint, read from the GL-003 CSS variables at
// runtime so the map stays in lockstep with the token file (never a hardcoded hex).
// Falls back to the documented token values if the variable can't be read
// (SSR-safety; this app is CSR-only, but the guard is cheap).
function tokenColor(varName: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return v || fallback;
}

// ---- PMTiles basemap layer (imperative; protomaps-leaflet has no React wrapper) -
// Defensive by design: if the layer can't be created or added (a styling/flavor
// mismatch in a future protomaps-leaflet, a malformed .pmtiles, etc.), we degrade
// to "no basemap" — the routes/glow still render on the neutral surface — rather
// than throwing and taking down the whole panel. The pluggable-basemap contract
// (Mack's file may be absent) is upstream of this; this catch is the second belt.
function BasemapLayer({ url, flavor }: { url: string; flavor: string }) {
  const map = useMap();
  useEffect(() => {
    // protomaps-leaflet draws VECTOR tiles to a Leaflet canvas overlay — no raster
    // <img> tiles, so the strict img-src 'self' data: CSP is never touched, and the
    // .pmtiles file is fetched same-origin via HTTP Range (connect-src 'self').
    let layer: ReturnType<typeof leafletLayer> | null = null;
    try {
      layer = leafletLayer({
        url,
        // 'dark' resolves through @protomaps/basemaps namedFlavor → dark paint +
        // label rules + a dark background. Pairs with the dark cockpit chrome; the
        // cool selection + warm glow carry the colour on top. If a build ships no
        // matching flavor the layer still renders its default style.
        flavor,
        attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
      });
      (layer as unknown as L.Layer).addTo(map);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('[WorkoutMap] basemap layer failed; rendering routes on neutral background', err);
      layer = null;
    }
    return () => {
      try {
        (layer as unknown as L.Layer | null)?.remove();
      } catch { /* layer already gone */ }
    };
  }, [map, url, flavor]);
  return null;
}

// ---- Ember glow: all/filtered routes as additive low-opacity polylines -------
// Drawn with ONE shared canvas renderer. Low opacity means overlapping tracks
// stack into a brighter "ember" where Tom runs often — Strava-glut, dependency-
// free. v2 (leaflet.heat) can later derive a point cloud from the same data; this
// layer is deliberately forward-compatible (Pax §4).
function GlowLayer({
  collection,
  glowKey,
  renderer,
  color,
}: {
  collection: FeatureCollection<LineString>;
  glowKey: string;
  renderer: L.Canvas;
  color: string;
}) {
  // react-leaflet's <GeoJSON> does NOT react to `data` changes after mount, so we
  // remount on change via `key`. The key must change whenever the underlying set
  // changes — keyed on the FILTER signature (not feature count, which can collide
  // between two different filters that happen to yield the same number of routes).
  return (
    <GeoJSON
      key={glowKey}
      data={collection}
      // Canvas renderer + thin, low-alpha line = additive glow on overlap.
      style={() => ({
        renderer,
        color,
        weight: 2,
        opacity: 0.18,
        interactive: false,
      })}
    />
  );
}

// ---- Highlighted single route ------------------------------------------------
// The selected route in the cool --status-info steel blue. Two visual moves make it
// "pop" against the warm brass glow without inventing a colour:
//   • a colour-matched glow halo via the canvas 2D shadowBlur (GL-003 §6.3 — glow
//     inherits the source colour, never white), drawn as an underlay polyline, and
//   • a brighter, thicker core line on top.
// Start/end markers (small circle markers in the same cool family) anchor the route.
function HighlightLayer({
  feature,
  renderer,
  color,
  glowHalo,
}: {
  feature: RouteFeature;
  renderer: L.Canvas;
  color: string;
  glowHalo: L.Canvas;
}) {
  const data = feature as unknown as Feature<LineString>;
  const coords = feature.geometry.coordinates;
  const start = coords.length ? coords[0] : null;
  const end = coords.length > 1 ? coords[coords.length - 1] : null;
  return (
    <>
      {/* Glow underlay — wide, soft, low-alpha; the dedicated glowHalo renderer
          carries a canvas shadowBlur so this reads as light, not a fat line. The
          renderer rides inside the style callback (react-leaflet's <GeoJSON> takes
          path options there, not as a top-level prop). */}
      <GeoJSON
        key={`hl-glow-${feature.properties.workout_id}`}
        data={data}
        style={() => ({ renderer: glowHalo, color, weight: 7, opacity: 0.28, interactive: false })}
      />
      {/* Core line — bright, crisp, on the shared renderer above the glow. */}
      <GeoJSON
        key={`hl-core-${feature.properties.workout_id}`}
        data={data}
        style={() => ({ renderer, color, weight: 5, opacity: 0.98, interactive: false })}
      />
      {start && (
        <GeoJSON
          key={`hl-start-${feature.properties.workout_id}`}
          data={{ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: start } } as Feature}
          pointToLayer={(_f, latlng) => L.circleMarker(latlng, {
            renderer, radius: 5, color, weight: 2, fillColor: color, fillOpacity: 0.9, interactive: false,
          })}
        />
      )}
      {end && (
        <GeoJSON
          key={`hl-end-${feature.properties.workout_id}`}
          data={{ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: end } } as Feature}
          pointToLayer={(_f, latlng) => L.circleMarker(latlng, {
            renderer, radius: 5, color, weight: 2, fillColor: 'transparent', fillOpacity: 0, interactive: false,
          })}
        />
      )}
    </>
  );
}

// ---- Imperative camera control: fit to the selected route, or to the glow ----
function CameraController({
  selected,
  fallbackBbox,
}: {
  selected: RouteFeature | null;
  fallbackBbox: [number, number, number, number] | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (selected && selected.geometry.coordinates.length > 1) {
      const latlngs = selected.geometry.coordinates.map(([lon, lat]) => [lat, lon] as L.LatLngTuple);
      map.fitBounds(L.latLngBounds(latlngs), { padding: [28, 28], animate: true, maxZoom: 16 });
      return;
    }
    if (fallbackBbox) {
      const [minLon, minLat, maxLon, maxLat] = fallbackBbox;
      map.fitBounds(
        L.latLngBounds([minLat, minLon], [maxLat, maxLon]),
        { padding: [24, 24], animate: false, maxZoom: 13 },
      );
    }
  }, [map, selected, fallbackBbox]);
  return null;
}

// ---- Fullscreen bridge: invalidateSize() after every fullscreen transition ----
// Leaflet caches the container size; a CSS-driven viewport-fill (or a native
// fullscreen) resizes the container out-of-band, so the tile/canvas grid must be
// re-measured or the basemap renders partial/blank. We invalidate on the next two
// frames (one for layout flush, one belt-and-braces after the CSS transition lands).
function FullscreenResizer({ active }: { active: boolean }) {
  const map = useMap();
  useEffect(() => {
    let raf1 = 0;
    let raf2 = 0;
    raf1 = requestAnimationFrame(() => {
      map.invalidateSize({ animate: false });
      raf2 = requestAnimationFrame(() => map.invalidateSize({ animate: false }));
    });
    // A timeout backstop catches the tail of any CSS transition on the wrap.
    const t = window.setTimeout(() => map.invalidateSize({ animate: false }), 260);
    return () => {
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
      window.clearTimeout(t);
    };
  }, [map, active]);
  return null;
}

// Compute an overall bbox for the whole (filtered) set so the map frames Tom's
// routes on first paint even before a single one is selected.
function overallBbox(workouts: WorkoutSummary[]): [number, number, number, number] | null {
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
  for (const w of workouts) {
    if (!w.bbox) continue;
    const [a, b, c, d] = w.bbox;
    if (a < minLon) minLon = a;
    if (b < minLat) minLat = b;
    if (c > maxLon) maxLon = c;
    if (d > maxLat) maxLat = d;
  }
  if (!Number.isFinite(minLon)) return null;
  return [minLon, minLat, maxLon, maxLat];
}

export function WorkoutMap({
  workouts,
  heat,
  selectedRoute,
  basemapPresent,
}: {
  workouts: WorkoutSummary[];
  heat: HeatFeature[];
  selectedRoute: RouteFeature | null;
  basemapPresent: boolean;
}) {
  // One canvas renderer shared by the glow AND the highlight core/markers — the
  // single biggest perf lever for hundreds of lines (Pax §5). A SECOND, dedicated
  // canvas renderer carries the selection glow halo: it gets a shadowBlur applied to
  // its 2D context so the halo reads as light (GL-003 §6.3) without bleeding the
  // shadow onto the 900-line ember layer.
  const rendererRef = useRef<L.Canvas | null>(null);
  if (!rendererRef.current) rendererRef.current = L.canvas({ padding: 0.5 });
  const renderer = rendererRef.current;

  const haloRef = useRef<L.Canvas | null>(null);
  if (!haloRef.current) haloRef.current = L.canvas({ padding: 0.5 });
  const glowHalo = haloRef.current;

  // INKLINE line doctrine (GL-003 §4.2): the route field rests in PAPER (the
  // line is paper at rest); the SELECTED route is the pen — it turns MARKER
  // when it is teaching. This replaces the Graphite brass-glow + cool-blue
  // selection split (the §2.4 de-blue doctrine retires the info-blue accent).
  const brass = useMemo(() => tokenColor('--fg-muted', '#C9C4B8'), []);
  const selectColor = useMemo(() => tokenColor('--accent-marker', '#FF5A2D'), []);

  // Paint a colour-matched shadowBlur onto the halo renderer's 2D context once it
  // exists, so the selection glow halo reads as soft light. Re-applied whenever the
  // halo renderer's canvas is (re)created by Leaflet. Pure additive presentation —
  // no layout, no extra DOM nodes.
  useEffect(() => {
    const ctx = (glowHalo as unknown as { _ctx?: CanvasRenderingContext2D })._ctx;
    if (ctx) {
      ctx.shadowColor = selectColor;
      ctx.shadowBlur = 12;
    }
  }, [glowHalo, selectColor, selectedRoute]);

  const glowCollection = useMemo<FeatureCollection<LineString>>(
    () => ({ type: 'FeatureCollection', features: heat as unknown as Feature<LineString>[] }),
    [heat],
  );
  // Remount key for the glow layer: a cheap signature over the included route ids.
  // Two different filters that yield the same COUNT still differ here (different
  // ids), so the glow never goes stale. Order is server-stable, so join-is-enough.
  const glowKey = useMemo(
    () => `glow-${heat.length}-${heat.length ? heat[0].properties.id : 0}-${heat.length ? heat[heat.length - 1].properties.id : 0}`,
    [heat],
  );
  const fallbackBbox = useMemo(() => overallBbox(workouts), [workouts]);

  const basemapUrl = '/basemap/germany-z14.pmtiles';
  // DARK basemap flavor — pairs with the dark cockpit chrome; the cool selection +
  // warm glow carry the colour. Resolved via @protomaps/basemaps namedFlavor; the
  // layer falls back to a default style if a build ships no matching flavor.
  const basemapFlavor = 'dark';

  // ---- Fullscreen state (CSS-first, native-enhanced) -------------------------
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Native Fullscreen API is progressive enhancement ONLY (desktop). iOS Safari
  // does not support requestFullscreen on arbitrary DOM elements, so the CSS-fixed
  // fill is the reliable path and the source of truth for `isFullscreen`. When the
  // native API IS available, we drive it too so desktop gets a true fullscreen.
  const nativeFullscreenSupported = typeof document !== 'undefined'
    && !!(wrapRef.current?.requestFullscreen) && !!document.fullscreenEnabled;

  const enter = useCallback(() => {
    setIsFullscreen(true);
    const el = wrapRef.current;
    if (el && el.requestFullscreen && document.fullscreenEnabled) {
      // Best-effort; a rejection (e.g. not user-activated) leaves the CSS fill in
      // place, which is the whole point of the CSS-first approach.
      el.requestFullscreen().catch(() => { /* CSS fill carries it */ });
    }
  }, []);

  const exit = useCallback(() => {
    setIsFullscreen(false);
    if (typeof document !== 'undefined' && document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(() => { /* state already reset */ });
    }
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (isFullscreen) exit();
    else enter();
  }, [isFullscreen, enter, exit]);

  // Keep CSS state in sync if the user leaves native fullscreen via Esc / browser UI.
  useEffect(() => {
    if (typeof document === 'undefined') return undefined;
    const onChange = () => {
      if (!document.fullscreenElement && isFullscreen && nativeFullscreenSupported) {
        // Native exited (Esc / browser chrome) → drop the CSS fill too.
        setIsFullscreen(false);
      }
    };
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, [isFullscreen, nativeFullscreenSupported]);

  // Esc exits the CSS fullscreen even where there's no native fullscreen to leave.
  useEffect(() => {
    if (!isFullscreen) return undefined;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') exit(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isFullscreen, exit]);

  return (
    <div
      ref={wrapRef}
      className={`workout-map-wrap${isFullscreen ? ' is-fullscreen' : ''}`}
      data-fullscreen={isFullscreen}
    >
      <MapContainer
        center={GERMANY_CENTER}
        zoom={GERMANY_ZOOM}
        preferCanvas
        scrollWheelZoom
        className="workout-map"
        // When there's no basemap, the container background (token surface) IS the
        // map backdrop — no tiles, just the routes on neutral ground.
        zoomControl
        attributionControl
      >
        {basemapPresent && <BasemapLayer url={basemapUrl} flavor={basemapFlavor} />}
        <GlowLayer collection={glowCollection} glowKey={glowKey} renderer={renderer} color={brass} />
        {selectedRoute && (
          <HighlightLayer
            feature={selectedRoute}
            renderer={renderer}
            glowHalo={glowHalo}
            color={selectColor}
          />
        )}
        <CameraController selected={selectedRoute} fallbackBbox={fallbackBbox} />
        <FullscreenResizer active={isFullscreen} />
      </MapContainer>

      {/* Fullscreen toggle — sits above the Leaflet panes, GL-003-skinned in CSS. */}
      <button
        type="button"
        className="workout-map-fs-btn"
        onClick={toggleFullscreen}
        aria-pressed={isFullscreen}
        aria-label={isFullscreen ? S.workoutMap.exitFullscreen : S.workoutMap.enterFullscreen}
        title={isFullscreen ? S.workoutMap.exitFullscreenTitle : S.workoutMap.fullscreenTitle}
      >
        {isFullscreen
          ? <Minimize2 size={18} strokeWidth={1.5} aria-hidden="true" />
          : <Maximize2 size={18} strokeWidth={1.5} aria-hidden="true" />}
      </button>

      {!basemapPresent && (
        <div className="workout-map-basemap-hint" role="status">
          {S.workoutMap.basemapHint}
        </div>
      )}
    </div>
  );
}
