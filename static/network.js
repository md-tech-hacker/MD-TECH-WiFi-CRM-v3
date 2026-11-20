/* Network inventory is supplied by an authenticated gateway, never fabricated. */
const NETWORK_PLATFORMS = {
 unconfigured: ['Choose a platform', '', 'Select the gateway that will enforce guest access.'],
 tplink_wr841n_v14: ['TP-Link TL-WR841N V14 (stock firmware)', 'https://www.tp-link.com/us/user-guides/tl-wr841n_v14/chapter-6-configure-the-router-in-access-point-mode', 'Your router has manual access controls, but its stock guide does not document an external captive-portal API. Keep MD_TECH on this router in Access Point mode behind a separate enforcement gateway. OpenWrt flags V14 as unsuitable for secure current use because of its memory limits.'],
 mikrotik: ['MikroTik RouterOS', 'https://help.mikrotik.com/docs/spaces/ROS/pages/56459266/HotSpot+-+Captive+portal', 'Use HotSpot on an isolated guest bridge/VLAN. A connector must translate CRM authorization into RouterOS admission and disconnect actions. HotSpot requires IPv4; prevent unauthenticated IPv6 bypass.'],
 openwrt: ['OpenWrt + openNDS', 'https://openwrt.org/docs/guide-user/services/captive-portal/opennds', 'Verify the exact hardware revision in the OpenWrt device database. Install openNDS on the guest interface and implement its FAS authentication handoff. Never flash firmware for a different revision.'],
 opnsense: ['OPNsense', 'https://docs.opnsense.org/manual/captiveportal.html', 'Place a dedicated guest interface/VLAN behind the captive portal. Use a connector for its portal API or an audited RADIUS service. The CRM is not a RADIUS server.'],
 omada: ['TP-Link Omada', 'https://support.omadanetworks.com/us/document/13080/', 'Use compatible EAP/gateway hardware adopted by an Omada controller. Configure External Portal Server and implement the API matching your controller version. Consumer TP-Link routers are not equivalent to Omada.'],
 other: ['Other / stock router', '', 'Verify external portal, authentication, accounting and disconnect APIs in the exact firmware manual. If unsupported, keep the router as an access point behind a compatible gateway.']
};
function renderNetwork(n){
 const p=n.profile||{},t=n.telemetry,live=n.status==='reporting';
 const state={disabled:'Gateway API disabled',not_reporting:'No heartbeat received',reporting:'Gateway is reporting',stale:'Telemetry is stale'}[n.status]||'Unknown';
 document.getElementById('content').innerHTML=section('Router & network','Plan your gateway connection and inspect authenticated router telemetry.',btn(ic('refresh',16)+' Refresh','refresh'),'NETWORK OPERATIONS')+
 `<div class="page-alert ${live?'neutral':'warning'}">${ic('wifi',22)}<div><b>${escapeHTML(state)}</b><p>${t?'Last heartbeat '+escapeHTML(dateTime(t.received_at))+' · '+n.age_seconds+' seconds ago.':'A gateway adapter must send a heartbeat every 30 seconds. Data becomes stale after 90 seconds.'} Telemetry reports do not prove that firewall enforcement works.</p></div></div>
 <div class="network-layout"><section class="panel"><div class="panel-head"><div><span class="panel-eyebrow">DEPLOYMENT PROFILE</span><h3>Your gateway configuration</h3><p>Planning fields saved in the CRM</p></div></div><div class="panel-body"><form id="network-form" class="form-grid">
 ${field('Gateway platform','platform','','text',opts(Object.entries(NETWORK_PLATFORMS).map(([k,v])=>[k,v[0]]),p.platform||'unconfigured'))}
 ${field('Router name','router_name',p.router_name||'')}${field('Management IP (optional)','management_ip',p.management_ip||'')}${field('Guest VLAN (optional)','guest_vlan',p.guest_vlan||'','number')}
 <div class="field span2"><label for="network-notes">Installation notes</label><textarea id="network-notes" name="notes" maxlength="1000" placeholder="Hardware revision, guest subnet, controller version…">${escapeHTML(p.notes||'')}</textarea></div>
 <p class="helper span2">These fields document your setup. The SSID label in Settings does not rename the router’s broadcast network. Do not save passwords or API keys in notes.</p><div class="span2"><button class="btn primary" type="submit">Save network profile</button></div></form></div></section>
 <section class="panel"><div class="panel-head"><div><span class="panel-eyebrow">GATEWAY TELEMETRY</span><h3>Reported router details</h3><p>${t?'Authenticated adapter report':'Waiting for your gateway connector'}</p></div>${status(live?'Fresh':t?'Stale':'No data',live?'':'gray')}</div><div class="panel-body">${t?`<dl class="network-facts">${[['Router',t.name],['Model',t.model],['Firmware',t.firmware],['Broadcast SSID',t.ssid],['LAN address',t.lan_ip],['WAN address',t.wan_ip],['Uptime',Math.floor(t.uptime_seconds/3600)+'h '+Math.floor(t.uptime_seconds%3600/60)+'m'],['Client count',String(t.connected_clients)]].map(([k,v])=>`<div><dt>${escapeHTML(k)}</dt><dd>${escapeHTML(v||'Not reported')}</dd></div>`).join('')}</dl><p class="helper">Adapter-declared capabilities</p><div class="capability-list">${t.capabilities.map(x=>infoPill(x.replaceAll('_',' '),'blue')).join('')||'None reported'}</div>`:empty('No router model, SSID or client count has been reported. Connect a trusted gateway adapter to populate these fields.')}<button class="btn" type="button" data-page="settings">Gateway key & settings ${ic('arrow',15)}</button></div></section></div>
 <section class="panel network-guide"><div class="panel-head"><div><span class="panel-eyebrow">PLATFORM GUIDE</span><h3>Configure the enforcement path</h3><p>Vendor documentation and practical setup requirements</p></div></div><div class="panel-body"><div id="platform-guide"></div><ol class="deployment-steps"><li><b>Separate guests from management.</b> Internet → gateway → guest VLAN / SSID MD_TECH. Keep the admin dashboard and router management on a trusted VLAN or VPN.</li><li><b>Enable the gateway captive portal.</b> Supply DHCP and controlled DNS. Allow guests to reach only the HTTPS portal and necessary pre-login services. Block unauthenticated IPv4 and IPv6 forwarding.</li><li><b>Connect the adapter.</b> Store the gateway key on the trusted adapter, verify the gateway-owned browser handoff, bind the station, apply admission and report traffic deltas.</li><li><b>Apply policies and revocations.</b> Poll state and recheck authorization. Set firewall/session timeouts to expiry; remove existing flows on revoke. API failure must deny new admissions.</li><li><b>Verify with a real phone.</b> Before login: internet denied. Valid login: admitted. Invalid login, quota, expiry and revoke: denied. Check guest isolation and router-management access.</li></ol><p class="helper">Domain presets need DNS/firewall enforcement. VPNs, encrypted DNS and shared CDNs require additional gateway controls; full application identification is platform dependent.</p></div></section>`;
 updatePlatformGuide();
}
function updatePlatformGuide(){
 const select=document.querySelector('#network-form [name="platform"]'),el=document.getElementById('platform-guide');if(!select||!el)return;
 const [name,url,description]=NETWORK_PLATFORMS[select.value]||NETWORK_PLATFORMS.unconfigured;
 el.innerHTML=`<div class="platform-guide"><span class="shortcut-icon blue">${ic('wifi',24)}</span><div><h3>${escapeHTML(name)}</h3><p>${escapeHTML(description)}</p>${url?`<a class="button-link" target="_blank" rel="noopener noreferrer" href="${url}">Official configuration documentation ↗</a>`:''}</div></div>`;
}
function updateScopePicker(){
 const form=document.querySelector('#policy-form')||document.querySelector('#domain-form'),slot=document.getElementById('scope-picker');if(!form||!slot)return;
 const scope=form.elements.scope_type.value;
 if(scope==='all'){slot.innerHTML='<p class="helper">Applies to everyone. Scoped exceptions can override global rules.</p>';return}
 const records=scope==='user'?(cache.users||[]):(cache.devices||[]);
 slot.innerHTML=field(scope==='user'?'Select guest account':'Select managed device','scope_id','','text',opts([['','Choose '+scope+'…'],...records.map(r=>[r.id,scope==='user'?r.username:(r.name||r.mac)+' · '+r.mac])]));
 slot.querySelector('select').required=true;
}
function updatePolicyTarget(){
 const form=document.querySelector('#policy-form');if(!form)return;
 const kind=form.elements.kind.value,old=form.elements.target,parent=old.parentElement;
 if(kind==='app')parent.innerHTML=field('Application','target','','text',opts((cache.settings?.app_presets||[]).map(x=>[x,prettifyName(x)])));
 else if(kind==='device')parent.innerHTML=field('Managed device','target','','text',opts([['','Choose a device…'],...(cache.devices||[]).map(d=>[d.mac,(d.name||d.mac)+' · '+d.mac])]));
 else parent.innerHTML=field(kind==='ip'?'IP address / CIDR network':'Website domain','target',kind==='ip'?'':'youtube.com');
 // Keep one field wrapper when swapping an input for an accessible native selector.
 parent.innerHTML=parent.firstElementChild.innerHTML;
 form.elements.target.required=true;
 form.elements.target.placeholder=kind==='ip'?'192.168.50.0/24':'example.com';
}
document.addEventListener('change',e=>{
 if(e.target.name==='platform')updatePlatformGuide();
 if(e.target.name==='scope_type')updateScopePicker();
 if(e.target.name==='kind')updatePolicyTarget();
});
