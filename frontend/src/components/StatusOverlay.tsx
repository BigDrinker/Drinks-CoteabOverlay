import { useEffect, useMemo, useState } from "react";

type OverlayState = {
  status: string; biome: string; last_aura: string; aura_rarity: string; last_merchant: string;
  session: string; transparency: number; width: number; height: number; edit_mode: boolean;
  local_time: string; time_period: string; theme: string; accent: string; font: string;
  show_status: boolean; show_biome: boolean; show_aura: boolean; show_rarity: boolean;
  show_merchant: boolean; show_time: boolean; show_session: boolean;
};

const themeMap: Record<string, { panel: string; panel2: string; border: string; text: string; muted: string; accent: string }> = {
  midnight: { panel: "10,13,24", panel2: "21,25,43", border: "124,139,255", text: "#f5f7ff", muted: "#a4acc2", accent: "#aeb8ff" },
  crimson: { panel: "24,8,13", panel2: "43,13,20", border: "255,91,111", text: "#fff4f6", muted: "#c9a0a8", accent: "#ff7186" },
  emerald: { panel: "7,19,15", panel2: "12,37,28", border: "62,220,150", text: "#f2fff9", muted: "#9ec9b5", accent: "#59e4a6" },
  solar: { panel: "24,17,7", panel2: "44,30,10", border: "242,168,59", text: "#fff9ed", muted: "#cfb98f", accent: "#ffc766" },
  frost: { panel: "7,18,27", panel2: "12,32,48", border: "84,190,255", text: "#f2fbff", muted: "#a4c4d4", accent: "#78d2ff" },
};

export default function StatusOverlay() {
  const [data, setData] = useState<OverlayState>({
    status:"STOPPED", biome:"NORMAL", last_aura:"None", aura_rarity:"Unknown", last_merchant:"None",
    session:"00:00:00", transparency:.08, width:360, height:230, edit_mode:false,
    local_time:"--:--:--", time_period:"DAY", theme:"midnight", accent:"#aeb8ff", font:"Inter",
    show_status:true, show_biome:true, show_aura:true, show_rarity:true, show_merchant:true, show_time:true, show_session:true
  });

  useEffect(() => {
    document.documentElement.style.setProperty("background", "transparent", "important");
    document.body.style.setProperty("background", "transparent", "important");
    document.getElementById("root")?.style.setProperty("background", "transparent", "important");
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
    const refresh = async () => { try { const next = await window.pywebview?.api?.get_overlay_state(); if (next) setData(next); } catch {} };
    refresh(); const id = window.setInterval(refresh, 350); return () => window.clearInterval(id);
  }, []);

  const running = data.status === "RUNNING";
  const palette = themeMap[data.theme] || themeMap.midnight;
  const panelAlpha = Math.max(0.08, Math.min(1, 1 - Number(data.transparency || 0)));
  const accent = data.accent || palette.accent;
  const fontFamily = useMemo(() => ({
    Inter:"Inter, system-ui, sans-serif", Sarpanch:"Sarpanch, Inter, system-ui, sans-serif",
    Orbitron:"Orbitron, Inter, system-ui, sans-serif", Monospace:"Consolas, 'Courier New', monospace",
    Rounded:"'Arial Rounded MT Bold', Arial, sans-serif"
  } as Record<string,string>)[data.font] || "Inter, system-ui, sans-serif", [data.font]);

  const drag = (event: React.MouseEvent) => {
    if (!data.edit_mode || event.button !== 0) return;
    if ((event.target as HTMLElement).closest(".status-overlay-resize-handle, .status-overlay-row, .status-overlay-state")) return;
    window.pywebview?.api?.begin_overlay_drag();
  };
  const resize = (direction:string, event:React.MouseEvent) => {
    if (!data.edit_mode || event.button !== 0) return;
    event.stopPropagation(); window.pywebview?.api?.begin_overlay_resize(direction);
  };
  const style = {
    "--overlay-bg":`rgba(${palette.panel},${panelAlpha})`, "--overlay-bg2":`rgba(${palette.panel2},${panelAlpha})`,
    "--overlay-border":`rgba(${palette.border},.72)`, "--overlay-text":palette.text,
    "--overlay-muted":palette.muted, "--overlay-accent":accent, "--overlay-font":fontFamily,
  } as React.CSSProperties;

  return <div className={`status-overlay ${data.edit_mode ? "editing" : ""}`} style={style} onMouseDown={drag}>
    {data.edit_mode && <div className="status-overlay-edit-label">EDIT MODE · DRAG EMPTY AREA · RESIZE ANY EDGE</div>}
    <div className="status-overlay-scroll">
      <div className="status-overlay-head">
        <span className="status-overlay-title">COTEAB</span>
        {data.show_status && <span className={`status-overlay-state ${running ? "running" : "stopped"}`}><i />{data.status}</span>}
      </div>
      {data.show_biome && <div className="status-overlay-row"><span>Biome</span><strong>{data.biome}</strong></div>}
      {data.show_aura && <div className="status-overlay-row"><span>Last Aura</span><strong title={data.last_aura}>{data.last_aura}</strong></div>}
      {data.show_rarity && <div className="status-overlay-row"><span>Aura Rarity</span><strong title={data.aura_rarity}>{data.aura_rarity}</strong></div>}
      {data.show_merchant && <div className="status-overlay-row"><span>Last Merchant</span><strong title={data.last_merchant}>{data.last_merchant}</strong></div>}
      {data.show_time && <div className="status-overlay-row"><span>Time</span><strong>{data.local_time} · {data.time_period}</strong></div>}
      {data.show_session && <div className="status-overlay-row"><span>Session</span><strong>{data.session}</strong></div>}
    </div>
    {data.edit_mode && <>{(["n","s","e","w","ne","nw","se","sw"] as const).map(dir =>
      <div key={dir} className={`status-overlay-resize-handle resize-${dir}`} onMouseDown={e => resize(dir,e)} />
    )}</>}
  </div>;
}
