/* =====================================================================
   APPROVAL ENGINE — joins Approval configuration (Admin) to every module that raises a request.
   Each request reads the live rule for its action: the first group whose conditions match decides
   the approval levels, "Otherwise" catches the rest. With no rule for an action, the module keeps
   its own default route (Sales Manager → MD for deals, MD for catalogue and plan changes).
   A request keeps the route it was given when it was raised; publishing a rule changes new requests.
   ===================================================================== */
const AP_ROLE = {'role:mgr':'Sales Manager', 'role:md':'MD', 'role:sm':'Sales Manager', 'role:fin':'Finance', 'role:adm':'BMP Admin'};
const apP = name => personByName(name);
const apRoleOf = name => { const p = apP(name); return p ? (p.type === 'md' ? 'MD' : p.perms.includes('BMP Admin') ? 'BMP Admin' : p.role) : 'Approver'; };
/* one approver key ('role:…' or a person key) → the people who can act on it */
function apPeopleOf(k, maker){
  const act = S.users.filter(u => u.status === 'Active'), nm = u => u.short || (PEOPLE[u.key] || {}).name;
  if (k === 'role:mgr') return [managerOf(maker)];
  if (k === 'role:md') return [mdName()];
  if (k === 'role:sm'){ const m = managerOf(maker), L = act.filter(u => u.role === 'Sales Manager').map(nm); return [...new Set([L.includes(m) ? m : null, ...L].filter(Boolean))]; }
  if (k === 'role:fin') return act.filter(u => u.role === 'Finance' && PEOPLE[u.key] && PEOPLE[u.key].type === 'fin').map(nm);
  if (k === 'role:adm') return act.filter(u => (u.perms || []).includes('BMP Admin')).map(nm);
  const u = act.find(x => x.key === k); return u ? [nm(u)] : [];
}
/* a level: everyone who can approve it (any one is enough), never the maker */
function apLevel(who, maker){
  const names = [...new Set(who.flatMap(k => apPeopleOf(k, maker)))].filter(n => n && n !== maker);
  if (!names.length) return null;
  const roles = [...new Set(names.map(apRoleOf))];
  const role = who.length === 1 && AP_ROLE[who[0]] && who[0] !== 'role:mgr' ? AP_ROLE[who[0]] : roles.length === 1 ? roles[0] : 'Approver';   // the maker's manager shows their own role
  return {names, role};
}
/* role-limit conditions ("above the maker's role limit") need the maker; everything else uses a6CondOk */
function apCondOk(c, V, maker){
  const f = A5F[c.f]; if (!f) return false;
  if (f.type === 'rolelim'){ const p = apP(maker), lim = (c.lims || {})[p ? (p.type === 'md' ? 'MD' : p.role) : 'Sales Rep'], x = V[c.f === 'discLim' ? 'discount' : 'value'];
    return lim !== '' && lim != null && x != null && +x > +lim; }
  if (f.type === 'every') return true;
  if (f.type !== 'num' && Array.isArray(V[c.f]) && !V[c.f].length) return false;   // nothing to compare (e.g. a SKU with no country)
  return a6CondOk(c, V);
}
const apGroupOk = (g, V, maker) => g.conds.length && (g.match === 'any' ? g.conds.some(c => apCondOk(c, V, maker)) : g.conds.every(c => apCondOk(c, V, maker)));
/* resolve an action for one request → {rule, group, why, levels:[{names, role}]} or null when no rule is set */
function apRoute(ak, V, maker){
  const r = a6Rules()[ak], act = a5Act(ak); if (!r) return null;
  if (!r.on) return {rule:ak, ruleName:act ? act.name : ak, group:-1, why:'Approval is switched off', levels:[]};   // "every request goes ahead without approval"
  const gi = r.groups.findIndex(g => !g.conds.some(a6CondErr) && apGroupOk(g, V, maker));
  const lv = gi >= 0 ? r.groups[gi].levels : r.other.mode === 'approve' ? r.other.levels : [];
  const levels = []; lv.forEach(l => { const x = apLevel(l.who, maker); if (x && !(levels.length && levels[levels.length - 1].names.join() === x.names.join())) levels.push(x); });
  return {rule:ak, ruleName:act ? act.name : ak, group:gi, why: gi >= 0 ? `Group ${gi + 1}: ${a6GroupTxt(r.groups[gi])}` : r.groups.length ? 'Everything else' : 'All requests', levels};
}
const apNames = l => l.names.map(fullOf).join(' or ');
const apChainTxt = R => R.levels.length ? R.levels.map(l => `${apNames(l)} (${l.role})`).join(', then ') : 'No approval needed';

/* ---------- deals (Create deal or plan · Revise rates) ---------- */
const apDealKey = d => d.kind === 'revision' ? 'deal-revise' : 'deal-create';
function apDealLive(d){
  const R = apRoute(apDealKey(d), a6DealVals(d), d.maker);
  if (R) return R;
  const p = apP(d.maker), L = p && p.type === 'sm' ? ['MD'] : mdTriggers(d).length ? ['Sales Manager','MD'] : ['Sales Manager'];   // module default
  return {rule:null, ruleName:'Default route', group:-1, why: mdTriggers(d).length ? 'MD because: ' + mdTriggers(d).join('; ') : 'Default route', levels:L.map(r => ({names:[r === 'MD' ? mdName() : managerOf(d.maker)], role:r}))};
}
const apDeal = d => d.apr || apDealLive(d);
const apDealWaiting = d => ['Waiting for Sales Manager','Waiting for MD'].includes(d.stage);
const apDealCur = d => apDealWaiting(d) && d.apr ? d.apr.levels[d.lvl || 0] : null;
/* who can act on a waiting deal: the open level's people (the old route: the stage's approver) */
function apDealMine(d){
  if (!apDealWaiting(d) || isTM()) return false;
  const L = apDealCur(d), n = me().name;
  if (L) return L.names.includes(n);
  return dealAssignee(d) === n;
}
function apDealEnter(d, by){   // put the deal on its level, or approve it when no level is left
  const L = d.apr.levels[d.lvl || 0];
  if (!L){ d.stage = 'Approved'; if (!d.lvl) d.history.unshift({on:D(0), who:'System', what:`Approved automatically · ${d.apr.ruleName}: ${d.apr.why} needs no approval`}); dealNotify(d, d.maker, `${d.id} · ${dealTitle(d)} is approved. Add the papers and publish it.`); return; }
  d.stage = L.role === 'MD' ? 'Waiting for MD' : 'Waiting for Sales Manager';
  d.chain.push({who:L.names[0], any:L.names, role:L.role, state:'now'});
  const lv = d.apr.levels.length > 1 ? ` · level ${(d.lvl || 0) + 1} of ${d.apr.levels.length}` : '';
  L.names.forEach(n => dealNotify(d, n, d.lvl ? `${fullOf(by)} approved ${d.id} · ${dealTitle(d)} (${wsp(d.wid).name}). It now needs your approval${lv}.` : `${fullOf(by)} sent ${d.id} · ${dealTitle(d)} (${wsp(d.wid).name}) for your approval${lv}.`));
}
function apDealSubmit(d, by){ d.apr = cloneJ(apDealLive(d)); d.lvl = 0; apDealEnter(d, by); }
function apDealApprove(d, who, note){
  const L = apDealCur(d);
  d.chain.push({who, role: L ? L.role : (T() === 'md' ? 'MD' : 'Sales Manager'), on:0, state:'ok', note});
  if (!d.apr){ d.apr = cloneJ(apDealLive(d)); d.lvl = Math.max(0, d.apr.levels.findIndex(l => l.names.includes(who))); }
  d.lvl = (d.lvl || 0) + 1;
  const nx = d.apr.levels[d.lvl];
  d.history.unshift({on:D(0), who, what: nx ? `Approved at level ${d.lvl} · sent to ${apNames(nx)} (${nx.role})` : `Approved by ${L ? L.role : 'approver'}`});
  if (nx) dealNotify(d, d.maker, `${fullOf(who)} approved ${d.id}. It’s now with ${apNames(nx)} (${nx.role}).`);
  apDealEnter(d, who);
  toast(nx ? `Approved and sent to ${apNames(nx)} (${nx.role}).` : 'Approved. The maker can now add the papers and publish.', 'ok');
}
function apDealNextTxt(d){
  const nx = d.apr ? d.apr.levels[(d.lvl || 0) + 1] : null;
  return nx ? `It goes to ${apNames(nx)} (${nx.role}) next · ${esc(d.apr.ruleName)}: ${esc(d.apr.why)}.` : 'It becomes Approved. The maker then adds the papers and publishes.';
}
const apWhoTag = d => { const c = (d.chain || []).find(x => x.state === 'now'); return c ? `${c.role} · ${fullOf(c.who)}` : d.stage === 'Waiting for MD' ? 'MD · ' + fullOf(mdName()) : 'Sales Manager · ' + fullOf(managerOf(d.maker)); };
function apDealWaitTxt(d){ const L = apDealCur(d); return L ? `${apNames(L)} (${L.role})` : (d.stage === 'Waiting for MD' ? mdName() + ' (MD)' : managerOf(d.maker) + ' (Sales Manager)'); }
function apDealWhyTxt(d){ const R = apDeal(d); return R.rule ? `${R.ruleName} · ${R.why}` : (mdTriggers(d).join('; ') || 'the maker is a Sales Manager'); }
function apGoesTo(d){ const R = apDealLive(d), src = R.rule ? ` · Approval rule: ${R.ruleName} › ${R.why}` : '';
  return R.levels.length ? R.levels.map(l => `${apNames(l)} (${l.role})`).join(', then ') + src : `no one. It’s approved when you submit${src}`; }
/* steps for the deal header: one per approval level */
function apDealSteps(d){
  const R = apDeal(d), approved = ['Approved','Published · waiting for payment','Live','Past'].includes(d.stage), at = d.apr ? (d.lvl || 0) : -1;
  return R.levels.map((l, i) => [`${l.role === 'Sales Manager' ? 'Sales Manager' : l.role} OK`, approved || (at > i) ? 'done' : apDealWaiting(d) && (at === i || (at < 0 && ((l.role === 'MD') === (d.stage === 'Waiting for MD')))) ? 'now' : '']);
}
/* setup summary (account creation journey): the plan's approval status */
function apDealSub(d){
  if (apDealWaiting(d)){ const R = apDeal(d), L = apDealCur(d), i = d.lvl || 0, n = R.levels.length;
    return `Pending approval · ${esc(apDealWaitTxt(d))}${n > 1 ? ` · level ${Math.min(i + 1, n)} of ${n}` : ''}${R.levels[i + 1] ? ` · then ${esc(R.levels.slice(i + 1).map(l => apNames(l)).join(', then '))}` : ''}`; }
  if (d.stage === 'Draft' && (d.chain || []).some(c => c.state === 'bad')){ const c = d.chain.filter(x => x.state === 'bad').slice(-1)[0]; return `Sent back by ${esc(fullOf(c.who))}${c.note ? ' · ' + esc(c.note) : ''}`; }
  if (d.stage === 'Approved'){ const by = (d.chain || []).filter(c => c.state === 'ok' && c.role !== 'Submitted').map(c => fullOf(c.who)); return `Approved${by.length ? ' by ' + esc(by.join(', ')) : ' automatically'} · add the papers and publish`; }
  return esc(d.stage);
}

/* ---------- catalogue and SKU change requests ---------- */
function apCrKey(c){
  const t = String(c.title || '');
  if (/^(Catalog|Revise catalog|New category)/.test(t)) return 'cat-create';
  if (/^Bulk/.test(t)) return 'sku-bulk';
  if (c.lines.some(l => l.field === 'New SKU')) return 'sku-create';
  if (c.lines.some(l => ['deact','remove'].includes(l._f))) return 'sku-status';
  return 'sku-edit';
}
function apCrVals(c){
  const S_ = c.lines.map(l => sku(l.code)).filter(Boolean), p = personByName(c.maker);
  const rc = c.lines.map(l => { const o = parseFloat(String(l.old).replace(/[^0-9.]/g, '')), n = parseFloat(String(l.next).replace(/[^0-9.]/g, '')); return o && n ? Math.abs(n / o - 1) * 100 : 0; });
  return {product:[...new Set(S_.map(s => A6_PROD[s.product]).filter(Boolean))], country:[...new Set(S_.map(s => s.country ? (A6_CTRY[s.country] || ctyName(s.country)) : null).filter(Boolean))],
    rateChange:Math.max(0, ...rc), rows:c.lines.length, indicative:[S_.some(s => s.indicative) ? 'Yes' : 'No'], inDeals:[S_.some(s => S.deals.some(d => d.stage === 'Live' && (d.lines || []).some(l => l.on && l.code === s.code))) ? 'Yes' : 'No'],
    skuStatus:c.lines.map(l => l._f === 'deact' ? 'Deactivate' : l._f === 'remove' ? 'Remove' : null).filter(Boolean), raisedBy:[p ? (p.type === 'md' ? 'MD' : p.role) : 'Sales Rep']};
}
const apCrCur = c => c.status === 'Waiting for MD' && c.apr ? c.apr.levels[c.lvl || 0] : null;
const apCrMine = c => { if (c.status !== 'Waiting for MD' || isTM()) return false; const L = apCrCur(c); return L ? L.names.includes(me().name) : can.mdApprove(); };
const apCrWaitTxt = c => { const L = apCrCur(c); return L ? `${apNames(L)} (${L.role})` : 'Meera (MD)'; };
const apCrStatus = c => { const L = apCrCur(c); return !L || L.role === 'MD' ? c.status : L.role === 'Approver' ? 'Waiting for approval' : 'Waiting for ' + L.role; };
/* give every waiting request its route once; a route with no level approves it straight away */
function apCrSync(){
  S.changeReqs.filter(c => c.status === 'Waiting for MD' && !c.apr).forEach(c => {
    const R = apRoute(apCrKey(c), apCrVals(c), c.maker);
    c.apr = R ? cloneJ(R) : {rule:null, ruleName:'Default route', group:-1, why:'Default route', levels:[{names:[mdName()], role:'MD'}]}; c.lvl = 0;
    const L = c.apr.levels[0];
    if (!L){ c.apr.auto = true; setTimeout(() => { if (c.status === 'Waiting for MD'){ S._apSys = true; try { ACT['cr-decide']({dataset:{id:c.id, k:'ok'}}); } finally { S._apSys = false; } } }, 0); return; }
    if (c.on === 0) L.names.filter(n => n !== mdName() || L.role !== 'MD').forEach(n => S.notifs.unshift({for:n, to:[], on:0, text:`${fullOf(c.maker)} submitted ${c.id}: ${c.title}. It needs your approval${c.apr.rule ? ` (${c.apr.ruleName} · ${c.apr.why})` : ''}.`, go:{v:'work', tab:'approvals', grp:'SKU approval'}}));
  });
}
/* approve one level; returns true while more levels are left */
function apCrAdvance(c){
  if (!c.apr || S._apSys) return false;
  const who = me().name; (c.trail = c.trail || []).push({who, role:(apCrCur(c) || {}).role || 'MD', on:0});
  c.lvl = (c.lvl || 0) + 1; const nx = c.apr.levels[c.lvl];
  if (!nx) return false;
  nx.names.forEach(n => S.notifs.unshift({for:n, to:[], on:0, text:`${fullOf(who)} approved ${c.id} (level ${c.lvl}). It now needs your approval: ${c.title}.`, go:{v:'work', tab:'approvals', grp:'SKU approval'}}));
  S.notifs.unshift({for:c.maker, to:[], on:0, text:`${fullOf(who)} approved ${c.id}. It’s now with ${apNames(nx)} (${nx.role}).`, go:{v:'skus'}});
  log('Approved change request (level ' + c.lvl + ')', c.id); toast(`Approved. ${c.id} now goes to ${apNames(nx)} (${nx.role}).`, 'ok');
  return true;
}
const apCrDecider = () => S._apSys ? 'System' : me().name;

/* ---------- plans and add-on packs (Revise plan) ---------- */
function apPlanApprovers(){ const R = apRoute('plan-edit', {raisedBy:['Finance'], every:true}, ''); return R && R.levels.length ? R.levels[0].names : [mdName()]; }
const apPlanMine = () => !isTM() && apPlanApprovers().includes(me().name);

/* ---------- Actions, bell and dashboard: everything waiting on me, whoever the rule picked ---------- */
function apExtraWork(items){
  const p = me(), seen = new Set(items.map(i => i.go && i.go.id).filter(Boolean)), add = o => items.push(Object.assign({wait:0, tone:'', icon:'inbox'}, o));
  if (isTM()) return items;
  S.deals.filter(d => apDealMine(d) && !seen.has(d.id) && d.maker !== p.name).forEach(d => add({what:`Approve deal · ${DEAL_SHORT[d.kind] || 'Deal'}`, acc:acct(d.aid).name, ws:wsp(d.wid).name, by:d.maker, wait:-(d.submitted || 0), go:{v:'deal', id:d.id}}));
  if (p.type !== 'md') S.changeReqs.filter(apCrMine).forEach(c => add({what:`Approve catalogue change · ${c.title}`, acc:c.urgent ? 'Urgent' : 'SKU module', by:c.maker, wait:-c.on, tone: c.urgent ? 'dan' : '', icon:'box', go:{v:'work', tab:'approvals', grp:'SKU approval'}, skuAppr:true}));
  if (p.type !== 'md' && apPlanMine()) try { pkPending().forEach(add); } catch {}
  items.forEach(i => i.late = i.wait > S.limits.approvalDays);
  return items.sort(by(i => i.wait, 1));
}

/* ---------- overlays opened inside an embedded page dim the whole portal ----------
   Accounts, Actions, Plans and Add-on packs run in frames, so their scrim only covers the frame. While one is open,
   the same scrim covers the rest of the portal (sidebar and top bar); a click on it closes the overlay like the
   page's own scrim. The frame itself is cut out, so its own scrim and dialog stay as they are. */
(() => {
  const shade = document.createElement('div');
  shade.id = 'frame-scrim'; shade.hidden = true;
  shade.style.cssText = 'position:fixed;inset:0;z-index:1000;background:var(--scrim)';
  document.body.appendChild(shade);
  let open = null;   // {frame, scrim} while an embedded overlay is open
  /* modals inside a frame are centred in the frame; --frame-dx / --frame-dy (half the frame's offset from the page's
     top-left, in the frame's own pixels) move them back to the centre of the whole page */
  const centre = f => { const w = f.contentWindow, de = w && w.document && w.document.documentElement; if (!de || !w.innerWidth) return;
    const r = f.getBoundingClientRect(), sc = r.width / w.innerWidth || 1;
    /* an open dialog moves only as far as it can while staying whole inside the frame (narrow windows) */
    const dlg = w.document.querySelector('#overlay .dialog, #overlay .scrim > *'), room = (inner, size) => dlg ? Math.max(0, (inner - size) / 2 - 8) : Infinity;
    const dx = Math.round(Math.min(r.left / 2 / sc, room(w.innerWidth, dlg ? dlg.offsetWidth : 0))) + 'px', dy = Math.round(Math.min(r.top / 2 / sc, room(w.innerHeight, dlg ? dlg.offsetHeight : 0))) + 'px';
    if (de.style.getPropertyValue('--frame-dx') !== dx) de.style.setProperty('--frame-dx', dx);
    if (de.style.getPropertyValue('--frame-dy') !== dy) de.style.setProperty('--frame-dy', dy); };
  const sync = () => {
    document.querySelectorAll('#acframe, iframe.pkf').forEach(f => { try { centre(f); } catch (e) {} });
    open = null;
    for (const f of document.querySelectorAll('#acframe, iframe.pkf')){
      if (f.hidden || !f.offsetParent) continue;
      let s = null; try { s = f.contentDocument && f.contentDocument.querySelector('.scrim'); } catch (e) {}
      if (s){ open = {frame:f, scrim:s}; break; }
    }
    if (shade.hidden !== !open) shade.hidden = !open;   // written only on change, so the watchers below don't loop
    if (!open) return;
    const r = open.frame.getBoundingClientRect(), [L, T, R, B] = [r.left, r.top, r.right, r.bottom].map(n => Math.round(n) + 'px');
    const clip = `polygon(evenodd, 0 0, 100% 0, 100% 100%, 0 100%, 0 0, ${L} ${T}, ${R} ${T}, ${R} ${B}, ${L} ${B}, ${L} ${T})`;
    if (shade.dataset.clip !== clip){ shade.dataset.clip = clip; shade.style.clipPath = clip; }
  };
  shade.addEventListener('click', () => { if (open) open.scrim.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true})); sync(); });
  /* each frame is watched from the moment it loads; Plans and Add-on packs make a new frame per visit */
  document.addEventListener('load', e => { const f = e.target;
    if (!(f instanceof HTMLIFrameElement) || !f.matches('#acframe, iframe.pkf')) return;
    try { new MutationObserver(sync).observe(f.contentDocument.body, {childList:true, subtree:true}); } catch (e) {}
    sync(); }, true);
  window.addEventListener('resize', sync);
  new MutationObserver(recs => { if (recs.some(r => r.target !== shade)) sync(); }).observe(document.body, {attributes:true, attributeFilter:['hidden', 'style', 'class'], subtree:true, childList:true});
})();
