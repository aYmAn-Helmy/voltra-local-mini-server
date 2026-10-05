from __future__ import annotations

DASHBOARD = r'''<!doctype html>
<html lang="en" dir="ltr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Voltra Power Manager</title>
<style>
:root{font-family:Inter,system-ui,"Segoe UI",Tahoma,Arial,sans-serif;color-scheme:dark;background:#07111d;color:#edf5ff;--panel:#0c1826;--panel2:#101e2d;--line:#20354a;--muted:#8fa7bf;--blue:#2196ff;--green:#20d878;--amber:#ffb020;--red:#ff5060}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 70% -20%,#12315d 0,#07111d 34%,#050c14 80%);min-height:100vh}.shell{max-width:1500px;margin:auto;padding:22px}.top{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:2px 0 18px}.brand h1{margin:0;font-size:28px}.brand p{margin:6px 0 0;color:var(--muted)}.badges{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.badge{border:1px solid var(--line);background:#0c1a29;border-radius:999px;padding:8px 12px;font-size:13px}.badge.real{border-color:#8a343b;color:#ff939c}.badge.demo{border-color:#765d1d;color:#ffd06a}.badge.online{border-color:#146f49;color:#75f0ad}.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:16px}.stat{background:linear-gradient(145deg,#0d1b2a,#09131e);border:1px solid var(--line);border-radius:16px;padding:15px;min-height:98px}.stat span{color:var(--muted);font-size:13px}.stat b{display:block;font-size:28px;margin-top:9px}.panel{background:rgba(11,24,38,.94);border:1px solid var(--line);border-radius:18px;padding:17px;box-shadow:0 18px 50px #0005}.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}.tab{border:1px solid #29445f;background:#0c1a29;color:#b9cce0;padding:10px 15px;border-radius:11px;cursor:pointer}.tab.active{border-color:#338fe0;background:#123a61;color:#fff;box-shadow:0 0 0 1px #168cff33 inset}.page{display:none}.page.active{display:block}.section-title{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:0 0 12px}.section-title h2{margin:0;font-size:20px}.muted{color:var(--muted)}.strip{background:#0a1521;border:1px solid #223b53;border-radius:17px;padding:15px;margin:12px 0}.strip.disabled{opacity:.78;border-color:#51451f}.strip.offline{border-color:#49303a}.strip-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex-wrap:wrap}.strip-name{font-size:19px;font-weight:800}.status{font-weight:700}.status.online{color:#65efa6}.status.offline{color:#ff8d97}.status.disabled{color:#ffca68}.actions{display:flex;gap:7px;flex-wrap:wrap;align-items:center}.btn{border:0;border-radius:10px;padding:9px 12px;cursor:pointer;background:#253b51;color:#fff;font-weight:650}.btn:hover{filter:brightness(1.13)}.btn:disabled{opacity:.38;cursor:not-allowed;filter:none}.btn.blue{background:#176ca3}.btn.green{background:#14784b}.btn.amber{background:#7a5819}.btn.red{background:#8c2936}.btn.ghost{background:transparent;border:1px solid #34506b}.btn.sm{padding:7px 9px;font-size:12px}.outlets{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:13px}.outlet{background:#0e1b29;border:1px solid #213951;border-radius:13px;padding:13px;min-height:150px}.outlet-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.ps-head{display:flex;align-items:center;gap:10px;min-width:0}.ps-logo{width:34px;height:34px;flex:0 0 34px;display:grid;place-items:center;border-radius:10px;background:linear-gradient(145deg,#0d4d91,#0d83dc);box-shadow:0 0 18px #178cff2b}.ps-logo svg{width:24px;height:24px;display:block}.ps-title{font-size:17px;font-weight:850;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.outlet-sub{font-size:11px;color:var(--muted);margin-top:4px}.relay{font-size:15px;font-weight:850;padding:5px 8px;border-radius:8px;background:#111f2c}.relay.on{color:#57e794;border:1px solid #1d6d49}.relay.off{color:#93a8bd;border:1px solid #344a5e}.power-line{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:13px 0 10px;padding:10px 11px;border:1px solid #29435b;background:#0a1723;border-radius:11px}.power-label{display:flex;align-items:center;gap:6px;color:#91abc4;font-size:12px}.watt{font-size:23px;font-weight:900;margin:0;color:#fff;direction:ltr}.unmapped-head{display:flex;align-items:center;gap:9px}.unmapped-icon{width:34px;height:34px;display:grid;place-items:center;border-radius:10px;background:#15283a;color:#7f9bb5;font-size:17px}.tag{display:inline-block;padding:3px 8px;border-radius:999px;background:#14314d;color:#add8ff;font-size:11px}.pending-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.pending{background:#0e1c2b;border:1px dashed #2e6389;border-radius:16px;padding:16px}.field{width:100%;background:#08131e;border:1px solid #2b4760;color:#fff;padding:10px 11px;border-radius:9px}.formline{display:grid;grid-template-columns:1fr 1fr auto;gap:10px;margin:10px 0}.mapping{display:grid;grid-template-columns:1.2fr 1.4fr auto;gap:10px;align-items:center;padding:11px;border-bottom:1px solid #1e3449}.mapping:last-child{border-bottom:0}.mapping.mapping-dirty{background:#102943;border:1px solid #2d78b5;border-radius:12px;margin:4px 0}.mapping-note{color:#ffd06a;font-size:12px;margin-top:5px}.mapping-actions{display:flex;gap:7px;align-items:center;flex-wrap:wrap}.empty{padding:28px;text-align:center;border:1px dashed #35516a;border-radius:14px;color:#93a9bf}.advanced{margin-top:12px;border-top:1px solid #1e3449;padding-top:10px}.advanced summary{cursor:pointer;color:#a9bfd3}.kv{display:grid;grid-template-columns:120px 1fr;gap:6px 12px;margin-top:10px;font-size:13px}.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;direction:ltr;text-align:left}.notice{padding:12px;border:1px solid #70581a;background:#2a220f;border-radius:11px;color:#f3d77d;margin:10px 0}.good{padding:12px;border:1px solid #1c6848;background:#0d2a20;border-radius:11px;color:#8cf0bb;margin:10px 0}.toast{position:fixed;left:20px;bottom:20px;background:#12263a;border:1px solid #376082;padding:12px 15px;border-radius:12px;display:none;z-index:80;max-width:520px}.modal{position:fixed;inset:0;background:#000a;display:none;align-items:center;justify-content:center;padding:20px;z-index:70}.modal.show{display:flex}.modalbox{width:min(590px,100%);background:#0d1b29;border:1px solid #304c66;border-radius:18px;padding:20px}.modalbox h3{margin-top:0}.danger-zone{border:1px solid #5f2931;background:#241216;border-radius:14px;padding:14px;margin-top:14px}.history{display:grid;gap:9px}.history-item{border:1px solid #293b4d;border-radius:12px;padding:12px;background:#0a141f}.count{background:#17344f;color:#bfe3ff;border-radius:999px;padding:2px 8px;font-size:12px;margin-inline-start:5px}
*{scrollbar-width:thin;scrollbar-color:#365d7d transparent}*::-webkit-scrollbar{width:5px;height:5px}*::-webkit-scrollbar-track{background:transparent}*::-webkit-scrollbar-thumb{background:#365d7d;border-radius:999px}*::-webkit-scrollbar-thumb:hover{background:#5792bf}.playzone-embedded,.playzone-embedded body{scrollbar-width:none!important;-ms-overflow-style:none!important}.playzone-embedded::-webkit-scrollbar,.playzone-embedded body::-webkit-scrollbar{width:0!important;height:0!important;display:none!important}#pzVoltraScrollTrack{position:fixed;top:4px;bottom:4px;left:2px;width:6px;z-index:170;background:transparent;opacity:.5;transition:opacity .18s;touch-action:none}#pzVoltraScrollTrack:hover,#pzVoltraScrollTrack.dragging{opacity:.95}#pzVoltraScrollTrack.hidden{display:none}#pzVoltraScrollThumb{position:absolute;top:0;left:1px;width:4px;min-height:30px;border-radius:999px;background:#365d7d;box-shadow:0 0 0 1px #08131e99;cursor:grab;touch-action:none;will-change:transform}#pzVoltraScrollTrack.dragging #pzVoltraScrollThumb{cursor:grabbing;background:#5792bf}@media(max-width:1000px){.stats{grid-template-columns:repeat(2,1fr)}.outlets{grid-template-columns:repeat(2,1fr)}.pending-grid{grid-template-columns:1fr}.mapping,.formline{grid-template-columns:1fr}}
@media(max-width:560px){.shell{padding:12px}.stats,.outlets{grid-template-columns:1fr}.brand h1{font-size:23px}.stat{min-height:auto}}

/* v0.15 calm device cards — inspired by modern smart-home dashboards */
#managedStrips{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.device-card{position:relative;overflow:hidden;background:linear-gradient(180deg,#101d2b 0%,#0b1622 100%);border:1px solid #22384d;border-radius:24px;padding:20px;box-shadow:0 18px 42px #0000002b;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}
.device-card:hover{transform:translateY(-2px);border-color:#315574;box-shadow:0 24px 55px #00000040}
.device-card.offline{opacity:.72}.device-card.disabled{opacity:.78}
.device-card::after{content:"";position:absolute;inset:auto -90px -110px auto;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,#1f8fff1b 0,transparent 68%);pointer-events:none}
.device-head{display:flex;align-items:center;gap:13px;min-width:0}
.device-icon{width:52px;height:52px;flex:0 0 52px;border-radius:16px;display:grid;place-items:center;background:linear-gradient(145deg,#172c41,#0d2031);border:1px solid #2a455f;font-size:24px;box-shadow:inset 0 1px #ffffff0d}
.device-ident{min-width:0;flex:1}.device-name{font-size:20px;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.device-model{margin-top:5px;font-size:12px;color:#829bb3;direction:ltr;text-align:right}
.device-state{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border-radius:999px;font-size:12px;font-weight:750;border:1px solid #2c455c;background:#0a1520;white-space:nowrap}.device-state.online{color:#76e8a8;border-color:#1f6d49;background:#0b281e}.device-state.offline{color:#ff9aa3;border-color:#6f3740;background:#2a1519}.device-state.disabled{color:#ffd277;border-color:#735a22;background:#2a220f}
.device-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:18px 0 15px}.metric{padding:10px 8px;border:1px solid #1e3448;border-radius:14px;background:#09131e;text-align:center}.metric b{display:block;font-size:16px;direction:ltr}.metric span{display:block;color:#7891a9;font-size:10px;margin-top:4px}
.socket-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.socket{position:relative;min-height:132px;border:1px solid #22384b;background:#0b1723;border-radius:18px;padding:14px;transition:.16s ease}.socket.on{border-color:#246b4a;background:linear-gradient(155deg,#0c251d,#0b1723 72%)}.socket.off{border-color:#22384b}.socket.unavailable{opacity:.58}
.socket-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}.socket-name{font-size:15px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.socket-sub{font-size:10px;color:#7891a9;margin-top:4px}.socket-power{font-size:22px;font-weight:900;margin-top:16px;direction:ltr}.socket-power small{font-size:11px;color:#7891a9;font-weight:600}
.power-toggle{width:42px;height:42px;border:0;border-radius:14px;display:grid;place-items:center;cursor:pointer;font-size:19px;background:#172638;color:#71879d;box-shadow:inset 0 0 0 1px #2b4258;transition:.16s ease}.power-toggle.on{background:#19b96b;color:white;box-shadow:0 8px 22px #19b96b33}.power-toggle:hover{transform:scale(1.04)}.power-toggle:disabled{cursor:not-allowed;opacity:.45;transform:none}
.device-footer{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:16px;padding-top:14px;border-top:1px solid #1c3042}.health-pill{display:flex;align-items:center;gap:7px;color:#8da4b9;font-size:12px}.health-dot{width:7px;height:7px;border-radius:50%;background:#20d878;box-shadow:0 0 12px #20d87888}.health-dot.warn{background:#ffb020;box-shadow:0 0 12px #ffb02077}.health-dot.bad{background:#ff5060;box-shadow:0 0 12px #ff506077}
.device-menu{position:relative}.device-menu summary{list-style:none;cursor:pointer;width:38px;height:38px;border:1px solid #294055;border-radius:12px;display:grid;place-items:center;background:#0c1825;color:#a8bed2;font-size:20px}.device-menu summary::-webkit-details-marker{display:none}.device-menu[open] summary{border-color:#3a6587;color:#fff}.device-menu-pop{position:absolute;z-index:30;left:0;bottom:46px;min-width:190px;padding:7px;background:#0d1a28;border:1px solid #2a455f;border-radius:14px;box-shadow:0 18px 50px #0009}.device-menu-pop button{width:100%;text-align:right;background:transparent;border:0;color:#dce9f5;padding:9px 10px;border-radius:9px;cursor:pointer}.device-menu-pop button:hover{background:#162a3d}.device-menu-pop button.danger{color:#ff8d97}
.devices-empty{grid-column:1/-1;padding:44px 20px;text-align:center;border:1px dashed #304b63;border-radius:22px;background:#09141f;color:#8fa7bf}
.devices-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:15px}.devices-toolbar-copy h2{margin:0;font-size:24px}.devices-toolbar-copy p{margin:5px 0 0;color:#8299af;font-size:13px}
@media(max-width:1050px){#managedStrips{grid-template-columns:1fr}.device-metrics{grid-template-columns:repeat(4,1fr)}}
@media(max-width:620px){.device-card{padding:15px;border-radius:20px}.device-metrics{grid-template-columns:repeat(2,1fr)}.socket-grid{grid-template-columns:1fr}.device-state{padding:6px 8px}.device-icon{width:46px;height:46px;flex-basis:46px}.device-name{font-size:18px}}

/* v0.18 mobile-first dashboard — layout matched to the supplied reference */
:root{--v18-bg:#070d1b;--v18-card:#111827;--v18-card2:#151e31;--v18-line:#202a3d;--v18-muted:#818ba3;--v18-text:#f0f3fb;--v18-green:#31df7d;--v18-green-soft:#143a2d}
html{background:var(--v18-bg)}body{background:var(--v18-bg)!important;color:var(--v18-text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Tahoma,Arial,sans-serif}
.shell{position:relative;max-width:760px!important;margin:0 auto!important;padding:22px 16px 100px!important;direction:ltr}
.app-header{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:22px}
.app-header h1{font-size:31px;line-height:1;margin:9px 0 0;font-weight:850;letter-spacing:-1.2px}
.live-kicker{font-size:11px;letter-spacing:3px;color:var(--v18-green);font-weight:800}.live-dot{display:inline-block;width:5px;height:5px;border-radius:99px;background:var(--v18-green);box-shadow:0 0 12px #31df7dcc;margin-right:6px}
.header-actions{display:flex;gap:10px}.icon-btn{width:43px;height:43px;border-radius:13px;border:1px solid var(--v18-line);background:#0e1627;color:#8f99af;font-size:22px;display:grid;place-items:center;cursor:pointer;box-shadow:inset 0 1px #ffffff08}.icon-btn:hover{color:#fff;border-color:#34425d}
.account-card,.power-hero,.search-box,.quick-card,.strip-card{border:1px solid var(--v18-line);box-shadow:inset 0 1px #ffffff06}
.account-card{height:70px;border-radius:19px;background:linear-gradient(155deg,#121a2b,#0f1727);display:flex;align-items:center;padding:11px 15px;gap:13px;margin-bottom:16px;cursor:pointer}
.avatar{width:44px;height:44px;border-radius:50%;display:grid;place-items:center;background:var(--v18-green);color:#07160d;font-weight:900;font-size:16px}.account-copy{min-width:0;flex:1}.account-copy strong{display:block;font-size:15px}.account-copy span{display:block;color:var(--v18-muted);font-size:12px;margin-top:4px}.chevron{font-size:29px;color:#7f899f;font-weight:200}
.power-hero{border-radius:20px;background:linear-gradient(165deg,#151e31 0%,#121a2b 100%);padding:20px 20px 17px;margin-bottom:15px;position:relative;overflow:hidden}
.power-hero:after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:linear-gradient(90deg,transparent,var(--v18-green),transparent);opacity:.6}
.hero-label{font-size:12px;color:#8e97ad;font-weight:650}.hero-value{display:flex;align-items:flex-end;gap:8px;margin:7px 0 10px;color:var(--v18-green)}.hero-value span{font:800 46px/1 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:-2px}.hero-value small{font-size:13px;color:#9ca5b9;margin-bottom:7px}
.hero-meta{display:flex;gap:15px;flex-wrap:wrap;color:#939caf;font-size:11px}.hero-meta b{color:#c5cbd8}
.quick-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin-bottom:14px}.quick-card{min-width:0;height:82px;border-radius:13px;background:#101829;color:#8e97ad;padding:9px 4px 8px;cursor:pointer;overflow:hidden}.quick-card:hover{border-color:#2e405c;color:#d6dbe7}.quick-icon{margin:0 auto 7px;display:grid;place-items:center;width:34px;height:34px;border-radius:11px;background:#102c2a;color:var(--v18-green);font-size:20px}.quick-card>span:last-child{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:10.5px}
.search-box{height:54px;border-radius:15px;background:#101829;display:flex;align-items:center;gap:10px;padding:0 15px;margin-bottom:16px;color:#7c869d}.search-box>span{font-size:24px;line-height:1}.search-box input{width:100%;border:0;outline:0;background:transparent;color:#e8ebf3;font-size:14px;font-weight:600}.search-box input::placeholder{color:#69738b}
.compat-stats{display:none!important}
.nav-drawer{display:none;position:absolute;z-index:90;top:76px;right:16px;width:min(280px,calc(100% - 32px));padding:8px;border-radius:17px;border:1px solid #2a354a;background:#101829;box-shadow:0 25px 70px #000b}.nav-drawer.show{display:grid;gap:4px}.nav-drawer .tab{display:block;width:100%;text-align:left;border:0!important;background:transparent!important;color:#c2c8d5!important;border-radius:10px!important;padding:11px 12px!important}.nav-drawer .tab:hover,.nav-drawer .tab.active{background:#172238!important;color:#fff!important;box-shadow:none!important}
.app-pages{display:block}.page{display:none}.page.active{display:block}.page:not(#page-strips){direction:rtl;background:#101829;border:1px solid var(--v18-line);border-radius:20px;padding:17px;box-shadow:inset 0 1px #ffffff06}.secondary-ui .account-card,.secondary-ui .power-hero,.secondary-ui .quick-grid,.secondary-ui .search-box{display:none}.secondary-ui .app-header{margin-bottom:16px}.secondary-ui .fab-add{display:none}
#managedStrips{display:grid!important;grid-template-columns:1fr!important;gap:15px!important}
.strip-card{border-radius:19px;background:linear-gradient(160deg,#101828,#0e1625);padding:15px 14px 13px;overflow:visible;transition:.15s ease}.strip-card.offline{opacity:.72}.strip-card.disabled{opacity:.7}
.strip-card-head{display:flex;align-items:center;gap:9px}.strip-status-dot{width:8px;height:8px;border-radius:99px;background:var(--v18-green);box-shadow:0 0 12px #31df7dcc;flex:none}.strip-card.offline .strip-status-dot{background:#788196;box-shadow:none}.strip-title{font-size:19px;font-weight:850;min-width:0;max-width:52%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.online-pill{font:700 9px/1 ui-monospace,SFMono-Regular,monospace;letter-spacing:1px;padding:6px 9px;border-radius:999px;color:#69e5a0;border:1px solid #255c49;background:#102b25;text-transform:uppercase}.online-pill.offline{color:#929aad;border-color:#343e51;background:#161d2a}
.gear-btn{margin-left:auto;width:33px;height:33px;border:0;background:transparent;color:#8993a8;font-size:19px;cursor:pointer;border-radius:9px}.gear-btn:hover{background:#182238;color:#fff}
.strip-subrow{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:9px 0 13px;color:#848da3;font:500 11px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace}.strip-subrow .strip-watts{color:var(--v18-green);white-space:nowrap}
.outlet-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.outlet-tile{min-height:116px;border:1px solid #202a3d;background:#141d2f;border-radius:15px;padding:12px;cursor:pointer;position:relative;transition:border-color .15s,background .15s,transform .15s}.outlet-tile:hover{transform:translateY(-1px)}.outlet-tile.on{background:linear-gradient(145deg,#15322e,#172335);border-color:#287151;box-shadow:inset 0 0 0 1px #31df7d10}.outlet-tile.unavailable{cursor:not-allowed;opacity:.55;transform:none}
.socket-circle{width:35px;height:35px;border-radius:50%;display:grid;place-items:center;border:2px solid #38445c;color:#667087;font-size:16px;margin-bottom:12px}.outlet-tile.on .socket-circle{border-color:var(--v18-green);color:var(--v18-green);box-shadow:0 0 15px #31df7d22}
.outlet-name{font-size:13px;font-weight:780;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.outlet-state{margin-top:6px;color:#737d94;font:700 10px/1 ui-monospace,SFMono-Regular,monospace}.outlet-tile.on .outlet-state{color:var(--v18-green)}.outlet-power{margin-top:6px;color:var(--v18-green);font:750 12px/1 ui-monospace,SFMono-Regular,monospace}.outlet-tile:not(.on) .outlet-power{display:none}
.strip-bulk{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}.bulk-btn{height:45px;border-radius:14px;border:1px solid #202a3d;background:#111928;color:#697389;font-weight:800;font-size:12px;cursor:pointer}.bulk-btn.on{border-color:#277451;background:linear-gradient(145deg,#17382f,#17312e);color:var(--v18-green)}.bulk-btn:disabled{opacity:.42;cursor:not-allowed}
.strip-details{margin-top:10px;border-top:1px solid #1d2739;padding-top:9px}.strip-details summary{cursor:pointer;color:#6f7a91;font-size:10px;list-style:none}.strip-details summary::-webkit-details-marker{display:none}
.strip-menu-wrap{position:relative}.strip-menu-wrap .device-menu-pop{left:auto;right:0;bottom:auto;top:38px}
.fab-add{position:fixed;z-index:60;right:max(18px,calc((100vw - 760px)/2 + 18px));bottom:24px;height:53px;padding:0 24px;border:0;border-radius:27px;background:var(--v18-green);color:#092016;font-weight:900;font-size:14px;box-shadow:0 16px 35px #31df7d35;cursor:pointer}.fab-add:hover{filter:brightness(1.07)}
body.bright-ui{--v18-card:#182238;--v18-card2:#1b2740}.bright-ui .power-hero,.bright-ui .strip-card,.bright-ui .account-card{filter:brightness(1.08)}
.devices-empty{border-color:#273249!important;background:#101829!important;border-radius:18px!important;color:#818ba3!important}
.toast{direction:rtl}
@media(max-width:520px){.shell{padding:18px 16px 92px!important}.app-header h1{font-size:29px}.icon-btn{width:41px;height:41px}.quick-grid{gap:7px}.quick-card{height:80px}.hero-value span{font-size:43px}.hero-meta{gap:11px}.strip-title{font-size:18px;max-width:48%}.outlet-grid{gap:9px}.outlet-tile{min-height:113px}.fab-add{right:17px;bottom:20px}}
@media(min-width:761px){.strip-card{padding:18px}.outlet-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.outlet-tile{min-height:125px}.quick-card>span:last-child{font-size:11.5px}}

</style></head><body><div class="shell">
<header class="app-header">
  <div>
    <div class="live-kicker"><span class="live-dot"></span> VOLTRA LIVE</div>
    <h1 id="screenTitle">My strips</h1>
  </div>
  <div class="header-actions">
    <button class="icon-btn" onclick="refresh()" title="Refresh" aria-label="Refresh">↻</button>
    <button class="icon-btn" onclick="toggleDisplayMode()" title="Display" aria-label="Display">☼</button>
    <button class="icon-btn" onclick="toggleNav()" title="Menu" aria-label="Menu">⋮</button>
  </div>
</header>

<section class="account-card" onclick="goTab('advanced')">
  <div class="avatar">VL</div>
  <div class="account-copy">
    <strong>Voltra Local</strong>
    <span id="accountVersion">Local power manager</span>
  </div>
  <span class="chevron">›</span>
</section>

<section class="power-hero">
  <div class="hero-label">Total power right now</div>
  <div class="hero-value"><span id="statPower">0.0</span><small>W</small></div>
  <div class="hero-meta">
    <span><b id="statOnline">0</b> strips online</span>
    <span><b id="outletOnCount">0</b>/<b id="outletTotalCount">0</b> outlets on</span>
    <span><b id="planCount">0</b> plans active</span>
  </div>
</section>

<section class="quick-grid">
  <button class="quick-card" onclick="goTab('energy')"><span class="quick-icon">▥</span><span>Consumption</span></button>
  <button class="quick-card" onclick="goTab('automation');loadAutomation()"><span class="quick-icon">◷</span><span>Schedules</span></button>
  <button class="quick-card" onclick="goTab('automation');loadAutomation()"><span class="quick-icon">ϟ</span><span>Power automation</span></button>
  <button class="quick-card" onclick="goTab('mapping')"><span class="quick-icon">⌘</span><span>Rooms</span></button>
</section>

<label class="search-box">
  <span>⌕</span>
  <input id="stripSearch" type="search" placeholder="Search strips and outlets" oninput="setStripSearch(this.value)">
</label>

<div class="compat-stats" aria-hidden="true">
  <span id="statActive">0</span><span id="statPending">0</span><span id="statMapped">0</span>
  <span id="pendingTabCount">0</span><span id="modeBadge"></span><span id="connectionBadge"></span>
</div>

<nav id="navDrawer" class="nav-drawer">
  <button class="tab active" data-page="strips">My strips</button>
  <button class="tab" data-page="discover">Add strip</button>
  <button class="tab" data-page="mapping">Rooms & mapping</button>
  <button class="tab" data-page="network">Network setup</button>
  <button class="tab" data-page="automation">Automation</button>
  <button class="tab" data-page="energy">Energy</button>
  <button class="tab" data-page="advanced">Advanced</button>
</nav>

<main class="app-pages">
<div id="page-strips" class="page active">
  <div id="managedStrips"></div>
</div>
<div id="page-discover" class="page"><div class="section-title"><div><h2>اكتشاف مشترك جديد</h2><div class="muted">Voltra يكتشف المشترك تلقائيًا عند اتصاله بـ TCP 10086. اكتب اسمًا فقط ثم اضغط إضافة.</div></div><button class="btn ghost" onclick="refresh()">تحديث</button></div><div id="pendingStrips"></div><div class="notice">لو المشترك لا يظهر هنا، استخدم تبويب <b>إعداد الشبكة</b> لتوجيهه إلى IP جهاز PlayZone. لا نعمل LAN Scan ولا نخمن عنوان المشترك.</div></div>
<div id="page-mapping" class="page"><div class="section-title"><div><h2>ربط الشاشات بأجهزة PlayStation</h2><div class="muted">كل جهاز يرتبط بمخرج واحد. المشتركات المعطلة لا تظهر كاختيار جديد، لكن ربطها القديم يظل محفوظًا.</div></div></div><div id="mappings"></div></div>
<div id="page-network" class="page"><h2>إعداد مشترك على شبكة Wi‑Fi</h2><div class="notice">استخدم هذه الخطوة فقط عند تجهيز مشترك جديد أو تغيير الشبكة. جهاز السيرفر لازم يكون قادرًا على الوصول إلى شبكة <b>TONLY_TAP_xxxxxxx</b> وقت الإعداد.</div><div class="formline"><input id="wifiSsid" class="field" placeholder="اسم شبكة 2.4GHz"><input id="wifiPassword" class="field" type="password" placeholder="كلمة المرور"><input id="serverIp" class="field" placeholder="IP جهاز PlayZone مثل 192.168.1.65"></div><button class="btn blue" onclick="provision()">إرسال إعدادات الشبكة</button><p class="muted">بعد الإرسال يعمل المشترك Reboot ويتصل تلقائيًا بالسيرفر على TCP 10086، ثم يظهر في “إضافة مشترك”.</p></div>
<div id="page-automation" class="page"><div class="section-title"><div><h2>الجداول والـ Offline Queue</h2><div class="muted">الجداول تعمل محليًا بدون إنترنت طالما Voltra Server شغال.</div></div><button class="btn ghost" onclick="loadAutomation()">تحديث</button></div><div class="formline"><select id="scheduleTarget" class="field"></select><input id="scheduleTime" class="field" type="time" value="23:00"><select id="scheduleAction" class="field"><option value="off">إيقاف</option><option value="on">تشغيل</option></select></div><div class="actions"><button class="btn blue" onclick="createSchedule()">إضافة جدول يومي</button><button class="btn ghost" onclick="clearQueue()">مسح الأوامر المعلقة</button></div><div id="automationList" style="margin-top:14px"></div></div>
<div id="page-energy" class="page"><div class="section-title"><div><h2>استهلاك الطاقة</h2><div class="muted">ملخص مبني على العينات المحلية المخزنة في السيرفر.</div></div></div><div class="formline"><select id="energyTarget" class="field"></select><select id="energyHours" class="field"><option value="24">آخر 24 ساعة</option><option value="168">آخر 7 أيام</option><option value="720">آخر 30 يوم</option></select><button class="btn blue" onclick="loadEnergy()">عرض</button></div><div id="energyResult" class="good">اختر مشترك واضغط عرض.</div></div>
<div id="page-advanced" class="page"><div class="section-title"><div><h2>المشتركات غير المستخدمة / السجل</h2><div class="muted">المتجاهلة أو المستبدلة أو التي تمت إزالتها. الاحتفاظ بالسجل يمنع الالتباس إذا ظل جهاز قديم متصلًا بالشبكة.</div></div></div><div id="historyStrips" class="history"></div><div class="danger-zone"><b>ملاحظة أمان</b><div class="muted" style="margin-top:6px">Voltra مخصص لفصل كهرباء الشاشة فقط. لا توصل جهاز PS4 نفسه على Outlet يتم التحكم فيه تلقائيًا.</div></div></div>
</main><button class="fab-add" onclick="goTab('discover')">＋ Add strip</button><div class="toast" id="toast"></div>
<div class="modal" id="renameModal"><div class="modalbox"><h3>تغيير اسم المشترك</h3><input class="field" id="renameValue"><div style="margin-top:12px" class="actions"><button class="btn blue" onclick="saveRename()">حفظ</button><button class="btn ghost" onclick="closeModal('renameModal')">إلغاء</button></div></div></div>
<div class="modal" id="replaceModal"><div class="modalbox"><h3>استبدال المشترك</h3><p class="muted">سيتم نقل نفس ربط الـOutlets إلى المشترك الجديد، وتعطيل القديم ووضعه في السجل.</p><div id="replaceOldInfo" class="good"></div><select id="replaceSelect" class="field"></select><div style="margin-top:12px" class="actions"><button class="btn amber" onclick="confirmReplace()">استبدال ونقل الربط</button><button class="btn ghost" onclick="closeModal('replaceModal')">إلغاء</button></div></div></div>
</div>
<script>
let data={strips:[],ps4_devices:[],mappings:{},summary:{}};let automationData={schedules:{},rules:{},queue:[]};let renameMac=null;let replaceOldMac=null;let stripSearchValue='';const mappingDrafts={};const mappingDirty=new Set();const mappingSaving=new Set();
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const playzoneMode=location.pathname==='/voltra-console'||location.pathname.startsWith('/voltra-console/');
async function api(path,opt={}){const token=playzoneMode?(localStorage.getItem('playzone_token')||''):'';const headers={'content-type':'application/json',...(opt.headers||{})};if(playzoneMode&&token)headers['Authorization']='Bearer '+token;const requestPath=playzoneMode?path.replace(/^\/voltra\/api/,'/api/root/voltra-console'):path;const r=await fetch(requestPath,{...opt,headers});const t=await r.text();let v={};try{v=t?JSON.parse(t):{}}catch{v={raw:t}}if(r.status===401&&playzoneMode)throw new Error(v.detail||v.error||'جلسة PlayZone غير صالحة أو الحساب ليس ROOT');if(!r.ok)throw new Error(v.detail||v.error||r.statusText);return v}
function toast(msg,bad=false){const t=document.getElementById('toast');t.textContent=msg;t.style.display='block';t.style.borderColor=bad?'#9b3c48':'#376082';setTimeout(()=>t.style.display='none',3600)}
function mappingFor(mac,outlet){return Object.entries(data.mappings||{}).find(([id,m])=>m.mac===mac&&Number(m.outlet)===Number(outlet))?.[0]||null}
function ps4Name(id){return data.ps4_devices.find(x=>String(x.id)===String(id))?.name||id}
function psLogo(){return `<span class="ps-logo" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 8v24l8 3V16.8c0-2.4 2.1-3.1 4-2.5 2.3.7 3.6 2.2 3.6 4.4 0 3.2-2.5 5.4-6.1 4.4v7.3c8.5 2.1 13.5-2 13.5-10.3 0-8.5-7.6-11.2-15-13.4L18 8Z" fill="white"/><path d="M7 34.8c-2.2 1-2.6 2.5-.8 3.1 2.4.8 6.7.6 10.2-.5l4.1-1.3v-5.3l-4.4 1.4c-3.1 1-6.5 1.8-9.1 2.6Zm20.6-2.4v5.5c4.3-1.3 8.8-2.3 12.5-1.7 1.8.3 2.1 1.2.2 2.1-3.1 1.5-8.5 2.3-12.7 3.7v3.7c6.7-2.1 13.1-3.8 16.7-6.4 2.9-2.1 1.8-4.5-2.2-5.1-3.8-.6-9.1-.1-14.5 1.3v-3.1Z" fill="white"/></svg></span>`}
function stripByMac(mac){return data.strips.find(x=>x.mac===mac)}
function goTab(name){
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.page===name));
  document.querySelectorAll('.page').forEach(x=>x.classList.toggle('active',x.id==='page-'+name));
  document.body.classList.toggle('secondary-ui',name!=='strips');
  const titles={strips:'My strips',discover:'Add strip',mapping:'Rooms & mapping',network:'Network setup',automation:'Automation',energy:'Consumption',advanced:'Advanced'};
  const title=document.getElementById('screenTitle');if(title)title.textContent=titles[name]||'Voltra';
  document.getElementById('navDrawer')?.classList.remove('show');
  if(name==='automation')loadAutomation();
}
function toggleNav(){document.getElementById('navDrawer')?.classList.toggle('show')}
function toggleDisplayMode(){document.body.classList.toggle('bright-ui');localStorage.setItem('voltra_bright_ui',document.body.classList.contains('bright-ui')?'1':'0')}
function setStripSearch(value){stripSearchValue=String(value||'').trim().toLowerCase();renderManaged()}
function closeModal(id){document.getElementById(id).classList.remove('show')}
function activeStrips(){return data.strips.filter(s=>s.managed&&(s.state==='active'||s.state==='disabled'))}
function pendingStrips(){return data.strips.filter(s=>s.state==='pending')}
function candidateReplacementStrips(oldMac){return data.strips.filter(s=>s.mac!==oldMac&&s.online&&!s.managed&&['pending','ignored','removed'].includes(s.state))}
function render(forceMappings=false){
  const q=data.summary||{};
  statActive.textContent=q.active_strips??activeStrips().length;
  statOnline.textContent=q.online_strips??activeStrips().filter(s=>s.online).length;
  statPending.textContent=q.pending_strips??pendingStrips().length;
  statMapped.textContent=q.mapped_devices??Object.keys(data.mappings||{}).length;
  statPower.textContent=Number(q.total_power_w||0).toFixed(1);
  pendingTabCount.textContent=pendingStrips().length;
  modeBadge.textContent=data.mode==='demo'?'DEMO MODE':'REAL HARDWARE';
  connectionBadge.textContent='● Voltra connected';
  const active=activeStrips();
  let total=0,on=0;
  for(const s of active){for(const o of (s.outlets||[])){total++;if(o.relay)on++}}
  outletOnCount.textContent=on;
  outletTotalCount.textContent=total||active.length*4;
  planCount.textContent=Object.values(automationData.schedules||{}).filter(x=>x.enabled!==false).length;
  accountVersion.textContent='v'+(data.version||'—')+' · Local mini server';
  renderManaged();renderPending();renderMappings(forceMappings);renderHistory();renderTargets();
}
function stateLabel(s){if(s.state==='disabled')return '<span class="status disabled">● معطل</span>';return `<span class="status ${s.online?'online':'offline'}">● ${s.online?'Online':'Offline'}</span>`}
function renderManaged(){
  const root=document.getElementById('managedStrips');
  let arr=activeStrips();
  if(stripSearchValue){
    arr=arr.filter(s=>{
      const mapped=[];
      for(let n=1;n<=4;n++){const id=mappingFor(s.mac,n);if(id)mapped.push(ps4Name(id))}
      const hay=[s.name,s.mac,s.room,...mapped].filter(Boolean).join(' ').toLowerCase();
      return hay.includes(stripSearchValue);
    });
  }
  if(!arr.length){
    root.innerHTML='<div class="devices-empty"><b>No strips found</b><br><span>'+(stripSearchValue?'Try another search.':'Add your first strip to start controlling outlets.')+'</span></div>';
    return;
  }
  root.innerHTML=arr.map(s=>{
    const can=s.online&&s.enabled&&s.state==='active';
    const status=s.state==='disabled'?'DISABLED':(s.online?'ONLINE':'OFFLINE');
    let outs='';
    for(let n=1;n<=4;n++){
      const o=(s.outlets||[]).find(x=>Number(x.channel)===n);
      const pid=mappingFor(s.mac,n);
      const name=pid?ps4Name(pid):`Outlet ${n}`;
      const isOn=!!o?.relay;
      outs+=`<div class="outlet-tile ${isOn?'on':''} ${can?'':'unavailable'}" ${can?`onclick="powerOutlet('${s.mac}',${n},${!isOn})"`:''}>
        <div class="socket-circle">Ⅱ</div>
        <div class="outlet-name" dir="auto">${esc(name)}</div>
        <div class="outlet-state">${isOn?'ON':'OFF'}</div>
        <div class="outlet-power">${Number(o?.power_w||0).toFixed(1)} W</div>
      </div>`;
    }
    const room=s.room?esc(s.room):'Local strip';
    const health=s.health?.status?String(s.health.status).replaceAll('_',' '):'unknown';
    return `<section class="strip-card ${!s.online?'offline':''} ${s.state==='disabled'?'disabled':''}">
      <div class="strip-card-head">
        <span class="strip-status-dot"></span>
        <div class="strip-title" dir="auto">${esc(s.name||s.mac)}</div>
        <span class="online-pill ${s.online?'':'offline'}">${status}</span>
        <details class="device-menu strip-menu-wrap">
          <summary class="gear-btn">⚙</summary>
          <div class="device-menu-pop">
            <button onclick="openRename('${s.mac}')">Rename</button>
            <button onclick="toggleStrip('${s.mac}',${!s.enabled})">${s.enabled?'Disable':'Enable'}</button>
            <button onclick="openReplace('${s.mac}')">Replace strip</button>
            <button class="danger" onclick="removeStrip('${s.mac}')">Remove strip</button>
          </div>
        </details>
      </div>
      <div class="strip-subrow"><span>${room} · ${esc(health)}</span><span class="strip-watts">${Number(s.total_power_w||0).toFixed(1)} W</span></div>
      <div class="outlet-grid">${outs}</div>
      <div class="strip-bulk">
        <button class="bulk-btn on" ${can?'':'disabled'} onclick="turnStrip('${s.mac}',true)">Turn all on</button>
        <button class="bulk-btn" ${can?'':'disabled'} onclick="turnStrip('${s.mac}',false)">Turn all off</button>
      </div>
      <details class="strip-details"><summary>Device details · ${s.voltage_v!=null?Number(s.voltage_v).toFixed(1)+' V':'—'} · Wi-Fi ${s.wifi_rssi_dbm!=null?s.wifi_rssi_dbm+' dBm':'—'} · Health ${s.health?.score??'—'}%</summary>
        <div class="kv"><span class="muted">MAC</span><span class="mono">${esc(s.mac)}</span><span class="muted">IP</span><span class="mono">${esc(s.last_ip||'-')}</span><span class="muted">Firmware</span><span class="mono">${esc(s.firmware_version||'-')}</span></div>
      </details>
    </section>`;
  }).join('');
}
function renderPending(){const root=document.getElementById('pendingStrips'),arr=pendingStrips().filter(s=>s.online);if(!arr.length){root.innerHTML='<div class="empty"><b>في انتظار مشترك جديد...</b><br><span class="muted">أول ما المشترك يتصل بـ TCP 10086 هيظهر هنا تلقائيًا.</span></div>';return}root.innerHTML='<div class="pending-grid">'+arr.map(s=>`<div class="pending"><div class="strip-head"><div><div class="strip-name">تم اكتشاف مشترك جديد</div><div class="muted">Online الآن</div></div><span class="status online">● Online</span></div><details class="advanced"><summary>بيانات الجهاز</summary><div class="kv"><span class="muted">MAC</span><span class="mono">${esc(s.mac)}</span><span class="muted">IP</span><span class="mono">${esc(s.last_ip||'-')}</span><span class="muted">Firmware</span><span class="mono">${esc(s.firmware_version||'-')}</span></div></details><input id="adopt-${s.mac}" class="field" style="margin-top:12px" value="مشترك ${esc(s.mac.slice(-4))}" placeholder="اسم المشترك"><div class="actions" style="margin-top:10px"><button class="btn green" onclick="adoptStrip('${s.mac}')">إضافة المشترك</button><button class="btn ghost" onclick="ignoreStrip('${s.mac}')">تجاهل</button></div></div>`).join('')+'</div>'}
function availableOptions(currentId){let html='<option value="">— غير مربوط —</option>';for(const s of activeStrips().filter(x=>x.enabled&&x.state==='active')){for(let n=1;n<=4;n++){const assigned=mappingFor(s.mac,n);if(assigned&&String(assigned)!==String(currentId))continue;html+=`<option value="${s.mac}:${n}">${esc(s.name||s.mac)} / Outlet ${n}${s.online?'':' (Offline)'}</option>`}}return html}
function savedMappingValue(id){const m=(data.mappings||{})[id];return m?`${m.mac}:${m.outlet}`:''}
function mappingEditorLocked(){const a=document.activeElement;return mappingDirty.size>0||!!(a&&a.matches&&a.matches('#mappings select'))}
function stageMapping(encoded){const id=decodeURIComponent(encoded),el=document.getElementById(`map-${encodeURIComponent(id)}`);if(!el)return;mappingDrafts[String(id)]=el.value;mappingDirty.add(String(id));const row=el.closest('.mapping');if(row){row.classList.add('mapping-dirty');const info=row.children[0];if(info&&!info.querySelector('.mapping-note')){const note=document.createElement('div');note.className='mapping-note';note.textContent='● تغيير غير محفوظ';info.appendChild(note)}const actions=row.querySelector('.mapping-actions'),b=row.querySelector('.mapping-save');if(b){b.textContent='حفظ التغيير';b.classList.remove('blue');b.classList.add('green')}if(actions&&!actions.querySelector('.mapping-cancel')){const c=document.createElement('button');c.type='button';c.className='btn ghost mapping-cancel';c.textContent='إلغاء';c.onclick=()=>cancelMapping(encodeURIComponent(id));actions.appendChild(c)}}}
function cancelMapping(encoded){const id=String(decodeURIComponent(encoded));delete mappingDrafts[id];mappingDirty.delete(id);renderMappings(true)}
function renderMappings(force=false){const root=document.getElementById('mappings');if(!force&&root.children.length&&mappingEditorLocked())return;if(!data.ps4_devices.length){root.innerHTML='<div class="empty">أجهزة PlayZone ستظهر هنا تلقائيًا بعد المزامنة.</div>';return}root.innerHTML=data.ps4_devices.map(p=>{const id=String(p.id),m=data.mappings[p.id],strip=m?stripByMac(m.mac):null,dirty=mappingDirty.has(id);return `<div class="mapping ${dirty?'mapping-dirty':''}" data-map-id="${esc(id)}"><div><b>${esc(p.name)}</b><div class="muted">${esc(p.id)}</div>${m&&strip?.state==='disabled'?'<span class="status disabled">المشترك معطل — الربط محفوظ</span>':''}${dirty?'<div class="mapping-note">● تغيير غير محفوظ</div>':''}</div><select class="field" id="map-${encodeURIComponent(p.id)}" onchange="stageMapping('${encodeURIComponent(p.id)}')">${availableOptions(p.id)}</select><div class="mapping-actions"><button class="btn ${dirty?'green':'blue'} mapping-save" onclick="saveMapping('${encodeURIComponent(p.id)}')">${dirty?'حفظ التغيير':'حفظ الربط'}</button>${dirty?`<button class="btn ghost" onclick="cancelMapping('${encodeURIComponent(p.id)}')">إلغاء</button>`:''}</div></div>`}).join('');for(const p of data.ps4_devices){const id=String(p.id),m=data.mappings[p.id],el=document.getElementById(`map-${encodeURIComponent(p.id)}`);if(!el)continue;let value=mappingDirty.has(id)?(mappingDrafts[id]??''):savedMappingValue(p.id);if(value){let opt=[...el.options].find(o=>o.value===value);if(!opt&&m&&value===`${m.mac}:${m.outlet}`){opt=document.createElement('option');opt.value=value;opt.textContent=`الربط الحالي: ${stripByMac(m.mac)?.name||m.mac} / Outlet ${m.outlet}`;el.prepend(opt)}if(opt)el.value=value}else el.value=''}}
function renderHistory(){const root=document.getElementById('historyStrips');const arr=data.strips.filter(s=>!s.managed&&!['pending'].includes(s.state));if(!arr.length){root.innerHTML='<div class="empty">لا يوجد سجل لمشتركات متجاهلة أو مستبدلة أو تمت إزالتها.</div>';return}const labels={ignored:'متجاهل',removed:'تمت إزالته',replaced:'تم استبداله'};root.innerHTML=arr.map(s=>`<div class="history-item"><div class="strip-head"><div><b>${esc(s.name||s.mac)}</b><div class="muted">${labels[s.state]||esc(s.state)} ${s.online?'· Online الآن':''}</div></div><div class="actions">${s.online?`<button class="btn green sm" onclick="adoptStrip('${s.mac}',true)">إضافة من جديد</button>`:''}</div></div><details class="advanced"><summary>التفاصيل</summary><div class="kv"><span>MAC</span><span class="mono">${esc(s.mac)}</span><span>IP</span><span class="mono">${esc(s.last_ip||'-')}</span>${s.replaced_by?`<span>استُبدل بـ</span><span class="mono">${esc(s.replaced_by)}</span>`:''}</div></details></div>`).join('')}
function renderTargets(){const outletOptions=activeStrips().map(s=>{let x='';for(let n=1;n<=4;n++)x+=`<option value="${s.mac}:${n}">${esc(s.name||s.mac)} / Outlet ${n}</option>`;return x}).join('');if(document.getElementById('scheduleTarget'))scheduleTarget.innerHTML=outletOptions||'<option value="">لا يوجد مشترك فعال</option>';if(document.getElementById('energyTarget'))energyTarget.innerHTML=activeStrips().map(s=>`<option value="${s.mac}">${esc(s.name||s.mac)}</option>`).join('')||'<option value="">لا يوجد مشترك فعال</option>'}
async function loadAutomation(){try{
  automationData=await api('/voltra/api/automation');
  const schedules=Object.values(automationData.schedules||{}),queued=automationData.queue||[];
  if(document.getElementById('planCount'))planCount.textContent=schedules.filter(x=>x.enabled!==false).length;
  automationList.innerHTML=`<div class="good">جداول: ${schedules.length} · أوامر معلقة: ${queued.length}</div>`+schedules.map(s=>`<div class="history-item"><div class="strip-head"><div><b>${esc(stripByMac(s.mac)?.name||s.mac)} / Outlet ${s.outlet}</b><div class="muted">${s.time} · ${s.on?'تشغيل':'إيقاف'} · Offline: ${esc(s.offline_policy)}</div></div><button class="btn red sm" onclick="deleteSchedule('${s.id}')">حذف</button></div></div>`).join('');
}catch(e){toast(e.message,true)}}
async function createSchedule(){const v=scheduleTarget.value;if(!v)return toast('اختر مخرج',true);const cut=v.lastIndexOf(':'),mac=v.slice(0,cut),outlet=Number(v.slice(cut+1));try{await api('/voltra/api/schedules',{method:'POST',body:JSON.stringify({mac,outlet,on:scheduleAction.value==='on',time:scheduleTime.value,days:[0,1,2,3,4,5,6],offline_policy:'queue'})});await loadAutomation();toast('تمت إضافة الجدول')}catch(e){toast(e.message,true)}}
async function deleteSchedule(id){try{await api('/voltra/api/schedules/'+encodeURIComponent(id),{method:'DELETE'});await loadAutomation();toast('تم حذف الجدول')}catch(e){toast(e.message,true)}}
async function clearQueue(){try{const r=await api('/voltra/api/queue',{method:'DELETE'});await loadAutomation();toast('تم مسح '+(r.cleared||0)+' أمر')}catch(e){toast(e.message,true)}}
async function loadEnergy(){if(!energyTarget.value)return toast('اختر مشترك',true);try{const r=await api('/voltra/api/energy?mac='+encodeURIComponent(energyTarget.value)+'&hours='+encodeURIComponent(energyHours.value));energyResult.innerHTML=`<b>${Number(r.energy_kwh||0).toFixed(3)} kWh</b><br>متوسط القدرة: ${Number(r.average_power_w||0).toFixed(1)} W · أعلى قدرة: ${Number(r.max_power_w||0).toFixed(1)} W · عينات: ${r.samples||0}`}catch(e){toast(e.message,true)}}
async function liveLoop(){if(playzoneMode)return;for(;;){try{const r=await fetch('/voltra/api/events',{headers:{Accept:'text/event-stream'}});if(!r.ok)throw new Error('SSE '+r.status);const reader=r.body.getReader(),decoder=new TextDecoder();let buf='';for(;;){const x=await reader.read();if(x.done)break;buf+=decoder.decode(x.value,{stream:true});let cut;while((cut=buf.indexOf('\n\n'))>=0){const packet=buf.slice(0,cut);buf=buf.slice(cut+2);if(packet.includes('data:')){await refresh();if(document.getElementById('page-automation')?.classList.contains('active'))await loadAutomation()}}}}catch(e){}await new Promise(r=>setTimeout(r,2000))}}

async function refresh(forceMappings=false){try{data=await api('/voltra/api/overview');render(forceMappings)}catch(e){connectionBadge.textContent='● API ERROR';connectionBadge.className='badge real';toast(e.message,true)}}
async function adoptStrip(mac,again=false){const el=document.getElementById('adopt-'+mac);const current=stripByMac(mac);const name=el?.value.trim()||current?.name||`مشترك ${mac.slice(-4)}`;try{await api(`/voltra/api/strips/${mac}/adopt`,{method:'POST',body:JSON.stringify({name})});await refresh();goTab('strips');toast(again?'تمت إعادة إضافة المشترك':'تمت إضافة المشترك بنجاح')}catch(e){toast(e.message,true)}}
async function ignoreStrip(mac){if(!confirm('تجاهل هذا المشترك؟ لن يتم التحكم فيه، ويمكن إضافته من جديد لاحقًا.'))return;try{await api(`/voltra/api/strips/${mac}/ignore`,{method:'POST',body:'{}'});await refresh();toast('تم تجاهل المشترك')}catch(e){toast(e.message,true)}}
async function toggleStrip(mac,enabled){const s=stripByMac(mac);if(!enabled&&!confirm(`تعطيل ${s?.name||mac} مؤقتًا؟ الربط سيظل محفوظًا لكن أوامر الطاقة ستتوقف.`))return;try{await api(`/voltra/api/strips/${mac}/enabled`,{method:'POST',body:JSON.stringify({enabled})});await refresh();toast(enabled?'تم تفعيل المشترك':'تم تعطيل المشترك')}catch(e){toast(e.message,true)}}
async function removeStrip(mac){const s=stripByMac(mac),count=s?.mapped_count||0;if(!confirm(`إزالة ${s?.name||mac} من Voltra؟\n\nسيتم فك ${count} ربط/روابط مرتبطة به. سجل المشترك سيظل ظاهرًا في قسم متقدم لمنع إعادة اكتشافه فورًا أثناء اتصاله.`))return;try{const r=await api(`/voltra/api/strips/${mac}`,{method:'DELETE'});await refresh();toast(`تمت الإزالة وفك ${r.removed_mappings?.length||0} ربط`)}catch(e){toast(e.message,true)}}
function openRename(mac){renameMac=mac;renameValue.value=stripByMac(mac)?.name||'';renameModal.classList.add('show')}async function saveRename(){try{await api(`/voltra/api/strips/${renameMac}`,{method:'PUT',body:JSON.stringify({name:renameValue.value})});closeModal('renameModal');await refresh();toast('تم تغيير الاسم')}catch(e){toast(e.message,true)}}
function openReplace(mac){replaceOldMac=mac;const s=stripByMac(mac),c=candidateReplacementStrips(mac);replaceOldInfo.textContent=`${s?.name||mac} — سيتم نقل ${s?.mapped_count||0} ربط بنفس أرقام الـOutlets.`;replaceSelect.innerHTML=c.length?c.map(x=>`<option value="${x.mac}">${esc(x.name||('مشترك '+x.mac.slice(-4)))} — ${esc(x.last_ip||x.mac)}</option>`).join(''):'<option value="">لا يوجد مشترك جديد Online جاهز للاستبدال</option>';replaceModal.classList.add('show')}
async function confirmReplace(){const newMac=replaceSelect.value;if(!newMac)return toast('وصل المشترك الجديد أولًا حتى يظهر في القائمة',true);const old=stripByMac(replaceOldMac),nw=stripByMac(newMac);if(!confirm(`استبدال ${old?.name||replaceOldMac} بالمشترك ${nw?.name||newMac} ونقل الربط؟`))return;try{const r=await api(`/voltra/api/strips/${replaceOldMac}/replace`,{method:'POST',body:JSON.stringify({new_mac:newMac})});closeModal('replaceModal');await refresh();toast(`تم الاستبدال ونقل ${r.transferred_devices?.length||0} جهاز`)}catch(e){toast(e.message,true)}}
async function turnStrip(mac,on){
  const s=stripByMac(mac);if(!s)return;
  if(!confirm((on?'Turn all outlets ON in ':'Turn all outlets OFF in ')+(s.name||mac)+'?'))return;
  try{
    for(let n=1;n<=4;n++){
      const o=(s.outlets||[]).find(x=>Number(x.channel)===n);
      if(Boolean(o?.relay)===Boolean(on))continue;
      await api(`/voltra/api/strips/${mac}/outlets/${n}/state`,{method:'POST',body:JSON.stringify({on})});
    }
    await refresh();toast(on?'All outlets are on':'All outlets are off');
  }catch(e){toast(e.message,true);await refresh()}
}
async function powerOutlet(mac,outlet,on){const s=stripByMac(mac);if(!confirm(`${on?'تشغيل':'إيقاف'} Outlet ${outlet} في ${s?.name||mac}؟\nالتحكم مخصص للشاشة فقط.`))return;try{await api(`/voltra/api/strips/${mac}/outlets/${outlet}/state`,{method:'POST',body:JSON.stringify({on})});await refresh();toast('تم تنفيذ الأمر')}catch(e){toast(e.message,true)}}
async function saveMapping(encoded){const id=String(decodeURIComponent(encoded)),el=document.getElementById(`map-${encodeURIComponent(id)}`);if(!el||mappingSaving.has(id))return;const v=el.value,row=el.closest('.mapping'),btn=row?.querySelector('.mapping-save');mappingSaving.add(id);el.disabled=true;if(btn){btn.disabled=true;btn.textContent='جاري الحفظ...'}try{if(!v)await api(`/voltra/api/ps4/${encodeURIComponent(id)}/power-mapping`,{method:'DELETE'});else{const cut=v.lastIndexOf(':'),mac=v.slice(0,cut),outlet=v.slice(cut+1);if(cut<1||!outlet)throw new Error('اختيار الربط غير صالح');await api(`/voltra/api/ps4/${encodeURIComponent(id)}/power-mapping`,{method:'PUT',body:JSON.stringify({mac,outlet:Number(outlet)})})}delete mappingDrafts[id];mappingDirty.delete(id);toast('تم حفظ الربط');await refresh(true)}catch(e){el.disabled=false;if(btn){btn.disabled=false;btn.textContent='حفظ التغيير'}toast(e.message,true)}finally{mappingSaving.delete(id)}}
async function provision(){if(!wifiSsid.value||!serverIp.value)return toast('اكتب اسم شبكة Wi‑Fi وIP جهاز PlayZone',true);if(!confirm('تأكد أن جهاز PlayZone قادر على الوصول إلى شبكة TONLY_TAP الخاصة بالمشترك. متابعة؟'))return;try{await api('/voltra/api/provision',{method:'POST',body:JSON.stringify({ssid:wifiSsid.value,password:wifiPassword.value,server_ip:serverIp.value})});wifiPassword.value='';toast('تم إرسال الإعدادات. انتظر Reboot وظهور المشترك في صفحة الإضافة.');setTimeout(()=>{refresh();goTab('discover')},2500)}catch(e){toast(e.message,true)}}
function setupPlayZoneScrollbar(){if(!playzoneMode)return;document.documentElement.classList.add('playzone-embedded');const track=document.createElement('div');track.id='pzVoltraScrollTrack';track.setAttribute('aria-hidden','true');track.innerHTML='<div id="pzVoltraScrollThumb"></div>';document.body.appendChild(track);const thumb=track.firstElementChild;let drag=null;function update(){const s=document.scrollingElement||document.documentElement,total=s.scrollHeight,view=s.clientHeight,max=Math.max(0,total-view);if(total<=view+2){track.classList.add('hidden');return}track.classList.remove('hidden');const th=Math.max(30,Math.round(track.clientHeight*view/total)),travel=Math.max(1,track.clientHeight-th),top=max?Math.round(travel*s.scrollTop/max):0;thumb.style.height=th+'px';thumb.style.transform='translateY('+top+'px)'}thumb.addEventListener('pointerdown',e=>{const s=document.scrollingElement||document.documentElement;drag={id:e.pointerId,y:e.clientY,top:s.scrollTop};thumb.setPointerCapture?.(e.pointerId);track.classList.add('dragging');e.preventDefault()});thumb.addEventListener('pointermove',e=>{if(!drag||drag.id!==e.pointerId)return;const s=document.scrollingElement||document.documentElement,max=Math.max(0,s.scrollHeight-s.clientHeight),travel=Math.max(1,track.clientHeight-thumb.offsetHeight);s.scrollTop=drag.top+((e.clientY-drag.y)/travel)*max;e.preventDefault()});const stop=e=>{if(!drag||(e?.pointerId!=null&&drag.id!==e.pointerId))return;drag=null;track.classList.remove('dragging')};thumb.addEventListener('pointerup',stop);thumb.addEventListener('pointercancel',stop);track.addEventListener('pointerdown',e=>{if(e.target===thumb)return;const s=document.scrollingElement||document.documentElement,r=track.getBoundingClientRect(),ratio=Math.max(0,Math.min(1,(e.clientY-r.top)/Math.max(1,r.height))),max=Math.max(0,s.scrollHeight-s.clientHeight);s.scrollTo({top:ratio*max,behavior:'smooth'})});window.addEventListener('scroll',update,{passive:true});window.addEventListener('resize',update,{passive:true});new ResizeObserver(update).observe(document.documentElement);update()}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>goTab(b.dataset.page));if(localStorage.getItem('voltra_bright_ui')==='1')document.body.classList.add('bright-ui');setupPlayZoneScrollbar();refresh().then(loadAutomation);liveLoop();setInterval(refresh,15000)
</script></body></html>'''
