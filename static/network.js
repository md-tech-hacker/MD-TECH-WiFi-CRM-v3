/* Network inventory is supplied by an authenticated gateway, never fabricated. */
const NETWORK_PLATFORMS = {
 unconfigured: ['Choose a platform', '', 'Select the gateway that will enforce guest access.'],
 mikrotik: ['MikroTik RouterOS (HotSpot)', 'https://help.mikrotik.com/docs/spaces/ROS/pages/56459266/HotSpot+-+Captive+portal', 'Use HotSpot on an isolated guest bridge/VLAN. Connect with WinBox, WebFig or REST/API on 192.168.88.1. A connector translates CRM authorization into RouterOS user admission, bandwidth queues and disconnect actions.'],
 openwrt: ['OpenWrt + openNDS', 'https://openwrt.org/docs/guide-user/services/captive-portal/opennds', 'Verify device support in OpenWrt table of hardware. LuCI web interface default on 192.168.1.1. Install openNDS on the guest interface with FAS (Forward Authentication Service) handoff to this CRM.'],
 opnsense: ['OPNsense Gateway', 'https://docs.opnsense.org/manual/captiveportal.html', 'Place dedicated guest interface/VLAN behind OPNsense captive portal. Default web admin on 192.168.1.1. Use a connector for the Captive Portal REST API or RADIUS service.'],
 pfsense: ['pfSense Gateway', 'https://docs.netgate.com/pfsense/en/latest/captiveportal/index.html', 'Configure pfSense Captive Portal on the guest zone. Default webConfigurator on 192.168.1.1:443. Connect via API or FreeRADIUS authentication.'],
 unifi: ['Ubiquiti UniFi Gateway / APs', 'https://help.ui.com/hc/en-us/articles/115000166827-UniFi-Hotspot-Portal', 'Adopt UniFi APs and gateway in UniFi Network Controller. Configure External Guest Portal pointing to this CRM host with controller authorization API.'],
 omada: ['TP-Link Omada SDN', 'https://support.omadanetworks.com/us/document/13080/', 'Adopt Omada EAPs/gateway in an Omada Controller. Configure External Portal Server and implement the API matching your controller version (v5+).'],
 generic_linux: ['Linux / Raspberry Pi Gateway', '', 'Turn any Linux PC or Raspberry Pi into a captive portal gateway using nftables/iptables + dnsmasq with standard APs.'],
 tplink_wr841n_v14: ['TP-Link TL-WR841N V14 (stock firmware)', 'https://www.tp-link.com/us/user-guides/tl-wr841n_v14/chapter-6-configure-the-router-in-access-point-mode', 'This router supports several connection roles. Choose how you use it above to see the matching setup instructions. Automatic guest-login enforcement still needs a compatible access-control gateway.'],
 other: ['Other / Custom Gateway Router', '', 'Verify external portal, authentication, accounting and disconnect APIs in the exact firmware manual. If unsupported, keep the router as an access point behind a compatible gateway.']
};
const ROUTER_ROLES={
 unknown:{name:'Choose your router setup',connection:'Choose whether this is your main router, an access point, or an extender.',steps:['Select how you use this router.','Connect this computer to that router by Wi-Fi or Ethernet.','Open the router settings and follow the matching setup instructions.'],note:'The CRM cannot detect the router role from a Wi-Fi name alone.',chapter:'chapter-2-connect-to-the-internet'},
 router:{name:'Main router',connection:'Connect the internet cable or modem to this router, then connect your devices to it.',steps:['Connect your modem or provider’s Ethernet cable to the router’s internet port.','Set up the internet connection using the details supplied by your provider.','Choose the Wi-Fi name and password for your devices.'],note:'This role does not require another Wi-Fi network. Captive-portal enforcement still needs compatible gateway software or hardware.',chapter:'chapter-4-configure-the-router-in-wireless-router-mode'},
 ap:{name:'Wired access point',connection:'Use an Ethernet cable from an existing router to provide Wi-Fi here.',steps:['Connect this router to the existing network by Ethernet.','Choose access point mode in the router settings.','Set the Wi-Fi name and password, and confirm which device supplies network addresses.'],note:'For guest login enforcement, place it behind a compatible access-control gateway. Its management address may come from your existing router.',chapter:'chapter-6-configure-the-router-in-access-point-mode'},
 wisp:{name:'Connect through another Wi-Fi',connection:'Use an existing Wi-Fi network as this router’s internet connection.',steps:['Choose the wireless internet connection mode in the router settings.','Select the existing Wi-Fi network and enter its password directly in the router.','Set the Wi-Fi network your own devices will join.'],note:'This is different from extender mode. When adding a separate gateway, verify that it can identify each guest device.',chapter:'chapter-5-configure-the-router-in-wisp-mode'},
 extender:{name:'Wi-Fi extender',connection:'Connect to an existing Wi-Fi network to extend its coverage.',steps:['Choose extender mode in the router settings.','Select the existing Wi-Fi network and enter its password directly in the router.','Place the extender where it still receives a good signal, then check the extended Wi-Fi.'],note:'An extender expands coverage; it does not add captive-portal enforcement. Its management address may come from your existing router.',chapter:'chapter-7-configure-the-router-in-range-extender-mode'}
};
function roleInstructions(mode){
 const role=ROUTER_ROLES[mode]||ROUTER_ROLES.unknown;
 return `<div class="router-role-guide"><span class="panel-eyebrow">SELECTED SETUP</span><h3>${escapeHTML(role.name)}</h3><p>${escapeHTML(role.connection)}</p><ol>${role.steps.map(s=>`<li>${escapeHTML(s)}</li>`).join('')}</ol><p class="helper">${escapeHTML(role.note)}</p><a class="button-link" href="https://www.tp-link.com/us/user-guides/tl-wr841n_v14/${role.chapter}" target="_blank" rel="noopener noreferrer">Instructions for this setup ↗</a><p class="helper">Selecting a role updates this guide. Apply the actual mode in your router’s own settings.</p></div>`;
}
function updateRouterRole(){
 const form=document.getElementById('network-form');if(!form?.elements?.operating_mode)return;
 const mode=form.elements.operating_mode.value,role=ROUTER_ROLES[mode]||ROUTER_ROLES.unknown;
 const guide=document.getElementById('router-role-guide');if(guide)guide.innerHTML=roleInstructions(mode);
 const summary=document.getElementById('router-role-summary');if(summary)summary.textContent=role.connection;
 const title=document.getElementById('router-role-title');if(title)title.textContent=mode==='unknown'?'Set up your internet connection':role.name;
 const wifi=form.elements.upstream_ssid?.closest('.field');if(wifi)wifi.hidden=!['wisp','extender'].includes(mode);
 const docs=document.getElementById('router-role-docs');if(docs)docs.href='https://www.tp-link.com/us/user-guides/tl-wr841n_v14/'+role.chapter;
 const accessTitle=document.getElementById('router-access-title'),accessText=document.getElementById('router-access-description');if(accessTitle)accessTitle.textContent=['ap','extender'].includes(mode)?'Manage device access':'Review access controls';if(accessText)accessText.textContent=['ap','extender'].includes(mode)?'Review device filtering in this mode. Website restrictions need to be applied by the main gateway.':'Review the device and website controls available in your router settings.';
 updatePlatformGuide();
}
function renderNetwork(n){
 const p=n.profile||{},t=n.telemetry,live=n.status==='reporting';
 const state={disabled:'Gateway API disabled',not_reporting:'No heartbeat received',reporting:'Gateway is reporting',stale:'Telemetry is stale'}[n.status]||'Unknown';
 document.getElementById('content').innerHTML=section('Router & network','Connect to your router administration and distinguish live observations from saved details.',btn(ic('refresh',16)+' Refresh','refresh'),'NETWORK OPERATIONS')+
 `<section class="panel connection-start"><div class="panel-head"><div><span class="panel-eyebrow">START HERE</span><h3>1. Choose your connection</h3><p>Your router can provide the main internet connection, share a wired connection, connect through another Wi-Fi, or extend its coverage.</p></div></div><div class="panel-body"><div class="router-role-picker">${field('How do you use this router?','operating_mode','','text',opts(Object.entries(ROUTER_ROLES).map(([key,r])=>[key,r.name]),p.operating_mode||'unknown')).replace('<select ','<select form="network-form" ')}</div><div id="connection-check-results" role="status">Checking this computer’s network connection…</div><div class="windows-settings">${btn(ic('shield',16)+' Windows network access','network-permissions','primary')}<a class="btn" href="ms-settings:network-wifi">Windows Wi-Fi settings</a><a class="btn" href="ms-settings:network-ethernet">Ethernet settings</a><a class="btn" href="ms-settings:privacy-location">Wi-Fi location permissions</a></div><p class="helper">Windows may require location access to read SSID details. Grant it in Windows settings if prompted; this CRM cannot override an OS permission. These links open settings on the computer using this browser.</p></div></section>`+
 routerConfiguration(n)+
 `<div class="page-alert ${live?'neutral':'warning'}">${ic('wifi',22)}<div><b>${escapeHTML(state)}</b><p>${t?'Last heartbeat '+escapeHTML(dateTime(t.received_at))+' · '+n.age_seconds+' seconds ago.':'A gateway adapter must send a heartbeat every 30 seconds. Data becomes stale after 90 seconds.'} Telemetry reports do not prove that firewall enforcement works.</p></div></div>
 <div class="network-layout"><section class="panel" id="router-connection"><div class="panel-head"><div><span class="panel-eyebrow">ROUTER CONNECTION</span><h3>Router address & installation</h3><p>Save its real LAN address to open the router controls</p></div></div><div class="panel-body"><p class="helper">Select your gateway platform or router model below. Read the firmware version and operation mode from its admin Status page.</p>${btn('Fill platform defaults','known-router','small')}<form id="network-form" class="form-grid">
 ${field('Gateway platform','platform','','text',opts(Object.entries(NETWORK_PLATFORMS).map(([k,v])=>[k,v[0]]),p.platform||'unconfigured'))}
 ${field('Router / Gateway name','router_name',p.router_name||'')}${field('Management address preset','address_preset','','text',opts([['','Custom / saved address'],['192.168.88.1','192.168.88.1 · MikroTik default'],['192.168.1.1','192.168.1.1 · OpenWrt / pfSense / UniFi default'],['192.168.0.1','192.168.0.1 · TP-Link / Omada default'],['10.0.0.1','10.0.0.1 · Enterprise gateway default']],p.management_ip||'192.168.0.1'))}
 ${field('Management IP (verify before saving)','management_ip',p.management_ip||'192.168.0.1')}${field('Guest VLAN (optional)','guest_vlan',p.guest_vlan||'','number')}
 <p class="helper span2">${p.management_ip?'This is your saved address; use Test router connection to check it.':'192.168.0.1 is the manufacturer’s default suggestion, not an address detected from your router.'} <a href="https://www.tp-link.com/us/user-guides/tl-wr841n_v14/faq" target="_blank" rel="noopener noreferrer">Official V14 login defaults ↗</a></p>
 ${field('Main Wi-Fi name (optional)','upstream_ssid',p.upstream_ssid||'')}${field('Installed firmware (optional)','firmware_version',p.firmware_version||'')}
 <div class="field span2"><label for="network-notes">Installation notes</label><textarea id="network-notes" name="notes" maxlength="1000" placeholder="Hardware revision, guest subnet, controller version…">${escapeHTML(p.notes||'')}</textarea></div>
 <p class="helper span2">Save the connection address here. Apply Wi-Fi, DHCP and access changes in the router admin interface above. These recorded fields do not change the hardware. Do not save passwords or API keys in notes.</p><div class="span2"><button class="btn primary" type="submit">Save router connection</button></div></form></div></section>
 <section class="panel"><div class="panel-head"><div><span class="panel-eyebrow">GATEWAY TELEMETRY</span><h3>Reported router details</h3><p>${t?'Authenticated adapter report':'Waiting for your gateway connector'}</p></div>${status(live?'Fresh':t?'Stale':'No data',live?'':'gray')}</div><div class="panel-body">${t?`<dl class="network-facts">${[['Router',t.name],['Model',t.model],['Firmware',t.firmware],['Broadcast SSID',t.ssid],['LAN address',t.lan_ip],['WAN address',t.wan_ip],['Uptime',Math.floor(t.uptime_seconds/3600)+'h '+Math.floor(t.uptime_seconds%3600/60)+'m'],['Client count',String(t.connected_clients)]].map(([k,v])=>`<div><dt>${escapeHTML(k)}</dt><dd>${escapeHTML(v||'Not reported')}</dd></div>`).join('')}</dl><p class="helper">Adapter-declared capabilities</p><div class="capability-list">${t.capabilities.map(x=>infoPill(x.replaceAll('_',' '),'blue')).join('')||'None reported'}</div>`:empty('No router model, SSID or client count has been reported. Connect a trusted gateway adapter to populate these fields.')}<button class="btn" type="button" data-page="settings">Gateway key & settings ${ic('arrow',15)}</button></div></section></div>
 <section class="panel network-guide"><div class="panel-head"><div><span class="panel-eyebrow">PLATFORM GUIDE</span><h3>Configure the enforcement path</h3><p>Vendor documentation and practical setup requirements</p></div></div><div class="panel-body"><div id="platform-guide"></div><ol class="deployment-steps"><li><b>Separate guests from management.</b> Keep your guest Wi-Fi behind the access-control gateway. Keep the admin dashboard and router management on a trusted VLAN or VPN.</li><li><b>Enable the gateway captive portal.</b> Supply DHCP and controlled DNS. Allow guests to reach only the HTTPS portal and necessary pre-login services. Block unauthenticated IPv4 and IPv6 forwarding.</li><li><b>Connect the adapter.</b> Store the gateway key on the trusted adapter, verify the gateway-owned browser handoff, bind the station, apply admission and report traffic deltas.</li><li><b>Apply policies and revocations.</b> Poll state and recheck authorization. Set firewall/session timeouts to expiry; remove existing flows on revoke. API failure must deny new admissions.</li><li><b>Verify with a real phone.</b> Before login: internet denied. Valid login: admitted. Invalid login, quota, expiry and revoke: denied. Check guest isolation and router-management access.</li></ol><p class="helper">Domain presets need DNS/firewall enforcement. VPNs, encrypted DNS and shared CDNs require additional gateway controls; full application identification is platform dependent.</p></div></section>`;
 document.getElementById('content').insertAdjacentHTML('beforeend',`<section class="panel host-network-panel"><div class="panel-head"><div><span class="panel-eyebrow">READ-ONLY HOST DETECTION</span><h3>This computer’s actual connection</h3><p>Read from Windows on the machine running this CRM</p></div>${btn(ic('refresh',16)+' Detect again','inspect-host')}</div><div class="panel-body" id="host-network-results" role="status">Reading network interfaces…</div></section>`);
 updatePlatformGuide();updateRouterRole();
}
function routerConfiguration(n){
 const role=ROUTER_ROLES[n.profile?.operating_mode]||ROUTER_ROLES.unknown;
 const platKey=n.profile?.platform||'unconfigured';
 const plat=NETWORK_PLATFORMS[platKey]||NETWORK_PLATFORMS.unconfigured;
 const url=n.management_url,link=url?`<a class="btn primary" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">${ic('external',16)} Open router admin</a>`:btn('Enter router IP below','router-address','primary');
 const rows=[['Change Wi-Fi name & password','Set the network name and password your guests use to connect.'],[role.name,role.connection],['Manage network addresses','Set the router address and manage automatic addresses for connected devices.'],['See connected devices','Review the phones, computers and other devices connected to your router.'],['Manage device & website access','Choose which devices and websites can use your connection.'],['Secure router access','Change the router administrator password and control who can open its settings.'],['Update & back up your router','Check the installed firmware and save a backup of the router settings.']];
 const docUrl=plat[1]||('https://www.tp-link.com/us/user-guides/tl-wr841n_v14/'+role.chapter);
 const docLabel=platKey==='mikrotik'?'MikroTik HotSpot Documentation ↗':platKey==='openwrt'?'OpenWrt openNDS Guide ↗':platKey==='opnsense'?'OPNsense Portal Guide ↗':platKey==='pfsense'?'pfSense Captive Portal ↗':platKey==='unifi'?'UniFi Hotspot Guide ↗':platKey==='omada'?'Omada External Portal Guide ↗':'Detailed router instructions ↗';
 const loginBtn=platKey==='mikrotik'?'<a class="btn" href="http://192.168.88.1" target="_blank" rel="noopener noreferrer">MikroTik WebFig login ↗</a>':platKey==='openwrt'?'<a class="btn" href="http://192.168.1.1" target="_blank" rel="noopener noreferrer">OpenWrt LuCI login ↗</a>':'<a class="btn" href="http://tplinkwifi.net/" target="_blank" rel="noopener noreferrer">Default router login address ↗</a>';
 return `<section class="panel router-controls"><div class="panel-head"><div><span class="panel-eyebrow">CONFIGURE YOUR ROUTER</span><h3>2. Connect and configure your router / gateway</h3><p>${url?'Saved management address: '+escapeHTML(n.profile.management_ip):'No management address has been supplied. A router connection has not been established.'}</p></div><div class="router-connection-actions">${url?btn('Test router connection','test-router'):''}${link}</div></div><div class="panel-body"><div id="router-probe-result" role="status">${n.connection_check?renderRouterProbe(n.connection_check):''}</div><div class="windows-settings">${loginBtn}<a class="btn" id="router-role-docs" href="${escapeHTML(docUrl)}" target="_blank" rel="noopener noreferrer">${escapeHTML(docLabel)}</a></div><p class="helper">The default login hostname or IP works only when connected to the appropriate router network. No connection is assumed.</p><p class="router-boundary">Router and firewall access settings must be applied in the router’s own interface or via an integration connector. The CRM stores policies and authorizations, while your gateway enforces them.</p><div id="router-role-guide">${roleInstructions(n.profile?.operating_mode)}</div><div class="router-control-grid">${rows.map(([name,path],index)=>`<div class="router-control-item"><span>${ic('settings',17)}</span><div><strong ${index===1?'id="router-role-title"':index===4?'id="router-access-title"':''}>${escapeHTML(name)}</strong><p ${index===1?'id="router-role-summary"':index===4?'id="router-access-description"':''}>${escapeHTML(path)}</p></div>${url?`<a href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer" aria-label="Open router to configure ${escapeHTML(name)}">${ic('external',17)}</a>`:''}</div>`).join('')}</div><p class="helper">Available settings depend on your router firmware and connection type. Saving the address does not verify router identity. Sign in directly in the opened router tab; the CRM does not collect its password. Changing mode or LAN IP may temporarily disconnect you.</p></div></section>`;
}
function renderRouterProbe(result){return `<div class="decision-result ${result.reachable?'decision-allow':'decision-deny'}"><strong>${result.reachable?'Web service reachable (TCP check only)':'Router web service not reachable'}</strong><p>${escapeHTML(result.message)}</p><small>${escapeHTML(result.target)} · ${escapeHTML(dateTime(result.checked_at))}${result.reachable_ports?.length?' · Ports '+result.reachable_ports.join(', '):''}</small></div>`}
async function testRouterConnection(){
 const el=document.getElementById('router-probe-result');if(!el)return;el.textContent='Checking saved LAN address on ports 80 and 443…';
 try{const r=await api('/network/check',{method:'POST'});if(el.isConnected)el.innerHTML=renderRouterProbe(r)}catch(e){if(el.isConnected)el.textContent=e.message}
}
async function loadHostNetwork(force=false){
 const el=document.getElementById('host-network-results');if(!el)return;
 el.textContent='Reading actual Windows network settings…';
 try{const h=await api('/network/host'+(force?'?refresh=true':''));cache.hostNetwork=h;if(!el.isConnected)return h;
 if(h.wifi_ssid){const label=document.querySelector('.workspace-copy small');if(label&&label.textContent==='SSID: not reported')label.textContent='Host Wi-Fi: '+h.wifi_ssid}
 const first=document.getElementById('connection-check-results'),wifiState={connected:'Wi-Fi connected',service_stopped:'Windows Wi-Fi service is stopped',permission_required:'Windows permission required',not_connected:'No active Wi-Fi connection',unavailable:'Connection inspection unavailable'}[h.wifi_status]||'Wi-Fi status unavailable';
 if(first)first.innerHTML=`<div class="host-ssid"><span>${ic(h.wifi_ssid?'wifi':'devices',20)}</span><div><small>${escapeHTML(wifiState)}</small><strong>${escapeHTML(h.wifi_ssid||((h.interfaces||[]).length?'Ethernet / other IP connection detected':'No connection detected'))}</strong></div>${infoPill('Read from Windows','blue')}</div><p class="helper">${escapeHTML(h.message)}</p>`;
 el.innerHTML=`<div class="host-ssid"><span>${ic('wifi',20)}</span><div><small>Windows Wi-Fi connection</small><strong>${escapeHTML(h.wifi_ssid||'No active Wi-Fi SSID detected')}</strong></div>${infoPill('Host observation','blue')}</div><p class="helper">${escapeHTML(h.message)}</p><p class="helper">WLAN service: ${escapeHTML(h.wlan_service||'Unknown')}</p>${(h.interfaces||[]).map(i=>`<dl class="network-facts">${[['Interface',i.name],['MAC address',i.mac],['Host addresses',i.addresses.join(', ')],['Subnet masks',(i.subnets||[]).join(', ')],['Default gateways (unverified)',i.gateways.join(', ')||'None'],['DNS servers',i.dns_servers.join(', ')||'Not reported'],['DHCP',i.dhcp_enabled?'Enabled':'Disabled'],['DHCP server',i.dhcp_server]].map(([label,value])=>`<div><dt>${escapeHTML(label)}</dt><dd>${escapeHTML(value||'Not reported')}</dd></div>`).join('')}</dl>`).join('')||'<p class="helper">No network interfaces could be read.</p>'}${Object.keys(h.wifi||{}).length?`<h4>Wi-Fi radio details</h4><dl class="network-facts">${Object.entries(h.wifi).map(([k,v])=>`<div><dt>${escapeHTML(k.replaceAll('_',' '))}</dt><dd>${escapeHTML(v)}</dd></div>`).join('')}</dl>`:''}<h4>Installed network adapters</h4>${(h.adapters||[]).map(a=>`<p class="helper"><b>${escapeHTML(a.name)}</b> · ${escapeHTML(a.connection||a.type||'Network adapter')} · ${a.enabled?'Enabled':'Disabled'}${a.speed_bps?' · '+Math.round(Number(a.speed_bps)/1000000)+' Mbps':''}</p>`).join('')||'<p class="helper">No physical adapter details available.</p>'}<p class="helper">Observed ${escapeHTML(dateTime(h.observed_at))}. A host gateway address is not automatically used as your router’s address.</p>`;
 return h;
 }catch(e){if(el.isConnected)el.textContent=e.message;const first=document.getElementById('connection-check-results');if(first)first.textContent=e.message;return null}
}
function openWindowsNetworkAccess(){
 modal('Windows network access',`<div class="permission-intro"><span class="confirmation-icon">${ic('wifi',26)}</span><div><span class="confirmation-eyebrow">WINDOWS PRIVACY & CONNECTION</span><h3>Read your real network details</h3><p>Windows controls access to Wi-Fi names and radio information. Ethernet details usually do not need location access.</p></div></div><ol class="permission-steps"><li>Connect this computer to your router using Wi-Fi or Ethernet.</li><li>Open Windows location settings. Allow location access for desktop apps if Windows requires it for Wi-Fi details.</li><li>Return here and recheck. If Wi-Fi hardware or its service is unavailable, a permission change alone will not create a connection.</li></ol><div class="windows-settings">${btn('Open Windows location settings','open-windows-settings:location','primary')}${btn('Open Wi-Fi settings','open-windows-settings:wifi')}</div><p class="helper">These actions open Windows settings on the CRM host and work only from a local administrator session. Windows remains responsible for granting access; the CRM does not bypass or enable permissions.</p><div id="windows-access-result" role="status"></div><div class="modal-actions">${btn('Close','close-modal')}${btn(ic('refresh',15)+' Recheck network access','recheck-network','primary')}</div>`);
}
async function openWindowsSettings(page){
 const result=await api('/network/windows-settings',{method:'POST',body:{page}});
 const el=document.getElementById('windows-access-result');if(el)el.innerHTML=`<div class="permission-result"><strong>Windows settings opened</strong><p>${escapeHTML(result.message)}</p></div>`;
 toast('Windows settings opened. Complete any permission choice in Windows.');
}
async function recheckWindowsNetworkAccess(){
 const result=document.getElementById('windows-access-result');if(result)result.textContent='Checking the current Windows connection…';
 let h;
 if(document.getElementById('host-network-results'))h=await loadHostNetwork(true);else h=await api('/network/host?refresh=true');
 if(!h){if(result)result.textContent='Network details could not be read. Check Windows settings and try again.';return}
 cache.hostNetwork=h;
 const title=h.wifi_status==='connected'?'Wi-Fi details are available':h.wifi_status==='permission_required'?'Windows permission is still required':h.wifi_status==='service_stopped'?'Wi-Fi service is stopped':h.interfaces?.length?'Ethernet / network details are available':'No active network was detected';
 if(result?.isConnected)result.innerHTML=`<div class="permission-result"><strong>${escapeHTML(title)}</strong><p>${escapeHTML(h.message)}</p>${h.wifi_ssid?`<p>Connected Wi-Fi: ${escapeHTML(h.wifi_ssid)}</p>`:''}</div>`;
}
function fillKnownRouter(){
 const f=document.getElementById('network-form');if(!f)return;
 const p=f.elements.platform?.value||'tplink_wr841n_v14';
 const defaults={
  mikrotik:{name:'MikroTik RouterOS Gateway',ip:'192.168.88.1'},
  openwrt:{name:'OpenWrt Gateway (openNDS)',ip:'192.168.1.1'},
  opnsense:{name:'OPNsense Firewall',ip:'192.168.1.1'},
  pfsense:{name:'pfSense Firewall',ip:'192.168.1.1'},
  unifi:{name:'UniFi Controller / Gateway',ip:'192.168.1.1'},
  omada:{name:'Omada Controller Gateway',ip:'192.168.0.1'},
  generic_linux:{name:'Linux nftables Gateway',ip:'192.168.50.1'},
  tplink_wr841n_v14:{name:'TP-Link TL-WR841N V14',ip:'192.168.0.1'},
  other:{name:'Wi-Fi Gateway Router',ip:'192.168.1.1'}
 };
 const choice=defaults[p]||defaults.tplink_wr841n_v14;
 if(!f.elements.platform.value||f.elements.platform.value==='unconfigured'){
  f.elements.platform.value='tplink_wr841n_v14';
  f.elements.platform.dispatchEvent(new Event('change',{bubbles:true}));
 }
 f.elements.router_name.value=choice.name;
 f.elements.management_ip.value=choice.ip;
 f.elements.management_ip.focus();
 toast('Platform defaults filled: '+choice.name+' ('+choice.ip+'). Enter your specific settings and save.');
}
function updatePlatformGuide(){
 const select=document.querySelector('#network-form [name="platform"]'),el=document.getElementById('platform-guide');if(!select||!el)return;
 let [name,url,description]=NETWORK_PLATFORMS[select.value]||NETWORK_PLATFORMS.unconfigured;
 if(select.value==='tplink_wr841n_v14'){const mode=document.getElementById('network-form')?.elements?.operating_mode?.value;url='https://www.tp-link.com/us/user-guides/tl-wr841n_v14/'+(ROUTER_ROLES[mode]||ROUTER_ROLES.unknown).chapter}
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
 const kind=form.elements.kind.value,old=form.elements.target,parent=old.closest('.field');
 if(kind==='app')parent.innerHTML=field('Application','target','','text',opts((cache.settings?.app_presets||[]).map(x=>[x,prettifyName(x)])));
 else if(kind==='device')parent.innerHTML=field('Managed device','target','','text',opts([['','Choose a device…'],...(cache.devices||[]).map(d=>[d.mac,(d.name||d.mac)+' · '+d.mac])]));
 else parent.innerHTML=field(kind==='ip'?'IP address / CIDR network':'Website domain','target',kind==='ip'?'':'youtube.com');
 // Keep one field wrapper when swapping an input for an accessible native selector.
 parent.innerHTML=parent.firstElementChild.innerHTML;
 form.elements.target.required=true;
 form.elements.target.placeholder=kind==='ip'?'192.168.50.0/24':'example.com';
}
document.addEventListener('change',e=>{
 if(e.target.name==='operating_mode')updateRouterRole();
 if(e.target.name==='address_preset'&&e.target.value){const f=document.getElementById('network-form');if(f)f.elements.management_ip.value=e.target.value}
 if(e.target.name==='platform')updatePlatformGuide();
 if(e.target.name==='scope_type')updateScopePicker();
 if(e.target.name==='kind')updatePolicyTarget();
});

document.addEventListener('input',e=>{if(e.target.name==='management_ip'){const f=document.getElementById('network-form');if(f&&f.elements?.address_preset){f.elements.address_preset.value='';f.elements.address_preset.dispatchEvent(new Event('change',{bubbles:true}))}}});
