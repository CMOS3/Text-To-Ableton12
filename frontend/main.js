const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');

let backendProcess = null;

function startBackend(mainWindow) {
    const pythonExe = path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe');
    backendProcess = spawn(pythonExe, ['-m', 'uvicorn', 'backend.main:app', '--reload', '--port', '8000'], {
        cwd: path.join(__dirname, '..')
    });

    backendProcess.stdout.on('data', (data) => {
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('backend-log', { type: 'info', message: data.toString() });
        }
    });

    backendProcess.stderr.on('data', (data) => {
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('backend-log', { type: 'error', message: data.toString() });
        }
    });

    backendProcess.on('close', (code) => {
        console.log(`Backend process exited with code ${code}`);
    });
}

function createWindow() {
    const win = new BrowserWindow({
        width: 1200,
        height: 800,
        backgroundColor: '#1a1a1a', // Match Ableton's dark theme
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: true
        },
        // Standard window with native controls as requested
    });

    win.loadFile('index.html');
    
    startBackend(win);
    
    // Open DevTools during development if needed
    // win.webContents.openDevTools();
}

app.whenReady().then(() => {
    ipcMain.on('restart-app', () => {
        app.relaunch({ args: process.argv.slice(1) });
        app.quit();
    });

    ipcMain.handle('select-folder', async () => {
        const result = await dialog.showOpenDialog({
            properties: ['openDirectory']
        });
        if (result.canceled) {
            return null;
        }
        return result.filePaths[0];
    });

    ipcMain.handle('deploy-remote-script', async (event, destinationPath) => {
        try {
            const scriptPath = path.join(__dirname, '..', 'remote_script', 'deploy.ps1');
            const command = `powershell.exe -ExecutionPolicy Bypass -File "${scriptPath}" -destination "${destinationPath}"`;
            const output = execSync(command).toString();
            return { success: true, message: output };
        } catch (error) {
            console.error('Deployment error:', error);
            return { success: false, message: error.message };
        }
    });

    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('will-quit', () => {
    if (backendProcess) {
        try {
            execSync(`taskkill /pid ${backendProcess.pid} /T /F`);
        } catch (error) {
            console.error('Failed to kill backend process:', error.message);
        }
    }
});
