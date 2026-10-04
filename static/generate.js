/* Draft feedback controls. Cache detached fields so editing text preserves values. */
function initCustomFeedback(doc, configurations = [], suggestions = {}, autofillGuard = false) {
  const form = doc.getElementById('generationForm');
  if (!form) return;
  const body = doc.getElementById('feedbackBody');
  const fields = doc.getElementById('generationPlaceholders');
  const cache = new Map([...fields.children].map(row => [row.dataset.placeholder, row]));
  const configs = new Map(configurations.map(ph => [ph.name, ph]));

  function createField(name) {
    const ph = configs.get(name);
    const row = doc.createElement('div');
    row.className = 'mb-3';
    row.dataset.placeholder = name;
    const label = doc.createElement('label');
    label.className = 'form-label';
    label.htmlFor = `ph_${name}`;
    label.textContent = name;
    const dropdown = ph?.input_type === 'dropdown' && ph.options?.length;
    const control = doc.createElement(dropdown ? 'select' : 'input');
    control.className = dropdown ? 'form-select' : 'form-control';
    control.id = `ph_${name}`;
    control.name = `ph_${name}`;
    control.required = true;
    row.append(label, control);
    if (dropdown) {
      for (const [i, text] of ['Select…', ...ph.options].entries()) {
        const option = doc.createElement('option');
        option.value = i ? text : '';
        option.textContent = text;
        option.disabled = !i;
        option.selected = !i;
        control.append(option);
      }
    } else {
      control.type = 'text';
      control.placeholder = `Enter ${name}`;
      if (autofillGuard) {
        control.autocomplete = 'off';
        control.setAttribute('data-1p-ignore', 'true');
        control.setAttribute('data-lpignore', 'true');
        control.setAttribute('data-bwignore', 'true');
        control.setAttribute('data-protonpass-ignore', 'true');
        control.setAttribute('data-form-type', 'other');
      }
      if (Object.hasOwn(suggestions, name) && Array.isArray(suggestions[name]) && suggestions[name].length) {
        const list = doc.createElement('datalist');
        list.id = `mru_${name}`;
        control.setAttribute('list', list.id);
        for (const value of suggestions[name]) {
          const option = doc.createElement('option');
          option.value = value;
          list.append(option);
        }
        row.append(list);
      }
    }
    return row;
  }

  function updateFields() {
    // Python's Unicode \w accepts letters, numbers, and underscore.
    const names = [...new Set([...body.value.matchAll(/\{([\p{L}\p{N}_]+)\}/gu)].map(m => m[1]))];
    fields.replaceChildren(...names.map(name => {
      if (!cache.has(name)) cache.set(name, createField(name));
      return cache.get(name);
    }));
  }

  function updateSaveChoice() {
    const saving = form.querySelector('[name="save_mode"]:checked')?.value === 'save';
    doc.getElementById('newTemplateNameGroup').hidden = !saving;
    doc.getElementById('newTemplateName').required = saving;
  }
  body.addEventListener('input', updateFields);
  form.querySelectorAll('[name="save_mode"]').forEach(radio => radio.addEventListener('change', updateSaveChoice));
  updateFields();
  updateSaveChoice();
}

if (typeof module !== 'undefined') module.exports = { initCustomFeedback };
