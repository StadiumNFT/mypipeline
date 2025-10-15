const { contextBridge, ipcRenderer } = require('electron');
const { spawn } = require('child_process');

function runCmd(cmd, args, cwd, onData) {
  const p = spawn(cmd, args, { cwd, shell: true });
  p.stdout.on('data', d => onData(d.toString()));
  p.stderr.on('data', d => onData(d.toString()));
  return new Promise((resolve) => { p.on('close', code => resolve(code)); });
}

contextBridge.exposeInMainWorld('pipeline', {
  chooseRoot: async () => await ipcRenderer.invoke('choose-root'),
  runPair:  async (root, onData) => await runCmd('python', ['-m','pipeline.run','pair'], root, onData),
  runQueue: async (root, onData) => await runCmd('python', ['-m','pipeline.run','queue','--batch-size','20'], root, onData),
  runPost:  async (root, jobId, onData) => await runCmd('python', ['-m','pipeline.run','post','--job-id', jobId], root, onData),
});
