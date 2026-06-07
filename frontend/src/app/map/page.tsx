"use client";
import dynamic from "next/dynamic";

const MapView = dynamic(() => import("@/components/map-view"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-[#060d1a]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-teal-400/40 border-t-teal-400 rounded-full animate-spin" />
        <span className="text-xs text-white/30 tracking-wider">Loading global map…</span>
      </div>
    </div>
  ),
});

/* Break out of the layout's p-6 padding so the map fills edge-to-edge */
export default function MapPage() {
  return (
    <div className="-m-6 h-[calc(100%+3rem)]">
      <MapView />
    </div>
  );
}
