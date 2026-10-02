/* La registrazione precede la compilazione dei dati, anche senza profilo. */
async function quickStart() {
  if (requesting || !online || state?.runtime.recording_id || !safeLeave()) return;
  requesting = true;
  renderRuntime(); renderDetail();
  let created = null;
  try {
    if (refreshPromise) await refreshPromise;
    created = await api('/api/lessons/quick-start', 'POST');
    dirty = false;
    $('profile-panel').hidden = true;
    $('create-panel').hidden = true;
    $('collection').value = 'active'; $('search').value = '';
    await refresh(true);
  } catch (error) {
    toast(error.message);
    // Recupera lo stato anche se la risposta dell'avvio è andata persa.
    await refresh(true);
  } finally {
    requesting = false;
    renderRuntime(); renderDetail();
  }
  const id = created?.id || state?.runtime.recording_id;
  if (id) {
    await selectLesson(id);
    toast(detail?.status === 'recording' ? 'Registrazione avviata. Puoi completare i dati quando vuoi.'
      : detail?.error || 'Controlla il microfono e premi Registra per riprovare.');
  }
}
$('quick-start').onclick = quickStart;
$('profile-quick-start').onclick = quickStart;
$('metadata-summary').addEventListener('click', () => {
  // Compila prima dell'apertura: l'evento toggle differito può sovrascrivere
  // i primi caratteri già inseriti quando il browser è impegnato.
  if ($('metadata-panel').open || !detail) return;
  const form = $('metadata-form');
  for (const key of ['title', 'docente', 'course', 'materia', 'year', 'section']) form.elements[key].value = detail[key] || '';
  $('metadata-error').hidden = true;
  const choice = $('metadata-assignment');
  choice.replaceChildren(new Option('Inserisci o modifica i dati qui sotto', ''));
  for (const item of teacherProfile?.assignments || []) choice.add(new Option(
    `${item.course} · ${item.teaching} · ${item.year}${item.section}`, item.id));
});
$('metadata-assignment').onchange = () => {
  const item = teacherProfile?.assignments.find(item => item.id === $('metadata-assignment').value);
  if (!item) return;
  const form = $('metadata-form');
  const values = { docente: teacherProfile.name, course: item.course, materia: item.teaching, year: item.year, section: item.section };
  for (const [key, value] of Object.entries(values)) form.elements[key].value = value;
};
$('metadata-form').onsubmit = async event => {
  event.preventDefault();
  if (requesting || !selected) return;
  const id = selected, fields = Object.fromEntries(new FormData(event.target));
  requesting = true; renderRuntime(); renderDetail();
  $('metadata-error').hidden = true;
  try {
    if (refreshPromise) await refreshPromise;
    detail = await api(`/api/lessons/${id}/metadata`, 'POST', fields);
    $('metadata-panel').open = false;
    await refresh(true);
    toast('Dati della lezione salvati.');
  } catch (error) {
    $('metadata-error').textContent = error.message; $('metadata-error').hidden = false;
  } finally {
    requesting = false; renderDetail(); renderRuntime();
  }
};
