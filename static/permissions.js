const add=document.getElementById('add-rule');
if(add){
 add.hidden=false;
 add.addEventListener('click',()=>{
  const total=document.getElementById('id_form-TOTAL_FORMS');
  const html=document.getElementById('empty-rule').innerHTML.replaceAll('__prefix__',total.value);
  const target=document.getElementById('new-rules');
  target.insertAdjacentHTML('beforeend',html);total.value=String(Number(total.value)+1);
  target.lastElementChild.querySelector('select')?.focus();
 });
}
