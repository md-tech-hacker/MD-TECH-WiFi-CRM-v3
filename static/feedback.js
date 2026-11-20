/* Shared dialogs and dismissible notifications; no browser alert/confirm calls. */
(() => {
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const paths={check:'<path d="m5 12 4 4L19 6"/>',warning:'<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3h.01"/>',close:'<path d="m6 6 12 12M18 6 6 18"/>',shield:'<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6l8-4Z"/><path d="m8 12 3 3 5-6"/>'};
 const icon=(name,size=20)=>`<svg aria-hidden="true" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${paths[name]}</svg>`;
 let restoreFocus=null,pending=null;
 function close(result=false,restore=true){
  const root=document.getElementById('modal');if(!root)return;
  const resolve=pending;pending=null;root.classList.add('hidden');root.replaceChildren();
  document.getElementById('app').inert=false;document.body.classList.remove('dialog-open');
  const previous=restoreFocus;restoreFocus=null;
  if(restore&&previous?.isConnected)setTimeout(()=>{if(!previous.disabled)previous.focus();else document.getElementById('content')?.focus()},0);
  if(resolve)resolve(result);
 }
 function open(title,content,footer='',options={}){
  const previous=document.activeElement;close(false,false);restoreFocus=previous;
  const root=document.getElementById('modal');
  root.innerHTML=`<div class="modal-card ${options.confirm?'confirmation-card':''}" role="${options.confirm?'alertdialog':'dialog'}" aria-modal="true" aria-labelledby="dialog-title" ${options.confirm?'aria-describedby="confirmation-description"':''}><div class="modal-top"><h2 id="dialog-title">${escape(title)}</h2><button type="button" class="close-btn" data-action="close-modal" aria-label="Close dialog">${icon('close',18)}</button></div><div class="modal-content">${content}${footer}</div></div>`;
  root.classList.remove('hidden');document.getElementById('app').inert=true;document.body.classList.add('dialog-open');
  queueMicrotask(()=>{
   const focus=options.confirm?root.querySelector('[data-confirm-choice="cancel"]'):(root.querySelector('input:not(.choice-native),textarea,.choice-trigger,select:not(.choice-native)')||root.querySelector('button'));
   focus?.focus();
  });
 }
 function confirm({title='Continue?',message,accept='Continue',cancel='Cancel',tone='warning'}){
  return new Promise(resolve=>{
   open(title,`<div class="confirmation-intro"><span class="confirmation-icon ${tone==='danger'?'danger':'warning'}">${icon(tone==='danger'?'warning':'shield',26)}</span><div><span class="confirmation-eyebrow">${tone==='danger'?'REVIEW THIS CHANGE':'CONFIRM YOUR ACTION'}</span><p id="confirmation-description">${escape(message)}</p></div></div><div class="confirmation-actions"><button type="button" class="btn" data-confirm-choice="cancel">${escape(cancel)}</button><button type="button" class="btn ${tone==='danger'?'danger confirm-danger':'primary'}" data-confirm-choice="accept">${escape(accept)}</button></div>`,'',{confirm:true});
   pending=resolve;
  });
 }
 function notify(message,{error=false,title=error?'Action could not be completed':'Action completed',duration=error?9000:5500}={}){
  const root=document.getElementById('toast');root.setAttribute('role','region');root.setAttribute('aria-label','Notifications');root.setAttribute('aria-live','off');
  const card=document.createElement('div');card.className='feedback-toast'+(error?' error':'');card.setAttribute('role',error?'alert':'status');card.setAttribute('aria-atomic','true');
  card.innerHTML=`<span class="feedback-toast-icon">${icon(error?'warning':'check')}</span><div class="feedback-toast-copy"><strong>${escape(title)}</strong><p>${escape(message)}</p></div><button type="button" class="feedback-dismiss" aria-label="Dismiss notification">${icon('close',15)}</button><span class="feedback-progress" aria-hidden="true"></span>`;
  card.style.setProperty('--toast-duration',duration+'ms');
  let timer,remaining=duration,started=Date.now();
  const dismiss=()=>{clearTimeout(timer);card.remove()};
  const pause=()=>{if(card.classList.contains('paused'))return;clearTimeout(timer);remaining=Math.max(0,remaining-(Date.now()-started));card.classList.add('paused')};
  const resume=()=>{if(card.matches(':hover,:focus-within'))return;clearTimeout(timer);started=Date.now();card.classList.remove('paused');timer=setTimeout(dismiss,remaining)};
  card.querySelector('button').addEventListener('click',dismiss);
  card.addEventListener('pointerenter',pause);card.addEventListener('pointerleave',resume);
  card.addEventListener('focusin',pause);card.addEventListener('focusout',()=>setTimeout(resume,0));
  while(root.children.length>=3)root.firstElementChild.querySelector('button').click();
  root.append(card);timer=setTimeout(dismiss,duration);
 }
 document.addEventListener('click',e=>{const choice=e.target.closest('[data-confirm-choice]');if(choice)close(choice.dataset.confirmChoice==='accept')});
 document.addEventListener('keydown',e=>{
  const root=document.getElementById('modal');if(!root||root.classList.contains('hidden'))return;
  if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();close();return}
  if(e.key!=='Tab')return;
  const items=[...root.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href],[tabindex="0"]')].filter(el=>el.tabIndex>=0&&el.getClientRects().length&&!el.classList.contains('choice-native'));
  const first=items[0],last=items[items.length-1];
  if(!first){e.preventDefault();return}
  if(e.shiftKey&&(document.activeElement===first||!root.contains(document.activeElement))){e.preventDefault();last.focus()}
  else if(!e.shiftKey&&(document.activeElement===last||!root.contains(document.activeElement))){e.preventDefault();first.focus()}
 },true);
 window.MDFeedback={open,close,confirm,notify};
})();
