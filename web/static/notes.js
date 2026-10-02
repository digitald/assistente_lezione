/* Markdown semplice per gli appunti: solo elementi DOM creati esplicitamente.
   HTML, immagini e collegamenti restano testo; nessun contenuto diventa codice. */
function notesInline(parent, source, depth = 0) {
  if (depth > 3) { parent.append(document.createTextNode(source)); return; }
  const pattern = /(`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|_[^_\n]+_)/g;
  let end = 0;
  for (const match of source.matchAll(pattern)) {
    parent.append(document.createTextNode(source.slice(end, match.index)));
    const value = match[0];
    const strong = value.startsWith('**') || value.startsWith('__');
    const tag = value.startsWith('`') ? 'code' : strong ? 'strong' : 'em';
    const element = document.createElement(tag);
    const width = strong ? 2 : 1;
    const content = value.slice(width, -width);
    if (tag === 'code') element.textContent = content;
    else notesInline(element, content, depth + 1);
    parent.append(element);
    end = match.index + value.length;
  }
  parent.append(document.createTextNode(source.slice(end)));
}

function renderNotes(source, target) {
  const fragment = document.createDocumentFragment();
  const lines = source.replace(/\r\n?/g, '\n').split('\n');
  let paragraph = [], lists = [], quote = null;
  const flushParagraph = () => {
    if (paragraph.length) {
      const p = document.createElement('p');
      notesInline(p, paragraph.join('\n'));
      fragment.append(p);
      paragraph = [];
    }
  };
  const reset = () => { flushParagraph(); lists = []; quote = null; };
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index];
    if (!line.trim()) { reset(); continue; }
    if (/^\s*```/.test(line)) {
      reset();
      const code = [], pre = document.createElement('pre'), element = document.createElement('code');
      while (++index < lines.length && !/^\s*```\s*$/.test(lines[index])) code.push(lines[index]);
      element.textContent = code.join('\n'); pre.append(element); fragment.append(pre);
      continue;
    }
    const heading = line.match(/^ {0,3}(#{1,6})\s+(.+)$/);
    if (heading) {
      reset();
      const element = document.createElement('h' + heading[1].length);
      notesInline(element, heading[2].replace(/\s+#+\s*$/, '')); fragment.append(element);
      continue;
    }
    if (/^\s*(---+|\*\*\*+)\s*$/.test(line)) { reset(); fragment.append(document.createElement('hr')); continue; }
    const quoted = line.match(/^\s*>\s?(.*)$/);
    if (quoted) {
      flushParagraph(); lists = [];
      if (!quote) { quote = document.createElement('blockquote'); fragment.append(quote); }
      const p = document.createElement('p'); notesInline(p, quoted[1]); quote.append(p);
      continue;
    }
    const item = line.match(/^(\s*)([-+*]|\d+[.)])\s+(.+)$/);
    if (item) {
      flushParagraph(); quote = null;
      const indent = item[1].replace(/\t/g, '    ').length;
      const type = /^\d/.test(item[2]) ? 'ol' : 'ul';
      while (lists.length && lists.at(-1).indent > indent) lists.pop();
      if (lists.length && lists.at(-1).indent === indent && lists.at(-1).type !== type) lists.pop();
      if (!lists.length || lists.at(-1).indent < indent) {
        const list = document.createElement(type);
        if (type === 'ol') list.start = Number.parseInt(item[2], 10);
        const parent = lists.at(-1)?.last || fragment;
        parent.append(list);
        lists.push({ indent, type, list, last: null });
      }
      const li = document.createElement('li');
      notesInline(li, item[3]); lists.at(-1).list.append(li); lists.at(-1).last = li;
      continue;
    }
    // Una riga rientrata prosegue l'ultimo punto, senza perderne il contenuto.
    if (lists.length && /^\s+/.test(line)) {
      lists.at(-1).last.append(document.createTextNode('\n'));
      notesInline(lists.at(-1).last, line.trim());
      continue;
    }
    lists = []; quote = null; paragraph.push(line);
  }
  flushParagraph();
  if (!source.trim()) {
    const empty = document.createElement('p');
    empty.className = 'notes-empty';
    empty.textContent = 'Gli appunti appariranno qui. Generali dalla trascrizione oppure scrivili con Modifica.';
    fragment.append(empty);
  }
  target.replaceChildren(fragment);
}

function formatNotes(kind) {
  const editor = $('editor');
  if (editor.disabled || tab !== 'notes' || notesMode !== 'edit') return;
  const start = editor.selectionStart, end = editor.selectionEnd;
  if (kind === 'bold') {
    const text = editor.value.slice(start, end) || 'concetto chiave';
    editor.setRangeText('**' + text + '**', start, end, 'select');
  } else {
    const first = editor.value.lastIndexOf('\n', start - 1) + 1;
    const next = editor.value.indexOf('\n', end);
    const last = next === -1 ? editor.value.length : next;
    const lines = editor.value.slice(first, last).split('\n');
    const prefixes = { heading: '## ', subheading: '### ', bullet: '- ', quote: '> ' };
    editor.setRangeText(lines.map((line, i) => (kind === 'numbered' ? `${i + 1}. ` : prefixes[kind]) + line).join('\n'), first, last, 'select');
  }
  editor.focus();
  editor.dispatchEvent(new Event('input', { bubbles: true }));
}
