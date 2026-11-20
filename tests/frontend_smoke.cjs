// Self-contained frontend rendering smoke tests; no browser or packages needed.
// Run: node tests/frontend_smoke.cjs
const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');const path=require('node:path');
const root=path.resolve(__dirname,'..','static');
const elements={};
const element=id=>elements[id]??(elements[id]={innerHTML:'',textContent:'',insertAdjacentHTML(position,html){this.innerHTML+=html},querySelector(sel){return {innerHTML:'',insertAdjacentHTML(){}}},insertBefore(child){this.innerHTML=child.innerHTML+this.innerHTML},classList:{contains:()=>false,toggle:()=>{},remove:()=>{},add:()=>{}},style:{setProperty:()=>{}},dataset:{}});
const document={
 querySelector(s){if(s.startsWith('#'))return element(s.slice(1));return element(s)},
 querySelectorAll(){return []},getElementById:element,addEventListener(){},createElement(){return {innerHTML:'',className:''}},
};
const context=vm.createContext({console,document,window:{addEventListener(){}},setTimeout,clearTimeout,Date,Intl,Number,String,Map,Set,Array,Object,Math,Error,Promise,location:{hash:''}});
vm.runInContext(fs.readFileSync(path.join(root,'studio.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'network.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'records.js'),'utf8'),context);
const main=fs.readFileSync(path.join(root,'main.js'),'utf8').replace(/showAuth\(\)\.catch\([\s\S]*$/,'');
vm.runInContext(main,context);
const policies=[{id:1,name:'Block TikTok',kind:'app',target:'tiktok',action:'block',enabled:1,scope_type:'all',scope_id:null}];
const settings={app_presets:['youtube','instagram','facebook','tiktok'],gateway_enabled:false};
const sample={counts:{sessions:1,devices:2,vouchers:5,blocked_devices:1,users:2,policies:1,blocks_today:0},traffic_chart:Array.from({length:7},(_,i)=>({date:`2026-10-${String(10+i).padStart(2,'0')}`,bytes:0})),recent_activity:[],recent_devices:[],total_bytes:0,gateway_enabled:false};
vm.runInContext('cache.settings='+JSON.stringify(settings)+';cache.policies='+JSON.stringify(policies)+';me="admin";',context);
vm.runInContext('renderApplications(cache.policies,cache.settings)',context);
assert.match(element('content').innerHTML,/Popular apps & services/);
assert.match(element('app-cards').innerHTML,/YouTube/);
assert.match(element('app-cards').innerHTML,/Block rule active/);
assert.match(element('content').innerHTML,/Rules are configured, not automatically enforced/);
assert.match(element('app-cards').innerHTML,/\/static\/icons\/youtube.svg/);
vm.runInContext('renderNetwork({profile:{platform:"tplink_wr841n_v14"},telemetry:null,status:"not_reporting",age_seconds:null})',context);
assert.match(element('content').innerHTML,/No heartbeat received/);
assert.match(element('content').innerHTML,/Reported router details/);
assert.match(element('content').innerHTML,/TP-Link TL-WR841N V14/);
assert.match(element('content').innerHTML,/manufacturer’s default suggestion/);
assert.match(element('content').innerHTML,/Windows Wi-Fi settings/);
assert.match(element('content').innerHTML,/Save router connection/);
vm.runInContext('renderNetwork({profile:{management_ip:"192.168.50.1"},management_url:"http://192.168.50.1/",telemetry:null,status:"not_reporting",age_seconds:null})',context);
assert.match(element('content').innerHTML,/Test router connection/);
const users=[{display_name:'Sarah N',username:'sarah',email:'',devices_count:0,enabled:1,created_at:'2026-10-17T13:00:00Z'}];
const vouchers=[{enabled:1,used_count:0,max_uses:1}];
const devices=[{id:1,name:'Laptop',mac:'aa:bb:cc:dd:ee:ff',ip:'192.168.1.111',source:'local',blocked:0,rx_bytes:0,tx_bytes:0}];
const activity=[];
const records={dashboard:sample,sessions:[],devices,users,vouchers,activity,policies};
vm.runInContext('renderReports('+JSON.stringify(records)+')',context);
assert.match(element('content').innerHTML,/Analytics &amp; reports/);
assert.match(element('content').innerHTML,/Reported data transfer/);
assert.match(element('content').innerHTML,/Enabled accounts/);
assert.match(element('content').innerHTML,/No traffic reported yet/);
vm.runInContext('renderDashboard('+JSON.stringify(sample)+')',context);
assert.match(element('content').innerHTML,/Manage your network/);
assert.match(element('content').innerHTML,/Gateway not connected/);
for(const k of ['users','vouchers','devices','policies','sessions','activity']){
 vm.runInContext('cache['+JSON.stringify(k)+']='+JSON.stringify(records[k])+';current='+JSON.stringify(k)+';searchText="";renderList(current);enhanceRecords(current,cache[current]);',context);
 assert.match(element('content').innerHTML, /record-summary/);
}
// Confirm a genuine policy write, rather than a UI-only toggle.
vm.runInContext(`api=async(url,options={})=>{
 if(url==='/policies'&&(!options.method||options.method==='GET'))return cache.policies;
 if(options.method==='POST') {cache.policies.push({id:2,...options.body,enabled:1});return {ok:true};}
 if(options.method==='PATCH'){const entry=cache.policies.find(x=>x.id===Number(url.split('/').at(-1)));entry.enabled=options.body.enabled?1:0;return {ok:true};}
 throw new Error('Unexpected mock endpoint '+url);
};toast=()=>{};`,context);
(async()=>{
 await vm.runInContext('togglePreset("youtube")',context);
 assert.equal(vm.runInContext('cache.policies.some(x=>x.kind==="app"&&x.target==="youtube"&&x.enabled)',context),true);
 await vm.runInContext('togglePreset("youtube")',context);
 assert.equal(vm.runInContext('cache.policies.some(x=>x.kind==="app"&&x.target==="youtube"&&x.enabled)',context),false);
 assert.ok(fs.readFileSync(path.join(root,'index.html'),'utf8').includes('/static/studio.js'));
 console.log('Frontend smoke tests passed: apps, app policy toggles, reports, dashboard, six records views, integration banner.');
})().catch(e=>{console.error(e);process.exitCode=1});
