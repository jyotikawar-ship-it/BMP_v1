"""Merge the two Helo BMP prototypes into one single-file HTML.
usage: python3 -I build.py <fileA.html> <fileB.html> <out.html> <accounts.html>
A = "SKU configuration, catalog configuration, plan configuration and add-on pack configuration"
B = "Dashboard and approval configuration"
"""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from chunks import chunks as _chunks
import cssmerge

a_path, b_path, out_path, ac_path = sys.argv[1:5]   # ac = "BMP account creation review": Accounts and Actions, embedded unchanged
A_HTML = open(a_path, encoding='utf-8').read()
B_HTML = open(b_path, encoding='utf-8').read()

def between(s, start, end, from_=0):
    i = s.index(start, from_) + len(start); j = s.index(end, i); return s[i:j], j

# ---------- split each file ----------
a_css, _ = between(A_HTML, '<style>', '</style>')
b_css, _ = between(B_HTML, '<style>', '</style>')
a_body_i = A_HTML.index('</style>'); b_body_i = B_HTML.index('</style>')
a_js, _ = between(A_HTML, '<script>', '</script>', a_body_i)
# file B: first <script> is the 90% zoom helper, the second is the app
_, j = between(B_HTML, '<script>', '</script>', b_body_i)
b_js, _ = between(B_HTML, '<script>', '</script>', j)
a_js = a_js[1:] if a_js.startswith('\n') else a_js
b_js = b_js[1:] if b_js.startswith('\n') else b_js
b_shell = B_HTML[b_body_i + len('</style>'):B_HTML.index('<script>', b_body_i)].strip()

def chunks_of(text):
    p = os.path.join(HERE, '_tmp.js'); open(p, 'w', encoding='utf-8').write(text)
    try: return _chunks(p)
    finally: os.remove(p)

def must_replace(s, old, new, count=1, what=''):
    n = s.count(old)
    if n != count: raise SystemExit(f'patch "{what or old[:60]}": expected {count} match(es), found {n}')
    return s.replace(old, new)

# sidebar brand: no workspace-switcher caret (there is one business)
b_shell = must_replace(b_shell, '<svg class="sb-sw" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m7 15 5 5 5-5"/><path d="m7 9 5-5 5 5"/></svg>', '', what='brand caret')

# ---------- A: text-level patches before chunking ----------
# Catalogs: the tour button reads "How it works"
a_js = must_replace(a_js, "Watch the tour</button>", "How it works</button>", what='tour button label')
a_js = re.sub(r'\bczDrag\b', 'czDragA', a_js)
TAIL = "trialDocApi.resume();\nentApi.restore();\nif (!PEOPLE[S.user]) S.user = 'meera';\nrender();"
assert a_js.count(TAIL) == 1, 'A boot tail'
a_js = a_js.replace(TAIL, '')   # A's boot tail moves to the very end, after file 2's code          # A's home-customise drag state; B has a czDrag() function
# Plans page (the designer's embedded page, PK_SRC): its action bar's "Discard" reads "Cancel"
import base64
_m = re.search(r'(PK_SRC\s*=\s*")([A-Za-z0-9+/=]+)"', a_js); assert _m, 'PK_SRC'
_pk = base64.b64decode(_m.group(2)).decode('utf-8')
_pk = must_replace(_pk, """data-act="discard" ${dirty?\'\':\'disabled\'}>Discard</button>""", """data-act="discard" ${dirty?\'\':\'disabled\'}>Cancel</button>""", what='plans Discard→Cancel')
# Plans page: Helo Clarity comes first in the plan editor's rail (and is the section a plan opens on), then Helo Messaging
_i = _pk.index('const rail = `<div class="rail">\n') + len('const rail = `<div class="rail">\n')
_c = _pk.index('    <div class="card rail-c ${onC?', _i); _e = _pk.index('  </div>`;', _c)
assert _pk[_i:_c].startswith('    <div class="card rail-c ${onM?'), 'plans rail order'
_pk = _pk[:_i] + _pk[_c:_e] + _pk[_i:_c] + _pk[_e:]
_pk = must_replace(_pk, "orig:clone(base), product:'messaging', cview:'sub'", "orig:clone(base), product:'clarity', cview:'sub'", what='plans opens on Clarity')
# Plans page: country tabs work like Accounts › Helo Messaging (configure plan). Each channel has its own countries;
# "Add country" opens an inline searchable list of the rate cards that channel has in the Accounts catalogue
# (International and regions first, then countries with their flag), and × on a tab removes it after a confirm.
MSG_CTY = {"sms": [["INTL", "International"], ["IN", "India"]], "rcs": [["IN", "India"]], "whatsapp": [["INTL", "International"], ["R-NA", "North America"], ["R-AF", "Africa"], ["R-AP", "Asia Pacific"], ["R-CEE", "Central & Eastern Europe"], ["R-LA", "Latin America"], ["R-ME", "Middle East"], ["R-WE", "Western Europe"], ["R-OT", "Other"], ["AR", "Argentina"], ["BR", "Brazil"], ["CL", "Chile"], ["CO", "Colombia"], ["EG", "Egypt"], ["FR", "France"], ["DE", "Germany"], ["IN", "India"], ["ID", "Indonesia"], ["IL", "Israel"], ["IT", "Italy"], ["MY", "Malaysia"], ["MX", "Mexico"], ["NL", "Netherlands"], ["NG", "Nigeria"], ["PK", "Pakistan"], ["PE", "Peru"], ["RU", "Russia"], ["SA", "Saudi Arabia"], ["ZA", "South Africa"], ["ES", "Spain"], ["TR", "Türkiye"], ["AE", "United Arab Emirates"], ["GB", "United Kingdom"]]}   # from the Accounts file: MSG_REGIONS + ISO_CTY, kept to rate cards with active SKUs, per channel
_pk = must_replace(_pk, "function viewMessaging(){\n", "function viewMessaging(){\n  { const cs=chCountries(P.draft,P.channel); if(!cs.includes(P.country)) P.country=cs[0]; }\n", what='plans channel countries')
_pk = must_replace(_pk, '''  const tabs = d.countries.map(k=>`<button class="utab" role="tab" aria-selected="${k===ct}" data-act="country" data-c="${esc(k)}">${esc(k)} <span class="n">${selCount(d,ch,k)}</span></button>`).join('')
    + `<button class="utab" data-act="addcountry" style="color:var(--primary)">${ic('plus',14)}Add country</button>`;''',
'''  const cs = chCountries(d,ch);
  const tabs = cs.map(k=>`<span class="pc-ctab"><button class="utab" role="tab" aria-selected="${k===ct}" data-act="country" data-c="${esc(k)}">${esc(k)} <span class="n">${selCount(d,ch,k)}</span></button>${cs.length>1?`<button class="pc-chip-x" data-act="rmcountry" data-c="${esc(k)}" aria-label="Remove ${esc(k)}">${ic('x',12)}</button>`:''}</span>`).join('')
    + ctyAddTab(ch, chName);''', what='plans country tabs')
_pk = must_replace(_pk, 'function viewMessaging(){', """I.globe = '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>';
const MSG_CTY = """ + json.dumps(MSG_CTY, ensure_ascii=False) + """;
const chCountries = (d,ch) => d.countries.filter(k=>d.msg[ch][k]);
const ctyCode = n => { for(const ch in MSG_CTY){ const x=MSG_CTY[ch].find(([,m])=>m===n); if(x) return x[0]; } return ''; };
const flagOf = n => { const c=ctyCode(n); return /^[A-Z]{2}$/.test(c) ? String.fromCodePoint(...[...c].map(x=>0x1F1E6+x.charCodeAt(0)-65)) : c ? ic('globe',14) : ''; };
function ctyAddTab(ch, chName){
  if(!P.ccAdd) return `<button class="utab pc-addtab" data-act="addcountry" aria-haspopup="listbox" aria-expanded="false">${ic('plus',14)}Add country</button>`;
  const free = (MSG_CTY[ch]||[]).filter(([,n])=>!P.draft.msg[ch][n]), k = CAT[ch].length;
  return `<span class="pc-addwrap"><button class="utab pc-addtab on" data-act="ccaddx" aria-expanded="true" aria-haspopup="listbox">${ic('plus',14)}Add country</button>
    <span class="pc-ddmenu" role="listbox" aria-label="Choose a country"><input class="inp sm" type="search" id="ccq" placeholder="Search countries" aria-label="Search countries" style="flex:none;min-height:34px;margin-bottom:4px;position:sticky;top:0;z-index:1;box-shadow:0 -8px 0 4px var(--surface)">${free.map(([,c])=>`<button role="option" class="pc-ddopt" data-act="ccpick" data-c="${esc(c)}" data-q="${esc(c.toLowerCase())}"><span class="b3">${flagOf(c)} ${esc(c)}</span><span class="pc-ddn" aria-label="${k} SKUs">${k}</span></button>`).join('')}<span class="b4 pc-ddnone" hidden>No country matches.</span>${free.length?'':`<span class="b4" style="padding:8px 10px">No other countries in the ${esc(chName)} catalogue.</span>`}</span></span>`;
}
function viewMessaging(){""", what='plans ctyAddTab')
_pk = must_replace(_pk, "case 'addcountry': openModal({type:'country'}); break;",
  "case 'addcountry': P.ccAdd=true; render(); setTimeout(()=>{const q=document.getElementById('ccq'); q&&q.focus();},30); break;\n"
  "    case 'ccaddx': P.ccAdd=false; render(); break;\n"
  "    case 'ccpick': { const c=t.dataset.c, d=P.draft; if(!d.countries.includes(c)) d.countries.push(c); d.msg[P.channel][c]=d.msg[P.channel][c]||[]; P.country=c; P.sq=''; P.ccAdd=false; render(); toast(`${c} added`); break; }\n"
  "    case 'rmcountry': openModal({type:'rmcty', c:t.dataset.c}); break;", what='plans country actions')
_pk = must_replace(_pk, "  } else if(M.type==='leave'){", '''  } else if(M.type==='rmcty'){
    const c=M.c, chName=CHANNELS.find(x=>x.id===P.channel).name, k=selCount(P.draft,P.channel,c);
    o.innerHTML = `<div class="scrim" data-act="scrim"><div class="dlg" role="alertdialog" aria-modal="true" aria-labelledby="mt">
      <div class="dlg-h"><h2 class="h6" id="mt" style="font-size:18px">Remove ${esc(c)}?</h2><div class="b3 muted">The country and all its ${esc(chName)} SKUs will be taken off this plan.</div></div>
      <div class="dlg-b">${k?`<div class="sum"><span class="b2">${flagOf(c)} ${esc(c)}</span><span class="b3 muted num">${esc(chName)} · ${k} SKU${k===1?'':'s'}</span></div>`:''}
        <div class="b3 muted">You can add it back from Add country. Nothing changes until you save the plan.</div></div>
      <div class="dlg-f"><button class="btn btn-sec" data-act="mclose">Cancel</button><button class="btn btn-dan" data-act="mconfirm">${ic('trash',14)}Remove</button></div></div></div>`;
    setTimeout(()=>{const b=o.querySelector('[data-act=mclose]'); b&&b.focus();},0);
  } else if(M.type==='leave'){''', what='plans remove-country dialog')
_pk = must_replace(_pk, "  if(M.type==='country'){", '''  if(M.type==='rmcty'){ const c=M.c, d=P.draft, ch=P.channel, chName=CHANNELS.find(x=>x.id===ch).name, n=selCount(d,ch,c);
    delete d.msg[ch][c]; if(!CHANNELS.some(x=>d.msg[x.id][c])) d.countries=d.countries.filter(x=>x!==c); if(P.country===c) P.country=chCountries(d,ch)[0];
    closeModal(); render(); toast(n?`Removed ${c} and its ${n} SKU${n===1?'':'s'} from ${chName}`:`${c} removed from ${chName}`); return; }
  if(M.type==='country'){''', what='plans remove-country confirm')
_pk = must_replace(_pk, "\n</script>", '''
// the country list: search, and close on Escape or a click outside it
document.addEventListener('input',ev=>{ const t=ev.target; if(t.id!=='ccq') return; const q=t.value.trim().toLowerCase(), box=t.closest('.pc-ddmenu'); let n=0;
  box.querySelectorAll('.pc-ddopt').forEach(b=>{ const hit=!q||b.dataset.q.includes(q); b.hidden=!hit; if(hit) n++; }); box.querySelector('.pc-ddnone').hidden=n>0; });
document.addEventListener('mousedown',ev=>{ if(P && P.ccAdd && !ev.target.closest('.pc-addwrap')){ P.ccAdd=false; render(); } });
document.addEventListener('keydown',ev=>{ if(ev.key==='Escape' && P && P.ccAdd && !M){ P.ccAdd=false; render(); } });
</script>''', what='plans country list events')
_pk = must_replace(_pk, "\n</style>", '''
/* country tabs and the Add country list (same as Accounts › configure plan) */
.ctabs{overflow:visible;flex-wrap:wrap}
.pc-ctab{display:inline-flex;align-items:center}
.pc-chip-x{display:grid;place-items:center;width:20px;height:20px;border-radius:50%;color:var(--text-muted)}
.pc-chip-x:hover{background:var(--border-subtle);color:var(--text-primary)}
.pc-ctab .pc-chip-x{margin-left:-4px}
.pc-addtab{display:inline-flex;align-items:center;gap:6px;color:var(--primary);font-weight:600}
.pc-addtab:hover,.pc-addtab.on{background:var(--accent-subtle);color:var(--primary)}
.pc-addwrap{position:relative;display:inline-flex}
.pc-ddmenu{position:absolute;top:calc(100% + 4px);left:0;z-index:30;min-width:240px;max-height:280px;overflow:auto;background:var(--surface);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);box-shadow:0 8px 24px rgba(0,0,0,.12);padding:4px;display:flex;flex-direction:column}
.pc-ddopt{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 10px;border:0;border-radius:var(--radius-md);background:transparent;text-align:left;cursor:pointer}
.pc-ddopt[hidden]{display:none}.pc-ddopt .b3{display:inline-flex;align-items:center;gap:6px}
.pc-ddn{font-size:12px;line-height:16px;font-weight:600;color:var(--text-secondary);background:var(--surface-muted);border-radius:var(--radius-full);padding:1px 8px;min-width:24px;text-align:center}
.pc-ddopt:hover,.pc-ddopt:focus-visible{background:var(--accent-subtle);outline:none}
</style>''', what='plans country css')
a_js = a_js[:_m.start(2)] + base64.b64encode(_pk.encode('utf-8')).decode() + a_js[_m.end(2):]
A = chunks_of(a_js); B = chunks_of(b_js)
Akey = {}; [Akey.setdefault(c['key'], c) for c in A]
Bkey = {}; [Bkey.setdefault(c['key'], c) for c in B]
def setA(key, text): Akey[key]['text'] = text
def patchA(key, old, new, count=1): Akey[key]['text'] = must_replace(Akey[key]['text'], old, new, count, key + ': ' + old[:50])

# people and teams from B (the dashboard's sales-team data needs them); everything else from A
for k in ['decl:PEOPLE', 'decl:PERSONA_ORDER', 'decl:TEAM_OF', 'decl:REPS', 'decl:TGT_PEOPLE', 'decl:PUB_SHORT', 'decl:toast', 'decl:openMenu']:
    setA(k, Bkey[k]['text'])
# Arun Mehta (Sales Manager) can create everything: catalogs, SKUs, plans and add-on packs (SKU Maker) and approval rules
patchA('decl:PEOPLE', "role:'Sales Manager', type:'sm',  perms:[],           mgr:'meera', title:'Sales Manager · West'", "role:'Sales Manager', type:'sm',  perms:['SKU Maker','Approval rules'], mgr:'meera', title:'Sales Manager · West'")
patchA('decl:can', "  admin:         () => meRaw().perms.includes('BMP Admin') || T() === 'md',", "  admin:         () => meRaw().perms.includes('BMP Admin') || T() === 'md',\n  apprRules:     () => can.admin() || meRaw().perms.includes('Approval rules'),   // create and publish approval rules")
# account owners from B (only the owner column differs)
mask = lambda t: re.sub(r"^(\s*\['[^']*','[A-Z]{2}',)'[^']*'", r"\1'_'", t, flags=re.M)
assert mask(Akey['decl:ACC_SEED']['text']) == mask(Bkey['decl:ACC_SEED']['text']), 'ACC_SEED differs beyond owners'
setA('decl:ACC_SEED', Bkey['decl:ACC_SEED']['text'])
# icons: A's set plus the ones only B has
a_ic = set(re.findall(r"^\s+([\w$]+)\s*:", Akey['decl:IP']['text'], re.M))
extra = [l.rstrip().rstrip(',') for l in Bkey['decl:IP']['text'].split('\n')[1:] if re.match(r"^\s+([\w$]+)\s*:", l) and re.match(r"^\s+([\w$]+)", l).group(1) not in a_ic]
Akey['decl:IP']['text'] += '\nObject.assign(IP, {\n' + ',\n'.join(extra) + '\n});'
patchA('decl:S', "route: {v:'skus'}", "route: {v:'home2'}")
patchA('decl:trialLog', "to:t.to || null, ext:null})));", "to:t.to || null, ext:t.ext || null, req:t.req || null, h2:!!t.h2})));")
patchA('decl:trialLog', "by:w.trial.by, ext:w.trial.ext || null, running:true}));", "by:w.trial.by, ext:w.trial.ext || null, req:w.trial.req || null, running:true}));")
# shell
patchA('decl:renderNav', "I('menu', 18)", "I('sidebar', 20)")
patchA('decl:renderUserMenu', 'PERSONA_ORDER.map', 'PERSONA_SWITCH.map')
SHELL_JS = open(os.path.join(HERE, 'shell.js'), encoding='utf-8').read()
for k in ['decl:navItems', 'decl:NAV_PARENT', 'decl:go', 'decl:KEEP_VIEWS']: Akey[k]['text'] = ''
setA('decl:render', SHELL_JS)
nav_a = [c for c in A if c['key'].startswith("stmt:$('#navtoggle').addEventListener")]
nav_b = [c for c in B if c['key'].startswith("stmt:$('#navtoggle').addEventListener")]
assert len(nav_a) == 1 and len(nav_b) == 1; nav_a[0]['text'] = nav_b[0]['text']
# visibility: an approver the rule picked can open what they're asked to approve
patchA('decl:canSee', 'function canSee(a){', 'function canSee0(a){')
Akey['decl:canSee']['text'] += "\nfunction canSee(a){ return canSee0(a) || (!!a && !isTM() && S.deals.some(d => d.aid === a.id && d.apr && d.apr.levels.some(l => l.names.includes(me().name)))); }"
patchA('decl:canSeeWs', 'function canSeeWs(w){', 'function canSeeWs0(w){')
Akey['decl:canSeeWs']['text'] += "\nfunction canSeeWs(w){ return canSeeWs0(w) || (!!w && !isTM() && S.deals.some(d => d.wid === w.id && d.apr && d.apr.levels.some(l => l.names.includes(me().name)))); }"

# ---------- approval engine hooks (deals) ----------
setA('decl:routeFor', 'function routeFor(d){ return apDealLive(d).levels.map(l => l.role); }   // roles on the route, from Approval configuration')
patchA('decl:savePlanDeal', """    const route = routeFor(d);
    d.stage = route[0] === 'MD' ? 'Waiting for MD' : 'Waiting for Sales Manager';
    d.submitted = 0;
    d.chain = [{who: isTM() ? 'Kiran for Arun' : maker, role:'Submitted', on:0, state:'ok'}, {who: route[0] === 'MD' ? mdName() : managerOf(maker), role: route[0], state:'now'}];""",
"""    d.submitted = 0;
    d.chain = [{who: isTM() ? 'Kiran for Arun' : maker, role:'Submitted', on:0, state:'ok'}];""")
patchA('decl:savePlanDeal', "    log(resend ? 'Resubmitted deal' : 'Submitted deal for approval', d.id);",
       "    apDealSubmit(d, maker);      // route from Approval configuration › Create deal or plan\n    log(resend ? 'Resubmitted deal' : 'Submitted deal for approval', d.id);")
patchA('decl:dealSteps', "const L = [['Configure', S1], ['Sales Manager OK', S2], ['MD OK', S3], ['Papers & e-sign', S4], ['Publish', S5]];",
       "const L = [['Configure', S1], ...apDealSteps(d), ['Papers & e-sign', S4], ['Publish', S5]];")
patchA('decl:dealNext', "mine = (who === 'md' && can.mdApprove()) || (who === 'sm' && can.firstApprove() && (TEAM_OF[me().key] || []).includes(d.maker));", "mine = apDealMine(d);")
patchA('decl:dealNext', "Sent to you because: ${mdTriggers(d).join('; ') || 'the maker is a Sales Manager'}", "Sent to you because: ${esc(apDealWhyTxt(d))}", 2)
patchA('decl:dealNext', "(mdTriggers(d).length ? 'If you approve, it goes to the MD next.' : 'If you approve, it’s approved. No MD step is needed.')",
       "(d.apr && d.apr.levels[(d.lvl || 0) + 1] ? `If you approve, it goes to ${apNames(d.apr.levels[(d.lvl || 0) + 1])} next.` : d.apr && d.apr.rule ? 'If you approve, it’s approved.' : 'If you approve, it’s approved. No MD step is needed.')")
patchA('decl:dealNext', "t:`Waiting for ${who === 'md' ? mdName() + ' (MD)' : managerOf(d.maker) + ' (Sales Manager)'} · ${plural(since, 'day')}`", "t:`Waiting for ${apDealWaitTxt(d)} · ${plural(since, 'day')}`")
def patch_any(old, new, count=1):
    hits = [c for c in A if old in c['text']]
    if len(hits) != 1 or hits[0]['text'].count(old) != count: raise SystemExit(f'patch_any "{old[:60]}": {len(hits)} chunks')
    hits[0]['text'] = hits[0]['text'].replace(old, new)
patch_any("${next === 'Waiting for MD' ? 'It goes to Meera (MD) next because: ' + esc(mdTriggers(d).join('; ')) + '.' : 'It becomes Approved. The maker then adds the papers and publishes.'}", "${apDealNextTxt(d)}")
patch_any("who = me().name, role = T() === 'md' ? 'MD' : 'Sales Manager';", "who = me().name, role = (apDealCur(d) || {}).role || (T() === 'md' ? 'MD' : 'Sales Manager');")
patch_any("""      d.chain.push({who, role, on:0, state:'ok', note:n});
      if (d.stage === 'Waiting for Sales Manager' && routeFor(d).includes('MD')){ d.stage = 'Waiting for MD'; d.chain.push({who:mdName(), role:'MD', state:'now'}); d.history.unshift({on:D(0), who, what:'Approved at Sales Manager step · sent to MD'}); toast('Approved and sent to the MD.', 'ok'); }
      else { d.stage = 'Approved'; d.history.unshift({on:D(0), who, what:`Approved by ${role}`}); toast('Approved. The maker can now add the papers and publish.', 'ok'); }""",
"""      apDealApprove(d, who, n);   // next level from Approval configuration, or Approved""")
patch_any("const d = deal(x.did); if (d){ const route = routeFor(d); d.stage = route[0] === 'MD' ? 'Waiting for MD' : 'Waiting for Sales Manager'; d.submitted = 0; d.chain = [{who:'Kiran for Arun', role:'Submitted', on:0, state:'ok'}, {who: route[0] === 'MD' ? 'Meera' : 'Arun', role:route[0], state:'now'}]; }",
          "const d = deal(x.did); if (d){ d.submitted = 0; d.chain = [{who:'Kiran for Arun', role:'Submitted', on:0, state:'ok'}]; apDealSubmit(d, d.maker); }")
patch_any("toast(`Submitted to ${d.stage === 'Waiting for MD' ? 'Meera (MD)' : managerOf(d.maker)}. Configuration PDF",
          "toast(`${d.stage === 'Approved' ? 'Approved straight away: the approval rule needs no approval for it.' : 'Submitted to ' + apDealWaitTxt(d) + '.'} Configuration PDF")
patch_any("Goes to ${routeFor(dm).map(r => r === 'MD' ? 'the MD' : managerOf(maker) + ' (Sales Manager)').join(', then ')}.", "Goes to ${esc(apGoesTo(dm))}.")
patch_any("${routeFor(d).join(' → ')}${trig.length ? ' · MD because: ' + esc(trig.join('; ')) : ''}",
          "${esc(apChainTxt(apDeal(d)))}${apDeal(d).rule ? ' · ' + esc(apDeal(d).ruleName) + ': ' + esc(apDeal(d).why) : trig.length ? ' · MD because: ' + esc(trig.join('; ')) : ''}")
# Actions / bell
patchA('decl:myWork', 'function myWork(){', 'function myWork0(){')
Akey['decl:myWork']['text'] += '\nfunction myWork(){ return apExtraWork(myWork0()); }   // plus whatever Approval configuration routed to me'
patchA('decl:myWork', "S.changeReqs.filter(c => c.status === 'Waiting for MD').forEach(", "S.changeReqs.filter(c => c.status === 'Waiting for MD' && apCrMine(c)).forEach(")
patchA('decl:myWork', "pkPending().forEach(add);", "if (apPlanMine()) pkPending().forEach(add);")
# catalogue / SKU change requests
patchA('decl:crCards', "const md = can.mdApprove(), mine = c.maker === meRaw().name;", "const md = apCrMine(c), mine = c.maker === meRaw().name;")
patchA('decl:crCards', "${pill(c.status, ", "${pill(apCrStatus(c), ")
patchA('decl:crCards', '<span class="b4">Waiting for Meera (MD).</span>',
       '<span class="b4">Waiting for ${esc(apCrWaitTxt(c))}${c.apr && c.apr.levels.length > 1 ? ` · level ${(c.lvl || 0) + 1} of ${c.apr.levels.length}` : \'\'}${c.apr && c.apr.rule ? ` · ${esc(c.apr.ruleName)}: ${esc(c.apr.why)}` : \'\'}.</span>')
patch_any("crCards(S.changeReqs.filter(c => c.status === 'Waiting for MD'))", "crCards(S.changeReqs.filter(c => c.status === 'Waiting for MD' && (apCrMine(c) || c.maker === me().name)))")
patchA('ACT:cr-decide', "if (k === 'ok'){\n    c.status = 'Approved'; c.decidedBy = 'Meera'; c.decidedOn = 0;",
       "if (k === 'ok'){\n    if (apCrAdvance(c)) return render();   // more approval levels to go\n    c.status = 'Approved'; c.decidedBy = apCrDecider(); c.decidedOn = 0;\n    if (c.maker !== c.decidedBy) S.notifs.unshift({for:c.maker, to:[], on:0, text:`${c.decidedBy === 'System' ? 'No approval was needed for' : fullOf(c.decidedBy) + ' approved'} ${c.id}: ${c.title}.`, go:{v:'skus'}});")
patchA('ACT:cr-decide-ok', "c.decidedBy = 'Meera';", "c.decidedBy = me().name; S.notifs.unshift({for:c.maker, to:[], on:0, text:`${fullOf(me().name)} ${t.dataset.k === 'back' ? 'sent back' : 'rejected'} ${c.id}: ${n}`, go:{v:'skus'}});")
# SaaS catalogs: a new single SKU can't be created yet; the option stays visible, disabled, with the reason on hover
SAAS_TIP = "Creating a new SKU isn’t available for SaaS catalogs yet. Assign existing SKUs instead."
Akey['decl:cmAddOpts']['text'] = ("const SAAS_NEW_TIP = " + json.dumps(SAAS_TIP) + ";\nconst saasNoNew = c => !!c && c.prod === 'clarity';   // SaaS catalog\n") + Akey['decl:cmAddOpts']['text']
patchA('decl:cmAddOpts', "data-k=\"${esc(c.name)}\" ${why ? `aria-disabled=\"true\" data-tip=\"${esc(why)}\"` : ''}>",
       "data-k=\"${esc(c.name)}\" ${why ? `aria-disabled=\"true\" data-tip=\"${esc(why)}\"` : m === 'single' && saasNoNew(c) ? `aria-disabled=\"true\" data-tip=\"${esc(SAAS_NEW_TIP)}\"` : ''}>")
patch_any("`<button role=\"menuitem\" data-act=\"cat-add\" data-m=\"${m}\" data-k=\"${esc(c.name)}\">${I(ic,18)}",
          "`<button role=\"menuitem\" data-act=\"cat-add\" data-m=\"${m}\" data-k=\"${esc(c.name)}\" ${m === 'single' && saasNoNew(c) ? `aria-disabled=\"true\" data-tip=\"${esc(SAAS_NEW_TIP)}\"` : ''}>${I(ic,18)}")
patch_any("<button class=\"btn btn-pri\" data-act=\"cat-add\" data-m=\"single\" data-k=\"${esc(c.name)}\" ${dz}>New SKU</button>",
          "<button class=\"btn btn-pri\" data-act=\"cat-add\" data-m=\"single\" data-k=\"${esc(c.name)}\" ${dz || (saasNoNew(c) ? `aria-disabled=\"true\" data-tip=\"${esc(SAAS_NEW_TIP)}\"` : '')}>New SKU</button>")
patch_any("<button role=\"menuitem\" data-act=\"cat-add\" data-m=\"single\" data-k=\"${esc(c.name)}\" ${cm.locked ? 'aria-disabled=\"true\" data-tip=\"Product catalogs have a fixed set of SKUs, so new SKUs can’t be added.\"' : ''}>",
          "<button role=\"menuitem\" data-act=\"cat-add\" data-m=\"single\" data-k=\"${esc(c.name)}\" ${cm.locked ? 'aria-disabled=\"true\" data-tip=\"Product catalogs have a fixed set of SKUs, so new SKUs can’t be added.\"' : saasNoNew(cm) || saasNoNew(catByName(c.name)) ? `aria-disabled=\"true\" data-tip=\"${esc(SAAS_NEW_TIP)}\"` : ''}>")
patch_any("const c = catByName(t.dataset.k), m = t.dataset.m; S._catMenu = null; S._skuNew = false; if (!c || !can.sku() || c.locked) return;",
          "const c = catByName(t.dataset.k), m = t.dataset.m; S._catMenu = null; S._skuNew = false; if (!c || !can.sku() || c.locked || (m === 'single' && saasNoNew(c))) return;")

# SaaS catalogs charged On/off list only on/off SKUs in "Select existing SKUs"; Charged by usage lists only usage SKUs; Both lists every one
patchA('decl:bkExPool', "const bkExPool = B => S.skus.filter(s => !s.legacy && s.product === B.prod && s.status === 'Active' && (B.prod !== 'clarity' || B.anyType || (bkFeat(B) ? s.type === 'Feature' : s.type !== 'Feature')));",
       "const bkCharge = s => s.access || (['Consumable','Usage'].includes(s.type) ? 'metered' : s.type === 'Feature' ? 'onoff' : '');   // how a SaaS SKU is charged\nconst bkExPool = B => S.skus.filter(s => !s.legacy && s.product === B.prod && s.status === 'Active' && (B.prod !== 'clarity' || (['onoff','metered','both'].includes(B.access) ? s.type === 'Feature' && (B.access === 'both' ? ['onoff','metered'].includes(bkCharge(s)) : bkCharge(s) === B.access) : B.anyType || (bkFeat(B) ? s.type === 'Feature' : s.type !== 'Feature'))));   // SaaS catalogs: features charged the catalog's way (Both = on/off and usage)")
patch_any("if (m === 'existing' && c.prod === 'clarity') Object.assign(B, {type:'MTP', anyType:true});",
          "if (m === 'existing' && c.prod === 'clarity') Object.assign(B, {type:'MTP', anyType:true, access:c.access || ''});")

# a tax category belongs to one country: the New category dialog's country list has no "Global (all countries)"
patchA('decl:ctyOpts', "const ctyOpts = (cur, flagAttr = true) =>", "const ctyOpts = (cur, flagAttr = true, global = true) =>")
patchA('decl:ctyOpts', "<optgroup label=\"Frequently used\"><option value=\"GL\" ${flagAttr ? 'data-flag=\"GL\"' : ''} ${cur === 'GL' ? 'selected' : ''}>Global (all countries)</option>",
       "<optgroup label=\"Frequently used\">${global ? `<option value=\"GL\" ${flagAttr ? 'data-flag=\"GL\"' : ''} ${cur === 'GL' ? 'selected' : ''}>Global (all countries)</option>` : ''}")
patch_any('id="bkc-cty" data-chg="bkc" data-k="cty">${ctyOpts(D.cty)}</select>', 'id="bkc-cty" data-chg="bkc" data-k="cty">${ctyOpts(D.cty, true, false)}</select>')

# a Global SKU (or SaaS feature) is priced in US dollars
patchA('decl:nsCur', "const nsCur = cty => cty === 'GL' ? 'INR' :", "const nsCur = cty => cty === 'GL' ? 'USD' :")

# SaaS on/off features (user's list, Nov 2026): every one configured On/off for India, so they're what an On/off SaaS catalog can pick
ONOFF_FEATS = [('Data and segments', ['Data ingestion (SDK and pixel)', 'Data ingestion (CRM)', 'Data ingestion (Files)', 'Data ingestion (APIs)',
    'Segment Builder + Re-targeting (Portfolio)', 'Segment Builder + Re-targeting (Projects)', 'Funnel analytics + Re-targeting',
    'Event Analytics (Mixpanel/Amplitude Grade) + Re-targeting', 'CQL — Clarity Query Language', 'Journeys (Sankey)', 'SCV (Basic + Events)', 'SCV (Advanced)']),
  ('Campaigns and workflows', ['Campaign scheduling + failover', 'Workflow Builder', 'AI Optimiser (WHEN + WHERE)', 'Events and Triggers', 'Workflow - AB Test Node', 'Workflow - API Node',
    'Campaigns - AB Test', 'Campaigns - Single Channel', 'Campaigns - MCO', 'Campaigns via Files', 'Campaigns via Segments']),
  ('Links and QR codes', ['QR Code Customisation', 'Smart Redirections (conditional landing)', 'Shortlinks & QR Codes']),
  ('Content and analytics', ['Content Studio', 'Analyse - Dashboard', 'Analyse - Reports'])]
FEAT_KEYS = {   # short keys, like the designer's ('sso', 'custom-domains'): the SKU code is FT-<KEY>-<COUNTRY>
  'Data ingestion (SDK and pixel)':'ingest-sdk', 'Data ingestion (CRM)':'ingest-crm', 'Data ingestion (Files)':'ingest-files', 'Data ingestion (APIs)':'ingest-api',
  'Segment Builder + Re-targeting (Portfolio)':'segment-portfolio', 'Segment Builder + Re-targeting (Projects)':'segment-projects', 'Funnel analytics + Re-targeting':'funnel',
  'Event Analytics (Mixpanel/Amplitude Grade) + Re-targeting':'event-analytics', 'CQL — Clarity Query Language':'cql', 'Journeys (Sankey)':'journeys',
  'SCV (Basic + Events)':'scv-basic', 'SCV (Advanced)':'scv-advanced', 'Campaign scheduling + failover':'campaign-schedule', 'Workflow Builder':'workflow-builder',
  'AI Optimiser (WHEN + WHERE)':'ai-optimiser', 'Events and Triggers':'events-triggers', 'Workflow - AB Test Node':'workflow-ab', 'Workflow - API Node':'workflow-api', 'Campaigns - AB Test':'campaign-ab',
  'Campaigns - Single Channel':'campaign-single', 'Campaigns - MCO':'campaign-mco', 'Campaigns via Files':'campaign-files', 'Campaigns via Segments':'campaign-segments',
  'QR Code Customisation':'qr-custom', 'Smart Redirections (conditional landing)':'smart-redirect', 'Shortlinks & QR Codes':'shortlinks',
  'Content Studio':'content-studio', 'Analyse - Dashboard':'analyse-dashboard', 'Analyse - Reports':'analyse-reports'}
def _fkey(n): return FEAT_KEYS[n]
_rows = ',\n'.join(f"  [{json.dumps(_fkey(n))}, {json.dumps(n)}, {json.dumps('On/off feature · ' + g)}, [['IN', 'onoff', 0, '', 'Monthly', 'Active']]]" for g, L in ONOFF_FEATS for n in L)
patchA('decl:FT_SEED', "  ['sso', 'Single sign-on', 'SAML and OIDC sign-in for workspaces.', [['IN', 'onoff', 2500, '', 'Monthly', 'Active']]],\n", _rows + ',\n')
patchA('decl:FT_SEED', "  ['custom-domains', 'Custom domains', 'Branded short links on the customer’s own domain.', [['IN', 'onoff', 1500, '', 'Monthly', 'Active']]],\n", '')
assert len(set(_fkey(n) for g, L in ONOFF_FEATS for n in L)) == 29

# SaaS charged-by-usage features = the Core features of Plans › Modify plan (Helo Clarity): its usage rates and seats,
# priced at the catalogue base rates, so they're what a "Charged by usage" SaaS catalog can pick
USAGE_FEATS = [('mtp', 'Monthly Tracked Profiles', 'profile', 0.12), ('executions', 'Executions', 'execution', 0.015),
  ('ai-tokens', 'AI Tokens', '1K tokens', 0.4), ('workflows', 'Workflows', 'workflow', 1500), ('seats', 'Seats', 'seat', 2500)]
_urows = ''.join(f"  [{json.dumps(k)}, {json.dumps(n)}, 'Charged by usage · Core feature in Plans', [['IN', 'metered', {p}, {json.dumps(u)}, 'Monthly', 'Active']]],\n" for k, n, u, p in USAGE_FEATS)
patchA('decl:FT_SEED', "  ['api-access', 'API access', 'Programmatic access to messaging and reporting.', [['IN', 'metered', 0.05, 'api_call', 'Monthly', 'Active']]],\n", _urows)
patchA('decl:FT_UNITS', "['1K tokens','Per 1K tokens']];", "['1K tokens','Per 1K tokens'], ['workflow','Per workflow']];")   # Workflows is charged per workflow in Plans

# New SKU: Message type is mandatory for messaging SKUs (no "(Optional)", same error as Channel)
patch_any("<label for=\"ns-traffic\">Message type${OPT}</label>${sel('traffic', 'traffic', (NS_MTYPES[N.chan] || []).map(x => [x, x]), N.chan ? 'Select message type' : 'Select channel first', N.chan ? '' : 'disabled')}</div>",
          "<label for=\"ns-traffic\">Message type</label>${sel('traffic', 'traffic', (NS_MTYPES[N.chan] || []).map(x => [x, x]), N.chan ? 'Select message type' : 'Select channel first', N.chan ? '' : 'disabled')}${err('traffic')}</div>")
patch_any("if (msg && !N.chan) E.chan = 'Choose the channel.';", "if (msg && !N.chan) E.chan = 'Choose the channel.'; if (msg && !N.traffic) E.traffic = N.chan ? 'Choose the message type.' : 'Choose the channel first.';")

# New category goes for approval: the CTA says "Submit for approval", the category waits as "Pending approval" and becomes
# active when its change request is approved (routed by Approval configuration › Create catalogue; MD by default)
patch_any('<button class="btn btn-pri" data-act="bkc-save">Create category</button>', '<button class="btn btn-pri" data-act="bkc-save">Submit for approval</button>')
patch_any('Assigned automatically when you create the category.', 'Assigned automatically when you submit the category.')
patch_any("bkCats().push({name:nm, base, cty:D.cty, ccode:D.ccode, codeType:D.codeType, code:D.code, custom:true}); log('Created category', D.ccode, '', `${nm} · ${D.codeType} ${D.code}`);",
          "const crId = 'CR-0' + (Math.max(150, ...S.changeReqs.map(r => +String(r.id).replace(/\\D/g, '') || 0)) + 1);\n"
          "    bkCats().push({name:nm, base, cty:D.cty, ccode:D.ccode, codeType:D.codeType, code:D.code, custom:true, pending:crId});\n"
          "    S.changeReqs.unshift({id:crId, title:`New category · ${nm}`, urgent:false, lines:[{code:'—', field:'New category', old:'—', next:`${nm} · ${D.codeType} ${D.code}`, eff:'On approval', _f:'newcat', _cat:nm}], reason:`New tax category for ${D.cty} · ${D.codeType} ${D.code}`, attach:'', maker:meRaw().name, on:0, status:'Waiting for MD', impact:{review:0, below:0, live:0, plans:0, revenue:'—'}});\n"
          "    log('Submitted category for approval', crId, '', `${nm} · ${D.codeType} ${D.code}`);")
patch_any("if (page){ S.bkCatD = null; S._catFor = null; closeOverlay(); toast(`${nm} created · ${D.codeType} ${D.code}.`, 'ok'); return render(); }",
          "if (page){ S.bkCatD = null; S._catFor = null; closeOverlay(); toast(`${nm} sent for approval · ${D.codeType} ${D.code}.`, 'ok'); return render(); }")
patch_any("toast(`${nm} created · ${D.codeType} ${D.code}.`, 'ok'); bkCatDone(); }", "toast(`${nm} sent for approval · ${D.codeType} ${D.code}.`, 'ok'); bkCatDone(); }")
# approved → active; rejected or sent back → withdrawn
patchA('ACT:cr-decide', "    c.lines.forEach(l => { if (l._f === 'catrename'){", "    c.lines.forEach(l => { if (l._f === 'newcat'){ const k = bkCats().find(x => x.name === l._cat); if (k) delete k.pending; return; } if (l._f === 'catrename'){")
patchA('ACT:cr-decide-ok', "c.decidedBy = me().name;", "c.decidedBy = me().name; c.lines.forEach(l => { if (l._f === 'newcat') S.bkCats = bkCats().filter(x => x.name !== l._cat || x.pending !== c.id); });")
# Categories and tax: a waiting category shows the designer's Pending approval status and can't be edited yet
patch_any('<td class="ctl-cat1"><div class="sk2-n">${esc(c.base || c.name)}</div>',
          '<td class="ctl-cat1"><div class="sk2-n">${esc(c.base || c.name)}${c.pending ? ` <span class="sk2-st t-warn"><i></i>Pending approval</span>` : \'\'}</div>')
patch_any('${mk ? `<button class="btn btn-sec sm" data-act="cat-tax" data-i="${i}">Edit tax code</button>` : \'\'}',
          '${mk ? `<button class="btn btn-sec sm" data-act="cat-tax" data-i="${i}" ${c.pending ? `aria-disabled="true" data-tip="Waiting for approval in ${esc(c.pending)}."` : \'\'}>Edit tax code</button>` : \'\'}')

patch_any("'cat-tax': t => { const c = bkCats()[+t.dataset.i]; if (!c) return;", "'cat-tax': t => { if (t.getAttribute && t.getAttribute('aria-disabled') === 'true') return; const c = bkCats()[+t.dataset.i]; if (!c) return;")

# SaaS features page: a configured feature's action reads "Edit" (was "Add country")
patch_any('data-act="ft-cfg" data-k="${esc(x.key)}">Add country</button>', 'data-act="ft-cfg" data-k="${esc(x.key)}">Edit</button>')

# Default product catalogs (Data & Intelligence, Communicate, Touchpoints, Services): existing SKUs can be assigned;
# New SKU and Bulk upload stay disabled with the designer's lock tooltip
LOCK_TIP = "Product catalogs have a fixed set of SKUs, so new SKUs can’t be added."
patch_any("c.archived ? 'This catalog is archived. Restore it to add SKUs.' : c.locked ? lockTip : '';",
          "c.archived ? 'This catalog is archived. Restore it to add SKUs.' : '';   // a product catalog only takes existing SKUs (set per option)")
patch_any('`<button role="menuitem" data-act="cat-add" data-m="${m}" data-k="${esc(c.name)}" ${m === \'single\' && saasNoNew(c) ?',
          '`<button role="menuitem" data-act="cat-add" data-m="${m}" data-k="${esc(c.name)}" ${c.locked && m !== \'existing\' ? `aria-disabled="true" data-tip="${esc(lockTip)}"` : m === \'single\' && saasNoNew(c) ?')
patchA('decl:cmAddOpts', ": m === 'single' && saasNoNew(c) ?", ": c.locked && m !== 'existing' ? `aria-disabled=\"true\" data-tip=\"" + LOCK_TIP + "\"` : m === 'single' && saasNoNew(c) ?")
patch_any("${dz || (saasNoNew(c) ?", "${dz || (c.locked ? `aria-disabled=\"true\" data-tip=\"${esc(lockTip)}\"` : saasNoNew(c) ?")
patch_any('data-m="file" data-k="${esc(c.name)}" ${dz}>upload a CSV', 'data-m="file" data-k="${esc(c.name)}" ${dz || (c.locked ? `aria-disabled="true" data-tip="${esc(lockTip)}"` : \'\')}>upload a CSV')
patch_any('data-act="cat-add" data-m="existing" data-k="${esc(c.name)}" ${cm.locked ? \'aria-disabled="true" data-tip="Product catalogs have a fixed set of SKUs, so new SKUs can’t be added."\' : \'\'}>',
          'data-act="cat-add" data-m="existing" data-k="${esc(c.name)}">')
patch_any("if (!c || !can.sku() || c.locked || (m === 'single' && saasNoNew(c))) return;", "if (!c || !can.sku() || (c.locked && m !== 'existing') || (m === 'single' && saasNoNew(c))) return;")

# A new SKU waiting for approval can be revised: the change updates its open request (no second request), the SKU stays
# Pending approval and the approver is told
patchA('decl:skuRevBlock', "if (s.status !== 'Active') return", "if (s.status !== 'Active' && s.status !== 'Pending approval') return")
patch_any("s.status === 'Active' ? `<button class=\"btn btn-pri\" data-act=\"sku-rev\"", "['Active','Pending approval'].includes(s.status) ? `<button class=\"btn btn-pri\" data-act=\"sku-rev\"")
patchA('ACT:sku-rev', "  const dup = S.changeReqs.find(c => c.status === 'Waiting for MD' && c.lines.some(l => l.code === s.code));",
       "  const pnew = skuPendingCr(s), dup = !pnew && S.changeReqs.find(c => c.status === 'Waiting for MD' && c.lines.some(l => l.code === s.code));")
patchA('ACT:sku-rev', "${dup ? note('warn', `${dup.id} for this SKU is already waiting for the MD. Wait for it before revising again.`) : ''}",
       "${dup ? note('warn', `${dup.id} for this SKU is already waiting for the MD. Wait for it before revising again.`) : pnew ? note('info', `This SKU is waiting for approval in ${pnew.id}. Your changes update that request.`) : ''}")
patchA('ACT:sku-rev', "<div class=\"b4\">A new rate becomes v${skuVer(s) + 1} once approved. Live deals keep their rates.</div>",
       "<div class=\"b4\">${pnew ? 'The new rate replaces the one waiting for approval.' : `A new rate becomes v${skuVer(s) + 1} once approved. Live deals keep their rates.`}</div>")
patchA('ACT:sku-rev-ok', "  if (bad) return;\n", r"""  if (bad) return;
  const pc = skuPendingCr(s);
  if (pc){ const old = s.name;
    L.forEach(l => { if (l._f === 'name') s.name = l.next; if (l._f === 'rate') s.base = l._v; if (l._f === 'desc') s.desc = l.next === '—' ? '' : l.next; });
    pc.lines.forEach(l => { if (l.code === s.code && l.field === 'New SKU' && s.type !== 'Feature') l.next = `${rate(s.base, s.cur)} per ${s.unit}`; });
    if (old !== s.name) pc.title = pc.title.split(old).join(s.name);
    (pc.revs = pc.revs || []).push({by:meRaw().name, on:0, what:L.map(l => l.field).join(', '), reason:r});
    const cur = typeof apCrCur === 'function' ? apCrCur(pc) : null;
    (cur ? cur.names : [mdName()]).forEach(n => S.notifs.unshift({for:n, to:[], on:0, text:`${fullOf(meRaw().name)} revised ${s.code} in ${pc.id} (${L.map(l => l.field.toLowerCase()).join(', ')}). It still needs your approval.`, go:{v:'work', tab:'approvals', grp:'SKU approval'}}));
    log('Revised SKU waiting for approval', pc.id, s.code, L.map(l => l.field).join(', '));
    S._skr = null; closeOverlay(); toast(`${s.code} updated in ${pc.id}. It’s still waiting for approval.`, 'ok'); return render(); }
""")
Akey['decl:skuRevBlock']['text'] += "\nconst skuPendingCr = s => s && s.status === 'Pending approval' ? S.changeReqs.find(c => c.status === 'Waiting for MD' && c.lines.some(l => l.code === s.code && l.field === 'New SKU')) : null;   // the request a new SKU is waiting in"

# Catalogs side list: "All" and "Archived" tabs under the Catalogs heading (the designer's sk2-tabs); All lists the active
# catalogs, Archived the archived ones. Archiving a catalog opens the Archived tab; restoring one goes back to All.
patchA('decl:cmNav', "const L = cmShown(), item = c =>", "const all = cmShown(), L = all.filter(c => !c.archived), AR = all.filter(c => c.archived), tab = S._cmTab === 'archived' ? 'archived' : 'all', LT = tab === 'archived' ? AR : L, item = c =>")
patchA('decl:cmNav', "${c.archived ? ' <span class=\"ctl-mut\">(archived)</span>' : ''}", "")
patchA('decl:cmNav', "New catalog</button>` : ''}</div>",
       "New catalog</button>` : ''}</div>\n    <nav class=\"sk2-tabs ctl-ntabs\" role=\"tablist\" aria-label=\"Catalog status\">${[['all', 'All', L.length], ['archived', 'Archived', AR.length]].map(([k, l, n]) => `<button class=\"sk2-tab ${tab === k ? 'on' : ''}\" role=\"tab\" aria-selected=\"${tab === k}\" data-act=\"cm-ntab\" data-k=\"${k}\">${l}<span class=\"sk2-bc num\">${n}</span></button>`).join('')}</nav>")
patchA('decl:cmNav', "${L.length > 6 ? `<label class=\"search sm ctl-ns\">", "${LT.length > 6 ? `<label class=\"search sm ctl-ns\">")
patchA('decl:cmNav', "<div class=\"ctl-list\">${L.map(item).join('')}</div>", "<div class=\"ctl-list\">${LT.map(item).join('')}</div>${LT.length ? '' : `<div class=\"b4 ctl-none\">${tab === 'archived' ? 'No archived catalogs.' : 'No active catalogs.'}</div>`}")
Akey['decl:cmNav']['text'] += "\nACT['cm-ntab'] = t => { S._cmTab = t.dataset.k; render(); };"
patch_any("c.archived = true; closeOverlay();", "c.archived = true; S._cmTab = 'archived'; closeOverlay();")
patch_any("c.archived = false; log('Restored catalog', c.name);", "c.archived = false; S._cmTab = 'all'; log('Restored catalog', c.name);")

# SaaS features: the status filter lists the statuses the table shows (Active, Pending approval … Unconfigured), not Configured/Unconfigured
patchA('decl:cmFeatsView', "stOf = x => x.cfgs.length ? 'configured' : 'new';",
       "stOf = x => x.cfgs.length ? [...new Set(x.cfgs.map(g => g.status))] : ['Unconfigured'], ST_ORDER = ['Active','Pending approval','Draft','Sent back','Inactive','Rejected','Unconfigured'];")
patchA('decl:cmFeatsView', "(!f.st.length || f.st.includes(stOf(x)))", "(!f.st.length || stOf(x).some(v => f.st.includes(v)))")
patchA('decl:cmFeatsView', "[['new', 'Unconfigured'], ['configured', 'Configured']]",
       "[...new Set(L0.flatMap(stOf))].sort((a, b) => (ST_ORDER.indexOf(a) + 99) % 99 - (ST_ORDER.indexOf(b) + 99) % 99).map(v => [v, v])")

# Revise catalog: the same fields as Create catalog (code, name, description, type, and the type's channels / charging /
# services); the type is locked. Revising never adds or removes SKUs (Add SKU does that). Changes go for approval.
REV_OLD = 'body.innerHTML = `<div class="fgrid qm-rev"><div class="field"><label for="bk-code">Catalog code</label><input class="inp num bk-code" id="bk-code" value="${esc(B.code)}" readonly aria-describedby="bk-code-h"><span class="hint" id="bk-code-h">Can’t be changed.</span></div>\n          <div class="field"><label for="bk-cat">Name</label><input class="inp${B.errs.cat ? \' bad\' : \'\'}" id="bk-cat" data-inp="bk" data-k="cat" maxlength="60" value="${esc(B.cat)}" autocomplete="off">${err(\'cat\')}</div>\n          <div class="field full"><label for="bk-desc">Description${OPT}</label><textarea class="inp" id="bk-desc" data-inp="bk" data-k="desc" rows="2" maxlength="300">${esc(B.desc || \'\')}</textarea></div>\n          <div class="full">${G(\'cats\', \'Allowed categories\', bkCats().map(c => [c.name, c.name]), \'A SKU picks one of these. Its category sets the tax code.\', \'bk-addcat\', \'Select categories\', \'category\')}</div>\n          <div class="full">${G(\'attrs\', \'Required SKU attributes\', CAT_ATTRS, \'Every SKU in this catalog must fill these before it can be activated.\', \'\', \'Select attributes\', \'attribute\')}</div></div>\n        ${P.upload || \'\'}`;'
patch_any(REV_OLD, """body.innerHTML = `<div class="fgrid qm-rev"><div class="field"><label for="bk-code">Catalog code</label><input class="inp num bk-code" id="bk-code" value="${esc(B.code)}" readonly aria-describedby="bk-code-h"><span class="hint" id="bk-code-h">Can’t be changed.</span></div>
          <div class="field"><label for="bk-cat">Catalog name</label><input class="inp${B.errs.cat ? ' bad' : ''}" id="bk-cat" data-inp="bk" data-k="cat" maxlength="60" value="${esc(B.cat)}" autocomplete="off">${err('cat')}</div>
          <div class="field full"><label for="bk-desc">Description${OPT}</label><textarea class="inp" id="bk-desc" data-inp="bk" data-k="desc" rows="2" maxlength="300">${esc(B.desc || '')}</textarea></div>
          ${bkTaxSection(B, B.errs, err, G)}</div>`;""")
patch_any("data-act=\"bk-type-pick\" data-v=\"${v}\">${l}</button>", "data-act=\"bk-type-pick\" data-v=\"${v}\" ${B.revise ? 'disabled data-tip=\"A catalog’s type can’t be changed.\"' : ''}>${l}</button>")
patch_any("${changes && bkDetailsOk(B) && bkExOk(B) ? '' : 'disabled'}", "${changes && bkDetailsOk(B) ? '' : 'disabled'}")
patch_any("revise:c.name, mode:'existing', step:'upload',", "revise:c.name, mode:'existing', step:'upload', chans:[...(c.chans || [])], svcs:[...(c.svcs || [])], access:c.access || '',")
# what counts as a change: name, description and the type's setting (SKUs aren't edited here)
patchA('decl:bkReviseChanges', """  const now = new Set(S.skus.filter(x => x.catalogName === B.revise && x.status === 'Active').map(x => x.code)), sel = new Set(B.ex.map(x => x.code));
  B.ex.forEach(x => { const s = sku(x.code); if (!s) return; if (!now.has(x.code)) n++; if (!bkFeat(B) && String(x.base).trim() && +x.base !== s.base) n++; });
  now.forEach(c => { if (!sel.has(c)) n++; });""", """  catRevSets(B, cur).forEach(() => n++);""")
Akey['decl:bkReviseChanges']['text'] += r"""
/* the type's own setting, changed in a revision: Allowed channels (Messaging), How are features charged? (SaaS), Allowed services (Services) */
function catRevSets(B, cur){ const L = [], j = a => (a || []).join('|'), chan = v => (BK_CHANS.find(x => x[0] === v) || [, v])[1], acc = v => (BK_ACCESS.find(x => x[0] === v) || [, v || '—'])[1];
  if (cur.prod === 'messaging' && j(B.chans) !== j(cur.chans)) L.push({code:'—', field:'Allowed channels', old:(cur.chans || []).map(chan).join(', ') || 'None', next:(B.chans || []).map(chan).join(', ') || 'None', eff:'On approval', _f:'catset', _key:'chans', _v:[...(B.chans || [])], _code:cur.code});
  if (cur.prod === 'clarity' && (B.access || '') !== (cur.access || '')) L.push({code:'—', field:'How features are charged', old:acc(cur.access), next:acc(B.access), eff:'On approval', _f:'catset', _key:'access', _v:B.access, _code:cur.code});
  if (cur.prod === 'svc' && j(B.svcs) !== j(cur.svcs)) L.push({code:'—', field:'Allowed services', old:(cur.svcs || []).join(', ') || 'None', next:(B.svcs || []).join(', ') || 'None', eff:'On approval', _f:'catset', _key:'svcs', _v:[...(B.svcs || [])], _code:cur.code});
  return L; }"""
# submit: a revision only sends its field changes
patchA('decl:bkSubmitExisting', "if (!bkDetailsOk(B) || !bkExOk(B)){", "if (!bkDetailsOk(B) || (!B.revise && !bkExOk(B))){")
patchA('decl:bkSubmitExisting', "  B.ex.forEach(x => { const s = sku(x.code); if (!s) return; const nv = +(+x.base).toFixed(4);", "  (B.revise ? [] : B.ex).forEach(x => { const s = sku(x.code); if (!s) return; const nv = +(+x.base).toFixed(4);")
patchA('decl:bkSubmitExisting', "    S.skus.filter(x => x.catalogName === B.revise && x.status === 'Active' && !keep.has(x.code)).forEach(x => lines.push({code:x.code, field:'Catalog', old:B.revise, next:'—', eff:'On approval', _f:'catalog'}));\n", "")
patchA('decl:bkSubmitExisting', "    if (!lines.length){ return toast('Nothing has changed yet.', 'info'); } }",
       "    if (cur){ if (cur.prod === 'messaging' && !(B.chans || []).length) return toast('Choose at least one channel.', 'err'); if (cur.prod === 'svc' && !(B.svcs || []).length) return toast('Choose at least one service.', 'err'); if (cur.prod === 'clarity' && !B.access) return toast('Choose how features are charged.', 'err'); lines.push(...catRevSets(B, cur)); }\n    if (!lines.length){ return toast('Nothing has changed yet.', 'info'); } }")
patchA('decl:bkSubmitExisting', "  const nc = lines.filter(l => l._f === 'rate').length, id = 'CR-0' + (150 + S.changeReqs.length);",
       "  const nc = lines.filter(l => l._f === 'rate').length, id = 'CR-0' + (Math.max(150, ...S.changeReqs.map(r => +String(r.id).replace(/\\D/g, '') || 0)) + 1);")
patchA('decl:bkSubmitExisting', "  if (B.modal) qmClose(); S.bk = null; toast(`${id} sent to the MD · ${plural(B.ex.length, feat ? 'feature' : 'SKU')}${nc ? `, ${plural(nc, 'new version')}` : ''}.`, 'ok'); cmBack();",
       "  if (B.modal) qmClose(); const wasRev = B.revise; S.bk = null; toast(wasRev ? `${id} sent for approval · ${plural(lines.length, 'change')}.` : `${id} sent to the MD · ${plural(B.ex.length, feat ? 'feature' : 'SKU')}${nc ? `, ${plural(nc, 'new version')}` : ''}.`, 'ok'); cmBack();")
# approved → the catalog takes the new setting
patchA('ACT:cr-decide', "    c.lines.forEach(l => { if (l._f === 'newcat'){", "    c.lines.forEach(l => { if (l._f === 'catset'){ const k = S.catalogs.find(x => x.code === l._code); if (k) k[l._key] = Array.isArray(l._v) ? [...l._v] : l._v; return; } if (l._f === 'newcat'){")

# Default catalogs hold the product features listed for them in Plans › Modify plan (Helo Clarity), per the Feature
# Inclusions sheet; "Assign existing SKUs" in one of them offers only that catalog's own features.
DEF_CAT_FEATS = {'Data & Intelligence':['ingest-sdk','ingest-files','segment-projects','funnel','scv-basic','ingest-api','segment-portfolio','event-analytics','cql','journeys','scv-advanced'],
  'Communicate':['campaign-schedule','workflow-builder','campaign-single','campaign-mco','campaign-files','ai-optimiser','events-triggers','workflow-ab','workflow-api','campaign-ab','campaign-segments','analyse-dashboard','analyse-reports','content-studio'],
  'Touchpoints':['shortlinks','qr-custom','smart-redirect']}
assert all(k in FEAT_KEYS.values() for L in DEF_CAT_FEATS.values() for k in L)
patchA('decl:bkExPool', "const bkExPool = B =>", "const bkExPool0 = B =>")
Akey['decl:bkExPool']['text'] += """
/* default catalogs: their SKU list is the product features Plans lists for them */
const DEF_CAT_FEATS = """ + json.dumps(DEF_CAT_FEATS) + """;
const defCatCodes = name => DEF_CAT_FEATS[name] ? new Set(DEF_CAT_FEATS[name].map(k => 'FT-' + k.toUpperCase() + '-IN')) : null;
const bkExPool = B => { const L = defCatCodes(B.fixed); if (L) return S.skus.filter(s => L.has(s.code) && s.status === 'Active');   // in a default catalog: only its own features
  const c = B.fixed && catByName(B.fixed); if (c && c.ch) return bkExPool0(B).filter(s => s.catalogue === c.name || cmChan(s) === c.name);   // SMS, RCS, WhatsApp: only that channel's SKUs
  return bkExPool0(B); };
function defCatSync(){ skuCatalogs(); ftList();
  const saas = (bkCats().find(k => k.cty === 'IN' && k.kind === 'saas') || {}).name;
  Object.keys(DEF_CAT_FEATS).forEach(name => { const c = catByName(name); if (!c) return; const L = defCatCodes(name);
    Object.assign(c, {prod:'clarity', access:'onoff', chans:[]});   // a SaaS catalog has no channels if (saas && !c.categories.includes(saas)) c.categories.unshift(saas);
    S.skus.filter(s => s.catalogName === name && !L.has(s.code)).forEach(s => Object.assign(s, {catalogName:null, catalogCategory:null, unassigned:true}));   // what isn't a Plans feature of this catalog moves out: unassigned, still in All SKUs
    S.skus.filter(s => L.has(s.code)).forEach(s => Object.assign(s, {catalogName:name, catalogCategory:saas || s.catalogCategory, unassigned:false})); }); }"""

# Assign existing SKUs: when every SKU related to the catalog is already in it (or there are none), show an empty state
patchA('decl:bkpPaint', "  const filtered = P.q || P.cty.length || P.ch.length || P.only;\n",
       """  const filtered = P.q || P.cty.length || P.ch.length || P.only;
  if (B.fixed && !filtered && (!pool.length || pool.every(s => s.catalogName === B.cat))){
    box.innerHTML = `<div class="bkp-none"><span class="b3">No ${noun}s related to this catalog</span><span class="b4">${pool.length ? `Every ${noun} related to ${esc(B.cat)} is already in it.` : `There are no approved ${noun}s related to ${esc(B.cat)} yet.`}</span></div>`;
    bkpFoot(); const sm = $('#bkp-sum'); if (sm) sm.textContent = ''; return; }
""")

# SKU and catalog creation belong to the Sales Manager: every Sales Manager can create (not only a granted SKU Maker),
# the "Switch to SKU Maker to create" button is gone, and Catalogs copy names the Sales Manager
patchA('decl:can', "  sku:           () => meRaw().perms.includes('SKU Maker'),", "  sku:           () => meRaw().perms.includes('SKU Maker') || (T() === 'sm' && !isTM()),   // Sales Managers create SKUs and catalogs")
patchA('decl:cmShell', """${can.sku() ? '' : `<button class="btn btn-sec" data-act="sku-as-maker" title="Creating SKUs is done by the SKU Maker">${I('user',16)}Switch to SKU Maker to create</button>`}""", "")
patch_any("'Only the SKU Maker can add SKUs. Switch to the SKU Maker to add them.'", "'Only the Sales Manager can add SKUs.'")
patch_any('data-tip="Only the SKU Maker can create SKUs. Switch to the SKU Maker to create one."', 'data-tip="Only the Sales Manager can create SKUs."')
patch_any("openDrawer('New change request', 'Made by the SKU Maker, approved by the MD before it takes effect',", "openDrawer('New change request', 'Made by the Sales Manager and approved before it takes effect',")
patch_any("k === 'back' ? 'Send back to the SKU Maker' : 'Reject change request'", "k === 'back' ? 'Send back to the maker' : 'Reject change request'")

patch_any(' : `<button class="btn btn-sec" style="height:40px" data-act="sku-as-maker" title="Creating SKUs is done by the SKU Maker">${I(\'user\',16)}Switch to SKU Maker to create</button>`}', ' : \'\'}')   # the older SKUs list: no "Switch to SKU Maker" button either

# Catalog is optional on New SKU and SaaS feature setup: leaving it empty means no catalog, so there is no "No catalog" option
patch_any("sel('cat', 'cat', [['__none__', 'No catalog'], ...nsCats().map(", "sel('cat', 'cat', [...nsCats().map(")
patch_any('${N.free && (!N.cat || N.cat === \'__none__\') ? `<span class="hint">${N.cat ? \'This SKU stays unassigned. You can add it to a catalog later.\' : \'Choose No catalog to keep it unassigned.\'}</span>` : \'\'}', '${N.free && (!N.cat || N.cat === \'__none__\') ? `<span class="hint">Leave it empty to keep this SKU unassigned. You can add it to a catalog later.</span>` : \'\'}')
patch_any("sel('cat', [['__none__', 'No catalog'], ...saasCats.map(", "sel('cat', [...saasCats.map(")

# demo data: the old-style rate revisions (Trellis Collections, Coral Orders) and their log line are gone; rate revisions
# are raised from a live deal's Revise rate now
patch_any("  // 1. Rate revision waiting for Sales Manager (Trellis Collections)\n  { const w = W('Trellis Collections'), live = liveDeal(w.id);\n    live.lines.push({code:'HMS-SM-IN-009', on:true, rate:0.19});\n    const r = cloneDeal(live, {kind:'revision', stage:'Waiting for Sales Manager', parent:live.id, maker:'Dev', created:-2, submitted:-2});\n    r.lines.slice(0,3).forEach((l, i) => { l.prev = l.rate; l.rate = +(l.rate * (i === 1 ? 0.92 : 0.96)).toFixed(4); l.revised = true; });\n    r.docs = {msa:{state:'Generated', how:'Renewed with rate revision clause'}, sla:{state:'Signed', how:'As per plan'}, approval:{state:'Uploaded', file:'Trellis_rate_approval_email.pdf'}, ent:{state:'Generated'}};\n    r.chain = [{who:'Dev', role:'Submitted', on:-2, state:'ok'},{who:'Arun', role:'Sales Manager', state:'now'}];\n    r.notes = 'Customer moved 40% of SMS volume to WhatsApp utility. Matching competitor rate on utility.';\n    r.history.unshift({on:D(-2), who:'Dev', what:'Rate revision submitted for approval'});\n  }\n", "  { const w = W('Trellis Collections'), live = liveDeal(w.id); live.lines.push({code:'HMS-SM-IN-009', on:true, rate:0.19}); }\n")
patch_any("  { const w = W('Coral Orders'), live = liveDeal(w.id); const r = cloneDeal(live, {kind:'revision', stage:'Waiting for Sales Manager', parent:live.id, maker:'Dev', created:-3, submitted:-3});\n    r.lines.slice(0, 2).forEach(l => { l.prev = l.rate; l.rate = +(l.rate * 0.95).toFixed(4); l.revised = true; });\n    r.docs = {msa:{state:'Generated', how:'Renewed with rate revision clause'}, approval:{state:'Uploaded', file:'Coral_volume_commitment.pdf'}};\n    r.chain = [{who:'Dev', role:'Submitted', on:-3, state:'ok'},{who:'Arun', role:'Sales Manager', state:'now'}]; r.history.unshift({on:D(-3), who:'Dev', what:'Rate revision submitted for approval'}); }\n", '')
patch_any("    L(-2,'Dev','Sales Rep','Submitted rate revision','Trellis Collections'),\n", '')
# no override requests: the demo requests and their log line go, and only the MD applies an override (as on the Accounts pages)
patch_any("    {id:'SR-14', kind:'Override', aid:A('Konkan Agro').id, by:'Kavya', on:-1, reason:'Customer committed to pay by 28 Oct. Confirmed on call with their CFO.', until:14, max:500000, status:'Waiting for MD'},\n", '')
patch_any("    L(-1,'Kavya','Finance','Requested MD override','Konkan Agro'),\n", '')
patch_any("  S.susReqs.push({id:'SR-17', kind:'Override', aid:A('Copperleaf Retail').id, by:'Arun', on:-1, reason:'Contract dispute resolved; customer signed the revised terms on 19 Oct.', until:30, max:null, status:'Waiting for MD'});\n", '')
patch_any("  S.susReqs.push({id:'SR-16', kind:'Override', aid:A('Zenith Travel').id, by:'Arun', on:0, reason:'Customer confirmed payment of ₹11.3 L on 24 Oct; finance head copied.', until:10, max:1500000, status:'Waiting for MD'});\n", '')
patch_any("requestOverride:() => ['sm','fin'].includes(T()) && !isTM(),", 'requestOverride:() => false,   // no override requests: only the MD applies an override')
# deals are approved by the MD: the demo deals that waited on a Sales Manager wait on the MD
patch_any("  // 8. Waiting for Sales Manager for 7 days (late) — Bluebell new deal adding Convo\n  { const w = W('Doctor Engagement'), live = liveDeal(w.id);\n    const d = cloneDeal(live, {kind:'new', stage:'Waiting for Sales Manager', parent:live.id, maker:'Dev', created:-9, submitted:-9});\n    d.products = ['clarity','convo']; d.sub.convo = 80000;\n    d.chain = [{who:'Dev', role:'Submitted', on:-9, state:'ok'},{who:'Arun', role:'Sales Manager', state:'now'}];", "  // 8. Waiting for the MD for 9 days (late) — Bluebell new deal adding Convo (deals are approved by the MD)\n  { const w = W('Doctor Engagement'), live = liveDeal(w.id);\n    const d = cloneDeal(live, {kind:'new', stage:'Waiting for MD', parent:live.id, maker:'Dev', created:-9, submitted:-9});\n    d.products = ['clarity','convo']; d.sub.convo = 80000;\n    d.chain = [{who:'Dev', role:'Submitted', on:-9, state:'ok'},{who:'Meera', role:'MD', state:'now'}];")
patch_any("products:['clarity','messaging'], stage:'Waiting for Sales Manager', maker:'Riya', created:-2, submitted:-2, start:6, discount:7});\n    d.sub = {clarity:180000}; d.docs = {}; d.chain = [{who:'Riya', role:'Submitted', on:-2, state:'ok'},{who:'Arun', role:'Sales Manager', state:'now'}];", "products:['clarity','messaging'], stage:'Waiting for MD', maker:'Riya', created:-2, submitted:-2, start:6, discount:7});\n    d.sub = {clarity:180000}; d.docs = {}; d.chain = [{who:'Riya', role:'Submitted', on:-2, state:'ok'},{who:'Meera', role:'MD', state:'now'}];")

# plans and add-on packs (embedded page): the approver comes from Approval configuration › Revise plan
patchA('decl:pkDoc', "(T() === 'md')", "apPlanMine()")
# its toasts sit top right like the portal's (the page's own are bottom centre)
patchA('decl:PK_CSS', ".rail,.split .rail{top:16px!important}</style>';", ".rail,.split .rail{top:16px!important}.toast{left:auto!important;right:calc(16px + env(safe-area-inset-right,0px))!important;top:calc(12px + env(safe-area-inset-top,0px))!important;bottom:auto!important;transform:none!important}.scrim{padding:16px calc(16px + 2 * var(--frame-dx,0px)) calc(16px + 2 * var(--frame-dy,0px)) 16px!important}</style>';")
patchA('decl:pkFrame', "if (!can.sku() && T() !== 'md') return noAccess(label);", "if (!can.sku() && T() !== 'md' && !apPlanMine()) return noAccess(label);")
# account creation journey · setup summary: approval status of the plan
patch_any("""        planSt = ['Sent back', 'Approved'].includes(od.stage) ? 'action' : 'pending';
        planSub = esc(od.stage);""",
"""        planSt = ['Sent back', 'Approved'].includes(od.stage) || (od.stage === 'Draft' && (od.chain || []).some(c => c.state === 'bad')) ? 'action' : apDealWaiting(od) ? 'review' : 'pending';
        planSub = apDealSub(od);""")

# BOOT tail of A moves to the very end
# ---------- B: the sections file 2 adds (Home 2 dashboard, approval configuration and helpers) ----------
TAKE = ['HOME · customisable dashboard','SALES TEAM PERFORMANCE widget','USAGE widgets','TRIALS widget','DASHBOARD PERIOD','ADD WIDGET','ADMIN PANEL · APPROVAL MANAGEMENT','APPROVAL MANAGEMENT 2','APPROVAL MANAGEMENT 3','VERSIONS 1B AND 2B','1B ·','4 · Hybrid','2B ·','HOME 2','1 · ','2 · ','REVENUE ·','PAYMENTS ·','TRIALS ·','WORKSPACE PIPELINE ·','3 · ','4 · ','5 · ','ACCOUNTS · Account','SALES TEAM ·','USAGE ·','ACTION CENTRE','SALES REP PERFORMANCE','EDIT DASHBOARD','CUSTOMISE','LEGENDS','USAGE —','TICK-BOX','NOV 21','APPROVAL CONFIGURATION']
BL = b_js.split('\n')
SECS = [(i + 1, BL[i].strip()) for i in range(1, len(BL)) if re.match(r'^\s*/\* =+', BL[i - 1])]
def b_section(line):
    s = ''
    for l, n in SECS:
        if l <= line: s = n
    return s
def taken(c):
    s = b_section(c['line'])
    return any(s.startswith(t) for t in TAKE)
a_texts = set(c['text'] for c in chunks_of(a_js))
B_ADD = []
for c in B:
    if not taken(c): continue
    if c['text'] in a_texts: continue
    if c['key'] == 'stmt:Object.assign(ACT, {' and "'range-apply'" in c['text'] and "'accf-clear'" in c['text']: continue   # same handlers A already has
    B_ADD.append(c['text'])

B_JS = '\n'.join(B_ADD)
for old, new, n in [
    ("who:d.stage === 'Waiting for MD' ? 'MD · Meera Iyer' : 'Sales Manager · Arun Mehta'", "who:apWhoTag(d)", 1),
    ("(d.stage === 'Waiting for MD' ? mine : team).push(x)", "(apDealMine(d) ? mine : team).push(x)", 1),
    ("S.deals.filter(d => d.stage === 'Waiting for MD' && d.submitted <= eo", "S.deals.filter(d => apDealMine(d) && d.submitted <= eo", 2),
    ("VIEWS.appr6 = function(){\n  if (!can.admin() || isTM())", "VIEWS.appr6 = function(){\n  if (!can.apprRules() || isTM())", 1)]:
    B_JS = must_replace(B_JS, old, new, n)    # the dashboard's approvals follow Approval configuration: waiting on the viewer
# Approval configuration: deals are approved by the MD (every group of the Create deal rule, and Otherwise, go to the MD)
B_JS = must_replace(B_JS, "  'deal-create':  a6Base([a6G('any', [a6C('discount', 'gt', 30), a6C('value', 'gt', 4000000)], [['role:mgr'], ['role:md']]),\n                          a6G('any', [a6CL('discLim'), a6CL('valLim')], [['role:mgr']])], null, 'Meera Iyer', -9),", "  'deal-create':  a6Base([a6G('any', [a6C('discount', 'gt', 30), a6C('value', 'gt', 4000000)], [['role:md']]),   // deals are approved by the MD\n                          a6G('any', [a6CL('discLim'), a6CL('valLim')], [['role:md']])], {mode:'approve', levels:[{who:['role:md']}]}, 'Meera Iyer', -9),")
import base64
AC_HTML = open(ac_path, encoding='utf-8').read()
# Actions in the embedded page: SKU approval and a new "Plans & add-ons" tab always show for the MD; plan and add-on
# rows open the portal's Plans / Add-on packs pages (the bridge in accounts_embed.js feeds the data)
for old, new in [
    ("...(T() === 'md' ? ['Workspace', 'Trial extension', 'Account'] : [])", "...(T() === 'md' ? ['Workspace', 'SKU approval', 'Trial extension', 'Account', 'Plans & add-ons'] : [])"),
    ("['Account changes','Deals','Workspace','SKU approval','Trial extension','Account'].indexOf(k)", "['Account changes','Deals','Workspace','SKU approval','Trial extension','Account','Plans & add-ons'].indexOf(k)"),
    ("function apprGroup(i){\n  const v = i.go?.v;\n", "function apprGroup(i){\n  const v = i.go?.v;\n  if (v === 'packs' || v === 'addons') return 'Plans & add-ons';\n"),
    ("function go(v, params = {}){ S.route = Object.assign({v}, params);", "function go(v, params = {}){ if (['packs','addons','skus'].includes(v) && window.__acBridge) return window.__acBridge.go(v, params); S.route = Object.assign({v}, params);")]:
    AC_HTML = must_replace(AC_HTML, old, new)
AC_JS = 'const AC_SRC = "' + base64.b64encode(AC_HTML.encode('utf-8')).decode() + '";\n' + open(os.path.join(HERE, 'accounts_embed.js'), encoding='utf-8').read()
INTEGRATE = AC_JS + '\n' + open(os.path.join(HERE, 'integrate.js'), encoding='utf-8').read()
js = '\n'.join(c['text'] for c in A if c['text'] != '') + \
     '\n\n/* =====================================================================\n   FROM "DASHBOARD AND APPROVAL CONFIGURATION": Home 2 dashboard, approval configuration and their helpers\n   ===================================================================== */\n' + \
     B_JS + '\n\n' + INTEGRATE + \
     "\n/* =====================================================================\n   BOOT\n   ===================================================================== */\nh2Seed();\ndefCatSync();\ntrialDocApi.resume();\nentApi.restore();\nif (!PERSONA_SWITCH.includes(S.user)) S.user = 'meera';\nrender();\n"

ZOOM_JS = """/* File 2 drew the portal at 90% browser zoom. The merged portal uses one scale for every screen:
   set UI_ZOOM to 0.9 to see everything the way file 2 showed it. File 2's code reads positions through zRect() / zIW() etc. */
(function(){
  const Z = 1; window.UI_ZOOM = Z; if (Z !== 1) document.documentElement.style.zoom = Z;
  document.documentElement.style.setProperty('--zvh', `calc(1vh / ${Z})`); document.documentElement.style.setProperty('--zvw', `calc(1vw / ${Z})`);
  Element.prototype.zRect = function(){ const r = this.getBoundingClientRect(); return new DOMRect(r.x / Z, r.y / Z, r.width / Z, r.height / Z); };
  window.zIW = () => window.innerWidth / Z; window.zIH = () => window.innerHeight / Z; window.zSX = () => window.scrollX / Z; window.zSY = () => window.scrollY / Z;
})();"""

b_shell = must_replace(b_shell, '<main id="view"></main>', '<main id="view"></main>\n    <iframe id="acframe" title="Accounts and Actions" hidden style="width:100%;height:calc(100vh - 60px);border:0;vertical-align:top;background:var(--canvas)"></iframe>')
css = cssmerge.merge_text(a_css, b_css)
css += '\n/* merged: a table\'s hidden label (.sr) stays inside its scroll box, so a wide table never scrolls the whole page */\n.sk2-card > .tblscroll{position:relative}\n'
css += '/* merged: the sticky cell holding an open row menu sits above the next rows, so the menu is never hidden */\ntd:has(> .sk2-mw > .sk2-catm){z-index:31}\n'
css += '/* merged: All / Archived tabs in the Catalogs side list */\n.ctl-nav .ctl-ntabs{height:40px;padding:0 4px;margin:0 0 8px;background:transparent}\n'
css += '/* merged: 12px between the upload drop zone and "Remove duplicate records" */\n.bk-up + .bk-chk{margin-top:12px;display:flex;width:fit-content}\n'
css += '/* merged: 16px between an uploaded file and its errors; 8px from the error line to the rows to fix */\n.bk-fwrap{gap:16px}\n.bk-files + .tblwrap{margin-top:8px}\n'
css += '/* merged: 16px between the browse section and Uploaded files */\n.bk-chk + .bk-files{margin-top:16px}\n'
css = css.replace('--zvh:calc(1vh / .9);--zvw:calc(1vw / .9)', '--zvh:1vh;--zvw:1vw')
head_a = A_HTML[:A_HTML.index('<style>')]
tail_a = A_HTML[A_HTML.rindex('</script>') + len('</script>'):]
html = head_a + '<style>\n' + css + '\n</style>\n\n' + b_shell + '\n<script>\n' + ZOOM_JS + '\n</script>\n<script>\n' + js + '\n</script>' + tail_a
open(out_path, 'w', encoding='utf-8').write(html)
print('wrote', out_path, f'{len(html)/1e6:.1f} MB', 'B chunks added:', len(B_ADD))
