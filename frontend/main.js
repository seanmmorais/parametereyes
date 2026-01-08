const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

const BACKEND_PORT = process.env.PARAMEYES_BACKEND_PORT || "5123";

function ts() {
  const d = new Date();
  return d.toISOString();
}

function log(...args) {
  console.log(`[${ts()}][main]`, ...args);
}

process.on("uncaughtException", (err) => {
  console.error(`[${ts()}][main][uncaughtException]`, err);
});

process.on("unhandledRejection", (reason) => {
  console.error(`[${ts()}][main][unhandledRejection]`, reason);
});

const isDev = !app.isPackaged;
let backendProc = null;

function resolvePython() {
  const v = process.env.PARAMEYES_PYTHON || (process.platform === "win32" ? "python" : "python3");
  log("resolvePython ->", v);
  return v;
}

function startBackend() {
  const py = resolvePython();
  const script = path.join(__dirname, "..", "backend", "server.py");

  log("[backend] starting:", py, script, "PORT=", BACKEND_PORT);

  backendProc = spawn(py, [script], {
    env: { ...process.env, PARAMEYES_BACKEND_PORT: BACKEND_PORT },
    stdio: "inherit",
    windowsHide: true,
  });

  backendProc.on("spawn", () => log("[backend] spawned pid=", backendProc.pid));
  backendProc.on("exit", (code, signal) => {
    log("[backend] exited code=", code, "signal=", signal);
    backendProc = null;
  });
  backendProc.on("error", (e) => log("[backend] error:", e));
}

function stopBackend() {
  if (!backendProc) {
    log("[backend] stopBackend: no process");
    return;
  }
  try {
    log("[backend] killing pid=", backendProc.pid);
    backendProc.kill();
  } catch (e) {
    log("[backend] kill error:", e);
  }
  backendProc = null;
}

function createWindow() {
  log("createWindow()");

  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false,
    webPreferences: {
      nodeIntegration: true,     // for debug-friendly renderer logging/imports
      contextIsolation: false,   // preload writes to window
      preload: path.join(__dirname, "preload.js"),
    },
  });

  win.on("ready-to-show", () => log("window ready-to-show"));
  win.on("closed", () => log("window closed"));
  win.webContents.on("did-finish-load", () => log("webContents did-finish-load"));
  win.webContents.on("did-fail-load", (e, code, desc, url) => log("did-fail-load", code, desc, url));
  win.webContents.on("console-message", (_e, level, message) => {
    // level: 0=log 1=warn 2=error
    log("[renderer console]", level, message);
  });

  win.maximize();
  log("window maximize() called");
  win.loadFile(path.join(__dirname, "renderer", "index.html"));

  win.once("ready-to-show", () => win.show());

  if (process.env.PARAMEYES_DEVTOOLS === "1") {
    log("Opening DevTools because PARAMEYES_DEVTOOLS=1");
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    log("DevTools disabled (set PARAMEYES_DEVTOOLS=1 to enable)");
  }
}

app.whenReady().then(() => {
  log("app.whenReady()");
  if (process.env.PARAMEYES_NO_BACKEND !== "1") {
    log("Starting backend (PARAMEYES_NO_BACKEND != 1)");
    startBackend();
  } else {
    log("Not starting backend (PARAMEYES_NO_BACKEND=1)");
  }

  createWindow();

  app.on("activate", () => {
    log("app activate");
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("before-quit", () => {
  log("before-quit");
  stopBackend();
});

app.on("window-all-closed", () => {
  log("window-all-closed");
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});
