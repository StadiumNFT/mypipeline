const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('path');

let win;

function createWindow () {
  win = new BrowserWindow({
    width: 1100,
    height: 720,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,    // must be false for security
      enableRemoteModule: false,
      sandbox: false             // <— this line fixes the “no dialog” issue
    }
  });
  win.loadFile('index.html');
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

ipcMain.handle('choose-root', async () => {
  const result = await dialog.showOpenDialog(win, { properties: ['openDirectory'] });
  if (result.canceled) return null;
  return result.filePaths[0];
});
