let teacherProfile=null;
const draftProfileKey = 'lesson-profile-draft-v1';
const draftLessonKey = 'lesson-create-draft-v1';
function readStored(key) {
  try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch { return null; }
}
function writeStored(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch { return false; }
}
function profileFields() {
  return { name: $('teacher-name').value, assignments: [...$('assignment-rows').children].map(row => {
    const item = {};
    if (row.dataset.id) item.id = row.dataset.id;
    for (const input of row.querySelectorAll('input')) item[input.dataset.field] = input.value;
    return item;
  }) };
}
function profileDraft() {
  const value = readStored(draftProfileKey);
  return value && typeof value.name === 'string' && Array.isArray(value.assignments)
    && value.assignments.length <= 100 && value.assignments.every(item => item && typeof item === 'object') ? value : null;
}
function saveProfileDraft() {
  const saved = writeStored(draftProfileKey, profileFields());
  $('profile-draft-status').textContent = saved
    ? 'Bozza conservata su questo browser. Premi Salva profilo per applicarla.'
    : 'Il browser non consente di conservare la bozza. Salva il profilo prima di ricaricare.';
}
function saveCreateDraft() {
  writeStored(draftLessonKey, {title: $('title-input').value, assignment: $('assignment-id').value,
    engine: $('engine').value, model: $('model').value});
}
function restoreCreateDraft() {
  const draft = readStored(draftLessonKey);
  if (!draft || typeof draft !== 'object') return;
  if (typeof draft.title === 'string') $('title-input').value = draft.title.slice(0, 200);
  if (['local', 'openai'].includes(draft.engine)) {
    $('engine').value = draft.engine;
    chooseModel();
    if ([...$('model').options].some(o => o.value === draft.model)) $('model').value = draft.model;
  }
  demoHints();
}
const classKeys=['course','teaching','year','section'];
const classControls=['course-choice','teaching-choice','year-choice','section-choice'];

function addAssignment(values={}){
  const row=document.createElement('div');row.className='assignment-row';row.dataset.id=values.id||'';
  const labels={course:'Corso',teaching:'Insegnamento',year:'Anno',section:'Sezione'};
  const placeholders={course:'Es. Communication Design',teaching:'Es. Grafica Multimediale I',year:'1',section:'Es. a'};
  for(const key of classKeys){
    const label=document.createElement('label');label.textContent=labels[key];
    const input=document.createElement('input');input.dataset.field=key;input.required=true;input.maxLength=200;
    input.placeholder=placeholders[key];input.value=values[key]||(key==='year'?'1':'');
    if(key==='year'){input.type='number';input.min='1';input.max='10'}
    label.append(input);row.append(label);
  }
  const remove=document.createElement('button');remove.type='button';remove.className='text-button danger';
  remove.textContent='Rimuovi';remove.onclick=()=>{row.remove();if(!$('assignment-rows').children.length)addAssignment();saveProfileDraft()};
  row.append(remove);$('assignment-rows').append(row);
}

function openProfile(){
  $('profile-panel').hidden=false;$('create-panel').hidden=true;$('profile-error').hidden=true;
  const draft=profileDraft();const values=draft||teacherProfile;
  $('profile-draft-status').textContent=draft?'Bozza ripristinata. Salva il profilo per applicare le modifiche.':'Le modifiche vengono conservate come bozza su questo browser.';
  $('teacher-name').value=values?.name||'';$('assignment-rows').replaceChildren();
  for(const item of values?.assignments||[])addAssignment(item);
  if(!$('assignment-rows').children.length)addAssignment();
  $('close-profile').hidden=false;$('close-profile').textContent=teacherProfile?.name?'Chiudi':'Più tardi';$('teacher-name').focus();
}

async function loadProfile(){
  teacherProfile=await api('/api/profile');
  $('profile-button').textContent=teacherProfile.name?teacherProfile.name+' · Profilo':'Profilo docente';
  fillClassChoices();restoreCreateDraft();
  if(!state?.runtime.recording_id&&(!teacherProfile.name||profileDraft()))openProfile();
}

function fillClassChoices(changed=-1){
  if(!teacherProfile?.assignments.length)return;
  let entries=teacherProfile.assignments;
  const remembered=readStored(draftLessonKey)?.assignment||readStored('lesson-class');
  const preferred=entries.find(item=>item.id===remembered)||entries[0];
  for(let index=0;index<classKeys.length;index++){
    const key=classKeys[index],control=$(classControls[index]);
    const current=control.value;
    const options=[...new Set(entries.map(item=>item[key]))];
    control.replaceChildren();
    for(const value of options){const option=document.createElement('option');option.value=value;option.textContent=key==='year'?'Anno '+value:value;control.append(option)}
    control.value=options.includes(current)&&index<=changed?current:options.includes(preferred[key])?preferred[key]:options[0];
    entries=entries.filter(item=>item[key]===control.value);
  }
  $('assignment-id').value=entries[0]?.id||'';
  const choice=entries[0];
  $('teacher-context').textContent=teacherProfile.name+(choice?' · '+choice.course+' · '+choice.teaching+' · '+choice.year+choice.section:'');
}

function rememberClass(){writeStored('lesson-class',$('assignment-id').value)}

// Bind after the main script has created its shared helpers.
document.addEventListener('DOMContentLoaded',()=>{
  $('profile-button').onclick=openProfile;
  $('close-profile').onclick=()=>{$('profile-panel').hidden=true};
  $('add-assignment').onclick=()=>{addAssignment();saveProfileDraft()};
  $('profile-form').addEventListener('input',saveProfileDraft);
  for(let index=0;index<classControls.length;index++)$(classControls[index]).onchange=()=>{fillClassChoices(index);rememberClass();saveCreateDraft()};
  $('profile-form').onsubmit=async event=>{
    event.preventDefault();const button=event.submitter;button.disabled=true;$('profile-error').hidden=true;
    const assignments=[...$('assignment-rows').children].map(row=>{
      const item={};if(row.dataset.id)item.id=row.dataset.id;
      for(const input of row.querySelectorAll('input'))item[input.dataset.field]=input.value;
      return item;
    });
    try{
      saveProfileDraft();
      teacherProfile=await api('/api/profile','POST',{name:$('teacher-name').value,assignments});
      writeStored(draftProfileKey,null);
      $('profile-panel').hidden=true;$('profile-button').textContent=teacherProfile.name+' · Profilo';
      fillClassChoices();openCreatePanel();toast('Profilo docente salvato.');
    }catch(error){$('profile-error').textContent=error.message;$('profile-error').hidden=false}
    finally{button.disabled=false}
  };
});
