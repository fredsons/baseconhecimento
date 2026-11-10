import * as pdfjs from './vendor/pdf.mjs';
pdfjs.GlobalWorkerOptions.workerSrc=new URL('./vendor/pdf.worker.mjs',import.meta.url).href;
const root=document.getElementById('pdf-viewer'),pages=document.getElementById('pdf-pages'),msg=document.getElementById('pdf-message');
const $=id=>document.getElementById(id),number=$('page-number');
let doc,scale=1,mode='fit',generation=0,current=1,observer,query='',searchPage=0,searchRun=0;
let slots=[],states=new Map(),textCache=new Map(),active=0,queue=[];
const controls=[...root.querySelectorAll('button,input')];controls.forEach(c=>c.disabled=true);
function message(text){msg.textContent=text;}
function markMatches(layer){
 for(const span of layer.querySelectorAll('span[role="presentation"]')){
  if(span.dataset.raw===undefined)span.dataset.raw=span.textContent;
  const raw=span.dataset.raw;span.replaceChildren();
  if(!query){span.textContent=raw;continue;}
  const lower=raw.toLocaleLowerCase('pt-BR');let at=0,index;
  while((index=lower.indexOf(query,at))!==-1){span.append(document.createTextNode(raw.slice(at,index)));const mark=document.createElement('mark');mark.textContent=raw.slice(index,index+query.length);span.append(mark);at=index+query.length;}
  span.append(document.createTextNode(raw.slice(at)));
 }
}
function release(slot){const state=states.get(slot);state?.task?.cancel();state?.layer?.cancel();const canvas=slot.querySelector('canvas');if(canvas){canvas.width=0;canvas.height=0;}slot.replaceChildren();states.delete(slot);}
function updateCurrent(){
 if(!slots.length)return;
 let lo=0,hi=slots.length-1,y=pages.scrollTop+24;
 while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(slots[mid].offsetTop<=y)lo=mid;else hi=mid-1;}
 current=pages.scrollTop+pages.clientHeight>=pages.scrollHeight-2?doc.numPages:lo+1;number.value=current;
 for(const slot of [...states.keys()])if(Math.abs(+slot.dataset.page-current)>3)release(slot);
}
function schedule(slot){
 if(states.has(slot)||queue.some(item=>item.slot===slot))return;
 queue.push({slot,gen:generation});pump();
}
function pump(){
 while(active<2&&queue.length){
  queue.sort((a,b)=>Math.abs(+a.slot.dataset.page-current)-Math.abs(+b.slot.dataset.page-current));
  const item=queue.shift();if(item.gen!==generation||Math.abs(+item.slot.dataset.page-current)>3)continue;
  active++;draw(item.slot,item.gen).catch(error=>{if(error.name!=='RenderingCancelledException'&&error.name!=='AbortException')message('Não foi possível exibir esta página. Tente ajustar o zoom.');}).finally(()=>{active--;pump();});
 }
}
async function draw(slot,gen){
 if(states.has(slot)||gen!==generation)return;
 const state={};states.set(slot,state);
 const page=await doc.getPage(+slot.dataset.page);
 if(gen!==generation||states.get(slot)!==state)return;
 const pageScale=mode==='fit'?Math.max(.2,(pages.clientWidth-40)/page.getViewport({scale:1}).width):scale;
 const viewport=page.getViewport({scale:pageScale});slot.style.width=viewport.width+'px';slot.style.height=viewport.height+'px';
 slot.style.setProperty('--scale-factor',pageScale);
 const canvas=document.createElement('canvas'),ratio=Math.min(devicePixelRatio||1,2);
 canvas.width=Math.floor(viewport.width*ratio);canvas.height=Math.floor(viewport.height*ratio);canvas.style.width=viewport.width+'px';canvas.style.height=viewport.height+'px';slot.append(canvas);
 state.task=page.render({canvasContext:canvas.getContext('2d'),viewport,transform:ratio===1?null:[ratio,0,0,ratio,0,0]});
 await state.task.promise;
 if(gen!==generation||states.get(slot)!==state)return;
 const text=await page.getTextContent();
 if(gen!==generation||states.get(slot)!==state)return;
 const container=document.createElement('div');container.className='textLayer';slot.append(container);
 state.layer=new pdfjs.TextLayer({textContentSource:text,container,viewport});await state.layer.render();markMatches(container);
}
async function layout(target=current){
 const gen=++generation;observer?.disconnect();queue=[];
 for(const slot of states.keys())release(slot);
 pages.replaceChildren();slots=[];
 const first=await doc.getPage(1);
 if(mode==='fit')scale=Math.max(.2,(pages.clientWidth-40)/first.getViewport({scale:1}).width);
 const viewport=first.getViewport({scale});
 if(gen!==generation)return;
 const fragment=document.createDocumentFragment();
 for(let i=1;i<=doc.numPages;i++){const slot=document.createElement('section');slot.dataset.page=i;slot.setAttribute('aria-label','Página '+i);slot.style.width=viewport.width+'px';slot.style.height=viewport.height+'px';fragment.append(slot);slots.push(slot);}
 pages.append(fragment);current=Math.min(doc.numPages,Math.max(1,target));
 observer=new IntersectionObserver(entries=>{for(const item of entries)if(item.isIntersecting)schedule(item.target);},{root:pages,rootMargin:'300px'});
 slots.forEach(slot=>observer.observe(slot));go(current);updateCurrent();
}
function go(value){
 const n=Math.max(1,Math.min(doc.numPages,Number.isFinite(+value)?Math.floor(+value):1));current=n;number.value=n;
 const slot=slots[n-1];if(!slot)return;pages.scrollTop=slot.offsetTop-12;schedule(slot);
}
let scrolling=false;
pages.addEventListener('scroll',()=>{if(!scrolling){scrolling=true;requestAnimationFrame(()=>{scrolling=false;updateCurrent();for(const slot of slots.slice(Math.max(0,current-2),current+2))schedule(slot);});}},{passive:true});
async function find(){
 const value=$('pdf-search').value.trim().toLocaleLowerCase('pt-BR'),run=++searchRun;
 if(value!==query){query=value;searchPage=0;}
 for(const layer of pages.querySelectorAll('.textLayer'))markMatches(layer);
 if(!query){message('Digite o texto que deseja localizar.');return;}
 message('Procurando no documento…');
 for(let offset=1;offset<=doc.numPages;offset++){
  const n=(searchPage+offset-1)%doc.numPages+1;
  let text=textCache.get(n);
  if(text===undefined){const content=await(await doc.getPage(n)).getTextContent();text=content.items.map(item=>item.str).join(' ').toLocaleLowerCase('pt-BR');if(textCache.size>30)textCache.delete(textCache.keys().next().value);textCache.set(n,text);}
  if(run!==searchRun)return;
  if(text.includes(query)){searchPage=n;go(n);message('Texto encontrado na página '+n+'. Os trechos visíveis estão destacados. Clique em Localizar para ir à próxima página com resultado.');return;}
 }
 message('Texto não encontrado neste documento.');
}
$('prev').onclick=()=>go(current-1);$('next').onclick=()=>go(current+1);number.onchange=()=>go(number.value);
$('zoom-in').onclick=()=>{mode='zoom';scale=Math.min(3,scale+.2);layout();};
$('zoom-out').onclick=()=>{mode='zoom';scale=Math.max(.2,scale-.2);layout();};
$('fit').onclick=()=>{mode='fit';layout();};$('find').onclick=find;
$('pdf-search').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();find();}};
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else if(root.requestFullscreen)await root.requestFullscreen();else root.classList.toggle('viewer-expanded');}catch{root.classList.toggle('viewer-expanded');}};
let resizeTimer;new ResizeObserver(()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(doc&&mode==='fit')layout();},180);}).observe(pages);
try{doc=await pdfjs.getDocument({url:root.dataset.url,disableAutoFetch:true,disableStream:true,rangeChunkSize:65536}).promise;number.max=doc.numPages;$('total').textContent='de '+doc.numPages;controls.forEach(c=>c.disabled=false);await layout(1);message('Documento pronto. Selecione o texto ou use os controles para navegar.');}
catch{message('Não foi possível abrir o PDF. Recarregue a página ou consulte a administração.');}
