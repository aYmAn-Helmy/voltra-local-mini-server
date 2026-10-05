from __future__ import annotations

DASHBOARD = r'''<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Voltra Dashboard</title>
<style>
:root{
  color-scheme:light;
  --bg:#f6f8fb;--panel:#ffffff;--panel-2:#f8fafc;--line:#dfe5ee;--text:#111827;
  --muted:#667892;--sidebar:#0f1930;--sidebar-2:#18233b;--sidebar-text:#dce5f4;
  --green:#14b85a;--green-soft:#ecfbf1;--green-line:#b9efcb;
  --blue:#2563eb;--blue-soft:#eef5ff;--red:#ef4444;--red-soft:#fff1f1;
  --amber:#f59e0b;--amber-soft:#fff7df;--shadow:0 1px 2px #0f172a0a,0 5px 16px #0f172a0b;
}
html[data-theme="dark"]{
  color-scheme:dark;
  --bg:#08101f;--panel:#101a2d;--panel-2:#0d1728;--line:#243149;--text:#edf2fb;
  --muted:#91a0b8;--sidebar:#070d1b;--sidebar-2:#111a2d;--sidebar-text:#e5ecf8;
  --green:#35dc7b;--green-soft:#102a20;--green-line:#245b42;
  --blue:#68a4ff;--blue-soft:#12223b;--red:#ff6d77;--red-soft:#2b171d;
  --amber:#ffbd4a;--amber-soft:#302512;--shadow:0 8px 26px #0000002b;
}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Tahoma,Arial,sans-serif}
button,input,select{font:inherit}
button{cursor:pointer}
.app{min-height:100vh;display:grid;grid-template-columns:236px minmax(0,1fr)}
.sidebar{position:sticky;top:0;height:100vh;background:var(--sidebar);color:var(--sidebar-text);display:flex;flex-direction:column;padding:20px 14px 14px;z-index:30}
.brand{display:flex;align-items:center;gap:11px;padding:0 8px 20px}
.logo{width:36px;height:36px;border-radius:12px;background:#0d513c;color:#48eb91;display:grid;place-items:center;font-size:21px;font-weight:900}
.brand strong{display:block;font-size:16px}.brand small{display:block;color:#8fa1bd;margin-top:2px;font-size:11px}
.nav{display:grid;gap:7px}
.nav-btn{display:flex;align-items:center;gap:12px;width:100%;border:0;background:transparent;color:#b7c3d7;padding:12px 13px;border-radius:10px;text-align:left}
.nav-btn:hover{background:#16223a;color:white}.nav-btn.active{background:white;color:#182033;box-shadow:0 1px 8px #0002}
html[data-theme="dark"] .nav-btn.active{background:#1d2a43;color:white}
.nav-ico{width:20px;text-align:center;font-size:17px}
.sidebar-spacer{flex:1}
.health-box{border:1px solid #26324b;background:var(--sidebar-2);border-radius:14px;padding:14px;margin:12px 0}
.health-label{font-size:10px;color:#91a0b9;margin-bottom:12px}
.health-row{display:flex;align-items:center;gap:11px}.health-ring{width:38px;height:38px;border:4px solid #26dc75;border-radius:50%;display:grid;place-items:center;font-size:10px;font-weight:800}
.health-copy strong{font-size:12px;display:block}.health-copy small{font-size:10px;color:#93a4bd}
.side-account{border-top:1px solid #22304a;padding-top:13px;display:flex;align-items:center;gap:9px}
.avatar{width:34px;height:34px;border-radius:50%;background:#0d513c;color:#55e89a;display:grid;place-items:center;font-weight:800}
.side-account div{min-width:0;flex:1}.side-account strong{display:block;font-size:12px}.side-account small{display:block;color:#8fa1bd;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.main{padding:30px 36px 50px;min-width:0}
.topbar{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:22px}
.topbar h1{margin:0;font-size:29px;letter-spacing:-.8px}.topbar p{margin:5px 0 0;color:var(--muted);font-size:13px}
.top-actions{display:flex;align-items:center;gap:10px}
.search{width:230px;height:38px;border:1px solid var(--line);border-radius:11px;background:var(--panel);display:flex;align-items:center;gap:8px;padding:0 11px;color:var(--muted)}
.search input{min-width:0;flex:1;border:0;outline:0;background:transparent;color:var(--text);font-size:12px}
.icon-btn{width:38px;height:38px;border:1px solid var(--line);border-radius:11px;background:var(--panel);color:var(--muted);display:grid;place-items:center}
.icon-btn:hover{color:var(--text);border-color:#b8c3d3}
.system-pill{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:6px 10px;background:var(--green-soft);color:#138442;font-size:11px;margin-bottom:24px}
.system-pill.warn{background:var(--amber-soft);color:#a66b00}.system-dot{width:7px;height:7px;border-radius:50%;background:currentColor}
.view{display:none}.view.active{display:block}
.stat-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:28px}
.stat-card{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:18px;box-shadow:var(--shadow);min-height:126px}
.stat-head{display:flex;align-items:center;gap:11px;color:var(--muted);font-size:12px}
.stat-icon{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;background:var(--blue-soft);color:var(--blue);font-size:17px}
.stat-icon.green{background:var(--green-soft);color:var(--green)}.stat-icon.gray{background:var(--panel-2);color:#7c8ba2}
.stat-value{font-size:29px;font-weight:750;line-height:1;margin-top:13px}.stat-caption{font-size:10px;color:var(--muted);margin-top:7px}
.section-head{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:14px}
.section-head h2{margin:0;font-size:17px}.section-head p{margin:4px 0 0;color:var(--muted);font-size:12px}
.filters{display:flex;align-items:center;background:var(--panel-2);padding:3px;border-radius:10px;border:1px solid var(--line)}
.filter-btn{border:0;background:transparent;color:var(--muted);font-size:11px;padding:7px 12px;border-radius:8px}.filter-btn.active{background:var(--panel);color:var(--text);box-shadow:0 1px 4px #0001}
.strip-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.strip-card{background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);overflow:hidden}
.strip-card.offline{opacity:.68}
.strip-header{display:flex;align-items:flex-start;gap:10px;padding:16px 16px 13px;border-bottom:1px solid var(--line)}
.strip-icon{width:35px;height:35px;border-radius:10px;background:var(--panel-2);display:grid;place-items:center;color:#718099}
.strip-main{min-width:0;flex:1}.strip-title-row{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.strip-name{font-size:13px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:220px}
.pill{font-size:9px;border-radius:999px;padding:4px 7px;border:1px solid var(--green-line);background:var(--green-soft);color:#148945}
.pill.offline{background:var(--panel-2);border-color:var(--line);color:var(--muted)}.pill.disabled{background:var(--amber-soft);border-color:#f6d784;color:#a76d00}
.strip-meta{font-size:10px;color:var(--muted);margin-top:3px}
.strip-tools{display:flex;align-items:center;gap:3px}.mini-btn{border:0;background:transparent;color:#8aa0bf;width:28px;height:28px;border-radius:7px}.mini-btn:hover{background:var(--panel-2);color:var(--text)}
.outlet-row{min-height:54px;display:flex;align-items:center;gap:10px;padding:9px 15px;border-bottom:1px solid var(--line);transition:.15s}.outlet-row:last-child{border-bottom:0}
.outlet-row.on{background:var(--green-soft)}
.outlet-icon{width:31px;height:31px;border-radius:9px;background:var(--panel-2);display:grid;place-items:center;color:#7890ad;flex:none}.outlet-row.on .outlet-icon{background:#d9f8e4;color:#15934b}html[data-theme="dark"] .outlet-row.on .outlet-icon{background:#173a28;color:#4ce58b}
.outlet-copy{min-width:0;flex:1}.outlet-name{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.outlet-sub{font-size:9px;color:var(--muted);margin-top:2px}
.outlet-watts{font-size:10px;color:var(--green);font-weight:700;min-width:52px;text-align:right}.outlet-state{font-size:10px;color:#8da0ba;font-weight:700;width:28px;text-align:right}.outlet-row.on .outlet-state{color:#118743}
.switch{position:relative;width:40px;height:22px;border-radius:999px;border:0;background:#cbd6e5;padding:0;flex:none;transition:.16s}.switch:after{content:"";position:absolute;width:18px;height:18px;top:2px;left:2px;border-radius:50%;background:white;box-shadow:0 1px 3px #0003;transition:.16s}.switch.on{background:#10ba59}.switch.on:after{left:20px}.switch:disabled{opacity:.42;cursor:not-allowed}
.quick-panel{width:min(560px,100%);background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);padding:18px;margin-top:20px}
.quick-panel h3{margin:0;font-size:14px}.quick-panel>p{margin:4px 0 14px;color:var(--muted);font-size:11px}
.quick-action{width:100%;border:0;border-radius:10px;display:flex;align-items:center;gap:11px;text-align:left;padding:11px 13px;margin-top:8px;color:var(--text)}
.quick-action.red{background:var(--red-soft)}.quick-action.blue{background:var(--blue-soft)}.quick-action.amber{background:var(--amber-soft)}
.qa-icon{width:34px;height:34px;border-radius:9px;background:var(--panel);display:grid;place-items:center}.qa-copy{flex:1}.qa-copy strong{display:block;font-size:11px}.qa-copy small{display:block;font-size:9px;color:var(--muted);margin-top:2px}.qa-arrow{color:var(--muted)}
.tip{margin-top:12px;background:var(--sidebar);color:#e7edf7;border-radius:10px;padding:12px;font-size:10px}.tip strong{display:block;font-size:11px;margin-bottom:3px}
.empty{grid-column:1/-1;border:1px dashed var(--line);border-radius:14px;padding:30px;text-align:center;color:var(--muted);background:var(--panel)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);padding:18px}
.room-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.room-card h3{margin:0 0 4px;font-size:14px}.room-card p{margin:0;color:var(--muted);font-size:10px}.room-list{margin-top:12px;display:grid;gap:7px}.room-item{display:flex;justify-content:space-between;gap:10px;background:var(--panel-2);border-radius:9px;padding:9px 10px;font-size:11px}
.form-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.field{width:100%;border:1px solid var(--line);background:var(--panel);color:var(--text);border-radius:10px;padding:10px 11px;outline:none}
.btn{border:1px solid var(--line);background:var(--panel);color:var(--text);border-radius:10px;padding:9px 12px;font-weight:650}.btn:hover{border-color:#aebbd0}.btn.primary{background:var(--blue);color:white;border-color:var(--blue)}.btn.green{background:var(--green);color:white;border-color:var(--green)}.btn.red{background:var(--red);color:white;border-color:var(--red)}
.energy-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:16px}.energy-box{background:var(--panel-2);border-radius:12px;padding:14px}.energy-box span{color:var(--muted);font-size:10px}.energy-box b{display:block;font-size:20px;margin-top:7px}
.account-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:16px}.account-section h3{margin:0 0 12px;font-size:14px}.row{display:flex;justify-content:space-between;gap:15px;padding:10px 0;border-bottom:1px solid var(--line);font-size:11px}.row:last-child{border-bottom:0}.row span:first-child{color:var(--muted)}
.pending-list{display:grid;gap:9px}.pending-device{border:1px solid var(--line);border-radius:11px;padding:11px;display:flex;align-items:center;justify-content:space-between;gap:10px}.pending-device strong{font-size:11px}.pending-device small{display:block;color:var(--muted);font-size:9px;margin-top:3px}
.modal{position:fixed;inset:0;background:#0f172a80;display:none;align-items:center;justify-content:center;padding:20px;z-index:100}.modal.show{display:flex}.modal-box{width:min(520px,100%);background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 30px 90px #0006}.modal-box h3{margin:0 0 14px}.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}
.toast{position:fixed;right:22px;bottom:22px;background:var(--sidebar);color:white;border-radius:11px;padding:11px 14px;display:none;z-index:120;font-size:11px;box-shadow:0 12px 40px #0005}
.mobile-menu{display:none}
@media(max-width:1150px){.stat-grid{grid-template-columns:repeat(2,1fr)}.room-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:900px){
  .app{grid-template-columns:1fr}.sidebar{position:relative;height:auto;display:block;padding:12px}.brand{padding-bottom:10px}.nav{display:flex;overflow:auto}.nav-btn{width:auto;white-space:nowrap}.sidebar-spacer,.health-box,.side-account{display:none}.main{padding:20px}.strip-grid{grid-template-columns:1fr}.account-grid{grid-template-columns:1fr}.room-grid{grid-template-columns:1fr}.topbar{align-items:center}.topbar p{display:none}
}
@media(max-width:620px){.main{padding:15px}.stat-grid{grid-template-columns:1fr 1fr;gap:9px}.stat-card{padding:13px;min-height:110px}.search{width:150px}.form-grid,.energy-summary{grid-template-columns:1fr}.strip-tools{display:none}.topbar h1{font-size:23px}}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand"><div class="logo">ϟ</div><div><strong>Voltra</strong><small>Smart power control</small></div></div>
    <nav class="nav">
      <button class="nav-btn active" data-view="dashboard"><span class="nav-ico">▦</span>Dashboard</button>
      <button class="nav-btn" data-view="rooms"><span class="nav-ico">⌂</span>Rooms</button>
      <button class="nav-btn" data-view="energy"><span class="nav-ico">⌁</span>Energy</button>
      <button class="nav-btn" data-view="account"><span class="nav-ico">♙</span>Account</button>
    </nav>
    <div class="sidebar-spacer"></div>
    <div class="health-box">
      <div class="health-label">System health</div>
      <div class="health-row"><div class="health-ring" id="healthPercent">100%</div><div class="health-copy"><strong id="healthTitle">All strips online</strong><small id="healthDetail">0 of 0 outlets on</small></div></div>
    </div>
    <div class="side-account"><div class="avatar">V</div><div><strong>Voltra Local</strong><small id="sideVersion">Local mini server</small></div></div>
  </aside>

  <main class="main">
    <div class="topbar">
      <div><h1 id="pageTitle">Dashboard</h1><p id="pageSubtitle">Monitor and control your smart power strips in real time.</p></div>
      <div class="top-actions">
        <label class="search"><span>⌕</span><input id="globalSearch" type="search" placeholder="Search strips..." oninput="setSearch(this.value)"></label>
        <button class="icon-btn" id="themeButton" onclick="toggleTheme()" title="Light / dark mode">☾</button>
        <button class="icon-btn" onclick="refresh()" title="Refresh">↻</button>
      </div>
    </div>

    <section id="view-dashboard" class="view active">
      <div class="system-pill" id="systemPill"><span class="system-dot"></span><span id="systemText">All systems normal</span></div>
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-head"><span class="stat-icon">▭</span><span>Total strips</span></div><div class="stat-value" id="statTotal">0</div><div class="stat-caption">Registered devices</div></div>
        <div class="stat-card"><div class="stat-head"><span class="stat-icon green">⌁</span><span>Online</span></div><div class="stat-value" id="statOnline">0</div><div class="stat-caption">Connected now</div></div>
        <div class="stat-card"><div class="stat-head"><span class="stat-icon green">⏻</span><span>Outlets on</span></div><div class="stat-value" id="statOn">0</div><div class="stat-caption">Currently powered</div></div>
        <div class="stat-card"><div class="stat-head"><span class="stat-icon gray">—</span><span>Outlets off</span></div><div class="stat-value" id="statOff">0</div><div class="stat-caption">Idle outlets</div></div>
      </div>

      <div class="section-head">
        <div><h2>Smart strips</h2><p>Control each outlet individually or monitor strip status at a glance.</p></div>
        <div class="filters">
          <button class="filter-btn active" data-filter="all">All</button>
          <button class="filter-btn" data-filter="online">Online</button>
          <button class="filter-btn" data-filter="offline">Offline</button>
        </div>
      </div>
      <div id="stripGrid" class="strip-grid"></div>

      <div class="quick-panel">
        <h3>Quick actions</h3><p>Common controls for your strips.</p>
        <button class="quick-action red" onclick="turnAllOff()"><span class="qa-icon">⏻</span><span class="qa-copy"><strong>Turn all off</strong><small>Switch off every powered outlet on online strips</small></span><span class="qa-arrow">→</span></button>
        <button class="quick-action blue" onclick="goView('rooms')"><span class="qa-icon">⌘</span><span class="qa-copy"><strong>Rooms & labels</strong><small>Organize strips and mapped devices</small></span><span class="qa-arrow">→</span></button>
        <button class="quick-action amber" onclick="openSchedule()"><span class="qa-icon">◷</span><span class="qa-copy"><strong>Schedules</strong><small>Automate on/off times</small></span><span class="qa-arrow">→</span></button>
        <div class="tip"><strong>Tip: schedules cut idle power</strong>Set automatic OFF times for chargers and screens from any strip.</div>
      </div>
    </section>

    <section id="view-rooms" class="view">
      <div class="section-head"><div><h2>Rooms</h2><p>Group your strips by room and manage mappings.</p></div><button class="btn" onclick="goView('account')">Device management</button></div>
      <div id="roomGrid" class="room-grid"></div>
    </section>

    <section id="view-energy" class="view">
      <div class="panel">
        <div class="section-head"><div><h2>Energy</h2><p>Local consumption summaries from Voltra telemetry.</p></div></div>
        <div class="form-grid">
          <select id="energyMac" class="field"></select>
          <select id="energyHours" class="field"><option value="24">Last 24 hours</option><option value="168">Last 7 days</option><option value="720">Last 30 days</option></select>
          <button class="btn primary" onclick="loadEnergy()">Load energy</button>
        </div>
        <div class="energy-summary">
          <div class="energy-box"><span>Energy</span><b id="energyKwh">—</b></div>
          <div class="energy-box"><span>Average power</span><b id="energyAvg">—</b></div>
          <div class="energy-box"><span>Peak power</span><b id="energyMax">—</b></div>
          <div class="energy-box"><span>Samples</span><b id="energySamples">—</b></div>
        </div>
      </div>
    </section>

    <section id="view-account" class="view">
      <div class="account-grid">
        <div class="panel account-section">
          <h3>Server & device setup</h3>
          <div class="row"><span>Server version</span><b id="accountVersion">—</b></div>
          <div class="row"><span>Mode</span><b id="accountMode">—</b></div>
          <div class="row"><span>Managed strips</span><b id="accountStrips">0</b></div>
          <div style="height:14px"></div>
          <h3>Provision a new strip</h3>
          <div class="form-grid">
            <input id="wifiSsid" class="field" placeholder="2.4 GHz Wi-Fi SSID">
            <input id="wifiPassword" class="field" type="password" placeholder="Wi-Fi password">
            <input id="serverIp" class="field" placeholder="Voltra server LAN IP">
          </div>
          <div style="margin-top:10px"><button class="btn primary" onclick="provision()">Send network setup</button></div>
        </div>
        <div class="panel account-section">
          <h3>Discovered strips</h3>
          <div id="pendingList" class="pending-list"></div>
        </div>
      </div>
    </section>
  </main>
</div>

<div id="renameModal" class="modal"><div class="modal-box"><h3>Rename strip</h3><input id="renameValue" class="field" placeholder="Strip name"><div class="modal-actions"><button class="btn" onclick="closeModal('renameModal')">Cancel</button><button class="btn primary" onclick="saveRename()">Save</button></div></div></div>
<div id="scheduleModal" class="modal"><div class="modal-box"><h3>Create daily schedule</h3><div class="form-grid"><select id="scheduleTarget" class="field"></select><input id="scheduleTime" class="field" type="time" value="23:00"><select id="scheduleAction" class="field"><option value="off">Turn off</option><option value="on">Turn on</option></select></div><div class="modal-actions"><button class="btn" onclick="closeModal('scheduleModal')">Cancel</button><button class="btn primary" onclick="createSchedule()">Create</button></div></div></div>
<div id="toast" class="toast"></div>

<script>
let data={strips:[],ps4_devices:[],mappings:{},summary:{}};
let automationData={schedules:{},rules:{},queue:[]};
let currentFilter='all';
let searchValue='';
let renameMac=null;
const playzoneMode=location.pathname==='/voltra-console'||location.pathname.startsWith('/voltra-console/');

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function api(path,opt={}){
  const token=playzoneMode?(localStorage.getItem('playzone_token')||''):'';
  const headers={'content-type':'application/json',...(opt.headers||{})};
  if(playzoneMode&&token)headers.Authorization='Bearer '+token;
  const requestPath=playzoneMode?path.replace(/^\/voltra\/api/,'/api/root/voltra-console'):path;
  const r=await fetch(requestPath,{...opt,headers});
  const t=await r.text();
  let v={};
  try{v=t?JSON.parse(t):{}}catch{v={raw:t}}
  if(!r.ok)throw new Error(v.detail||v.error||r.statusText);
  return v;
}

function toast(msg,bad=false){
  const t=document.getElementById('toast');
  t.textContent=msg;t.style.display='block';t.style.background=bad?'#7f1d1d':'#0f1930';
  clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.style.display='none',3000);
}

function activeStrips(){return (data.strips||[]).filter(s=>s.managed&&(s.state==='active'||s.state==='disabled'))}
function pendingStrips(){return (data.strips||[]).filter(s=>s.state==='pending'&&s.online)}
function mappingFor(mac,outlet){return Object.entries(data.mappings||{}).find(([id,m])=>m.mac===mac&&Number(m.outlet)===Number(outlet))?.[0]||null}
function deviceName(id){return (data.ps4_devices||[]).find(x=>String(x.id)===String(id))?.name||id}
function stripByMac(mac){return (data.strips||[]).find(x=>x.mac===mac)}

function goView(name){
  document.querySelectorAll('.view').forEach(x=>x.classList.toggle('active',x.id==='view-'+name));
  document.querySelectorAll('.nav-btn').forEach(x=>x.classList.toggle('active',x.dataset.view===name));
  const titles={dashboard:['Dashboard','Monitor and control your smart power strips in real time.'],rooms:['Rooms','Group strips by room and manage mapped devices.'],energy:['Energy','Review local power consumption and telemetry.'],account:['Account','Server status, discovery and device setup.']};
  const item=titles[name]||titles.dashboard;
  pageTitle.textContent=item[0];pageSubtitle.textContent=item[1];
  globalSearch.parentElement.style.display=name==='dashboard'?'flex':'none';
  if(name==='energy')renderEnergyTargets();
}

function setSearch(value){searchValue=String(value||'').trim().toLowerCase();renderStrips()}
function setFilter(value){
  currentFilter=value;
  document.querySelectorAll('.filter-btn').forEach(x=>x.classList.toggle('active',x.dataset.filter===value));
  renderStrips();
}

function computeStats(){
  const strips=activeStrips();
  let on=0;
  strips.forEach(s=>(s.outlets||[]).forEach(o=>{if(o.relay)on++}));
  const total=strips.length*4;
  return {strips,online:strips.filter(s=>s.online).length,on,off:Math.max(0,total-on),total};
}

function render(){
  const st=computeStats();
  statTotal.textContent=st.strips.length;statOnline.textContent=st.online;statOn.textContent=st.on;statOff.textContent=st.off;
  healthPercent.textContent=(st.strips.length?Math.round(st.online/st.strips.length*100):100)+'%';
  healthTitle.textContent=st.online===st.strips.length?'All strips online':(st.strips.length-st.online)+' strip(s) offline';
  healthDetail.textContent=st.on+' of '+st.total+' outlets on';
  sideVersion.textContent='v'+(data.version||'—')+' · Local mini server';
  accountVersion.textContent='v'+(data.version||'—');accountMode.textContent=data.mode||'real';accountStrips.textContent=st.strips.length;
  const unhealthy=st.strips.some(s=>!s.online||((s.health||{}).score??100)<55);
  systemPill.classList.toggle('warn',unhealthy);
  systemText.textContent=unhealthy?'Attention needed':'All systems normal';
  renderStrips();renderRooms();renderPending();renderEnergyTargets();renderScheduleTargets();
}

function renderStrips(){
  let strips=activeStrips();
  if(currentFilter==='online')strips=strips.filter(s=>s.online);
  if(currentFilter==='offline')strips=strips.filter(s=>!s.online);
  if(searchValue){
    strips=strips.filter(s=>{
      const names=[s.name,s.room,s.mac];
      for(let n=1;n<=4;n++){const id=mappingFor(s.mac,n);if(id)names.push(deviceName(id))}
      return names.filter(Boolean).join(' ').toLowerCase().includes(searchValue);
    });
  }
  if(!strips.length){stripGrid.innerHTML='<div class="empty">No strips match the current view.</div>';return}
  stripGrid.innerHTML=strips.map(stripCard).join('');
}

function stripCard(s){
  const can=s.online&&s.enabled&&s.state==='active';
  const status=s.state==='disabled'?'Disabled':(s.online?'Online':'Offline');
  const statusClass=s.state==='disabled'?'disabled':(s.online?'':'offline');
  const metrics=[];
  if(s.voltage_v!=null)metrics.push(Number(s.voltage_v).toFixed(1)+' V');
  if(s.wifi_rssi_dbm!=null)metrics.push('Wi-Fi '+s.wifi_rssi_dbm+' dBm');
  if(s.health?.score!=null)metrics.push('Health '+s.health.score+'%');
  let outlets='';
  for(let n=1;n<=4;n++){
    const o=(s.outlets||[]).find(x=>Number(x.channel)===n);
    const mapped=mappingFor(s.mac,n);
    const name=mapped?deviceName(mapped):'Outlet '+n;
    const isOn=!!o?.relay;
    outlets+='<div class="outlet-row '+(isOn?'on':'')+'">'+
      '<div class="outlet-icon">♧</div>'+
      '<div class="outlet-copy"><div class="outlet-name" dir="auto">'+esc(name)+'</div><div class="outlet-sub">Outlet '+n+'</div></div>'+
      '<div class="outlet-watts">'+(isOn?Number(o?.power_w||0).toFixed(1)+' W':'')+'</div>'+
      '<div class="outlet-state">'+(isOn?'ON':'OFF')+'</div>'+
      '<button class="switch '+(isOn?'on':'')+'" '+(can?'':'disabled')+' onclick="toggleOutlet(\''+s.mac+'\','+n+','+(!isOn)+',this)" aria-label="Toggle outlet"></button>'+
      '</div>';
  }
  return '<article class="strip-card '+(!s.online?'offline':'')+'">'+
    '<div class="strip-header">'+
      '<div class="strip-icon">▭</div>'+
      '<div class="strip-main"><div class="strip-title-row"><span class="strip-name" dir="auto">'+esc(s.name||s.mac)+'</span><span class="pill '+statusClass+'">'+status+'</span></div>'+
      '<div class="strip-meta">'+esc(s.room||'Unassigned room')+(metrics.length?' · '+esc(metrics.join(' · ')):'')+'</div></div>'+
      '<div class="strip-tools"><button class="mini-btn" onclick="refresh()">↻</button><button class="mini-btn" onclick="openSchedule(\''+s.mac+'\')">◷</button><button class="mini-btn" onclick="goView(\'energy\');selectEnergy(\''+s.mac+'\')">⌁</button><button class="mini-btn" onclick="editRoom(\''+s.mac+'\')">⌂</button><button class="mini-btn" onclick="openRename(\''+s.mac+'\')">⚙</button></div>'+
    '</div>'+outlets+'</article>';
}

async function toggleOutlet(mac,outlet,on,button){
  if(button)button.disabled=true;
  try{
    await api('/voltra/api/strips/'+mac+'/outlets/'+outlet+'/state',{method:'POST',body:JSON.stringify({on})});
    await refresh(false);
  }catch(e){toast(e.message,true)}finally{if(button)button.disabled=false}
}

async function turnAllOff(){
  const powered=[];
  activeStrips().filter(s=>s.online&&s.enabled&&s.state==='active').forEach(s=>(s.outlets||[]).forEach(o=>{if(o.relay)powered.push([s.mac,Number(o.channel)])}));
  if(!powered.length)return toast('All outlets are already off');
  if(!confirm('Turn off '+powered.length+' powered outlet(s)?'))return;
  try{
    for(const [mac,outlet] of powered)await api('/voltra/api/strips/'+mac+'/outlets/'+outlet+'/state',{method:'POST',body:JSON.stringify({on:false})});
    await refresh(false);toast('Powered outlets turned off');
  }catch(e){toast(e.message,true);await refresh(false)}
}

function renderRooms(){
  const groups={};
  activeStrips().forEach(s=>{const room=(s.room||'Unassigned').trim()||'Unassigned';(groups[room]||(groups[room]=[])).push(s)});
  const entries=Object.entries(groups);
  if(!entries.length){roomGrid.innerHTML='<div class="empty">No managed strips yet.</div>';return}
  roomGrid.innerHTML=entries.map(([room,strips])=>'<div class="panel room-card"><h3>'+esc(room)+'</h3><p>'+strips.length+' strip(s)</p><div class="room-list">'+strips.map(s=>'<div class="room-item"><span>'+esc(s.name||s.mac)+'</span><button class="mini-btn" onclick="editRoom(\''+s.mac+'\')">✎</button></div>').join('')+'</div></div>').join('');
}

async function editRoom(mac){
  const s=stripByMac(mac);if(!s)return;
  const room=prompt('Room name for '+(s.name||mac)+':',s.room||'');
  if(room===null)return;
  try{await api('/voltra/api/strips/'+mac+'/preferences',{method:'PUT',body:JSON.stringify({room})});await refresh(false);toast('Room updated')}catch(e){toast(e.message,true)}
}

function openRename(mac){renameMac=mac;renameValue.value=stripByMac(mac)?.name||'';renameModal.classList.add('show')}
function closeModal(id){document.getElementById(id).classList.remove('show')}
async function saveRename(){
  if(!renameMac)return;
  try{await api('/voltra/api/strips/'+renameMac,{method:'PUT',body:JSON.stringify({name:renameValue.value.trim()})});closeModal('renameModal');await refresh(false);toast('Strip renamed')}catch(e){toast(e.message,true)}
}

function renderPending(){
  const pending=pendingStrips();
  if(!pending.length){pendingList.innerHTML='<div class="empty">No new strips discovered.</div>';return}
  pendingList.innerHTML=pending.map(s=>'<div class="pending-device"><div><strong>'+esc(s.name||('Voltra '+s.mac.slice(-4)))+'</strong><small>'+esc(s.mac)+' · '+esc(s.last_ip||'')+'</small></div><button class="btn green" onclick="adoptStrip(\''+s.mac+'\')">Add</button></div>').join('');
}
async function adoptStrip(mac){
  const current=stripByMac(mac);const name=prompt('Name this strip:',current?.name||('Strip '+mac.slice(-4)));if(name===null)return;
  try{await api('/voltra/api/strips/'+mac+'/adopt',{method:'POST',body:JSON.stringify({name:name.trim()||('Strip '+mac.slice(-4))})});await refresh(false);toast('Strip added')}catch(e){toast(e.message,true)}
}
async function provision(){
  if(!wifiSsid.value||!serverIp.value)return toast('Enter Wi-Fi SSID and Voltra LAN IP',true);
  try{await api('/voltra/api/provision',{method:'POST',body:JSON.stringify({ssid:wifiSsid.value,password:wifiPassword.value,server_ip:serverIp.value})});wifiPassword.value='';toast('Provisioning commands sent')}catch(e){toast(e.message,true)}
}

function renderEnergyTargets(){
  const current=energyMac.value;
  energyMac.innerHTML=activeStrips().map(s=>'<option value="'+s.mac+'">'+esc(s.name||s.mac)+'</option>').join('');
  if(current&&activeStrips().some(s=>s.mac===current))energyMac.value=current;
}
function selectEnergy(mac){setTimeout(()=>{energyMac.value=mac;loadEnergy()},0)}
async function loadEnergy(){
  if(!energyMac.value)return;
  try{
    const r=await api('/voltra/api/energy?mac='+encodeURIComponent(energyMac.value)+'&hours='+encodeURIComponent(energyHours.value));
    energyKwh.textContent=Number(r.energy_kwh||0).toFixed(3)+' kWh';
    energyAvg.textContent=Number(r.average_power_w||0).toFixed(1)+' W';
    energyMax.textContent=Number(r.max_power_w||0).toFixed(1)+' W';
    energySamples.textContent=String(r.samples||0);
  }catch(e){toast(e.message,true)}
}

function renderScheduleTargets(){
  const current=scheduleTarget.value;
  let html='';
  activeStrips().forEach(s=>{for(let n=1;n<=4;n++){const id=mappingFor(s.mac,n);html+='<option value="'+s.mac+':'+n+'">'+esc(s.name||s.mac)+' / '+esc(id?deviceName(id):('Outlet '+n))+'</option>'}});
  scheduleTarget.innerHTML=html;
  if(current&&[...scheduleTarget.options].some(o=>o.value===current))scheduleTarget.value=current;
}
function openSchedule(mac=null){
  renderScheduleTargets();
  if(mac){const option=[...scheduleTarget.options].find(o=>o.value.startsWith(mac+':'));if(option)scheduleTarget.value=option.value}
  scheduleModal.classList.add('show');
}
async function createSchedule(){
  const v=scheduleTarget.value;if(!v)return;
  const cut=v.lastIndexOf(':');const mac=v.slice(0,cut),outlet=Number(v.slice(cut+1));
  try{
    await api('/voltra/api/schedules',{method:'POST',body:JSON.stringify({mac,outlet,on:scheduleAction.value==='on',time:scheduleTime.value,days:[0,1,2,3,4,5,6],offline_policy:'queue'})});
    closeModal('scheduleModal');await loadAutomation();toast('Schedule created');
  }catch(e){toast(e.message,true)}
}
async function loadAutomation(){try{automationData=await api('/voltra/api/automation')}catch(e){}}

function applyTheme(theme){
  document.documentElement.dataset.theme=theme;
  localStorage.setItem('voltra_dashboard_theme',theme);
  themeButton.textContent=theme==='dark'?'☀':'☾';
}
function toggleTheme(){applyTheme(document.documentElement.dataset.theme==='dark'?'light':'dark')}

async function refresh(renderAll=true){
  try{data=await api('/voltra/api/overview');if(renderAll)render();else render()}
  catch(e){toast('API: '+e.message,true)}
}

async function liveLoop(){
  if(playzoneMode)return;
  for(;;){
    try{
      const r=await fetch('/voltra/api/events',{headers:{Accept:'text/event-stream'}});
      if(!r.ok)throw new Error('SSE '+r.status);
      const reader=r.body.getReader(),decoder=new TextDecoder();let buf='';
      for(;;){
        const x=await reader.read();if(x.done)break;
        buf+=decoder.decode(x.value,{stream:true});
        let cut;
        while((cut=buf.indexOf('\n\n'))>=0){
          const packet=buf.slice(0,cut);buf=buf.slice(cut+2);
          if(packet.includes('data:'))await refresh(false);
        }
      }
    }catch(e){}
    await new Promise(r=>setTimeout(r,2000));
  }
}

document.querySelectorAll('.nav-btn').forEach(b=>b.addEventListener('click',()=>goView(b.dataset.view)));
document.querySelectorAll('.filter-btn').forEach(b=>b.addEventListener('click',()=>setFilter(b.dataset.filter)));
applyTheme(localStorage.getItem('voltra_dashboard_theme')||'light');
Promise.all([refresh(),loadAutomation()]).then(()=>render());
liveLoop();
setInterval(()=>refresh(false),15000);
</script>
</body>
</html>'''
