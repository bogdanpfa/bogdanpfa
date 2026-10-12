const $ = id => document.getElementById(id);
const search = $('search'), results = $('results'), message = $('search-message');
let debounce;
const dataFields = ['marca','nume','prenume','initiala_tata','functie','loc_munca'];

// loc_munca din bază e o cale „A/B/C”: în Locația se pune penultimul segment (editabil)
function splitLoc(){const parts=($('loc_munca').value||'').split('/').map(x=>x.trim()).filter(Boolean);if(parts.length>=2)$('loc_munca').value=parts[parts.length-2];}
function clearForm(){ dataFields.forEach(id=>$(id).value=''); $('tip_locatie').value='Regional'; }
function manual(){ clearForm(); search.value=''; results.hidden=true; message.textContent='Completați manual datele salariatului.'; $('nume').focus(); }
function showResults(items){ results.innerHTML=''; results.hidden=!items.length; if(!items.length){message.textContent=search.value.length>=2?'Nu a fost găsit niciun salariat în SRTFC Iași. Puteți introduce manual.':'';return;} message.textContent='';items.forEach(p=>{let b=document.createElement('button');b.type='button';b.className='result';b.innerHTML=`<strong>${p.marca} · ${p.nume_afisare || `${p.nume||''} ${p.prenume||''}`}</strong><small>${p.functie || 'Funcție necompletată'}${p.loc_munca?' · '+p.loc_munca:''}</small>`;b.addEventListener('click',()=>selectPerson(p.marca));results.append(b);}); }
async function selectPerson(marca){try{const r=await fetch('/api/persoane/'+encodeURIComponent(marca));const p=await r.json();if(!r.ok)throw new Error(p.error);dataFields.forEach(id=>$(id).value=p[id]||'');splitLoc();search.value=p.nume_afisare||`${p.nume||''} ${p.prenume||''}`;results.hidden=true;message.textContent='Datele au fost preluate din baza de persoane SRTFC Iași.';}catch(e){message.textContent=e.message;}}
search.addEventListener('input',()=>{clearTimeout(debounce);let q=search.value.trim();if(q.length<2){results.hidden=true;message.textContent='';return;}debounce=setTimeout(async()=>{try{let r=await fetch('/api/persoane?q='+encodeURIComponent(q));let d=await r.json();if(!r.ok)throw new Error(d.error);showResults(d);}catch(e){message.textContent=e.message;}},250);});
$('manual').addEventListener('click',manual);
const toggle=$('numar_manual'), nr=$('numar_inregistrare'), generate=$('generate');
function gate(){nr.disabled=!toggle.checked;generate.disabled=!(toggle.checked&&nr.value.trim());if(!toggle.checked)$('error').textContent='';}
toggle.addEventListener('change',gate);nr.addEventListener('input',gate);gate();
$('form').addEventListener('submit',async e=>{e.preventDefault();const error=$('error');error.textContent='';if(!toggle.checked||!nr.value.trim()){error.textContent='Activați și completați numărul de înregistrare.';return;}const payload={numar_manual:toggle.checked,servicii:[...document.querySelectorAll('input[name=servicii]:checked')].map(x=>x.value),operatiune:document.querySelector('input[name=operatiune]:checked').value};document.querySelectorAll('input[id],select[id]').forEach(x=>payload[x.id]=x.type==='checkbox'?x.checked:x.value);try{generate.disabled=true;generate.textContent='Se generează…';const r=await fetch('/api/pdf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!r.ok){const d=await r.json();throw new Error(d.error||'PDF-ul nu a putut fi generat.');}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='comanda_servicii.pdf';a.click();URL.revokeObjectURL(url);}catch(err){error.textContent=err.message;}finally{generate.textContent='Generează PDF';gate();}});

// „Adăugare” și „Ștergere” nu pot fi active în același timp
document.querySelectorAll('input[name=servicii]').forEach(c=>c.addEventListener('change',()=>{
  if(!c.checked)return;
  const opus={'Adăugare':'Ștergere','Ștergere':'Adăugare'}[c.value];
  if(opus)document.querySelectorAll('input[name=servicii]').forEach(o=>{if(o.value===opus)o.checked=false;});
}));
