import React, { useState, useRef, useCallback, useEffect } from "react";
import { Dialog, DialogContent } from "./ui/dialog";
import { ZoomIn, ZoomOut, X, RotateCcw } from "lucide-react";
import { mediaUrl } from "../lib/api";

const MIN_SCALE = 1;
const MAX_SCALE = 6;

export function ZoomableImage({ src, alt, label, className, testid, fit = "cover" }) {
  const [open, setOpen] = useState(false);
  const [scale, setScale] = useState(1);
  const [dragging, setDragging] = useState(false);
  const [baseSize, setBaseSize] = useState(null);
  const viewRef = useRef(null);
  const imgRef = useRef(null);
  const scaleRef = useRef(1);
  const dragRef = useRef(null);
  const pendingAnchor = useRef(null);

  const resolved = mediaUrl(src);

  const computeBase = useCallback(() => {
    const c = viewRef.current;
    const img = imgRef.current;
    if (!c || !img || !img.naturalWidth) return null;
    const cw = c.clientWidth, ch = c.clientHeight;
    const ir = img.naturalWidth / img.naturalHeight;
    let w = cw, h = cw / ir;
    if (h > ch) { h = ch; w = ch * ir; }
    return { w, h };
  }, []);

  const centerScroll = useCallback(() => {
    const c = viewRef.current;
    if (!c) return;
    c.scrollLeft = (c.scrollWidth - c.clientWidth) / 2;
    c.scrollTop = (c.scrollHeight - c.clientHeight) / 2;
  }, []);

  // Zoom dengan mempertahankan titik di bawah kursor (default: tengah)
  const zoomTo = useCallback((next, ev) => {
    const c = viewRef.current;
    const s = Math.min(Math.max(next, MIN_SCALE), MAX_SCALE);
    if (c && s !== scaleRef.current) {
      const rect = c.getBoundingClientRect();
      const ax = ev && ev.clientX != null ? ev.clientX - rect.left : c.clientWidth / 2;
      const ay = ev && ev.clientY != null ? ev.clientY - rect.top : c.clientHeight / 2;
      pendingAnchor.current = c.scrollWidth > 0
        ? { ax, ay, rx: (c.scrollLeft + ax) / c.scrollWidth, ry: (c.scrollTop + ay) / c.scrollHeight }
        : null;
    }
    scaleRef.current = s;
    setScale(s);
  }, []);

  const reset = useCallback(() => { pendingAnchor.current = null; scaleRef.current = 1; setScale(1); }, []);
  const openLightbox = () => { reset(); setOpen(true); };

  // Hitung ulang ukuran dasar saat dibuka / resize
  useEffect(() => {
    if (!open) return;
    const update = () => setBaseSize(computeBase());
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [open, computeBase]);

  // Terapkan posisi scroll setelah skala/ukuran berubah
  useEffect(() => {
    const c = viewRef.current;
    if (!open || !c) return;
    const a = pendingAnchor.current;
    pendingAnchor.current = null;
    if (a && scale > 1) {
      c.scrollLeft = a.rx * c.scrollWidth - a.ax;
      c.scrollTop = a.ry * c.scrollHeight - a.ay;
    } else {
      centerScroll();
    }
  }, [scale, baseSize, open, centerScroll]);

  // Wheel zoom + pinch zoom: listener native (React memasang listener passive)
  useEffect(() => {
    const el = viewRef.current;
    if (!open || !el) return;
    let pinch = null;
    const onWheel = (e) => {
      e.preventDefault();
      zoomTo(scaleRef.current + (e.deltaY < 0 ? 0.3 : -0.3), e);
    };
    const onTs = (e) => {
      if (e.touches.length === 2) {
        const [a, b] = e.touches;
        pinch = { d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), s: scaleRef.current };
      }
    };
    const onTm = (e) => {
      if (e.touches.length === 2 && pinch && pinch.d > 0) {
        e.preventDefault();
        const [a, b] = e.touches;
        const d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
        zoomTo((pinch.s * d) / pinch.d, { clientX: (a.clientX + b.clientX) / 2, clientY: (a.clientY + b.clientY) / 2 });
      }
    };
    const onTe = () => { pinch = null; };
    el.addEventListener("wheel", onWheel, { passive: false });
    el.addEventListener("touchstart", onTs, { passive: true });
    el.addEventListener("touchmove", onTm, { passive: false });
    el.addEventListener("touchend", onTe);
    return () => {
      el.removeEventListener("wheel", onWheel);
      el.removeEventListener("touchstart", onTs);
      el.removeEventListener("touchmove", onTm);
      el.removeEventListener("touchend", onTe);
    };
  }, [open, zoomTo]);

  // Drag mouse untuk menggeser (scroll) — dilacak di window agar tidak terputus
  useEffect(() => {
    if (!dragging) return;
    const mm = (e) => {
      const c = viewRef.current;
      const d = dragRef.current;
      if (!c || !d) return;
      c.scrollLeft = d.sl - (e.clientX - d.x);
      c.scrollTop = d.st - (e.clientY - d.y);
    };
    const mu = () => { dragRef.current = null; setDragging(false); };
    window.addEventListener("mousemove", mm);
    window.addEventListener("mouseup", mu);
    return () => { window.removeEventListener("mousemove", mm); window.removeEventListener("mouseup", mu); };
  }, [dragging]);

  const onMouseDown = (e) => {
    const c = viewRef.current;
    if (!c || scaleRef.current <= 1) return;
    e.preventDefault();
    dragRef.current = { x: e.clientX, y: e.clientY, sl: c.scrollLeft, st: c.scrollTop };
    setDragging(true);
  };

  const imgStyle = baseSize
    ? { width: baseSize.w * scale, height: baseSize.h * scale, maxWidth: "none", maxHeight: "none" }
    : { maxWidth: "100%", maxHeight: "100%" };

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
            className="relative h-[85vh] w-full overflow-auto select-none [touch-action:pan-x_pan-y]"
            onMouseDown={onMouseDown}
            onDoubleClick={(e) => zoomTo(scaleRef.current === 1 ? 2.5 : 1, e)}
            style={{ cursor: scale > 1 ? (dragging ? "grabbing" : "grab") : "zoom-in" }}>
            <div className="w-max min-w-full min-h-full grid place-items-center">
              <img ref={imgRef} src={resolved} alt={alt} draggable={false}
                onLoad={() => setBaseSize(computeBase())}
                className="object-contain" style={imgStyle} />
            </div>
          </div>
          <span className="absolute top-12 left-1/2 -translate-x-1/2 z-10 text-[11px] text-white/90 bg-black/50 rounded-full px-3 py-1 pointer-events-none">
            Scroll / klik 2x / cubit untuk zoom{scale > 1 ? " · seret atau geser scrollbar untuk memindahkan" : ""}
          </span>
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1.5 bg-black/60 backdrop-blur rounded-full px-2 py-1.5">
            <button onClick={() => zoomTo(scaleRef.current - 0.5)} data-testid="zoom-out-btn" className="h-9 w-9 grid place-items-center rounded-full text-white hover:bg-white/15 transition-colors"><ZoomOut className="h-5 w-5" /></button>
            <span className="text-white text-xs font-medium tabular-nums w-12 text-center">{Math.round(scale * 100)}%</span>
            <button onClick={() => zoomTo(scaleRef.current + 0.5)} data-testid="zoom-in-btn" className="h-9 w-9 grid place-items-center rounded-full text-white hover:bg-white/15 transition-colors"><ZoomIn className="h-5 w-5" /></button>
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
