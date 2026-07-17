import { useEffect, useState } from "react";
import { useConfig } from "../contexts/ConfigContext";
import ToggleSwitch from "../components/ToggleSwitch";

export default function OtherFeaturesPage() {
    const { config, saveConfig, error } = useConfig();
    const [overlay, setOverlay] = useState<any>(null);
    const [transparencyDraft, setTransparencyDraft] = useState(35);

    useEffect(() => {
        let active = true;
        window.pywebview?.api?.get_native_overlay_settings?.().then((settings: any) => {
            if (!active) return;
            setOverlay(settings);
            setTransparencyDraft(Math.round((settings?.background_transparency ?? 0.35) * 100));
        });
        return () => { active = false; };
    }, []);


    if (error) return <div style={{ padding: "20px", color: "red" }}>Error: {error}</div>;
    if (!config) return <div style={{ padding: "20px" }}>Loading...</div>;

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    const applyOverlayPatch = async (patch: Record<string, any>) => {
        const result = await window.pywebview?.api?.update_native_overlay_settings?.(patch);
        if (result?.success) {
            setOverlay(result.settings);
            setTransparencyDraft(Math.round((result.settings?.background_transparency ?? 0.35) * 100));
        } else if (result) {
            console.error("Overlay 2.0 setting failed:", result.error);
        }
        return result;
    };

    const rowLabels: Record<string,string> = {biome:"Biome",aura:"Last Aura",rarity:"Aura Rarity",merchant:"Last Merchant",merchant_time:"Time Since Merchant",time:"Local Time",session:"Session",biome_count:"Biome Changes",merchant_count:"Merchant Count"};
    const moveRow = (index:number, direction:number) => {
        const order=[...(overlay?.row_order || Object.keys(rowLabels))];
        const target=index+direction;
        if(target<0 || target>=order.length) return;
        [order[index],order[target]]=[order[target],order[index]];
        applyOverlayPatch({row_order:order,profile:"custom"});
    };


    return (
        <>
            <div className="page-header">
                <h2>Other Features</h2>
                <p>Additional macro capabilities and experimental options</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">⚡</div>
                    <div>
                        <h3>Rare Biome Actions</h3>
                        <p>Actions to take when a rare biome is detected</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Enable buff when Glitched/Dreamspace"
                    description="ONLY use this feature when you have your buffs DISABLED while hunting for Glitched/Dreamspace"
                    checked={config.enable_buff_glitched || false}
                    onChange={(val) => updateConfig("enable_buff_glitched", val)}
                />

                <ToggleSwitch
                    label="Reset character when there's a rare biome"
                    description="Reset character to Sol's Main Island during GLITCHED/DREAMSPACE/CYBERSPACE"
                    checked={config.reset_on_rare || false}
                    onChange={(val) => updateConfig("reset_on_rare", val)}
                />

                <ToggleSwitch
                    label="Teleport back to Limbo when rare biome ends"
                    description="Return to limbo automatically when rare biome ended"
                    checked={config.teleport_back_to_limbo || false}
                    onChange={(val) => updateConfig("teleport_back_to_limbo", val)}
                />
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">◈</div>
                    <div>
                        <h3>Overlay 2.0</h3>
                        <p>A clean control panel built only for the native overlay</p>
                    </div>
                </div>

                {!overlay ? <div style={{padding:'20px'}}>Loading overlay settings...</div> : <>
                    <div style={{padding:'8px 20px 4px',fontWeight:700,color:'var(--text-bright)'}}>General</div>
                    <div className="setting-row" style={{padding:'12px 20px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:'15px'}}>
                        <div><div style={{fontWeight:600,color:'var(--text-bright)'}}>Profile</div><div style={{fontSize:'.85rem',color:'var(--text-muted)'}}>Quick layouts for AFK, streaming, minimal, or full data</div></div>
                        <select className="form-input" style={{width:'180px'}} value={overlay.profile || 'custom'} onChange={async e=>{const r=await window.pywebview?.api?.apply_native_overlay_profile?.(e.target.value);if(r?.success){setOverlay(r.settings);setTransparencyDraft(Math.round(r.settings.background_transparency*100));}}}>
                            <option value="custom">Custom</option><option value="minimal">Minimal</option><option value="afk">AFK</option><option value="streaming">Streaming</option><option value="full">Full</option>
                        </select>
                    </div>
                    <ToggleSwitch label="Enable overlay" description="Show the native overlay above Roblox" checked={!!overlay.enabled} onChange={v=>applyOverlayPatch({enabled:v})}/>
                    <div className="setting-row" style={{padding:'12px 20px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:'15px'}}>
                        <div><div style={{fontWeight:600,color:'var(--text-bright)'}}>Layout</div><div style={{fontSize:'.85rem',color:'var(--text-muted)'}}>Compact shows the first four enabled rows</div></div>
                        <select className="form-input" style={{width:'180px'}} value={overlay.layout} onChange={e=>applyOverlayPatch({layout:e.target.value})}><option value="expanded">Expanded</option><option value="compact">Compact</option></select>
                    </div>
                    <div className="setting-row" style={{padding:'12px 20px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:'15px'}}>
                        <div><div style={{fontWeight:600,color:'var(--text-bright)'}}>Position</div><div style={{fontSize:'.85rem',color:'var(--text-muted)'}}>Custom uses the position you dragged it to</div></div>
                        <select className="form-input" style={{width:'180px'}} value={overlay.position} onChange={e=>applyOverlayPatch({position:e.target.value})}><option value="top-right">Top Right</option><option value="bottom-right">Bottom Right</option><option value="custom">Custom</option></select>
                    </div>

                    <div style={{padding:'18px 20px 4px',fontWeight:700,color:'var(--text-bright)'}}>Appearance</div>
                    <div className="setting-row" style={{padding:'12px 20px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:'15px'}}>
                        <div><div style={{fontWeight:600,color:'var(--text-bright)'}}>Background Transparency</div><div style={{fontSize:'.85rem',color:'var(--text-muted)'}}>Only the panel fades; text remains opaque</div></div>
                        <div style={{display:'flex',alignItems:'center',gap:'10px',width:'260px'}}><input type="range" min="0" max="90" value={transparencyDraft} onChange={e=>setTransparencyDraft(Number(e.target.value))} onPointerUp={()=>applyOverlayPatch({background_transparency:transparencyDraft/100})} onKeyUp={()=>applyOverlayPatch({background_transparency:transparencyDraft/100})} style={{flex:1}}/><span style={{minWidth:'42px',textAlign:'right'}}>{transparencyDraft}%</span></div>
                    </div>
                    <div className="setting-row" style={{padding:'12px 20px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:'15px'}}>
                        <div><div style={{fontWeight:600,color:'var(--text-bright)'}}>Theme</div><div style={{fontSize:'.85rem',color:'var(--text-muted)'}}>Complete panel color preset</div></div>
                        <select className="form-input" style={{width:'180px'}} value={overlay.theme} onChange={e=>applyOverlayPatch({theme:e.target.value})}>{['midnight','ocean','crimson','emerald','solar','frost','amoled','glass','neon','discord','spotify'].map(x=><option key={x} value={x}>{x.charAt(0).toUpperCase()+x.slice(1)}</option>)}</select>
                    </div>
                    <div className="setting-row" style={{padding:'12px 20px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:'15px'}}>
                        <div><div style={{fontWeight:600,color:'var(--text-bright)'}}>Accent</div><div style={{fontSize:'.85rem',color:'var(--text-muted)'}}>Title and border color</div></div>
                        <div style={{display:'flex',gap:'10px',alignItems:'center'}}><input type="color" value={overlay.accent} onChange={e=>applyOverlayPatch({accent:e.target.value})}/><input className="form-input" style={{width:'110px'}} value={overlay.accent} onChange={e=>setOverlay({...overlay,accent:e.target.value})} onBlur={e=>applyOverlayPatch({accent:e.target.value})}/></div>
                    </div>
                    <div className="setting-row" style={{padding:'12px 20px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:'15px'}}>
                        <div><div style={{fontWeight:600,color:'var(--text-bright)'}}>Font</div><div style={{fontSize:'.85rem',color:'var(--text-muted)'}}>Uses installed Windows fonts when available</div></div>
                        <select className="form-input" style={{width:'180px'}} value={overlay.font} onChange={e=>applyOverlayPatch({font:e.target.value})}>{['Inter','Orbitron','JetBrains Mono','Sarpanch','Exo 2','Poppins','Rounded'].map(x=><option key={x}>{x}</option>)}</select>
                    </div>

                    <div style={{padding:'18px 20px 4px',fontWeight:700,color:'var(--text-bright)'}}>Overlay Data</div>
                    {[
                        ['status','Status','Running or stopped'],['biome','Biome','Current detected biome'],['aura','Last Aura','Most recent accepted aura'],['rarity','Aura Rarity','Accepted aura rarity'],['merchant','Merchant','Most recently detected merchant'],['merchant_time','Time Since Merchant','Elapsed time after detection'],['time','Time / Day-Night','Local clock and period'],['session','Session','Macro session duration'],['biome_count','Biome Changes','Changes observed this overlay session'],['merchant_count','Merchant Count','Merchants observed this overlay session']
                    ].map(([key,label,description])=><ToggleSwitch key={key} label={label} description={description} checked={overlay.show?.[key] !== false} onChange={v=>applyOverlayPatch({show:{[key]:v},profile:'custom'})}/>) }

                    <div style={{padding:'18px 20px 4px',fontWeight:700,color:'var(--text-bright)'}}>Row Order</div>
                    <div style={{padding:'10px 20px 16px',display:'grid',gap:'7px'}}>
                        {(overlay.row_order || Object.keys(rowLabels)).map((key:string,index:number)=><div key={key} style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'8px 10px',border:'1px solid var(--border)',borderRadius:'6px',background:'var(--bg-input)'}}><span>{rowLabels[key] || key}</span><div style={{display:'flex',gap:'6px'}}><button className="btn" disabled={index===0} onClick={()=>moveRow(index,-1)}>↑</button><button className="btn" disabled={index===(overlay.row_order || Object.keys(rowLabels)).length-1} onClick={()=>moveRow(index,1)}>↓</button></div></div>)}
                    </div>

                    <div style={{padding:'18px 20px 4px',fontWeight:700,color:'var(--text-bright)'}}>Detection Notifications</div>
                    {['biome','aura','merchant'].map(key=><ToggleSwitch key={key} label={`${rowLabels[key]} notification`} description={`Show a short overlay alert when ${rowLabels[key].toLowerCase()} changes`} checked={overlay.notifications?.[key] !== false} onChange={v=>applyOverlayPatch({notifications:{[key]:v}})}/>)}

                    <div style={{padding:'18px 20px 4px',fontWeight:700,color:'var(--text-bright)'}}>Aura</div>
                    <div className="setting-row" style={{padding:'12px 20px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:'15px'}}>
                        <div><div style={{fontWeight:600,color:'var(--text-bright)'}}>Minimum Aura Rarity</div><div style={{fontSize:'.85rem',color:'var(--text-muted)'}}>Accepts any value up to 10,000,000,000</div></div>
                        <div style={{display:'flex',alignItems:'center',gap:'8px'}}><span>1 in</span><input className="form-input" inputMode="numeric" style={{width:'180px'}} value={String(overlay.minimum_rarity)} onChange={e=>setOverlay({...overlay,minimum_rarity:e.target.value.replace(/[^0-9]/g,'')})} onBlur={e=>applyOverlayPatch({minimum_rarity:Math.min(10000000000,Math.max(1,Number(e.target.value)||1))})}/></div>
                    </div>

                    <div style={{padding:'18px 20px 4px',fontWeight:700,color:'var(--text-bright)'}}>Advanced</div>
                    <ToggleSwitch label="Always on top" description="Keep the overlay above other windows" checked={overlay.always_on_top !== false} onChange={v=>applyOverlayPatch({always_on_top:v})}/>
                    <ToggleSwitch label="Click-through" description="Ignore mouse clicks when you are not editing it" checked={!!overlay.click_through} onChange={v=>applyOverlayPatch({click_through:v})}/>
                    <ToggleSwitch label="Scrollable" description="Allow wheel scrolling when content exceeds the panel" checked={overlay.scrollable !== false} onChange={v=>applyOverlayPatch({scrollable:v})}/>
                    <ToggleSwitch label="Remember position" description="Save the exact dragged position and resized dimensions" checked={overlay.remember_position !== false} onChange={v=>applyOverlayPatch({remember_position:v})}/>

                    <div className="setting-row" style={{padding:'16px 20px 20px',display:'flex',justifyContent:'flex-end',gap:'10px',flexWrap:'wrap'}}>
                        <button className="btn" onClick={()=>applyOverlayPatch({position:'top-right'})}>Snap Top Right</button>
                        <button className="btn" onClick={()=>applyOverlayPatch({position:'bottom-right'})}>Snap Bottom Right</button>
                        <button className="btn" onClick={async()=>{const r=await window.pywebview?.api?.export_native_overlay_settings?.(); if(r?.success) alert(`Exported to ${r.path}`); else alert(r?.error || 'Export failed');}}>Export Profile</button>
                        <button className="btn" onClick={async()=>{const r=await window.pywebview?.api?.import_native_overlay_settings?.(); if(r?.success){setOverlay(r.settings);setTransparencyDraft(Math.round(r.settings.background_transparency*100));} else alert(r?.error || 'Import failed');}}>Import Profile</button>
                        <button className="btn primary" onClick={async()=>{const result=await window.pywebview?.api?.reset_native_overlay_settings?.(); if(result?.success){setOverlay(result.settings);setTransparencyDraft(Math.round(result.settings.background_transparency*100));}}}>Reset Overlay 2.0</button>
                    </div>
                </>}
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🛠️</div>
                    <div>
                        <h3>System Settings</h3>
                        <p>Application-wide preferences</p>
                    </div>
                </div>

                <div className="setting-row" style={{ padding: '15px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <div style={{ fontWeight: 600, color: 'var(--text-bright)' }}>Open AppData Folder</div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Opens the folder where logs, config, and macro data are stored</div>
                    </div>
                    <button 
                        className="btn primary" 
                        onClick={() => window.pywebview?.api?.open_appdata()}
                        style={{ padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', backgroundColor: 'var(--primary)', color: 'white', border: 'none', fontWeight: 600 }}
                    >
                        Open Folder
                    </button>
                </div>

                <ToggleSwitch
                    label="GLITCHED visual effect on macro UI when GLITCHED biome is found (to look cool ofc)"
                    description={<span style={{ color: "red", fontWeight: "bold" }}>ONLY USE THIS IF YOU ARE NON PHOTOSENSITIVE</span>}
                    checked={config.enable_glitch_effect || false}
                    onChange={(val) => updateConfig("enable_glitch_effect", val)}
                />

                <ToggleSwitch
                    label="Anti-AFK"
                    description="Prevents Roblox disconnection even when Roblox isn't focused"
                    checked={config.anti_afk || false}
                    onChange={(val) => updateConfig("anti_afk", val)}
                />

                <div className="setting-row" style={{ padding: '0 20px 20px 20px', display: 'flex', alignItems: 'center', gap: '15px' }}>
                    <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Usage Duration (minutes):</span>
                    <input 
                        type="number" 
                        className="form-input" 
                        style={{ width: '80px', textAlign: 'center' }}
                        value={config.anti_afk_interval || "5"}
                        min="1"
                        max="20"
                        onChange={(e) => updateConfig("anti_afk_interval", e.target.value)}
                    />
                </div>

                <ToggleSwitch
                    label="Auto Update (startup)"
                    description="Automatically download the latest macro update when the app opens"
                    checked={config.auto_update_enabled !== false}
                    onChange={(val) => updateConfig("auto_update_enabled", val)}
                />

                <ToggleSwitch
                    label="Enable Idle Mode"
                    description="Disable all automated actions except biome/aura detection and anti-afk."
                    checked={config.enable_idle_mode || false}
                    onChange={(val) => updateConfig("enable_idle_mode", val)}
                />

                <ToggleSwitch
                    label="Make Roblox instance on fullscreen"
                    description="Automatically fullscreen Roblox window when macro starts"
                    checked={config.auto_roblox_fullscreen || false}
                    onChange={(val) => updateConfig("auto_roblox_fullscreen", val)}
                />

                <ToggleSwitch
                    label="AZERTY Keyboard Mode (experimental)"
                    description="Enable this if you currently using AZERTY keyboard layout :aga:"
                    checked={config.azerty_mode || false}
                    onChange={(val) => updateConfig("azerty_mode", val)}
                />
            </div>
        </>
    );
}
