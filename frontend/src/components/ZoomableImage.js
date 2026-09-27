import React, { useState, useRef, useCallback, useEffect } from "react";
import { Dialog, DialogContent } from "./ui/dialog";
import { ZoomIn, ZoomOut, X, RotateCcw } from "lucide-react";
import { mediaUrl } from "../lib/api";

const MIN_SCALE = 1;
const MAX_SCALE = 6;

export function ZoomableImage({ src, alt, label, className, testid, fit = "cover" }) {
  const [open, setOpen] = useState(false);
  const [scale, setScale] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const viewRef = useRef(null);
  const imgRef = useRef(null);
  const drag = useRef(null);
  const pinch = useRef(null);
  const scaleRef = useRef(1);
  const posRef = useRef({ x: 0, y: 0 });

  // Batasi geser agar gambar tidak hilang keluar area
  const clampPos = useCallback((p, s) => {
    const c = viewRef.current;
    const img = imgRef.current;
    if (!c || !img || !img.naturalWidth) return p;
    const cw = c.clientWidth, ch = c.clientHeight;
    const ir = img.naturalWidth / img.naturalHeight;
    let bw = cw, bh = cw / ir;
    if (bh > ch) { bh = ch; bw = ch * ir; }
    const mx = Math.max(0, (bw * s - cw) / 2);
    const my = Math.max(0, (bh * s - ch) / 2);
    return { x: Math.min(Math.max(p.x, -mx), mx), y: Math.min(Math.max(p.y, -my), my) };
  }, []);

  const setView = useCallback((s, p) => {
    s = Math.min(Math.max(s, MIN_SCALE), MAX_SCALE);
    p = s === 1 ? { x: 0, y: 0 } : clampPos(p, s);
    scaleRef.current = s;
    posRef.current = p;
    setScale(s);
    setPos(p);
  }, [clampPos]);

  const reset = useCallback(() => setView(1, { x: 0, y: 0 }), [setView]);
  const openLightbox = () => { reset(); setOpen(true); };
  const zoomIn = () => setView(scaleRef.current + 0.5, posRef.current);
  const zoomOut = () => setView(scaleRef.current - 0.5, posRef.current);

  // Wheel zoom: React memasang listener wheel sebagai passive, jadi pasang native non-passive
  useEffect(() => {
    const el = viewRef.current;
    if (!open || !el) return;
    const onWheel = (e) => {
      e.preventDefault();
      setView(scaleRef.current + (e.deltaY < 0 ? 0.3 : -0.3), posRef.current);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [open, setView]);

  // Geser dengan mouse: dengarkan di window agar drag cepat tidak terputus
  useEffect(() => {
    if (!dragging) return;
    const mm = (e) => {
      if (!drag.current) return;
      setView(scaleRef.current, { x: e.clientX - drag.current.x, y: e.clientY - drag.current.y });
    };
    const mu = () => { drag.current = null; setDragging(false); };
    window.addEventListener("mousemove", mm);
    window.addEventListener("mouseup", mu);
    return () => { window.removeEventListener("mousemove", mm); window.removeEventListener("mouseup", mu); };
  }, [dragging, setView]);

  const onDown = (e) => {
    if (e.touches && e.touches.length === 2) {
      const [a, b] = e.touches;
      pinch.current = { d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), s: scaleRef.current };
      drag.current = null;
      return;
    }
    if (scaleRef.current <= 1) return;
    const t = e.touches ? e.touches[0] : e;
    drag.current = { x: t.clientX - posRef.current.x, y: t.clientY - posRef.current.y };
    setDragging(true);
  };
  const onMove = (e) => {
    if (e.touches && e.touches.length === 2 && pinch.current) {
      const [a, b] = e.touches;
      const d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      if (pinch.current.d > 0) setView((pinch.current.s * d) / pinch.current.d, posRef.current);
      return;
    }
    if (e.touches && drag.current) {
      const t = e.touches[0];
      setView(scaleRef.current, { x: t.clientX - drag.current.x, y: t.clientY - drag.current.y });
    }
  };
  const onUp = () => { drag.current = null; pinch.current = null; setDragging(false); };

  const resolved = mediaUrl(src);

  return (
    <>
      <button type="button" onClick={openLightbox} data-testid={testid}
        className={`group relative block w-full overflow-hidden ${className || ""}`}>
        <img src={resolved} alt={alt}
          className={`w-full h-full transition-transform duration-300 group-hover:scale-105 ${fit === "contain" ? "object-contain bg-slate-50" : "object-cover"}`} />
        <span className="absolute inset-0 bg-black/0 group-hover:bg-black/25 transition-colors flex items-center justify-center">
          <span className="opacity-0 group-hover:opacity-100 transition-opacity h-9 w-9 rounded-full bg-white/90 grid place-items-center shadow-lg">
            <ZoomIn className="h-4 w-4 text-slate-700" />
          </span>
        </span>
      </button>

      <Dialog open={open} onOpenChange={(o) => { if (!o) reset(); setOpen(o); }}>
        <DialogContent
          className="max-w-6xl w-[95vw] p-0 bg-slate-900 border-slate-700 overflow-hidden [&>button]:hidden"
          data-testid={testid ? `${testid}-lightbox` : "zoom-lightbox"}>
          {label && (
            <div className="absolute top-0 left-0 right-0 z-10 px-4 py-3 bg-gradient-to-b from-black/70 to-transparent text-white text-sm font-medium pointer-events-none">
              {label}
            </div>
          )}
          <div
            ref={viewRef}
            className="relative h-[85vh] w-full overflow-hidden grid place-items-center select-none touch-none"
            onMouseDown={onDown}
            onTouchStart={onDown} onTouchMove={onMove} onTouchEnd={onUp}
            onDoubleClick={() => setView(scaleRef.current === 1 ? 2.5 : 1, posRef.current)}
            style={{ cursor: scale > 1 ? (dragging ? "grabbing" : "grab") : "zoom-in" }}>
            <img ref={imgRef} src={resolved} alt={alt} draggable={false}
              className="max-h-full max-w-full object-contain"
              style={{ transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})`, transition: dragging ? "none" : "transform 150ms ease-out" }} />
          </div>
          <span className="absolute top-12 left-1/2 -translate-x-1/2 z-10 text-[11px] text-white/90 bg-black/50 rounded-full px-3 py-1 pointer-events-none">
            Scroll / klik 2x / cubit untuk zoom{scale > 1 ? " · seret untuk menggeser" : ""}
          </span>
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1.5 bg-black/60 backdrop-blur rounded-full px-2 py-1.5">
            <button onClick={zoomOut} data-testid="zoom-out-btn" className="h-9 w-9 grid place-items-center rounded-full text-white hover:bg-white/15 transition-colors"><ZoomOut className="h-5 w-5" /></button>
            <span className="text-white text-xs font-medium tabular-nums w-12 text-center">{Math.round(scale * 100)}%</span>
            <button onClick={zoomIn} data-testid="zoom-in-btn" className="h-9 w-9 grid place-items-center rounded-full text-white hover:bg-white/15 transition-colors"><ZoomIn className="h-5 w-5" /></button>
            <button onClick={reset} data-testid="zoom-reset-btn" className="h-9 w-9 grid place-items-center rounded-full text-white hover:bg-white/15 transition-colors"><RotateCcw className="h-4 w-4" /></button>
          </div>
          <button onClick={() => { reset(); setOpen(false); }} data-testid="zoom-close-btn"
            className="absolute top-3 right-3 z-10 h-9 w-9 grid place-items-center rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </DialogContent>
      </Dialog>
    </>
  );
}
