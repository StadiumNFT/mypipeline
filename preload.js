let contextBridge;
let ipcRenderer;
try {
  ({ contextBridge, ipcRenderer } = require('electron'));
} catch (err) {
  contextBridge = null;
  ipcRenderer = null;
}
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const DEFAULT_CONFIG = {
  provider: 'Mock',
  model_name: 'gpt-5.1-vision',
  max_tokens: 900,
  compress_images: true,
  image_max_edge: 1024,
  per_item_timeout: 45,
  max_failures: 5
};

function configPath(root) {
  return path.join(root, 'pipeline', 'config', 'model.json');
}

function ensureConfig(root) {
  const cfgPath = configPath(root);
  if (!fs.existsSync(cfgPath)) {
    fs.mkdirSync(path.dirname(cfgPath), { recursive: true });
    fs.writeFileSync(cfgPath, JSON.stringify(DEFAULT_CONFIG, null, 2));
    return { ...DEFAULT_CONFIG };
  }
  try {
    const data = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    return { ...DEFAULT_CONFIG, ...data };
  } catch (err) {
    console.warn('Failed to parse model.json, resetting to defaults.', err);
    fs.writeFileSync(cfgPath, JSON.stringify(DEFAULT_CONFIG, null, 2));
    return { ...DEFAULT_CONFIG };
  }
}

function envPath(root) {
  return path.join(root, '.env');
}

function parseEnv(root) {
  const env = {
    AG5_API_KEY: '',
    MODEL_NAME: '',
    TOKEN_LIMIT: '',
    IMAGE_MAX_EDGE: ''
  };
  const file = envPath(root);
  if (!fs.existsSync(file)) {
    return env;
  }
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
  for (const line of lines) {
    if (!line || line.trim().startsWith('#') || !line.includes('=')) continue;
    const idx = line.indexOf('=');
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1);
    if (Object.prototype.hasOwnProperty.call(env, key)) {
      env[key] = value.trim();
    }
  }
  return env;
}

function writeEnv(root, updates) {
  const file = envPath(root);
  const out = [];
  const seen = new Set();
  if (fs.existsSync(file)) {
    const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
    for (const line of lines) {
      if (!line || line.trim().startsWith('#') || !line.includes('=')) {
        out.push(line);
        continue;
      }
      const idx = line.indexOf('=');
      const key = line.slice(0, idx).trim();
      if (seen.has(key)) {
        continue;
      }
      if (Object.prototype.hasOwnProperty.call(updates, key)) {
        const value = updates[key] ?? '';
        out.push(`${key}=${String(value)}`);
        seen.add(key);
      } else {
        const value = line.slice(idx + 1);
        out.push(`${key}=${value}`);
        seen.add(key);
      }
    }
  }
  for (const [key, value] of Object.entries(updates)) {
    if (!seen.has(key)) {
      out.push(`${key}=${String(value ?? '')}`);
    }
  }
  const finalLines = out.filter(line => line !== undefined && line !== null);
  fs.writeFileSync(file, finalLines.join('\n') + '\n');
}

function saveConfig(root, payload) {
  const existing = ensureConfig(root);
  const cfg = {
    ...existing,
    provider: payload.provider || DEFAULT_CONFIG.provider,
    model_name: payload.modelName || existing.model_name || DEFAULT_CONFIG.model_name,
    max_tokens: Number(payload.maxTokens) || existing.max_tokens || DEFAULT_CONFIG.max_tokens,
    compress_images: payload.compressImages !== undefined ? !!payload.compressImages : existing.compress_images,
    image_max_edge: Number(payload.imageMaxEdge) || existing.image_max_edge || DEFAULT_CONFIG.image_max_edge
  };
  const cfgPath = configPath(root);
  fs.mkdirSync(path.dirname(cfgPath), { recursive: true });
  fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2));
  writeEnv(root, {
    AG5_API_KEY: payload.apiKey ?? '',
    MODEL_NAME: cfg.model_name,
    TOKEN_LIMIT: String(cfg.max_tokens),
    IMAGE_MAX_EDGE: String(cfg.image_max_edge)
  });
  return cfg;
}

function runCmd(cmd, args, cwd, onData) {
  const p = spawn(cmd, args, { cwd, shell: true });
  p.stdout.on('data', d => onData(d.toString()));
  p.stderr.on('data', d => onData(d.toString()));
  return new Promise((resolve) => { p.on('close', code => resolve(code)); });
}

if (contextBridge && ipcRenderer) {
  contextBridge.exposeInMainWorld('pipeline', {
    chooseRoot: async () => await ipcRenderer.invoke('choose-root'),
    runPair:  async (root, onData) => await runCmd('python', ['-m','pipeline.run','pair'], root, onData),
    runQueue: async (root, onData) => await runCmd('python', ['-m','pipeline.run','queue','--batch-size','20'], root, onData),
    runPost:  async (root, jobId, onData) => await runCmd('python', ['-m','pipeline.run','post','--job-id', jobId], root, onData),
    loadSettings: async (root) => {
      const config = ensureConfig(root);
      const env = parseEnv(root);
      return { config, env };
    },
    saveSettings: async (root, payload) => {
      return saveConfig(root, payload);
    }
  });
}

module.exports = {
  DEFAULT_CONFIG,
  configPath,
  ensureConfig,
  envPath,
  parseEnv,
  writeEnv,
  saveConfig,
};
