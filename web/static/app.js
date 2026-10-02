const $ = id => document.getElementById(id);
const labels = {
  prepared: 'Pronta per registrare', recording: 'Registrazione', paused: 'In pausa',
  queued: 'In coda', transcribing: 'Trascrizione in corso', notes: 'Generazione appunti',
  ready: 'Salvata', failed: 'Da completare', interrupted: 'Interrotta'
};
const busyStates = ['recording', 'paused', 'queued', 'transcribing', 'notes'];
const models = {
  local: [['base', 'Whisper Base · rapido'], ['small', 'Whisper Small · intermedio'], ['medium', 'Whisper Medium · più impegnativo'], ['large-v3-turbo', 'Whisper Large v3 Turbo · veloce su GPU'], ['large-v3', 'Whisper Large v3 · modello completo']],
  openai: [['gpt-transcribe', 'GPT Transcribe · consigliato'], ['gpt-4o-transcribe', 'GPT-4o Transcribe · precedente'], ['gpt-4o-mini-transcribe', 'GPT-4o Mini · precedente'], ['whisper-1', 'Whisper API · precedente']]
};
let token = '', state = null, selected = null, detail = null, tab = 'transcript';
let dirty = false, requesting = false, refreshPromise = null, selectionVersion = 0;
let listSignature = '', pollTimer = null, online = false;
let notesMode = 'read', notesPreviewSource = null;
let tokenRefreshPromise = null;
let pendingAudio = null;

async function renewLocalToken() {
  if (!tokenRefreshPromise) {
    tokenRefreshPromise = (async () => {
      // Anche i server già avviati espongono qui il token corrente.
      const response = await fetch('/api/state', { cache: 'no-store', signal: AbortSignal.timeout(10000) });
      const current = await response.json();
      if (!response.ok || typeof current.token !== 'string' || !current.token) {
        throw new Error('Impossibile ristabilire la connessione. I dati inseriti sono ancora nel modulo.');
      }
      token = current.token;
      return current.token;
    })();
  }
  try { return await tokenRefreshPromise; }
  finally { tokenRefreshPromise = null; }
}

function toast(message) {
  $('toast').textContent = message;
  $('toast').hidden = false;
  clearTimeout(toast.timeout);
  toast.timeout = setTimeout(() => { $('toast').hidden = true; }, 5500);
}

async function api(path, method = 'GET', data) {
  const options = { method, headers: { 'X-Local-Token': token } };
  if (method === 'GET') options.signal = AbortSignal.timeout(10000);
  if (data instanceof FormData) options.body = data;
  else if (method !== 'GET') {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(data || {});
  }
  let response = await fetch(path, options);
  let body = await response.json();
  const expiredToken = response.status === 403 &&
    (body.code === 'local_token_expired' || body.error === 'Ricarica la pagina prima di continuare.');
  if (method !== 'GET' && expiredToken) {
    // Il server ha rifiutato il comando prima di eseguirlo: una sola riprova è sicura.
    // Non ripetere comandi su errori di rete o risposte generiche: l'esito è incerto.
    options.headers['X-Local-Token'] = await renewLocalToken();
    response = await fetch(path, options);
    body = await response.json();
  }
  if (!response.ok) throw new Error(body.error || 'Operazione non riuscita.');
  return body;
}

function safeLeave() {
  return !dirty || confirm('Ci sono modifiche non salvate. Vuoi abbandonarle?');
}

function time(seconds) {
  const n = Math.floor(seconds || 0);
  const minutes = Math.floor(n / 60) % 60;
  const hours = Math.floor(n / 3600);
  return (hours ? hours + ':' : '') + `${String(minutes).padStart(2, '0')}:${String(n % 60).padStart(2, '0')}`;
}

function renderList() {
  if (!state) return;
  const query = $('search').value.trim().toLocaleLowerCase('it');
  const collection = $('collection').value;
  const collectionTitle = { active: 'Lezioni', archived: 'Archiviate', trash: 'Cestino' }[collection];
  $('page-title').textContent = collectionTitle;
  $('list-title').textContent = collectionTitle;
  for (const button of document.querySelectorAll('[data-collection]')) {
    button.classList.toggle('active', button.dataset.collection === collection);
    button.setAttribute('aria-current', button.dataset.collection === collection ? 'page' : 'false');
  }
  const lessons = state.lessons.filter(l => (l.collection || 'active') === collection)
    .filter(l => `${l.title} ${l.materia} ${l.docente} ${l.course || ''} ${l.year || ''}${l.section || ''}`.toLocaleLowerCase('it').includes(query));
  // Il livello del microfono cambia spesso; l'archivio deve conservare focus e scroll.
  const signature = JSON.stringify([selected, collection, query, lessons.map(l =>
    [l.id, l.title, l.course, l.materia, l.year, l.section, l.created_at, l.status])]);
  if (signature !== listSignature) {
    const focused = document.activeElement?.dataset.lessonId;
    const fragment = document.createDocumentFragment();
    for (const lesson of lessons) {
      const button = document.createElement('button');
      button.dataset.lessonId = lesson.id;
      button.className = 'lesson-item' + (lesson.id === selected ? ' selected' : '');
      button.setAttribute('aria-current', lesson.id === selected ? 'true' : 'false');
      const title = document.createElement('strong');
      title.textContent = lesson.title;
      const meta = document.createElement('small');
      meta.textContent = [lesson.course, lesson.materia, lesson.year ? lesson.year + lesson.section : '',
        new Date(lesson.created_at).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' })].filter(Boolean).join(' · ');
      const badge = document.createElement('span');
      badge.className = 'badge ' + lesson.status;
      badge.textContent = labels[lesson.status] || lesson.status;
      button.append(title, meta, badge);
      button.onclick = () => selectLesson(lesson.id);
      fragment.append(button);
    }
    $('lesson-list').replaceChildren(fragment);
    if (focused) [...$('lesson-list').children].find(b => b.dataset.lessonId === focused)?.focus({ preventScroll: true });
    listSignature = signature;
  }
  $('empty-archive').hidden = lessons.length > 0;
  $('archive-total').textContent = lessons.length;
  $('empty-archive').textContent = query ? 'Nessuna lezione corrisponde alla ricerca.'
    : collection === 'trash' ? 'Il cestino è vuoto. Le lezioni spostate qui possono essere ripristinate.'
    : collection === 'archived' ? 'Nessuna lezione archiviata.' : 'Crea una lezione per registrare o importare audio.';
  $('lesson-count').textContent = state.lessons.filter(l => l.collection !== 'trash').length;
  $('ready-count').textContent = state.lessons.filter(l => l.status === 'ready' && l.collection !== 'trash').length;
}

async function selectLesson(id) {
  if (requesting || id === selected || !safeLeave()) return;
  const version = ++selectionVersion;
  $('metadata-panel').open = false;
  $('export-menu').open = false;
  dirty = false;
  selected = id;
  detail = null;
  tab = 'transcript';
  notesMode = 'read';
  $('lesson-detail').hidden = true;
  $('empty-workspace').hidden = true;
  $('loading-detail').hidden = false;
  renderList();
  try {
    const result = await api('/api/lessons/' + id);
    if (version !== selectionVersion || selected !== id) return;
    detail = result;
    renderDetail();
  } catch (error) {
    if (version === selectionVersion) {
      selected = null;
      $('empty-workspace').hidden = false;
      renderList();
      toast(error.message);
    }
  } finally {
    if (version === selectionVersion) $('loading-detail').hidden = true;
  }
}

function renderDetail() {
  if (!detail || detail.id !== selected) return;
  $('empty-workspace').hidden = true;
  $('loading-detail').hidden = true;
  $('lesson-detail').hidden = false;
  $('lesson-title').textContent = detail.title;
  $('lesson-meta').textContent = [detail.course, detail.materia, detail.year ? detail.year + detail.section : '', detail.docente].filter(Boolean).join(' · ') || 'LEZIONE';
  $('lesson-status').textContent = labels[detail.status] || detail.status;
  $('lesson-status').className = 'badge ' + detail.status;
  $('progress').textContent = detail.progress;
  const current = state.runtime.recording_id === detail.id;
  $('error-box').textContent = detail.error || detail.capture_warning || (current ? state.runtime.capture_error : '');
  $('error-box').hidden = !$('error-box').textContent;
  const collection = detail.collection || 'active', readonly = collection !== 'active';
  const busy = readonly || busyStates.includes(detail.status);
  const recording = ['recording', 'paused'].includes(detail.status);
  const blocked = requesting || !online;
  $('metadata-panel').hidden = readonly;
  $('metadata-summary').textContent = detail.metadata_pending ? 'Dati della lezione · da completare' : 'Dati della lezione';
  for (const control of $('metadata-form').elements) control.disabled = blocked || detail.status === 'notes';
  $('archive-lesson').hidden = readonly;
  $('restore-lesson').hidden = !readonly;
  $('restore-lesson').textContent = collection === 'trash' ? 'Ripristina lezione' : 'Riporta in Lezioni';
  $('trash-lesson').hidden = collection === 'trash';
  $('delete-lesson').hidden = collection !== 'trash';
  for (const id of ['archive-lesson', 'restore-lesson', 'trash-lesson', 'delete-lesson']) $(id).disabled = blocked || busyStates.includes(detail.status);
  $('collection-notice').hidden = !readonly;
  $('collection-notice').textContent = collection === 'trash'
    ? 'Nel cestino: audio e testi sono conservati. Ripristina la lezione per utilizzarla di nuovo.'
    : 'Lezione archiviata: puoi leggere e scaricare i contenuti. Riportala in Lezioni per modificarla.';
  $('record-panel').hidden = readonly || (!recording && detail.status !== 'prepared');
  $('start').disabled = blocked || readonly || detail.status !== 'prepared' || !!state.runtime.recording_id;
  $('pause').disabled = blocked || !current;
  $('pause').textContent = detail.status === 'paused' ? 'Riprendi' : 'Pausa';
  $('stop').disabled = blocked || !current;
  $('import-button').disabled = blocked || readonly || detail.status !== 'prepared';
  $('device').disabled = recording || blocked;
  $('save').disabled = blocked || busy || !dirty;
  $('generate').disabled = blocked || busy || !detail.transcript.trim() || dirty;
  $('generate').textContent = detail.notes ? 'Rigenera appunti' : '✦ Genera appunti';
  $('retry').hidden = !['failed', 'interrupted'].includes(detail.status) || (!detail.audio && detail.engine !== 'demo');
  $('retry').disabled = blocked || busy;
  $('editor').disabled = busy || requesting;
  $('dirty').hidden = !dirty;
  if (!dirty && $('editor').value !== (detail[tab] || '')) $('editor').value = detail[tab] || '';
  for (const name of ['transcript', 'notes']) {
    $(name + '-tab').classList.toggle('active', tab === name);
    $(name + '-tab').setAttribute('aria-selected', tab === name);
    $(name + '-tab').tabIndex = tab === name ? 0 : -1;
    $(name + '-tab').disabled = requesting;
  }
  $('editor-caption').textContent = tab === 'transcript' ? 'Revisiona il testo prima di generare gli appunti.' : 'Bozza da revisionare: controlla gli appunti rispetto alla lezione.';
  $('editor').setAttribute('aria-label', tab === 'transcript' ? 'Trascrizione della lezione' : 'Appunti della lezione');
  renderNotesView();
  renderExports();
  $('audio-player').hidden = !detail.audio || recording;
  if (detail.audio && !recording) {
    const src = `/api/lessons/${detail.id}/download/audio?play=1`;
    if ($('audio-player').getAttribute('src') !== src) $('audio-player').src = src;
  } else if ($('audio-player').hasAttribute('src')) {
    $('audio-player').pause();
    $('audio-player').removeAttribute('src');
    $('audio-player').load();
  }
  $('timer').textContent = time(current ? state.runtime.duration : detail.duration);
  $('level').value = current ? state.runtime.level : 0;
  $('level-text').textContent = state.demo ? 'Prova simulata · microfono non utilizzato'
    : current ? (state.runtime.paused ? 'In pausa' : state.runtime.level < 0.001 ? 'Segnale basso: controlla il microfono' : 'Audio acquisito') : 'Pronto per registrare';
}

function renderRuntime() {
  const active = state.lessons.find(l => l.id === state.runtime.recording_id);
  $('recording-banner').hidden = !active;
  if (active) $('recording-summary').textContent = `${state.runtime.paused ? 'In pausa' : 'Registrazione attiva'} · ${active.title} · ${time(state.runtime.duration)}`;
  $('new-button').disabled = requesting || !online;
  $('quick-start').disabled = $('profile-quick-start').disabled = requesting || !online || !!state.runtime.recording_id;
  $('import-new-button').disabled = requesting || !online;
  $('collection').disabled = requesting;
}

async function refresh(force = false) {
  if (refreshPromise) return refreshPromise;
  if (requesting && !force) return;
  refreshPromise = (async () => {
    try {
      state = await api('/api/state');
      token = state.token;
      online = true;
      $('connection').hidden = true;
      $('demo-banner').hidden = !state.demo;
      renderList();
      renderRuntime();
      const id = selected, version = selectionVersion;
      const summary = state.lessons.find(l => l.id === id);
      if (id && !summary) {
        // Un'altra scheda può avere eliminato la lezione: conserva eventuali bozze.
        if (dirty) throw new Error('La lezione non è più disponibile. Copia il testo prima di ricaricare.');
        clearSelection();
      } else if (id && detail && (detail.revision !== summary.revision || !summary.revision)) {
        const result = await api('/api/lessons/' + id);
        if (id === selected && version === selectionVersion) {
          detail = result;
          // Il lavoro può terminare tra la lettura dell'elenco e del dettaglio.
          const { transcript, notes, segments, ...latestSummary } = result;
          state.lessons = state.lessons.map(lesson => lesson.id === id ? latestSummary : lesson);
          renderList();
        }
      }
      renderDetail();
      demoHints();
    } catch (error) {
      online = false;
      $('connection').textContent = 'Connessione al pannello non disponibile. Verifica che la finestra del server sia aperta. Le modifiche nell’editor restano qui.';
      $('connection').hidden = false;
      if (state) renderRuntime();
      renderDetail();
    }
  })();
  try { await refreshPromise; } finally { refreshPromise = null; }
}

async function action(name, data) {
  if (!selected || requesting || !online) return;
  const id = selected;
  requesting = true;
  renderDetail();
  renderRuntime();
  try {
    if (refreshPromise) await refreshPromise;
    const result = await api(`/api/lessons/${id}/${name}`, 'POST', data);
    if (selected === id) detail = result;
    if (name === 'text') { dirty = false; toast('Modifiche salvate.'); }
    if (name === 'notes') { tab = 'notes'; notesMode = 'read'; }
    if (name === 'move') {
      dirty = false;
      $('collection').value = data.collection;
      toast(data.collection === 'trash' ? 'Lezione spostata nel cestino.' : data.collection === 'archived' ? 'Lezione archiviata.' : 'Lezione ripristinata.');
    }
    await refresh(true);
  } catch (error) { toast(error.message); }
  finally { requesting = false; renderDetail(); renderRuntime(); schedulePoll(); }
}

function chooseModel() {
  const engine = $('engine').value;
  $('model').replaceChildren();
  for (const [value, label] of models[engine]) {
    const option = document.createElement('option');
    option.value = value; option.textContent = label; $('model').append(option);
  }
  $('engine-hint').textContent = engine === 'local'
    ? `Elaborazione su ${state?.runtime.local_runtime?.device === 'cuda' ? 'GPU NVIDIA' : 'CPU'} · ${state?.runtime.local_runtime?.compute_type || 'int8'}. Il modello si scarica al primo uso. Gli appunti richiedono il servizio cloud.`
    : 'Il servizio riceve l’audio della lezione. Serve una chiave API configurata sul PC.';
}

function demoHints() {
  if (!state?.demo) return;
  $('engine').disabled = true;
  $('model').disabled = true;
  $('engine-hint').textContent = 'Contenuti simulati: puoi provare archivio, revisione e appunti senza microfono o servizi AI.';
}

function clearSelection() {
  ++selectionVersion;
  selected = null; detail = null; dirty = false;
  $('lesson-detail').hidden = true;
  $('loading-detail').hidden = true;
  $('empty-workspace').hidden = false;
  $('audio-player').pause();
  renderList();
}

function schedulePoll() {
  clearTimeout(pollTimer);
  const delay = document.hidden ? 15000 : state?.runtime.recording_id ? 1000
    : state?.lessons.some(l => busyStates.includes(l.status)) ? 3000 : 5000;
  pollTimer = setTimeout(async () => { await refresh(); schedulePoll(); }, delay);
}

function openCreatePanel() {
  if (!teacherProfile?.name) { openProfile(); return; }
  $('profile-panel').hidden = true;
  $('create-panel').hidden = false;
  $('create-error').hidden = true;
  fillClassChoices(); restoreCreateDraft();
  $('import-summary').hidden = !pendingAudio;
  $('import-summary').textContent = pendingAudio ? `Audio selezionato: ${pendingAudio.name} · ${(pendingAudio.size / 1024 / 1024).toFixed(1)} MB. Verrà caricato e trascritto dopo la creazione.` : '';
  $('create-submit').textContent = pendingAudio ? 'Crea e importa audio →' : 'Crea lezione →';
  $('title-input').focus();
}
$('new-button').onclick = () => { pendingAudio = null; openCreatePanel(); };
$('empty-new').onclick = () => $('new-button').click();
$('import-new-button').onclick = () => $('new-audio-file').click();
$('new-audio-file').onchange = () => {
  const file = $('new-audio-file').files[0];
  $('new-audio-file').value = '';
  if (!file) return;
  if (file.size >= 512 * 1024 * 1024) { toast('Il file deve essere inferiore a 512 MiB.'); return; }
  pendingAudio = file;
  if (!$('title-input').value.trim()) $('title-input').value = file.name.replace(/\.[^.]+$/, '').slice(0, 200);
  saveCreateDraft();
  openCreatePanel();
};
$('cancel-create').onclick = () => { $('create-panel').hidden = true; };
for (const button of document.querySelectorAll('[data-collection]')) {
  button.onclick = () => {
    $('collection').value = button.dataset.collection;
    $('collection').dispatchEvent(new Event('change'));
  };
}
$('engine').onchange = chooseModel;
$('search').oninput = renderList;
$('show-recording').onclick = () => selectLesson(state.runtime.recording_id);
$('create-form').onsubmit = async event => {
  event.preventDefault();
  if (requesting || !safeLeave()) return;
  const button = event.submitter;
  $('create-error').hidden = true;
  button.disabled = true;
  requesting = true;
  renderDetail();
  renderRuntime();
  let createdId = null;
  try {
    if (refreshPromise) await refreshPromise;
    const fields = Object.fromEntries(new FormData(event.target));
    const created = await api('/api/lessons', 'POST', fields);
    createdId = created.id;
    dirty = false;
    $('collection').value = 'active'; $('search').value = ''; $('create-panel').hidden = true;
    await refresh(true);
    rememberClass(); $('title-input').value = ''; writeStored(draftLessonKey, null);
  } catch (error) { $('create-error').textContent = error.message; $('create-error').hidden = false; }
  finally {
    requesting = false;
    button.disabled = false;
    renderDetail();
    renderRuntime();
  }
  if (createdId) {
    await selectLesson(createdId);
    if (pendingAudio) {
      const file = pendingAudio;
      pendingAudio = null;
      const form = new FormData(); form.append('audio', file);
      await action('import', form);
    }
  }
};
$('create-form').addEventListener('input', saveCreateDraft);
$('create-form').addEventListener('change', saveCreateDraft);
$('start').onclick = () => action('start', { device: $('device').value || null });
$('pause').onclick = () => action('pause');
$('stop').onclick = () => action('stop');
$('retry').onclick = () => { if (safeLeave()) { dirty = false; action('retry'); } };
$('generate').onclick = () => action('notes');
$('save').onclick = () => action('text', { [tab]: $('editor').value });
$('editor').oninput = () => {
  dirty = $('editor').value !== (detail?.[tab] || '');
  $('dirty').hidden = !dirty;
  $('save').disabled = !dirty || !online || requesting;
  $('generate').disabled = dirty || !online || requesting || !detail?.transcript.trim();
  renderNotesView();
  renderExports();
};
function renderExports() {
  for (const [id, kind, field] of [
    ['download', 'transcript', 'transcript'], ['download-notes', 'notes', 'notes'],
    ['download-markdown', 'notes-markdown', 'notes'], ['download-audio', 'audio', 'audio']
  ]) {
    const link = $(id), blocked = dirty && tab === field;
    link.hidden = !detail[field];
    link.setAttribute('aria-disabled', String(blocked));
    if (blocked) link.removeAttribute('href');
    else link.href = `/api/lessons/${detail.id}/download/${kind}`;
  }
  $('print-notes').hidden = !detail.notes;
  $('print-notes').disabled = dirty && tab === 'notes';
  $('export-hint').textContent = dirty ? 'Salva le modifiche per esportare il documento aggiornato.'
    : !detail.transcript && !detail.notes && !detail.audio ? 'I download saranno disponibili dopo la registrazione o l’importazione.'
    : 'Esporta i contenuti salvati della lezione.';
}
function renderNotesView() {
  const isNotes = tab === 'notes';
  const reading = isNotes && notesMode === 'read';
  $('notes-tools').hidden = !isNotes;
  $('notes-preview').hidden = !reading;
  $('editor').hidden = reading;
  $('format-toolbar').hidden = !isNotes || reading || $('editor').disabled;
  $('format-hint').hidden = $('format-toolbar').hidden;
  $('notes-read').setAttribute('aria-pressed', reading);
  $('notes-edit').setAttribute('aria-pressed', !reading);
  $('notes-edit').disabled = $('editor').disabled;
  if (reading && notesPreviewSource !== $('editor').value) {
    renderNotes($('editor').value, $('notes-preview'));
    notesPreviewSource = $('editor').value;
  }
}
$('notes-read').onclick = () => { notesMode = 'read'; renderNotesView(); };
$('notes-edit').onclick = () => { notesMode = 'edit'; renderNotesView(); $('editor').focus(); };
$('print-notes').onclick = () => {
  if (!detail?.notes || (dirty && tab === 'notes')) return;
  $('export-menu').open = false;
  renderNotes(detail.notes, $('notes-preview'));
  notesPreviewSource = null;
  document.body.classList.add('printing-notes');
  window.print();
};
window.addEventListener('afterprint', () => {
  document.body.classList.remove('printing-notes');
  if (detail) renderNotesView();
});
document.addEventListener('click', event => {
  if (!$('export-menu').contains(event.target)) $('export-menu').open = false;
});
$('export-menu').addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    $('export-menu').open = false;
    $('export-menu').querySelector('summary').focus();
  }
});
for (const button of document.querySelectorAll('[data-format]')) {
  button.onclick = () => formatNotes(button.dataset.format);
}
for (const name of ['transcript', 'notes']) {
  $(name + '-tab').onclick = () => {
    if (requesting || tab === name || !safeLeave()) return;
    dirty = false; tab = name; renderDetail();
  };
  $(name + '-tab').onkeydown = event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 'transcript' : event.key === 'End' ? 'notes' : name === 'transcript' ? 'notes' : 'transcript';
    $(next + '-tab').click(); $(tab + '-tab').focus();
  };
}
$('import-button').onclick = () => $('audio-file').click();
$('audio-file').onchange = () => {
  const file = $('audio-file').files[0];
  if (!file) return;
  if (file.size >= 512 * 1024 * 1024) {
    toast('Il file deve essere inferiore a 512 MiB.');
    $('audio-file').value = '';
    return;
  }
  const form = new FormData(); form.append('audio', file);
  action('import', form); $('audio-file').value = '';
};
$('collection').onchange = () => {
  if (requesting || !safeLeave()) { $('collection').value = detail?.collection || 'active'; return; }
  clearSelection();
};
async function moveLesson(collection) { if (safeLeave()) await action('move', { collection }); }
$('archive-lesson').onclick = () => moveLesson('archived');
$('restore-lesson').onclick = () => moveLesson('active');
$('trash-lesson').onclick = () => moveLesson('trash');
$('delete-lesson').onclick = async () => {
  if (!selected || requesting || !confirm('Eliminare definitivamente questa lezione? Audio, trascrizione e appunti verranno rimossi dal PC. Non potrai ripristinarli dal cestino.')) return;
  requesting = true; renderDetail(); renderRuntime();
  try {
    if (refreshPromise) await refreshPromise;
    await api('/api/lessons/' + selected, 'DELETE');
    clearSelection(); await refresh(true); toast('Lezione eliminata definitivamente.');
  } catch (error) { toast(error.message); }
  finally { requesting = false; renderDetail(); renderRuntime(); }
};
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
window.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's' && selected) {
    if ($('metadata-form').contains(event.target)) {
      event.preventDefault(); if (!$('save-metadata').disabled) $('metadata-form').requestSubmit();
      return;
    }
    event.preventDefault(); if (!$('save').disabled) $('save').click();
  }
});
document.addEventListener('visibilitychange', async () => {
  if (!document.hidden) await refresh();
  schedulePoll();
});
async function boot() {
  chooseModel();
  await refresh();
  try {
    await loadProfile();
    if (state?.api_key_expires_on) $('key-expiry').textContent = 'Chiave API · scadenza indicativa ' + new Date(state.api_key_expires_on + 'T12:00:00').toLocaleDateString('it-IT');
    const data = await api('/api/devices');
    for (const device of data.devices) {
      const option = document.createElement('option');
      option.value = device.id; option.textContent = device.name + (device.default ? ' · predefinito' : '');
      $('device').append(option);
    }
  } catch (error) { toast(error.message); }
  finally { schedulePoll(); }
}
boot();
