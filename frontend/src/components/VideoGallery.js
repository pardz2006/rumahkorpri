import React from "react";
import { PlayCircle } from "lucide-react";

function youTubeId(url) {
  const m = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})/);
  return m ? m[1] : null;
}

export function VideoGallery({ videos = [] }) {
  const list = (videos || []).filter(Boolean);
  if (!list.length) return null;
  return (
    <div data-testid="video-gallery">
      <p className="text-xs text-slate-500 mb-1.5 flex items-center gap-1"><PlayCircle className="h-3.5 w-3.5" /> Video Walkthrough</p>
      <div className="grid grid-cols-1 gap-3">
        {list.map((v, i) => {
          const yt = youTubeId(v);
          return (
            <div key={i} data-testid={`video-${i}`} className="rounded-xl overflow-hidden border border-slate-200 bg-black aspect-video">
              {yt ? (
                <iframe
                  className="w-full h-full"
                  src={`https://www.youtube.com/embed/${yt}`}
                  title={`Video ${i + 1}`}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              ) : (
                <video className="w-full h-full" src={v} controls preload="metadata" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
