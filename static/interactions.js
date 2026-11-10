(()=>{
 const dialog=document.getElementById('action-dialog');if(!dialog)return;
 let resolveDialog=null;
 function ask(title,description,action='Confirmar'){
  if(!dialog.showModal)return Promise.resolve(window.confirm(description));
  if(dialog.open)return Promise.resolve(false);
  document.getElementById('action-title').textContent=title;
  document.getElementById('action-description').textContent=description;
  document.getElementById('action-accept').textContent=action;
  return new Promise(resolve=>{resolveDialog=resolve;dialog.showModal();document.getElementById('action-cancel').focus();});
 }
 function finish(value){dialog.close();const callback=resolveDialog;resolveDialog=null;callback?.(value);}
 document.getElementById('action-cancel').onclick=()=>finish(false);
 document.getElementById('action-accept').onclick=()=>finish(true);
 dialog.addEventListener('cancel',event=>{event.preventDefault();finish(false);});
 const snapshots=new WeakMap(),approved=new WeakSet(),submitted=new WeakSet();
 const tracked=()=>Array.from(document.querySelectorAll('form[data-dirty]'));
 function snapshot(form){return JSON.stringify(Array.from(new FormData(form)).filter(([key])=>key!=='csrfmiddlewaretoken').map(([key,value])=>[key,value instanceof File?(value.name?[value.name,value.size,value.lastModified]:null):value]));}
 tracked().forEach(form=>snapshots.set(form,snapshot(form)));
 function dirty(form){return !submitted.has(form)&&snapshots.get(form)!==snapshot(form);}
 function unsaved(){return tracked().some(dirty);}
 window.addEventListener('beforeunload',event=>{if(unsaved()){event.preventDefault();event.returnValue='';}});
 document.addEventListener('click',async event=>{
  const link=event.target.closest('a[href]');if(!link||event.defaultPrevented||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||link.target==='_blank'||link.hasAttribute('download'))return;
  const target=new URL(link.href,location.href);if(target.origin!==location.origin||target.pathname===location.pathname&&target.search===location.search||!unsaved())return;
  event.preventDefault();
  if(await ask('Sair sem salvar?','Você fez alterações que ainda não foram salvas. Se sair agora, essas alterações serão perdidas.','Sair sem salvar')){tracked().forEach(form=>submitted.add(form));location.assign(link.href);}
 });
 document.addEventListener('submit',async event=>{
  const form=event.target;if(!(form instanceof HTMLFormElement))return;
  if(approved.has(form)){approved.delete(form);submitted.add(form);return;}
  let title=form.dataset.confirmTitle,description=form.dataset.confirmMessage,action=form.dataset.confirmAction||'Confirmar';
  if(form.dataset.confirmFile!==undefined&&form.querySelector('input[type=file]')?.files.length){title='Substituir o PDF?';description='O novo PDF passará a ser a versão atual. A versão anterior será preservada no histórico, com o mesmo endereço e as mesmas permissões.';action='Substituir PDF';}
  if(form.dataset.confirmDeactivate==='true'&&!form.querySelector('[name=is_active]')?.checked){title='Desativar este usuário?';description='Esta pessoa ficará impedida de entrar no sistema. Seus registros e o histórico serão preservados.';action='Desativar e salvar';}
  if(form.dataset.confirmPermissions!==undefined&&dirty(form)){
   title='Salvar alterações de acesso?';description='As novas regras podem conceder ou retirar acesso dos grupos. Regras marcadas para remoção serão excluídas somente ao confirmar.';action='Salvar permissões';
   const removals=Array.from(form.querySelectorAll('input[name$="-DELETE"]:checked')).map(input=>{const row=input.closest('fieldset');return row.querySelector('select[name$="-group"]').selectedOptions[0].text+' / '+row.querySelector('select[name$="-action"]').selectedOptions[0].text;});
   if(removals.length)description+=' Remover: '+removals.slice(0,8).join('; ')+(removals.length>8?' e mais '+(removals.length-8)+' regra(s).':'.');
  }
  if(description&&form.dataset.confirmSubject)description='“'+form.dataset.confirmSubject+'” — '+description;
  if(!description){submitted.add(form);return;}
  event.preventDefault();const submitter=event.submitter;
  if(await ask(title||'Confirmar ação',description,action)){approved.add(form);form.requestSubmit(submitter);}
 });
 document.querySelectorAll('[data-alert-dismiss]').forEach(button=>button.addEventListener('click',()=>button.closest('.app-alert').remove()));
 document.querySelector('form .errorlist')?.closest('form')?.querySelector('[aria-invalid=true]')?.focus();
})();
