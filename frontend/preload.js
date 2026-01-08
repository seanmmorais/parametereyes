function ts() {
  const d = new Date();
  return d.toISOString();
}
function log(...args) {
  console.log(`[${ts()}][preload]`, ...args);
}

try {
  const port = process.env.PARAMEYES_BACKEND_PORT || "5123";
  log("Initializing preload. PORT=", port);

  window.parametereyes = {
    appName: "Parametereyes",
    backendUrl: `http://127.0.0.1:${port}`,
  };

  log("window.parametereyes set:", window.parametereyes);
} catch (e) {
  console.error(`[${ts()}][preload][error]`, e);
}
