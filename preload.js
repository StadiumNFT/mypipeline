const { contextBridge, ipcRenderer } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const DEFAULT_CONFIG = {
  provider: 'Mock',
  model_name: 'gpt-5.1-vision',
  max_tokens: 900,
  compress_images: true,
  image_max_edge: 1024
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
    const [key, value] = line.split('=', 2);
    const trimmedKey = key.trim();
    if (Object.prototype.hasOwnProperty.call(env, trimmedKey)) {
      env[trimmedKey] = value.trim();
    }
  }
  return env;
}

function writeEnv(root, updates) {
  const file = envPath(root);
  let lines = [];
  if (fs.existsSync(file)) {
    lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
  }
  const seen = new Set();
  const out = [];
  for (const line of lines) {
    if (!line || line.trim().startsWith('#') || !line.includes('=')) {
      out.push(line);
      continue;
    }
    const [rawKey] = line.split('=');
    const key = rawKey.trim();
    if (Object.prototype.hasOwnProperty.call(updates, key)) {
      out.push(`${key}=${updates[key] ?? ''}`);
      seen.add(key);
    } else {
      out.push(line);
    }
  }
  for (const [key, value] of Object.entries(updates)) {
    if (!seen.has(key)) {
      out.push(`${key}=${value ?? ''}`);
    }
  }
  fs.writeFileSync(file, out.filter(line => line !== undefined).join('\n') + '\n');
}

function saveConfig(root, payload) {
  const cfg = {
    provider: payload.provider || DEFAULT_CONFIG.provider,
    model_name: payload.modelName || DEFAULT_CONFIG.model_name,
    max_tokens: Number(payload.maxTokens) || DEFAULT_CONFIG.max_tokens,
    compress_images: !!payload.compressImages,
    image_max_edge: Number(payload.imageMaxEdge) || DEFAULT_CONFIG.image_max_edge
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
