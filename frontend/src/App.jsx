import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid, PieChart, Pie, Cell } from 'recharts';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

const API = 'http://127.0.0.1:8000/api';

function App() {
  const [threats, setThreats] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [commands, setCommands] = useState([]);
  const [summary, setSummary] = useState(null);
  const [integrity, setIntegrity] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [mode, setMode] = useState(null);
  const [ros, setRos] = useState(null);
  const [classDist, setClassDist] = useState([]);
  const [drone, setDrone] = useState(null);
  const dronePathRef = useRef(null);
  const droneMarkerRef = useRef(null);
  const [showHelp, setShowHelp] = useState(false);
  const [whitelist, setWhitelist] = useState([]);
  const [risk, setRisk] = useState(null);
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const threatMarkers = useRef({});
  const audioRef = useRef(null);
  const alertedThreats = useRef(new Set());

  const fetchThreats = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/threats/`);
      setThreats(res.data);
      buildTrend(res.data);
      res.data.forEach(t => {
        if (t.confidence >= 0.85 && !alertedThreats.current.has(t.id)) {
          alertedThreats.current.add(t.id);
          if (audioRef.current) { audioRef.current.currentTime = 0; audioRef.current.play().catch(()=>{}); }
        }
      });
      updateMap(res.data);
    } catch (e) { console.error(e); }
  }, []);

  const fetchIncidents = useCallback(async () => {
    try { const r = await axios.get(`${API}/incidents/`); setIncidents(r.data);} catch(e){console.error(e);} }, []);
  const fetchLedger = useCallback(async () => {
    try { const r = await axios.get(`${API}/ledger/`); setLedger(r.data);} catch(e){console.error(e);} }, []);
  const fetchCommands = useCallback(async () => {
    try { const r = await axios.get(`${API}/commands/`); setCommands(r.data);} catch(e){console.error(e);} }, []);
  const fetchSummary = useCallback(async () => {
    try { const r = await axios.get(`${API}/dashboard/summary`); setSummary(r.data); buildClassDist(r.data.class_distribution);} catch(e){console.error(e);} }, []);
  const fetchIntegrity = useCallback(async () => {
    try { const r = await axios.get(`${API}/ledger/summary`); setIntegrity(r.data);} catch(e){console.error(e);} }, []);
  const fetchDrone = useCallback(async () => {
    try { const r = await axios.get(`${API}/commands/drone`); setDrone(r.data); updateDroneOnMap(r.data);} catch(e){console.error(e);} }, []);
  const fetchMode = useCallback(async () => {
    try { const r = await axios.get(`${API}/ops/mode`); setMode(r.data);} catch(e){console.error(e);} }, []);
  const fetchRos = useCallback(async () => {
    try { const r = await axios.get(`${API}/ros/summary`); setRos(r.data);} catch(e){console.error(e);} }, []);
  const fetchWhitelist = useCallback(async () => {
    try { const r = await axios.get(`${API}/airspace/whitelist`); setWhitelist(r.data);} catch(e){console.error(e);} }, []);
  const fetchRisk = useCallback(async () => {
    try { const r = await axios.get(`${API}/risk/score`); setRisk(r.data);} catch(e){console.error(e);} }, []);

  const seedScenario = async () => {
    try { await axios.post(`${API}/threats/seed`, { count: 8 }); fetchThreats(); } catch(e){console.error(e);} };

  const buildTrend = (list) => {
    const now = Date.now();
    const buckets = {};
    list.forEach(t => {
      const ts = new Date(t.created_at).getTime();
      if (now - ts > 15*60*1000) return;
      const m = Math.floor(ts/60000)*60000;
      if(!buckets[m]) buckets[m] = { time: new Date(m).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}), total:0 };
      buckets[m].total += 1;
      buckets[m][t.class] = (buckets[m][t.class]||0)+1;
    });
    setTrendData(Object.keys(buckets).sort().map(k => buckets[k]));
  };

  const initMap = () => {
    if (mapInstance.current) return;
    mapInstance.current = L.map(mapRef.current).setView([28.50,77.60],13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(mapInstance.current);
  };

  const buildClassDist = (dist) => {
    if(!dist) return;
    const arr = Object.entries(dist).map(([k,v]) => ({ name:k, value:v }));
    setClassDist(arr);
  };

  const exportEvidence = async () => {
    try {
      const r = await axios.get(`${API}/evidence/bundle`);
      const bstr = atob(r.data.base64);
      const bytes = new Uint8Array(bstr.length);
      for (let i=0;i<bstr.length;i++) bytes[i] = bstr.charCodeAt(i);
      const blob = new Blob([bytes], {type:'application/zip'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = r.data.filename; a.click();
      URL.revokeObjectURL(url);
    } catch(e){console.error(e);}  
  };

  const corruptLedger = async () => {
    try { await axios.post(`${API}/ledger/corrupt`); fetchIntegrity(); fetchLedger(); } catch(e){console.error(e);} };

  const toggleHelp = () => setShowHelp(s=>!s);
  const addWhitelist = async () => { try { const rid = prompt('Enter Remote ID to authorize (RID-xxxx)'); if(!rid) return; await axios.post(`${API}/airspace/whitelist`, { remote_id: rid }); fetchWhitelist(); fetchThreats(); fetchRisk(); } catch(e){console.error(e);} };
  const removeWhitelist = async (rid) => { try { await axios.delete(`${API}/airspace/whitelist/${rid}`); fetchWhitelist(); fetchThreats(); fetchRisk(); } catch(e){console.error(e);} };

  const updateMap = (list) => {
    if (!mapInstance.current) return;
    const existing = new Set(Object.keys(threatMarkers.current));
    list.forEach(t => {
      if (t.location && typeof t.location.lat === 'number') {
        if(!threatMarkers.current[t.id]) {
          const marker = L.circleMarker([t.location.lat, t.location.lon], { radius:6, color: t.confidence>=0.85?'#ff4444':'#ffaa00', weight:2 })
            .addTo(mapInstance.current).bindPopup(`${t.class} (${t.confidence})`);
          threatMarkers.current[t.id] = marker;
        }
      }
      existing.delete(t.id);
    });
    existing.forEach(id => { mapInstance.current.removeLayer(threatMarkers.current[id]); delete threatMarkers.current[id]; });
  };

  const updateDroneOnMap = (d) => {
  if(!mapInstance.current || !d || !d.location) return;
  const { lat, lon } = d.location;
  if(!droneMarkerRef.current){
    droneMarkerRef.current = L.marker([lat, lon], { title: 'Drone' }).addTo(mapInstance.current).bindPopup('Interceptor Drone');
  } else {
    droneMarkerRef.current.setLatLng([lat, lon]);
  }
  // path polyline
  if(d.origin_location && d.target_location){
    const pts = [ [d.origin_location.lat, d.origin_location.lon], [d.target_location.lat, d.target_location.lon] ];
    if(!dronePathRef.current){
      dronePathRef.current = L.polyline(pts, { color:'#4fc3f7', dashArray:'4,4' }).addTo(mapInstance.current);
    } else {
      dronePathRef.current.setLatLngs(pts);
    }
  }
  };

  useEffect(() => {
    fetchThreats(); fetchLedger(); fetchIncidents(); fetchCommands(); fetchIntegrity(); fetchSummary(); fetchMode(); fetchRos(); fetchDrone(); fetchWhitelist(); fetchRisk(); initMap();
    const i = setInterval(() => { fetchThreats(); fetchLedger(); fetchIncidents(); fetchCommands(); fetchIntegrity(); fetchSummary(); fetchMode(); fetchRos(); fetchDrone(); fetchWhitelist(); fetchRisk(); }, 6000);
    return () => clearInterval(i);
  }, [fetchThreats, fetchLedger, fetchIncidents, fetchCommands, fetchIntegrity, fetchSummary, fetchMode, fetchRos, fetchDrone, fetchWhitelist, fetchRisk]);

  const dispatchCommand = async (type='return_to_base') => {
    try { await axios.post(`${API}/commands/dispatch`, { command:type }); fetchCommands(); fetchLedger(); fetchIncidents(); } catch(e){console.error(e);} };

  return (
    <div className="app-shell">
      {/* Premium floating background elements */}
      <div className="floating-elements"></div>
      
      <header>
        <h1>🛡️ PROJECT KAVACH | TEAM TEJAS</h1>
        <div className="actions">
          <button onClick={seedScenario}>🎯 GENERATE SCENARIO</button>
          <button onClick={()=>dispatchCommand('return_to_base')}>🏠 RETURN DRONE</button>
          <button onClick={()=>dispatchCommand('hold_position')}>⏸️ HOLD POSITION</button>
          <button onClick={exportEvidence}>📦 EXPORT EVIDENCE</button>
          <button onClick={corruptLedger}>⚠️ SIMULATE TAMPER</button>
          <button onClick={toggleHelp}>{showHelp ? '✖️ CLOSE HELP':'❓ HELP GUIDE'}</button>
        </div>
      </header>
      <main className="grid">
        <section className="panel wide">
          <h2>🗺️ Spatial Awareness <span className="live-indicator">TRACKING</span></h2>
          <div ref={mapRef} className="map" />
          <h2 style={{marginTop:16}}>📈 Threat Analytics (15m Window) <span className="live-indicator">TREND</span></h2>
          <div style={{height:180}}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{top:5,right:10,left:0,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3d" />
                <XAxis dataKey="time" stroke="#8892a0" />
                <YAxis stroke="#8892a0" allowDecimals={false} />
                <Tooltip contentStyle={{background:'#1b232e', border:'1px solid #2d3644'}} />
                <Legend />
                <Line type="monotone" dataKey="total" stroke="#4fc3f7" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="panel">
          <h2>🎯 Active Threats <span className="live-indicator">LIVE</span></h2>
          <div className="list scroll">
            {threats.map(t => (
              <div key={t.id} className={`item threat ${t.confidence>=0.85?'high':'med'}`}>
                <div>
                  <strong>🔴 {t.class.toUpperCase()}</strong>
                  <small>{new Date(t.created_at).toLocaleTimeString()}</small>
                </div>
                <span className="confidence">{Math.round(t.confidence*100)}%</span>
              </div>
            ))}
            {!threats.length && <div className="empty">🔍 No active threats detected</div>}
          </div>
        </section>
        <section className="panel">
          <h2>🚨 Security Incidents <span className="live-indicator">MONITOR</span></h2>
          <div className="list scroll">
            {incidents.map(i => (
              <div key={i.id} className="item incident">
                <div><strong>⚠️ {i.title || 'Security Event'}</strong><small>📊 Status: {i.status.toUpperCase()}</small></div>
                <small>{new Date(i.created_at).toLocaleTimeString()}</small>
              </div>
            ))}
            {!incidents.length && <div className="empty">✅ No active incidents</div>}
          </div>
        </section>
        <section className="panel">
          <h2>🎮 Command Center <span className="live-indicator">ACTIVE</span></h2>
          <div className="list scroll">
            {commands.map(c => (
              <div key={c.id} className="item command">
                <div><strong>⚡ {c.command.toUpperCase()}</strong><small>🔄 {c.status.toUpperCase()}</small></div>
                <small>{new Date(c.created_at).toLocaleTimeString()}</small>
              </div>
            ))}
            {!commands.length && <div className="empty">🎯 No commands dispatched</div>}
          </div>
        </section>
        <section className="panel">
          <h2>🔗 Blockchain Ledger <span className="live-indicator">SECURED</span></h2>
          <div className="list scroll">
            {ledger.slice(-40).reverse().map(e => (
              <div key={e.id} className="item ledger">
                <div><strong>📦 {e.event_type.toUpperCase()}</strong><small>🆔 {e.id.slice(0,8)}...{e.id.slice(-4)}</small></div>
                <small>{new Date(e.timestamp || e.created_at || Date.now()).toLocaleTimeString()}</small>
              </div>
            ))}
            {!ledger.length && <div className="empty">🔒 No ledger entries</div>}
          </div>
          {integrity && (
            <div className={`integrity ${integrity.valid ? 'good':'bad'}`}>
              <span>🛡️ {integrity.valid ? 'Ledger Integrity Verified':'⚠️ Ledger Anomaly Detected'}</span>
              <small>📊 Events: {integrity.length} • 🪟 Window: {integrity.window_valid?'✅ OK':'❌ Issue'}</small>
            </div>
          )}
        </section>
        <section className="panel">
          <h2>📊 Operational Intelligence <span className="live-indicator">REALTIME</span></h2>
          {summary && (
            <div className="metrics">
              <div><span>Total Threats</span><strong>{summary.total_threats}</strong></div>
              <div><span>Commands</span><strong>{summary.command_count}</strong></div>
              <div><span>Open Incidents</span><strong>{summary.incidents_open}</strong></div>
              <div><span>Ledger Events</span><strong>{summary.ledger_length}</strong></div>
            </div>
          )}
          {mode && (
            <div className={`mode-badge ${mode.mode.toLowerCase()}`}>
              <strong>{mode.mode.replace('_',' ')}</strong>
              <small>{Math.round(mode.simulated_energy_delta*100)}% energy delta</small>
            </div>
          )}
          {ros && (
            <div className="ros-box">
              <div className="row"><span>Avoided Cost</span><strong>${ros.avoided_cost_estimate.toLocaleString()}</strong></div>
              <div className="row"><span>Ref Breach</span><strong>${ros.single_breach_reference.toLocaleString()}</strong></div>
              <div className="row"><span>ROS Ratio</span><strong>{ros.ros_ratio.toFixed(2)}</strong></div>
            </div>
          )}
          <div className="note">Prototype – simulated telemetry, ROS & adaptive modes.</div>
        </section>
        <section className="panel">
          <h2>Threat Class Mix</h2>
          <div style={{height:220}}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={classDist} dataKey="value" nameKey="name" outerRadius={80} innerRadius={40}>
                  {classDist.map((e,i)=>(<Cell key={e.name} fill={["#4fc3f7","#7ce0b3","#ffb347","#ff4d4d","#8b9bff"][i%5]} />))}
                </Pie>
                <Tooltip contentStyle={{background:'#1b232e', border:'1px solid #2d3644'}} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="note">Fused classification distribution (demo).</div>
        </section>
        <section className="panel">
          <h2>Airspace Whitelist</h2>
          <div className="list scroll" style={{maxHeight:140}}>
            {whitelist.map(rid => (
              <div key={rid} className="item">
                <div><strong>{rid}</strong><small>authorized</small></div>
                <button style={{fontSize:10}} onClick={()=>removeWhitelist(rid)}>Remove</button>
              </div>
            ))}
            {!whitelist.length && <div className="empty">No authorized IDs</div>}
          </div>
          <button style={{marginTop:8}} onClick={addWhitelist}>Add Remote ID</button>
          <h2 style={{marginTop:18}}>Risk Score</h2>
          <div style={{height:160, position:'relative'}}>
            <RiskGauge value={risk?.score || 0} />
            {risk && <div style={{position:'absolute', bottom:4, left:8, fontSize:10, opacity:.6}}>Unauth: {risk.components.unauthorized_count} • MaxConf: {Math.round(risk.components.max_confidence*100)}% • Inc: {risk.components.open_incidents}</div>}
          </div>
        </section>
      </main>
      {showHelp && (
        <div className="help-overlay">
          <div className="help-inner">
            <h3>Evaluator Guide – Project Kavach</h3>
            <ul>
              <li><strong>Generate Scenario:</strong> Seeds multi-class threats (map + lists update).</li>
              <li><strong>Adaptive Mode:</strong> Badge shifts to HIGH ALERT when high-confidence threats active; ECO when quiet (&gt;10m).</li>
              <li><strong>Ledger Integrity:</strong> Simulate Corrupt Ledger to demonstrate tamper detection.</li>
              <li><strong>Evidence Export:</strong> Produces signed snapshot bundle (demo) for chain-of-custody.</li>
              <li><strong>ROS Metrics:</strong> Shows avoided cost model (risk mitigation justification).</li>
              <li><strong>Drone Path:</strong> Dashed cyan line = active mission vector; marker = interceptor.</li>
              <li><strong>Class Mix & Trend:</strong> Categorical + temporal situational awareness.</li>
              <li><strong>Audio Pulse:</strong> New high severity detection cue.</li>
            </ul>
            <p style={{opacity:.6, fontSize:12}}>Human-in-the-loop principle maintained; all autonomous actions logged to verifiable ledger.</p>
          </div>
        </div>
      )}
      <audio ref={audioRef} preload="auto" src="data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=" />
    </div>
  );
}

export default App;

// Premium Crystal Risk Gauge Component
function RiskGauge({ value }) {
  const pct = Math.min(100, Math.max(0, value));
  const angle = (pct/100)*180; // semicircle
  
  // Dynamic colors and effects based on risk level
  let gaugeColor = '#00ff88';
  let glowColor = 'rgba(0, 255, 136, 0.6)';
  let statusText = '🟢 SECURE';
  
  if (pct > 70) {
    gaugeColor = '#ff4757';
    glowColor = 'rgba(255, 71, 87, 0.8)';
    statusText = '🔴 CRITICAL';
  } else if (pct > 40) {
    gaugeColor = '#ffa502';
    glowColor = 'rgba(255, 165, 2, 0.7)';
    statusText = '🟡 ELEVATED';
  } else if (pct > 15) {
    gaugeColor = '#00d4ff';
    glowColor = 'rgba(0, 212, 255, 0.6)';
    statusText = '🔵 MODERATE';
  }

  const needleRotation = -90 + (pct * 1.8); // Map 0-100 to -90 to +90 degrees

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '20px 16px',
      background: 'var(--glass-bg)',
      backdropFilter: 'blur(15px)',
      borderRadius: '20px',
      border: '1px solid var(--glass-border)',
      position: 'relative',
      overflow: 'hidden',
      boxShadow: `0 8px 32px rgba(0,0,0,0.3), 0 0 60px ${glowColor.replace('0.6', '0.1').replace('0.7', '0.1').replace('0.8', '0.1')}`
    }}>
      {/* Background glow */}
      <div style={{
        position: 'absolute',
        inset: 0,
        background: `radial-gradient(circle at center, ${glowColor.replace(/[\d.]+\)/, '0.08)')} 0%, transparent 70%)`,
        pointerEvents: 'none',
        borderRadius: 'inherit'
      }} />
      
      <svg viewBox="0 0 220 130" style={{width:'100%', height:'100%', position: 'relative', zIndex: 1}}>
        <defs>
          {/* Premium gauge gradient */}
          <linearGradient id="premiumGaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00ff88" stopOpacity="0.9" />
            <stop offset="30%" stopColor="#00d4ff" stopOpacity="0.95" />
            <stop offset="60%" stopColor="#ffa502" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#ff4757" stopOpacity="1" />
          </linearGradient>
          
          {/* Glow filter */}
          <filter id="premiumGlow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          
          {/* Needle glow */}
          <filter id="needleGlow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        {/* Background track */}
        <path 
          d="M15 110 A95 95 0 0 1 205 110" 
          stroke="rgba(255, 255, 255, 0.08)" 
          strokeWidth="12" 
          fill="none" 
          strokeLinecap="round" 
        />
        
        {/* Active gauge track */}
        <path 
          d="M15 110 A95 95 0 0 1 205 110" 
          stroke="url(#premiumGaugeGrad)" 
          strokeWidth="12" 
          fill="none" 
          strokeLinecap="round"
          filter="url(#premiumGlow)"
          opacity="0.9"
        />
        
        {/* Gauge tick marks */}
        {[0, 25, 50, 75, 100].map((tick, i) => {
          const tickAngle = -90 + (tick * 1.8);
          const cos = Math.cos((tickAngle * Math.PI) / 180);
          const sin = Math.sin((tickAngle * Math.PI) / 180);
          const x1 = 110 + cos * 85;
          const y1 = 110 + sin * 85;
          const x2 = 110 + cos * 95;
          const y2 = 110 + sin * 95;
          
          return (
            <g key={tick}>
              <line 
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke="rgba(255, 255, 255, 0.3)"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <text 
                x={110 + cos * 75} 
                y={110 + sin * 75 + 4}
                textAnchor="middle" 
                fontSize="10" 
                fill="rgba(255, 255, 255, 0.6)"
                fontWeight="500"
                fontFamily="Inter, sans-serif"
              >
                {tick}
              </text>
            </g>
          );
        })}
        
        {/* Premium needle */}
        <g transform={`translate(110,110) rotate(${needleRotation})`}>
          {/* Needle shadow */}
          <line 
            x1="0" y1="2" x2="0" y2="-72"
            stroke="rgba(0, 0, 0, 0.3)"
            strokeWidth="4"
            strokeLinecap="round"
          />
          {/* Main needle */}
          <line 
            x1="0" y1="0" x2="0" y2="-70"
            stroke={gaugeColor}
            strokeWidth="3"
            strokeLinecap="round"
            filter="url(#needleGlow)"
          />
          {/* Needle tip */}
          <circle 
            cx="0" cy="-70" r="3"
            fill={gaugeColor}
            filter="url(#needleGlow)"
          />
          {/* Center hub */}
          <circle 
            cx="0" cy="0" r="8"
            fill="var(--glass-bg)"
            stroke={gaugeColor}
            strokeWidth="2"
            filter="url(#needleGlow)"
          />
          <circle 
            cx="0" cy="0" r="3"
            fill={gaugeColor}
          />
        </g>
        
        {/* Digital readout */}
        <rect 
          x="70" y="75" width="80" height="25"
          fill="rgba(0, 0, 0, 0.4)"
          stroke="rgba(255, 255, 255, 0.1)"
          strokeWidth="1"
          rx="8"
        />
        <text 
          x="110" y="92" 
          textAnchor="middle" 
          fontSize="20" 
          fill={gaugeColor}
          fontWeight="800"
          fontFamily="Inter, sans-serif"
          filter="url(#premiumGlow)"
        >
          {pct}
        </text>
        
        {/* Risk label */}
        <text 
          x="110" y="125" 
          textAnchor="middle" 
          fontSize="11" 
          fill="rgba(255, 255, 255, 0.7)"
          fontWeight="600"
          fontFamily="Inter, sans-serif"
          style={{letterSpacing:'2px', textTransform: 'uppercase'}}
        >
          THREAT LEVEL
        </text>
      </svg>
      
      {/* Status indicator */}
      <div style={{
        marginTop: '12px',
        padding: '6px 14px',
        background: `linear-gradient(135deg, ${gaugeColor}25, ${gaugeColor}10)`,
        border: `1px solid ${gaugeColor}50`,
        borderRadius: '20px',
        fontSize: '11px',
        fontWeight: '700',
        color: gaugeColor,
        textTransform: 'uppercase',
        letterSpacing: '0.8px',
        textAlign: 'center',
        boxShadow: `0 4px 15px ${glowColor.replace(/[\d.]+\)/, '0.2)')}`,
        animation: pct > 70 ? 'pulse 2s infinite' : 'none'
      }}>
        {statusText}
      </div>
    </div>
  );
}
