const out = document.getElementById('output');
const rootEl = document.getElementById('rootPath');
const jobEl = document.getElementById('jobId');
function log(s){ out.value += s; out.scrollTop = out.scrollHeight; }

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
