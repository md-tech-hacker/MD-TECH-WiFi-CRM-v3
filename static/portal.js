/* Public guest portal. It verifies credentials; only an integrated gateway can grant Wi-Fi access. */
let mode='voucher';
const fields=document.getElementById('credential-fields');
const output=document.getElementById('guest-result');
const eHTML=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function tab(which){
 mode=which;
 document.getElementById('tab-voucher').setAttribute('aria-selected',String(mode==='voucher'));
 document.getElementById('tab-account').setAttribute('aria-selected',String(mode==='account'));
 document.getElementById('tab-voucher').classList.toggle('selected',mode==='voucher');
 document.getElementById('tab-account').classList.toggle('selected',mode==='account');
 fields.innerHTML=mode==='voucher'?'<label class="field-label" for="portal-code">Access code</label><input id="portal-code" name="code" placeholder="MD-XXXXXXXXXX" autocomplete="one-time-code" required>':'<label class="field-label" for="portal-username">Username</label><input id="portal-username" name="username" autocomplete="username" placeholder="Your username" required><label class="field-label" for="portal-password">Password</label><input id="portal-password" name="password" type="password" autocomplete="current-password" placeholder="Your password" required>';
 output.innerHTML='';
}
document.getElementById('tab-voucher').addEventListener('click',()=>tab('voucher'));
document.getElementById('tab-account').addEventListener('click',()=>tab('account'));

let returnUrl = '';
function initParams(){
 try{
  const params = new URLSearchParams(window.location.search);
  const mac = params.get('mac')||params.get('client_mac')||params.get('clientmac')||'';
  if(mac){
   const el=document.getElementById('device-mac');
   if(el)el.value=mac;
  }
  returnUrl = params.get('authdir')||params.get('link-login-only')||params.get('target')||params.get('dst')||'';
 }catch(_){}
}

async function load(){
 try{
  let r=await fetch('/api/portal/config');
  let c=await r.json();
  document.title=c.site_name+' — Guest Wi-Fi';
  document.getElementById('portal-title').textContent=c.portal_title;
  document.getElementById('portal-message').textContent=c.portal_message;
 }catch(_){}
}

document.getElementById('guest-form').addEventListener('submit',async event=>{
 event.preventDefault();
 const button=event.target.querySelector('button[type=submit]');
 button.disabled=true;
 output.innerHTML='';
 try{
  const form=Object.fromEntries(new FormData(event.target));
  const response=await fetch('/api/portal/login',{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({...form,method:mode})
  });
  let data=await response.json();
  if(!response.ok)throw new Error(data.detail||'Unable to sign in');
  output.innerHTML=`<div class="portal-success">
   <b>Credentials accepted</b><br>
   Session #${Number(data.session_id)} · Valid until ${eHTML(new Date(data.expires_at).toLocaleString())}<br><br>
   ${eHTML(data.message)}
   ${data.bind_token?`<div style="margin-top:12px;padding:8px;background:rgba(255,255,255,0.7);border-radius:6px;font-size:12px;"><span style="color:#666;">Bind Proof: </span><code style="word-break:break-all;">${eHTML(data.bind_token)}</code></div>`:''}
   ${returnUrl?`<div style="margin-top:12px;"><a class="btn primary full" href="${eHTML(returnUrl)}">Continue to browsing ↗</a></div>`:''}
  </div>`;
  event.target.reset();
 }catch(error){
  output.innerHTML=`<div class="portal-error">${eHTML(error.message)}</div>`;
 }finally{
  button.disabled=false;
 }
});

tab('voucher');
initParams();
load();
