import React from "react";
import { rupiah } from "../lib/api";

const STATUS_STYLE = {
  available: "bg-emerald-100 border-emerald-300 text-emerald-800 hover:bg-emerald-200 cursor-pointer",
  booked: "bg-amber-100 border-amber-300 text-amber-800 cursor-not-allowed",
  sold: "bg-slate-200 border-slate-300 text-slate-500 cursor-not-allowed",
};

export function BlockPlan({ units = [], onSelect }) {
  if (!units.length) return null;
  const blocks = {};
  units.forEach((u) => { (blocks[u.block] = blocks[u.block] || []).push(u); });
  const sortedBlocks = Object.keys(blocks).sort();

  return (
    <div data-testid="block-plan" className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-4 mb-4 text-xs">
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm bg-emerald-200 border border-emerald-300" /> Tersedia</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm bg-amber-200 border border-amber-300" /> Dipesan</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm bg-slate-200 border border-slate-300" /> Terjual</span>
      </div>
      <div className="space-y-4">
        {sortedBlocks.map((blk) => (
          <div key={blk}>
            <p className="text-xs font-semibold text-slate-500 mb-1.5">Blok {blk}</p>
            <div className="flex flex-wrap gap-2">
              {blocks[blk]
                .slice()
                .sort((a, b) => String(a.number).localeCompare(String(b.number), undefined, { numeric: true }))
                .map((u) => (
                  <button
                    key={u.id}
                    data-testid={`plot-${u.id}`}
                    onClick={() => u.status === "available" && onSelect?.(u)}
                    disabled={u.status !== "available"}
                    title={`${u.type} · Blok ${u.block}/${u.number} · ${rupiah(u.price)}`}
                    className={`h-14 w-14 rounded-lg border-2 flex flex-col items-center justify-center transition-colors ${STATUS_STYLE[u.status] || STATUS_STYLE.sold}`}>
                    <span className="text-sm font-bold leading-none">{u.number}</span>
                    <span className="text-[9px] mt-0.5 leading-none opacity-80">{u.building_area}m²</span>
                  </button>
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
