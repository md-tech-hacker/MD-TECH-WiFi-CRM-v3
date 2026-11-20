/* Shared real-record filters across account, device, policy and session screens. */
const recordViews={};
const RECORD_FILTERS={
 users:[['all','All accounts'],['enabled','Enabled'],['disabled','Disabled']],
 vouchers:[['all','All vouchers'],['available','Available now'],['unavailable','Unavailable']],
 devices:[['all','All devices'],['blocked','Blocked in CRM'],['unblocked','No device block'],['reported','Gateway reported'],['manual','Manually enrolled']],
 policies:[['all','All policies'],['enabled','Enabled'],['disabled','Paused'],['block','Block rules'],['allow','Allow rules']],
 sessions:[['all','All sessions'],['active','Active authorizations'],['verified','Gateway verified & active'],['pending','Awaiting verification'],['ended','Ended / expired']],
 activity:[['all','All categories'],['security','Security'],['blocked','Blocked requests'],['users','Guest accounts'],['sessions','Sessions'],['settings','Settings']]
};
function recordControls(page){
 const view=recordViews[page]||{filter:'all',sort:'saved'};
 return `<div class="record-filter">${field('Filter records','record_filter','','text',opts(RECORD_FILTERS[page]||[['all','All records']],view.filter))}</div><div class="record-filter">${field('Sort records','record_sort','','text',opts([['saved','Default order'],['name','Name / identity'],['newest','Newest first']],view.sort))}</div>`;
}
function selectRecords(page,items,query){
 const view=recordViews[page]||{filter:'all',sort:'saved'},f=view.filter,now=Date.now();
 const active=s=>s.state==='authorized'&&Date.parse(s.expires_at)>now;
 const available=v=>v.enabled&&v.used_count<v.max_uses&&(!v.expires_at||Date.parse(v.expires_at)>now);
 const records=items.filter(x=>{
  if(!Object.values(x).some(v=>String(v??'').toLowerCase().includes(query)))return false;
  if(f==='all')return true;
  if(page==='users'||page==='policies'&&['enabled','disabled'].includes(f))return f==='enabled'?!!x.enabled:!x.enabled;
  if(page==='policies')return x.action===f;
  if(page==='vouchers')return f==='available'?available(x):!available(x);
  if(page==='devices')return f==='blocked'?!!x.blocked:f==='unblocked'?!x.blocked:f==='manual'?x.source==='manual':x.source==='gateway';
  if(page==='sessions')return f==='active'?active(x):f==='verified'?active(x)&&!!x.gateway_verified:f==='pending'?active(x)&&!x.gateway_verified:!active(x);
  if(page==='activity')return x.category===f;
  return true;
 });
 if(view.sort==='name')records.sort((a,b)=>String(a.display_name||a.name||a.username||a.code_hint||a.action||a.id).localeCompare(String(b.display_name||b.name||b.username||b.code_hint||b.action||b.id)));
 if(view.sort==='newest')records.sort((a,b)=>Number(b.id||0)-Number(a.id||0));
 return records;
}
document.addEventListener('change',e=>{
 if(!['record_filter','record_sort'].includes(e.target.name))return;
 const view=recordViews[current]||{filter:'all',sort:'saved'};
 view[e.target.name==='record_filter'?'filter':'sort']=e.target.value;recordViews[current]=view;
 renderList(current);enhanceRecords(current,cache[current]||[]);
});
async function openPolicyCheck(){
 const [devices,settings,users]=await Promise.all([api('/devices'),api('/settings'),api('/users')]);
 modal('Check an access decision',`<form id="policy-check-form"><p class="helper">Evaluate the current rules and session state without changing any device’s access.</p><div class="form-grid">
 ${field('Device','mac','','text',opts([['','No device selected'],...devices.map(d=>[d.mac,(d.name||d.mac)+' · '+d.mac])]))}
 ${field('Destination domain','domain','youtube.com')}
 ${field('Application (optional)','app','','text',opts([['','Use domain matching'],...settings.app_presets.map(x=>[x,prettifyName(x)])]))}
 ${field('Evaluation mode','require_active_session','','text',opts([['true','Require verified active session'],['false','Policies only (no admission)']]))}
 ${field('User for policy-only preview','user_id','','text',opts([['','No user selected'],...users.map(u=>[u.id,u.username])]))}
 </div><div id="policy-check-result" role="status"></div>${actions().replace('Save changes','Evaluate decision')}</form>`);
}
