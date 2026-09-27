import React, { useState } from "react";
import { ZoomableImage } from "./ZoomableImage";
import { mediaUrl } from "../lib/api";
import { ChevronLeft, ChevronRight } from "lucide-react";

export function UnitGallery({ images = [], fallback, alt = "Foto", label = "Galeri" }) {
  const list = (images || []).filter(Boolean);
  const slides = list.length ? list : (fallback ? [fallback] : []);
  const [idx, setIdx] = useState(0);
  if (!slides.length) return null;

  const clamp = (i) => (i + slides.length) % slides.length;
  const go = (d) => setIdx((i) => clamp(i + d));

  return (
    <div data-testid="unit-gallery">
      <div className="relative">
        <ZoomableImage src={slides[idx]} alt={`${alt} ${idx + 1}`} label={`${label} ${idx + 1}/${slides.length}`}
          testid="gallery-main" className="h-56 rounded-xl border border-slate-200" />
        {slides.length > 1 && (
          <>
            <button type="button" onClick={(e) => { e.stopPropagation(); go(-1); }} data-testid="gallery-prev"
              className="absolute left-2 top-1/2 -translate-y-1/2 h-9 w-9 grid place-items-center rounded-full bg-white/85 hover:bg-white shadow-md text-slate-700 transition-colors">
              <ChevronLeft className="h-5 w-5" />
            </button>
            <button type="button" onClick={(e) => { e.stopPropagation(); go(1); }} data-testid="gallery-next"
              className="absolute right-2 top-1/2 -translate-y-1/2 h-9 w-9 grid place-items-center rounded-full bg-white/85 hover:bg-white shadow-md text-slate-700 transition-colors">
              <ChevronRight className="h-5 w-5" />
            </button>
            <span className="absolute bottom-2 right-2 text-xs font-medium text-white bg-black/55 rounded-full px-2 py-0.5">
              {idx + 1} / {slides.length}
            </span>
          </>
        )}
      </div>
      {slides.length > 1 && (
        <div className="mt-2 flex gap-2 overflow-x-auto pb-1 snap-x">
          {slides.map((s, i) => (
            <button key={i} type="button" onClick={() => setIdx(i)} data-testid={`gallery-thumb-${i}`}
              className={`snap-start shrink-0 h-14 w-20 rounded-lg overflow-hidden border-2 transition-colors ${i === idx ? "border-[hsl(var(--primary))]" : "border-transparent opacity-70 hover:opacity-100"}`}>
              <img src={mediaUrl(s)} alt={`thumb ${i + 1}`} className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
