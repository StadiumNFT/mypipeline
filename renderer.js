const out = document.getElementById('output');
const rootEl = document.getElementById('rootPath');
const jobEl = document.getElementById('jobId');
const settingsBtn = document.getElementById('openSettings');
const settingsModal = document.getElementById('settingsModal');
const settingsForm = document.getElementById('settingsForm');
const settingsClose = document.getElementById('settingsClose');
const settingsCancel = document.getElementById('settingsCancel');
const apiKeyInput = document.getElementById('settingApiKey');
const providerSelect = document.getElementById('settingProvider');
const modelNameInput = document.getElementById('settingModelName');
const maxTokensInput = document.getElementById('settingMaxTokens');
const imageEdgeInput = document.getElementById('settingImageEdge');
const compressCheckbox = document.getElementById('settingCompress');

function log(s){ out.value += s; out.scrollTop = out.scrollHeight; }

function toggleModelFields() {
  const isGPT = providerSelect.value === 'GPT-5 Vision';
  apiKeyInput.disabled = !isGPT;
  modelNameInput.disabled = !isGPT;
}

async function openSettingsModal() {
  const root = rootEl.value.trim();
  if (!root) {
    alert('Choose project root first.');
    return;
  }
  const { config, env } = await window.pipeline.loadSettings(root);
  providerSelect.value = config.provider || 'Mock';
  modelNameInput.value = config.model_name || env.MODEL_NAME || 'gpt-5.1-vision';
  maxTokensInput.value = config.max_tokens || 900;
  imageEdgeInput.value = config.image_max_edge || 1024;
  compressCheckbox.checked = !!config.compress_images;
  apiKeyInput.value = env.AG5_API_KEY || '';
  toggleModelFields();
  settingsModal.classList.add('visible');
}

function closeSettingsModal() {
  settingsModal.classList.remove('visible');
}

settingsBtn.addEventListener('click', openSettingsModal);
settingsClose.addEventListener('click', closeSettingsModal);
settingsCancel.addEventListener('click', closeSettingsModal);
providerSelect.addEventListener('change', toggleModelFields);

settingsForm.addEventListener('submit', async (evt) => {
  evt.preventDefault();
  const root = rootEl.value.trim();
  if (!root) {
    alert('Choose project root first.');
    return;
  }
  const payload = {
    provider: providerSelect.value,
    modelName: modelNameInput.value.trim(),
    maxTokens: maxTokensInput.value,
    imageMaxEdge: imageEdgeInput.value,
    compressImages: compressCheckbox.checked,
    apiKey: apiKeyInput.value.trim()
  };
  await window.pipeline.saveSettings(root, payload);
  const masked = payload.apiKey ? payload.apiKey.replace(/.(?=.{4})/g, '•') : '(none)';
  log(`\n[Settings] Saved (${payload.provider}) apiKey=${masked}.\n`);
  closeSettingsModal();
});

document.getElementById('chooseRoot').addEventListener('click', async () => {
  const root = await window.pipeline.chooseRoot();
  if (!root) return;
  rootEl.value = root;
  log('\n[Root] ' + root + '\n');
});
document.getElementById('runPair').addEventListener('click', async () => {
  const root = rootEl.value.trim();
  if (!root) return alert('Choose project root first.');
  log('\n[Run] Pairing...\n');
  await window.pipeline.runPair(root, log);
  log('\n[Done] Pair\n');
});
document.getElementById('runQueue').addEventListener('click', async () => {
  const root = rootEl.value.trim();
  if (!root) return alert('Choose project root first.');
  log('\n[Run] Queue...\n');
  await window.pipeline.runQueue(root, (s)=>{
    log(s);
    const m = s.match(/batch_\d+_[a-f0-9]{8}/g);
    if (m && m.length) { jobEl.value = m[m.length-1]; }
  });
  log('\n[Done] Queue\n');
});
document.getElementById('runPost').addEventListener('click', async () => {
  const root = rootEl.value.trim();
  const job = jobEl.value.trim();
  if (!root) return alert('Choose project root first.');
  if (!job) return alert('Enter a job id (or run Queue to auto-fill).');
  log(`\n[Run] Post-processing ${job}...\n`);
  await window.pipeline.runPost(root, job, log);
  log('\n[Done] Post\n');
});
