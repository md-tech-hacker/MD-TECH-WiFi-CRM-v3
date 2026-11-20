/* Shared searchable selection control. The underlying select only carries form data. */
(() => {
 let sequence=0, opened=null;
 const controls=new WeakMap();
 function close(restore=false){
  if(!opened)return;
  const {button,popup}=opened;
  button.setAttribute('aria-expanded','false');button.removeAttribute('aria-activedescendant');
  popup.remove();opened=null;
  if(restore){if(button.isConnected)button.focus();else setTimeout(()=>document.getElementById(button.id)?.focus(),0)}
 }
 function position(){
  if(!opened)return;
  const {button,popup}=opened;if(!button.isConnected){close();return}
  const r=button.getBoundingClientRect(),below=innerHeight-r.bottom-12,above=r.top-12;
  const height=Math.min(326,Math.max(below,above)),up=below<230&&above>below;
  popup.style.width=Math.min(Math.max(r.width,220),innerWidth-24)+'px';
  popup.style.left=Math.max(12,Math.min(r.left,innerWidth-popup.offsetWidth-12))+'px';
  popup.style.maxHeight=height+'px';
  popup.style.top=(up?Math.max(12,r.top-Math.min(popup.scrollHeight,height)-6):r.bottom+6)+'px';
 }
 function activate(index){
  if(!opened)return;
  const items=opened.items;if(!items.length)return;
  opened.index=(index+items.length)%items.length;
  items.forEach((el,i)=>el.classList.toggle('highlighted',i===opened.index));
  const el=items[opened.index];
  opened.button.setAttribute('aria-activedescendant',el.id);
  opened.search.setAttribute('aria-activedescendant',el.id);
  el.scrollIntoView({block:'nearest'});
 }
 function choose(index){
  if(!opened||!opened.items[index])return;
  const {select}=opened,value=opened.items[index].dataset.value;
  select.value=value;select.dispatchEvent(new Event('change',{bubbles:true}));close(true);
 }
 function draw(){
  if(!opened)return;
  const {select,list,search}=opened,query=search.value.trim().toLocaleLowerCase();
  list.replaceChildren();opened.items=[];
  for(const option of select.options){
   if(option.hidden||option.disabled||option.parentElement.disabled||!option.textContent.toLocaleLowerCase().includes(query))continue;
   const item=document.createElement('div');item.className='choice-option';item.role='option';
   item.id='choice-option-'+(++sequence);item.dataset.value=option.value;
   item.setAttribute('aria-selected',String(option.selected));
   const text=document.createElement('span');text.textContent=option.textContent;
   const check=document.createElement('span');check.className='choice-check';check.textContent=option.selected?'✓':'';
   item.append(text,check);list.append(item);opened.items.push(item);
  }
  if(!opened.items.length){const empty=document.createElement('p');empty.className='choice-empty';empty.textContent='No matching options';list.append(empty)}
  opened.index=Math.max(0,opened.items.findIndex(x=>x.dataset.value===select.value));
  position();activate(opened.index);
 }
 function open(control,query=''){
  if(control.select.disabled)return;
  close();const popup=document.createElement('div');popup.className='choice-popup';
  const search=document.createElement('input');search.type='search';search.className='choice-search';
  search.placeholder='Search options…';search.setAttribute('aria-label','Search '+control.label);search.autocomplete='off';
  const list=document.createElement('div');list.className='choice-options';list.role='listbox';list.id=control.listId;
  list.setAttribute('aria-label',control.label);search.setAttribute('aria-controls',list.id);
  popup.append(search,list);(control.select.closest('[role="dialog"]')||document.body).append(popup);
  opened={...control,popup,search,list,items:[],index:0};control.button.setAttribute('aria-expanded','true');
  search.value=query;search.addEventListener('input',draw);
  list.addEventListener('pointerdown',e=>e.preventDefault());
  list.addEventListener('click',e=>{const item=e.target.closest('.choice-option');if(item)choose(opened.items.indexOf(item))});
  draw();search.focus();
 }
 function enhance(select){
  if(controls.has(select)||select.multiple)return;
  const active=document.activeElement===select,wrapper=document.createElement('div');wrapper.className='choice-control';
  const button=document.createElement('button');button.type='button';button.className='choice-trigger';button.setAttribute('role','combobox');
  const text=document.createElement('span');text.className='choice-value';
  const arrow=document.createElement('span');arrow.className='choice-arrow';arrow.setAttribute('aria-hidden','true');arrow.textContent='';
  const id=select.id||'choice-'+(++sequence),listId=id+'-options';
  const label=select.closest('.field')?.querySelector('label');
  button.id=id;select.id=id+'-native';
  if(label){label.htmlFor=id;label.id=label.id||id+'-label';button.setAttribute('aria-labelledby',label.id)}
  else button.setAttribute('aria-label',select.getAttribute('aria-label')||select.name||'Select option');
  button.setAttribute('aria-haspopup','listbox');button.setAttribute('aria-expanded','false');button.setAttribute('aria-controls',listId);
  select.before(wrapper);wrapper.append(select,button);button.append(text,arrow);
  select.classList.add('choice-native');select.tabIndex=-1;select.setAttribute('aria-hidden','true');
  const control={select,button,text,listId,label:label?.textContent||select.getAttribute('aria-label')||select.name||'options'};
  const sync=()=>{text.textContent=select.selectedOptions[0]?.textContent||'Choose an option';button.disabled=select.disabled;button.setAttribute('aria-required',String(select.required));button.classList.remove('choice-invalid')};
  controls.set(select,control);sync();select.addEventListener('change',sync);
  select.addEventListener('invalid',e=>{e.preventDefault();button.classList.add('choice-invalid');open(control)});
  button.addEventListener('click',()=>opened?.button===button?close(true):open(control));
  button.addEventListener('keydown',e=>{
   if(['ArrowDown','ArrowUp','Enter',' '].includes(e.key)){e.preventDefault();open(control)}
   else if(e.key.length===1&&!e.ctrlKey&&!e.metaKey&&!e.altKey){e.preventDefault();open(control,e.key)}
  });
  if(active)button.focus();
 }
 function scan(){
  document.querySelectorAll('select').forEach(enhance);
  document.querySelectorAll('input[type="password"]:not([data-password-control])').forEach(input=>{
   input.dataset.passwordControl='true';const wrapper=document.createElement('div');wrapper.className='password-control';
   input.before(wrapper);wrapper.append(input);
   const toggle=document.createElement('button');toggle.type='button';toggle.className='password-toggle';toggle.textContent='Show';
   toggle.setAttribute('aria-label','Show password');toggle.setAttribute('aria-pressed','false');
   toggle.addEventListener('click',()=>{const show=input.type==='password';input.type=show?'text':'password';toggle.textContent=show?'Hide':'Show';toggle.setAttribute('aria-label',show?'Hide password':'Show password');toggle.setAttribute('aria-pressed',String(show))});
   wrapper.append(toggle);
   const note=document.createElement('span');note.className='caps-lock-note';note.textContent='Caps Lock is on';note.hidden=true;wrapper.append(note);
   input.addEventListener('keyup',e=>{note.hidden=typeof e.getModifierState!=='function'||!e.getModifierState('CapsLock')});input.addEventListener('blur',()=>note.hidden=true);
  });
  if(opened&&!opened.select.isConnected)close();
 }
 document.addEventListener('keydown',e=>{
  if(!opened)return;
  if(['ArrowDown','ArrowUp','Home','End','Enter','Escape'].includes(e.key)){
   e.preventDefault();e.stopImmediatePropagation();
   if(e.key==='Escape')close(true);else if(e.key==='Enter')choose(opened.index);
   else if(e.key==='Home')activate(0);else if(e.key==='End')activate(opened.items.length-1);
   else activate(opened.index+(e.key==='ArrowDown'?1:-1));
  }else if(e.key==='Tab')close();
 },true);
 document.addEventListener('pointerdown',e=>{if(opened&&!opened.popup.contains(e.target)&&!opened.button.contains(e.target))close()});
 document.addEventListener('reset',e=>setTimeout(()=>e.target.querySelectorAll('select').forEach(s=>s.dispatchEvent(new Event('change',{bubbles:true}))),0));
 window.addEventListener('resize',position);
 document.addEventListener('scroll',e=>{if(opened&&!opened.popup.contains(e.target))position()},true);
 const observer=new MutationObserver(scan);observer.observe(document.body,{childList:true,subtree:true});scan();
})();
