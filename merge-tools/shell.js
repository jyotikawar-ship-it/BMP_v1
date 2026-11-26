/* ONE PORTAL — every module is on. Home (dashboard) and Approval configuration come from the
   "Dashboard and approval configuration" file; Accounts, account creation, workspaces, deals, plan
   configuration, Catalogs, Plans and Add-on packs come from the "SKU, catalog, plan and add-on pack" file.
   Each screen keeps its own file's styling: <html data-src="b"> switches the file-2 styles on. */
const B_VIEWS = ['home2', 'appr6'];
const PERSONA_SWITCH = ['meera','arun','dev','nikhil'];   // who you can view the portal as; everyone else stays in the data and the workflows
function navItems(){
  const t = T(), tm = isTM();
  return [
    {group:'', items:[
      ['home2','Home','home'],
      ['accounts', t === 'rep' ? 'Workspaces' : 'Accounts', t === 'rep' ? 'layers' : 'building'],   // the embedded account creation review file
      ['work','Actions','inbox', acCount()]
    ]},
    {group:'Setup', items:[
      ['skus','Catalogs','tag'],
      ['packs','Plans','layers'],
      ['addons','Add-on packs','plug'],
      ['access','Team & access','users'],
      can.apprRules() && !tm ? ['appr6','Approval configuration','sliders'] : null,
      ['md','sm','rep','adm','fin','sku'].includes(t) && !tm ? ['targets','Target Configuration','chart'] : null
    ]}
  ];
}
const NAV_PARENT = {work0:'work', account:'accounts', workspace:'accounts', deal:'accounts', journey:'accounts', plan:'accounts', trialcfg:'accounts', home:'home2'};
const LINK_NAME = {workspace:'workspace', account:'account', accounts:'accounts', deal:'deal', payments:'payments', trials:'trials', work:'approvals inbox', catalogue:'catalogue', admin:'settings', access:'team and access'};
const V_ALIAS = {home:'home2', appr:'appr6', appr1b:'appr6', appr2:'appr6', appr2b:'appr6', appr3:'appr6', appr4:'appr6', appr5:'appr6', catalogue:'skus'};
function go(v, params = {}){
  v = V_ALIAS[v] || v;
  if (v === 'admin' && params.tab === 'appr') v = 'appr6';
  if (AC_VIEWS.includes(v)) S._acGo = params;                     // the embedded page opens on what was asked for
  if (!VIEWS[v] && v !== 'work0'){ toast(`This will open the ${LINK_NAME[v] || v} page once the modules are joined.`, 'info'); return; }
  S.route = Object.assign({v}, params); closeOverlay(); document.body.removeAttribute('data-nav'); render(); window.scrollTo(0,0); }
function render(){
  if (V_ALIAS[S.route.v]) S.route = Object.assign({}, S.route, {v:V_ALIAS[S.route.v]});
  if (!VIEWS[S.route.v] && S.route.v !== 'work0') S.route = {v:'home2'};
  try { apCrSync(); } catch (e) { console.error(e); }
  document.documentElement.dataset.src = B_VIEWS.includes(S.route.v) ? 'b' : 'a';
  renderNav();
  if (AC_VIEWS.includes(S.route.v) && AC_PEOPLE.includes(S.user)){ const p = S._acGo; S._acGo = null; acShow(p); return; }
  acHide();
  const fn = AC_VIEWS.includes(S.route.v) ? () => noAccess(S.route.v === 'work' ? 'Actions' : 'Accounts') : S.route.v === 'work0' ? VIEWS.work : VIEWS[S.route.v] || VIEWS.home2;
  let page;
  try { page = fn(); } catch (e) { console.error(e); page = {crumbs:[['Error']], head:'', body: note('dan', 'Something went wrong drawing this page: ' + esc(e.message))}; }
  if (page.redirect) return go(page.redirect.v, page.redirect);
  $('#crumbs').innerHTML = crumbsHtml(page.crumbs || [['Home']]);
  $('#view').innerHTML = (page.head || '') + (page.tabs || '') + `<div class="content" id="content">${page.body || ''}</div>` + (page.actionbar || '');
  page.after && page.after();
  fitRowMenus();
}
/* a row's ⋯ menu: drawn above the next rows, and opens upward when there's no room below it inside its card */
function fitRowMenus(){
  document.querySelectorAll('#view .sk2-catm').forEach(m => { const cell = m.closest('td'); if (cell) cell.style.zIndex = '31';   // its sticky cell sits above the next rows' sticky cells
    const card = m.closest('.sk2-card'); if (!card) return;
    const r = m.getBoundingClientRect(), c = card.getBoundingClientRect();
    if (r.bottom > c.bottom - 4 && !m.classList.contains('up')) m.classList.add('up');
    else if (r.top < c.top + 4 && m.classList.contains('up')) m.classList.remove('up'); });
}
/* the folded sidebar names each icon on hover */
function navTips(){
  const off = document.body.dataset.side === 'off';
  const tip = (el, l) => { if (!el) return; if (off) el.title = l; else el.removeAttribute('title'); };
  document.querySelectorAll('#sidenav .navitem').forEach(b => tip(b, b.querySelector('span:not(.cnt)').textContent));
  tip(document.querySelector('.side-brand'), 'Helo Business');
  tip($('#usercard'), $('#uname').textContent);
}
const renderNavA = renderNav;
renderNav = function(){ renderNavA(); navTips(); };
new MutationObserver(navTips).observe(document.body, {attributes:true, attributeFilter:['data-side']});
