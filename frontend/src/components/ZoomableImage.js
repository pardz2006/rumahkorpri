import React, { useState, useRef, useCallback } from "react";
import { Dialog, DialogContent } from "./ui/dialog";
import { ZoomIn, ZoomOut, X, RotateCcw } from "lucide-react";
import { mediaUrl } from "../lib/api";

export function ZoomableImage({ src, alt, label, className, testid }) {
  const [open, setOpen] = useState(false);
  const [scale, setScale] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const drag = useRef(null);

  const reset = useCallback(() => { setScale(1); setPos({ x: 0, y: 0 }); }, []);
  const openLightbox = () => { reset(); setOpen(true); };
  const zoomIn = () => setScale((s) => Math.min(s + 0.5, 5));
  const zoomOut = () => setScale((s) => { const n = Math.max(s - 0.5, 1); if (n === 1) setPos({ x: 0, y: 0 }); return n; });

  const onWheel = (e) => {
    e.preventDefault();
    setScale((s) => { const n = Math.min(Math.max(s + (e.deltaY < 0 ? 0.3 : -0.3), 1), 5); if (n === 1) setPos({ x: 0, y: 0 }); return n; });
  };
  const onDown = (e) => { if (scale <= 1) return; const t = e.touches ? e.touches[0] : e; drag.current = { x: t.clientX - pos.x, y: t.clientY - pos.y }; };
  const onMove = (e) => { if (!drag.current) return; const t = e.touches ? e.touches[0] : e; setPos({ x: t.clientX - drag.current.x, y: t.clientY - drag.current.y }); };
  const onUp = () => { drag.current = null; };

  const resolved = mediaUrl(src);

  return (
    <>
      <button type="button" onClick={openLightbox} data-testid={testid}
        className={`group relative block w-full overflow-hidden ${className || ""}`}>
        <img src={resolved} alt={alt} className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" />
        <span className="absolute inset-0 bg-black/0 group-hover:bg-black/25 transition-colors flex items-center justify-center">
          <span className="opacity-0 group-hover:opacity-100 transition-opacity h-9 w-9 rounded-full bg-white/90 grid place-items-center shadow-lg">
            <ZoomIn className="h-4.5 w-4.5 text-slate-700" />
          </span>
        </span>
      </button>

      <Dialog open={open} onOpenChange={(o) => { if (!o) reset(); setOpen(o); }}>
        <DialogContent
          className="max-w-5xl w-[95vw] p-0 bg-slate-900 border-slate-700 overflow-hidden [&>button]:hidden"
          data-testid={testid ? `${testid}-lightbox` : "zoom-lightbox"}>
          {label && (
            <div className="absolute top-0 left-0 right-0 z-10 px-4 py-3 bg-gradient-to-b from-black/70 to-transparent text-white text-sm font-medium">
              {label}
            </div>
          )}
          <div
            className="relative h-[80vh] w-full overflow-hidden grid place-items-center select-none"
            onWheel={onWheel} onMouseDown={onDown} onMouseMove={onMove} onMouseUp={onUp} onMouseLeave={onUp}
            onTouchStart={onDown} onTouchMove={onMove} onTouchEnd={onUp}
            style={{ cursor: scale > 1 ? (drag.current ? "grabbing" : "grab") : "zoom-in" }}
            onClick={() => { if (scale === 1) zoomIn(); }}>
            <img src={resolved} alt={alt} draggable={false}
              className="max-h-full max-w-full object-contain transition-transform duration-150"
              style={{ transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})` }} />
          </div>
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1.5 bg-black/60 backdrop-blur rounded-full px-2 py-1.5">
            <button onClick={zoomOut} data-testid="zoom-out-btn" className="h-9 w-9 grid place-items-center rounded-full text-white hover:bg-white/15 transition-colors"><ZoomOut className="h-5 w-5" /></button>
            <span className="text-white text-xs font-medium tabular-nums w-12 text-center">{Math.round(scale * 100)}%</span>
            <button onClick={zoomIn} data-testid="zoom-in-btn" className="h-9 w-9 grid place-items-center rounded-full text-white hover:bg-white/15 transition-colors"><ZoomIn className="h-5 w-5" /></button>
            <button onClick={reset} data-testid="zoom-reset-btn" className="h-9 w-9 grid place-items-center rounded-full text-white hover:bg-white/15 transition-colors"><RotateCcw className="h-4.5 w-4.5" /></button>
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
