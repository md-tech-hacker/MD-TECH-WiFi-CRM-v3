/* MD TECH Studio UI: functional extensions over the existing authenticated API.
   No simulated network telemetry, remote assets, build step, or framework. */
const APP_META = {
  youtube:['Video','YT','#fff2ec','#ed573e'],instagram:['Social','IG','#fcecf5','#ca4c91'],facebook:['Social','f','#eaf1ff','#3479e2'],tiktok:['Social','♪','#edf3f7','#19283a'],netflix:['Video','N','#fff0f0','#db3648'],discord:['Chat','D','#efedff','#6766df'],whatsapp:['Chat','W','#e6faef','#1caa69'],telegram:['Chat','T','#e9f6ff','#399bc6'],roblox:['Games','R','#edf1f6','#506079'],steam:['Games','S','#e9eff8','#264869'],spotify:['Music','S','#e4f9eb','#1b9e57'],twitter:['Social','X','#edf1f5','#253650'],reddit:['Social','r','#fff2eb','#f46e39'],snapchat:['Social','S','#fff9e1','#c9a314'],pinterest:['Social','P','#ffedf0','#ce3b52'],twitch:['Video','T','#f1eaff','#8554c9']
};
const prettifyName = s=>({youtube:'YouTube',tiktok:'TikTok',whatsapp:'WhatsApp',roblox:'Roblox',netflix:'Netflix',discord:'Discord',facebook:'Facebook',instagram:'Instagram',telegram:'Telegram',spotify:'Spotify'}[String(s||'').toLowerCase()]||String(s||'').replace(/\b\w/g,m=>m.toUpperCase()));
const numberFmt = n=>Number(n||0).toLocaleString();
const progressRing = (value, max, label, caption='') => {
 const pct=Math.max(0,Math.min(100,max?Math.round(value/max*100):0));
 return `<div class="progress-ring" data-pct="${pct}"><div class="ring-inner"><strong>${numberFmt(value)}</strong><small>${escapeHTML(label)}</small></div></div>${caption?`<span class="ring-caption">${escapeHTML(caption)}</span>`:''}`;
};
function applyVisualPercentages(){document.querySelectorAll('[data-pct]').forEach(el=>{const pct=Math.max(0,Math.min(100,Number(el.dataset.pct)||0));if(el.classList.contains('progress-ring'))el.style.setProperty('--ring',pct+'%');else el.style.width=pct+'%';});}
function infoPill(text, type='neutral') {return `<span class="info-pill ${type}">${escapeHTML(text)}</span>`}
function miniStat(icon, name, amount, foot, type='blue') {return `<div class="mini-stat"><div class="mini-stat-icon ${type}">${ic(icon,19)}</div><div><small>${escapeHTML(name)}</small><strong>${escapeHTML(amount)}</strong><span>${escapeHTML(foot)}</span></div></div>`}
function dashboardActionCenter(d){
 return `<div class="action-center panel"><div class="action-center-intro"><span class="panel-eyebrow">QUICK ACCESS</span><h3>Manage your network</h3><p>Everything in one place, from guest access to policy controls.</p></div><div class="shortcut-grid">
 <button data-page="users" class="shortcut"><span class="shortcut-icon blue">${ic('users',21)}</span><span><b>User credentials</b><small>Manage guest accounts</small></span>${ic('arrow',16)}</button>
 <button data-page="vouchers" class="shortcut"><span class="shortcut-icon purple">${ic('ticket',21)}</span><span><b>Access vouchers</b><small>Create guest codes</small></span>${ic('arrow',16)}</button>
 <button data-page="apps" class="shortcut"><span class="shortcut-icon coral">${ic('globe',21)}</span><span><b>Apps & websites</b><small>Manage block rules</small></span>${ic('arrow',16)}</button>
 <button data-page="reports" class="shortcut"><span class="shortcut-icon green">${ic('activity',21)}</span><span><b>Analytics center</b><small>View reported usage</small></span>${ic('arrow',16)}</button></div></div>`;
}
function enhanceRecords(page, rows){
 const content=document.getElementById('content');if(!content)return;
 const summary={
 users:[['Total accounts',rows.length,'users','blue'],['Enabled',rows.filter(x=>x.enabled).length,'shield','green'],['Disabled',rows.filter(x=>!x.enabled).length,'lock','coral']],
 vouchers:[['Generated codes',rows.length,'ticket','purple'],['Available',rows.filter(x=>x.enabled&&x.used_count<x.max_uses&&(!x.expires_at||x.expires_at>new Date().toISOString())).length,'shield','green'],['Redeemed uses',rows.reduce((n,x)=>n+Number(x.used_count||0),0),'activity','blue']],
 devices:[['Inventory size',rows.length,'devices','blue'],['Blocked in CRM',rows.filter(x=>x.blocked).length,'shield','coral'],['With IP recorded',rows.filter(x=>x.ip).length,'globe','green']],
 policies:[['Total rules',rows.length,'shield','blue'],['Active',rows.filter(x=>x.enabled).length,'activity','green'],['Block rules',rows.filter(x=>x.action==='block').length,'lock','coral']],
 sessions:[['All sessions',rows.length,'clock','blue'],['Authorized now',rows.filter(x=>x.state==='authorized'&&x.expires_at>new Date().toISOString()).length,'shield','green'],['Reported traffic',humanBytes(rows.reduce((n,x)=>n+Number(x.rx_bytes||0)+Number(x.tx_bytes||0),0)),'activity','purple']],
 activity:[['Activity events',rows.length,'activity','blue'],['Security blocks',rows.filter(x=>x.category==='blocked').length,'shield','coral'],['Event categories',new Set(rows.map(x=>x.category)).size,'layers','purple']]
 }[page];
 if(!summary)return;
 const el=document.createElement('div');el.className='record-summary';el.innerHTML=summary.map(([title,count,icon,color])=>`<div class="record-summary-card"><span class="record-summary-icon ${color}">${ic(icon,19)}</span><div><small>${escapeHTML(title)}</small><strong>${escapeHTML(String(count))}</strong></div></div>`).join('');
 const table=content.querySelector('.panel');if(table)content.insertBefore(el,table);
 const note=content.querySelector('.notebox.warning');if(note){note.insertAdjacentHTML('beforeend',`<div class="notice-detail">${ic('shield',15)} Gateway enforcement: not confirmed by this page.</div>`)}
}
let appCategory='All',appSearch='';
function renderApplications(policies, settings) {
 const presets=settings.app_presets||[];
 const appRules=policies.filter(x=>x.kind==='app');const domainRules=policies.filter(x=>x.kind==='domain');
 const covered=presets.filter(app=>appRules.some(p=>p.target===app&&p.action==='block'&&p.enabled&&p.scope_type==='all'));
 const totalActive=policies.filter(x=>x.enabled&&(x.kind==='app'||x.kind==='domain')).length;
 const categories=['All',...new Set(presets.map(x=>(APP_META[x]||['Other'])[0]))];
 document.getElementById('content').innerHTML=`${section('App & website control','Create app and domain rules from one place. Changes require a compatible gateway to affect Wi-Fi devices.',`${btn(ic('plus',16)+' Add website rule','add-domain-policy')}${btn(ic('plus',16)+' Advanced rule','add-policy','primary')}`,'ACCESS CONTROL')}
 <div class="page-alert warning"><span class="alert-icon">${ic('shield',20)}</span><div><b>Rules are configured, not automatically enforced.</b><p>App presets match known services/domains. A compatible gateway or DNS/firewall controller must apply these policies. Encrypted or alternative DNS traffic may bypass basic filtering.</p></div><button class="btn small" data-page="network">Router configuration ${ic('arrow',13)}</button></div>
 <div class="app-top-cards"><div class="feature-card indigo"><span class="feature-card-label">ACTIVE APP / WEB RULES</span><div class="feature-value">${numberFmt(totalActive)}</div><p>Enabled policies in the management database</p><span class="feature-graphic">${ic('shield',73)}</span></div>
 <div class="feature-card white"><span class="feature-card-label">BLOCKED APP PRESETS</span><div class="feature-value">${numberFmt(covered.length)}<span class="feature-suffix"> / ${presets.length}</span></div><p>Enabled global block policies</p><div class="tiny-progress"><i data-pct="${presets.length?Math.round(covered.length/presets.length*100):0}"></i></div></div>
 <div class="feature-card white"><span class="feature-card-label">WEBSITE RULES</span><div class="feature-value">${numberFmt(domainRules.length)}</div><p>Domain allow / block entries</p><button class="button-link" data-action="add-domain-policy">Manage domains ${ic('arrow',15)}</button></div></div>
 <div class="panel app-library"><div class="panel-head"><div><span class="panel-eyebrow">APPLICATION LIBRARY</span><h3>Popular apps & services</h3><p>One-click global block policy management</p></div><span class="pill-count">${presets.length} presets</span></div>
 <div class="app-toolbar"><div class="app-category" role="group" aria-label="App categories">${categories.map(x=>`<button type="button" data-app-category="${escapeHTML(x)}" class="chip ${x===appCategory?'selected':''}">${escapeHTML(x)}</button>`).join('')}</div><label class="table-search app-search">${ic('search',16)}<input id="app-filter" placeholder="Find an app..." aria-label="Find an app" value="${escapeHTML(appSearch)}"></label></div>
 <div id="app-cards" class="app-cards"></div></div>
 <div class="panel domain-panel"><div class="panel-head"><div><span class="panel-eyebrow">WEBSITE RULES</span><h3>Domain controls</h3><p>Custom website entries across your workspace</p></div>${btn(ic('plus',16)+' Add domain','add-domain-policy')}</div>
 ${domainRules.length?`<div class="table-wrap"><table class="data-table"><thead><tr><th>Website / domain</th><th>Action</th><th>Applied to</th><th>Status</th><th>Manage</th></tr></thead><tbody>${domainRules.map(x=>`<tr><td><span class="domain-favicon">${ic('globe',18)}</span><span class="cell-main">${escapeHTML(x.target)}</span><div class="cell-sub">${escapeHTML(x.name)}</div></td><td>${status(x.action==='block'?'Blocked':'Allowed',x.action==='block'?'red':'')}</td><td>${escapeHTML(x.scope_type)}${x.scope_id?' #'+x.scope_id:''}</td><td>${x.enabled?status('Active'):status('Paused','gray')}</td><td><div class="row-actions">${btn(x.enabled?'Pause':'Resume','toggle-policy:'+x.id,'small')}${btn('Delete','delete-policy:'+x.id,'small danger')}</div></td></tr>`).join('')}</tbody></table></div>`:empty('No domain policies yet. Add a website to manage it.')}</div>`;
 drawAppCards();applyVisualPercentages();
}
function drawAppCards(){
 const el=document.getElementById('app-cards');if(!el)return;
 const presets=cache.settings?.app_presets||[];const rules=cache.policies||[];
 const list=presets.filter(x=>(appCategory==='All'||(APP_META[x]||['Other'])[0]===appCategory)&&x.toLowerCase().includes(appSearch.toLowerCase()));
 el.innerHTML=list.length?list.map(name=>{
 const meta=APP_META[name]||['Other',name.slice(0,2).toUpperCase(),'#eaf0f6','#59728e'];
 const globalRules=rules.filter(p=>p.kind==='app'&&p.target===name&&p.action==='block'&&p.scope_type==='all');
 const active=globalRules.find(p=>p.enabled), hasRule=globalRules.length>0;
 const anyScoped=rules.some(p=>p.kind==='app'&&p.target===name&&p.scope_type!=='all'&&p.enabled);
 return `<article class="app-tile"><div class="app-tile-top"><span class="app-monogram app-theme-${escapeHTML(name)}"><img src="/static/icons/${escapeHTML(name)}.svg" width="28" height="28" alt="" loading="lazy"></span>${active?infoPill('Block rule active','red'):infoPill('No global block rule','neutral')}</div><div class="app-tile-body"><strong>${escapeHTML(prettifyName(name))}</strong><small>${escapeHTML(meta[0])}${anyScoped?' · Scoped rules exist':''}</small><details class="app-domains"><summary>View matching domains</summary><ul>${(cache.settings?.app_domains?.[name]||[]).map(d=>`<li>${escapeHTML(d)}</li>`).join('')}</ul></details></div><button type="button" class="app-toggle ${active?'active':''}" data-action="preset-toggle:${escapeHTML(name)}" aria-label="${active?'Disable':'Enable'} global block rule for ${escapeHTML(name)}"><span>${active?'Disable block':'Create block rule'}</span>${ic(active?'shield':'plus',15)}</button></article>`;
 }).join(''):`<div class="no-apps">${ic('search',24)}<strong>No matching services</strong><p>Try another name or category.</p></div>`;
 document.querySelectorAll('[data-app-category]').forEach(btn=>btn.classList.toggle('selected',btn.dataset.appCategory===appCategory));
}
async function togglePreset(name){
 const rules=(cache.policies||[]).filter(p=>p.kind==='app'&&p.target===name&&p.action==='block'&&p.scope_type==='all');
 const enabled=rules.find(p=>p.enabled);
 if(enabled) {for(const rule of rules.filter(p=>p.enabled)) await api('/policies/'+rule.id,{method:'PATCH',body:{enabled:false}});}
 else if(rules.length)await api('/policies/'+rules[0].id,{method:'PATCH',body:{enabled:true}});
 else await api('/policies',{method:'POST',body:{name:'Block '+prettifyName(name),kind:'app',target:name,action:'block',scope_type:'all',scope_id:null}});
 cache.policies=await api('/policies');renderApplications(cache.policies,cache.settings);
 toast(enabled?'Global app rule paused — gateway required':'Global app rule created — gateway required');
}
async function openQuickDomain(){
 const [users,devices]=await Promise.all([api('/users'),api('/devices')]);cache.users=users;cache.devices=devices;
 modal('Add a website policy',`<form id="domain-form"><div class="modal-hint">${ic('globe',20)} Add a domain-level rule. The CRM stores the decision; your gateway must enforce it.</div><div class="form-grid">${field('Website / domain','target','example.com')}${field('Rule action','action','','text',opts([['block','Block access'],['allow','Allow access']]))}${field('Rule name','name','Website control')}${field('Apply to','scope_type','','text',opts([['all','Everyone'],['user','A specific user'],['device','A specific device']]))}<div class="field span2" id="scope-picker"></div></div>${actions().replace('Save changes','Create rule')}</form>`);updateScopePicker();
}
function reportCard(label,value,caption,icon,type='blue') {return `<div class="report-stat"><span class="report-stat-icon ${type}">${ic(icon,19)}</span><span>${escapeHTML(label)}</span><b>${escapeHTML(String(value))}</b><small>${escapeHTML(caption)}</small></div>`}
function renderReports({dashboard:d,sessions,devices,users,vouchers,activity,policies}){
 const now=Date.now(),validSessions=sessions.filter(x=>x.state==='authorized'&&Date.parse(x.expires_at)>now);
 const blocked=activity.filter(x=>x.category==='blocked');const total=sessions.reduce((sum,s)=>sum+Number(s.rx_bytes||0)+Number(s.tx_bytes||0),0);
 const byState=new Map();sessions.forEach(s=>byState.set(s.state,(byState.get(s.state)||0)+1));
 const latest=activity.slice(0,6);
 document.getElementById('content').innerHTML=`${section('Analytics & reports','A transparent picture of the accounts, sessions and traffic reported to your CRM.',`${btn(ic('refresh',16)+' Refresh','refresh-report')}${btn(ic('export',16)+' Print report','print-report','primary')}`,'ANALYTICS')}
 <div class="report-ribbon"><span class="ribbon-live"><i></i> CRM data report</span><span>${ic('calendar',16)} Generated ${escapeHTML(new Date().toLocaleString())}</span><span class="ribbon-tail">These values are from saved records, not live router inspection.</span></div>
 <div class="report-stat-grid">${reportCard('Enabled accounts',users.filter(x=>x.enabled).length,'Guest credentials','users')}${reportCard('Active authorizations',validSessions.length,'Based on recorded expiry','clock','green')}${reportCard('Available vouchers',vouchers.filter(x=>x.enabled&&x.used_count<x.max_uses).length,'Voucher database','ticket','purple')}${reportCard('Security log events',blocked.length,'Records currently retained','shield','coral')}</div>
 <div class="report-duo"><section class="panel"><div class="panel-head"><div><span class="panel-eyebrow">NETWORK ANALYTICS</span><h3>Reported data transfer</h3><p>Last 7 calendar days · received gateway usage records</p></div>${infoPill('Gateway data only','blue')}</div><div class="panel-body"><div class="report-total-row"><div><small>Reported total</small><strong>${humanBytes(d.total_bytes)}</strong></div><span>${ic('activity',19)} Seven-day history</span></div>${chart(d.traffic_chart)}</div></section>
 <section class="panel"><div class="panel-head"><div><span class="panel-eyebrow">ACCESS OVERVIEW</span><h3>Session breakdown</h3><p>Stored authorizations and expiry states</p></div></div><div class="panel-body"><div class="session-visual">${progressRing(validSessions.length,sessions.length,'active',`${sessions.length} total sessions`)}</div><div class="report-legend"><div><i class="legend-mark green"></i> Currently authorized <strong>${validSessions.length}</strong></div><div><i class="legend-mark gray"></i> Other / expired <strong>${sessions.length-validSessions.length}</strong></div></div><div class="report-footnote">Authorization in the CRM is not proof that a Wi-Fi gateway has disconnected or admitted a device.</div></div></section></div>
 <div class="report-duo lower"><section class="panel"><div class="panel-head"><div><span class="panel-eyebrow">DEVICE INVENTORY</span><h3>Managed device access</h3><p>Known hardware and its configured access decision</p></div><button class="button-link" data-page="devices">View devices ${ic('arrow',15)}</button></div><div class="panel-body"><div class="device-distribution"><div class="distribution-item"><span class="dist-square green">${ic('shield',20)}</span><div><strong>${devices.filter(x=>!x.blocked).length}</strong><small>Allowed in CRM</small></div></div><div class="distribution-item"><span class="dist-square coral">${ic('lock',20)}</span><div><strong>${devices.filter(x=>x.blocked).length}</strong><small>Blocked in CRM</small></div></div></div><div class="distribution-track"><i data-pct="${devices.length?Math.round(100*devices.filter(x=>!x.blocked).length/devices.length):0}"></i></div><p class="report-note">${devices.length} enrolled devices. These are policy records, not verified online counts.</p></div></section>
 <section class="panel"><div class="panel-head"><div><span class="panel-eyebrow">POLICY SUMMARY</span><h3>Access rules</h3><p>Configured restrictions for websites, apps, IPs and devices</p></div><button class="button-link" data-page="policies">All policies ${ic('arrow',15)}</button></div><div class="panel-body"><div class="policy-breakdown">${['domain','app','ip','device'].map((k,i)=>`<div><span class="policy-tag ${['blue','purple','coral','green'][i]}">${ic(k==='domain'?'globe':k==='app'?'layers':k==='ip'?'activity':'devices',16)}</span><span>${escapeHTML(prettifyName(k))} rules</span><b>${policies.filter(p=>p.kind===k&&p.enabled).length}</b></div>`).join('')}</div></div></section></div>
 <section class="panel report-activity"><div class="panel-head"><div><span class="panel-eyebrow">LATEST CHANGES</span><h3>Recent audit trail</h3><p>Recorded administrative and access events</p></div><button class="button-link" data-page="activity">Full log ${ic('arrow',15)}</button></div><div class="panel-body">${latest.length?latest.map(eventRow).join(''):empty('No recorded events yet.')}</div></section>
 <div class="page-alert neutral">${ic('database',19)}<div><b>Export raw records</b><p>Download the original data rather than relying on visuals. Reports may be incomplete until a gateway reports usage and connections.</p></div><div class="export-cluster">${dl('sessions')}${dl('devices')}${dl('activity')}</div></div>`;
 applyVisualPercentages();
}
// Event delegation for new controls; does not change the backend or existing behavior.
document.addEventListener('click',event=>{
 const cat=event.target.closest('[data-app-category]');
 if(cat){appCategory=cat.dataset.appCategory;drawAppCards()}
});
document.addEventListener('input',event=>{
 if(event.target.id==='app-filter'){
   appSearch=event.target.value;
   const pos=event.target.selectionStart;
   drawAppCards();
   const input=document.getElementById('app-filter');if(input){input.focus();input.setSelectionRange(pos,pos)}
 }
});
