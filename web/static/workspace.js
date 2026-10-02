/* I pannelli di configurazione restano accessibili da tastiera e isolati dal lavoro. */
(() => {
  const panels = [$('profile-panel'), $('create-panel')];
  const background = [document.querySelector('.sidebar'), document.querySelector('.app-header'),
    document.querySelector('.workspace-layout'), document.querySelector('footer')];
  let activePanel = null;
  let opener = null;
  document.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (button && ['profile-button', 'new-button', 'empty-new', 'import-new-button'].includes(button.id)) opener = button;
  }, true);
  function sync() {
    const previous = activePanel;
    activePanel = panels.find(panel => !panel.hidden) || null;
    for (const element of background) element.inert = !!activePanel;
    if (activePanel && !activePanel.contains(document.activeElement)) {
      activePanel.querySelector('input, button:not([hidden])')?.focus();
    } else if (previous && !activePanel && opener?.isConnected) opener.focus();
  }
  const observer = new MutationObserver(sync);
  for (const panel of panels) observer.observe(panel, { attributes: true, attributeFilter: ['hidden'] });
  document.addEventListener('keydown', event => {
    if (!activePanel) return;
    if (event.key === 'Escape') {
      const close = activePanel.id === 'profile-panel' ? $('close-profile') : $('cancel-create');
      if (!close.hidden) { event.preventDefault(); close.click(); }
    }
    if (event.key !== 'Tab') return;
    const controls = [...activePanel.querySelectorAll('button, input, select, textarea, summary, a[href]')]
      .filter(el => !el.disabled && el.tabIndex >= 0 && el.getClientRects().length > 0);
    const first = controls[0], last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  });
  sync();
})();
