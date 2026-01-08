function ts() { return new Date().toISOString(); }
function log(...args) { console.log(`[${ts()}][renderer]`, ...args); }
function warn(...args) { console.warn(`[${ts()}][renderer]`, ...args); }
function err(...args) { console.error(`[${ts()}][renderer]`, ...args); }

window.addEventListener("error", (e) => {
  err("window error:", e.message, e.filename, e.lineno, e.colno, e.error);
});

window.addEventListener("unhandledrejection", (e) => {
  err("unhandledrejection:", e.reason);
});

log("renderer.js loaded");

// Load three.js + loaders/controls
// NOTE: This version assumes your "fix2" build where renderer.js uses dynamic imports
// (If your current renderer.js uses require(), keep that style instead.)
let THREE;
let OrbitControls;
let STLLoader;

(async function bootstrapThree() {
  try {
    log("Bootstrapping three.js...");
    THREE = await import("../node_modules/three/build/three.module.js");
    ({ OrbitControls } = await import("../node_modules/three/examples/jsm/controls/OrbitControls.js"));
    ({ STLLoader } = await import("../node_modules/three/examples/jsm/loaders/STLLoader.js"));
    log("three.js bootstrapped OK");
    main();
  } catch (e) {
    err("Failed to bootstrap three.js:", e);
  }
})();

function main() {
  (function () {
    const api =
      window.parametereyes || {
        appName: "Parametereyes",
        backendUrl: "http://127.0.0.1:5123",
      };

    log("api =", api);

    document.getElementById("appName").textContent = api.appName;
    document.getElementById("backendUrl").textContent = api.backendUrl;

    const panel = document.getElementById("panel");
    const navButtons = Array.from(document.querySelectorAll(".nav button"));

    function setActive(tab) {
      log("setActive()", tab);
      navButtons.forEach((b) =>
        b.classList.toggle("active", b.dataset.tab === tab)
      );
      renderTab(tab);
    }

    async function renderHome() {
      log("renderHome()");
      panel.innerHTML = `
      <h2>Home</h2>
      <p>Welcome to <b>${api.appName}</b>. This is a dashboard scaffold with a Python backend.</p>
      <div class="row"><span class="pill" id="healthPill">Backend health: (checking...)</span></div>
      <p style="margin-top:14px;">Next steps: build out <b>Edit GXB</b> to decode your custom stream and produce a real STL.</p>
    `;

      try {
        log("GET", `${api.backendUrl}/health`);
        const res = await fetch(`${api.backendUrl}/health`);
        const json = await res.json();
        document.getElementById("healthPill").textContent = `Backend health: ${
          json.status || "unknown"
        }`;
      } catch (e) {
        warn("health check failed:", e);
        document.getElementById("healthPill").textContent =
          "Backend health: offline";
      }
    }

    function renderPlaceholder(title) {
      panel.innerHTML = `
      <h2>${title}</h2>
      <p>This is a placeholder for <b>${title}</b>.</p>
      <p>Wire this up to your real workflow when you're ready.</p>
    `;
    }

    // ---- THREE VIEWER ----
    function createViewer(container) {
      log("createViewer()");
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0b1220);

      const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100000);
      camera.position.set(80, 60, 80);

      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setPixelRatio(window.devicePixelRatio || 1);
      container.innerHTML = "";
      container.appendChild(renderer.domElement);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;

      scene.add(new THREE.AmbientLight(0xffffff, 0.55));
      const dir = new THREE.DirectionalLight(0xffffff, 0.85);
      dir.position.set(120, 140, 90);
      scene.add(dir);

      const grid = new THREE.GridHelper(200, 20, 0x22314a, 0x22314a);
      grid.position.y = -30;
      scene.add(grid);

      let mesh = null;

      function resize() {
        const w = container.clientWidth;
        const h = container.clientHeight;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h, false);
      }

      function frameObject(obj) {
        const box = new THREE.Box3().setFromObject(obj);
        const size = new THREE.Vector3();
        box.getSize(size);
        const center = new THREE.Vector3();
        box.getCenter(center);

        obj.position.sub(center);

        const maxDim = Math.max(size.x, size.y, size.z);
        const dist = maxDim * 1.6;

        camera.position.set(dist, dist * 0.8, dist);
        camera.lookAt(0, 0, 0);
        controls.target.set(0, 0, 0);
        controls.update();
      }

      function setGeometry(geometry) {
        if (mesh) {
          scene.remove(mesh);
          mesh.geometry.dispose();
          mesh.material.dispose();
          mesh = null;
        }

        geometry.computeVertexNormals();

        const material = new THREE.MeshStandardMaterial({
          color: 0x5aa2ff,
          metalness: 0.1,
          roughness: 0.55,
        });

        mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);
        frameObject(mesh);
      }

      let anim = true;
      function loop() {
        if (!anim) return;
        controls.update();
        renderer.render(scene, camera);
        requestAnimationFrame(loop);
      }
      resize();
      loop();

      const ro = new ResizeObserver(() => resize());
      ro.observe(container);

      return {
        loadStlFromUrl: async (url) => {
          log("viewer.loadStlFromUrl()", url);
          const loader = new STLLoader();
          return new Promise((resolve, reject) => {
            loader.load(
              url,
              (geom) => {
                log("STL loaded OK");
                setGeometry(geom);
                resolve(true);
              },
              undefined,
              (e) => {
                err("STL load error:", e);
                reject(e);
              }
            );
          });
        },
        dispose: () => {
          log("viewer.dispose()");
          anim = false;
          ro.disconnect();
          renderer.dispose();
        },
      };
    }

    function escapeHtml(s) {
      return String(s)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function renderEditGxb() {
      log("renderEditGxb()");
      panel.innerHTML = `
      <h2>Edit GXB</h2>
      <p>Select a <code>.gxb</code> file, then click <b>Process</b>. The backend returns JSON info for a parameter panel and an STL to preview.</p>

      <div class="row">
        <input id="gxbFile" type="file" accept=".gxb" />
        <button class="btn" id="processBtn" disabled>Process</button>
        <span class="pill" id="statusPill">Idle</span>
      </div>

      <div class="split">
        <div class="panel-box">
          <div class="kv" id="paramPanel">
            <div class="kv-item">
              <div class="k">Parameters</div>
              <div class="v">Upload a .gxb to populate this panel.</div>
            </div>
          </div>
        </div>

        <div class="viewer" id="viewer"></div>
      </div>

      <pre id="debugOut" style="display:none;"></pre>
    `;

      const fileInput = document.getElementById("gxbFile");
      const processBtn = document.getElementById("processBtn");
      const statusPill = document.getElementById("statusPill");
      const paramPanel = document.getElementById("paramPanel");
      const viewerEl = document.getElementById("viewer");
      const debugOut = document.getElementById("debugOut");

      let file = null;

      log("Creating 3D viewer...");
      let viewer = createViewer(viewerEl);
      log("3D viewer created");

      function setStatus(text) {
        statusPill.textContent = text;
      }

      function showParams(info) {
        const rows = [];
        Object.entries(info || {}).forEach(([k, v]) => {
          const val = Array.isArray(v)
            ? v.join("\n")
            : v == null
            ? ""
            : String(v);
          rows.push(`
          <div class="kv-item">
            <div class="k">${escapeHtml(k)}</div>
            <div class="v"><pre style="margin:0;white-space:pre-wrap;background:transparent;border:0;padding:0;color:inherit;">${escapeHtml(
              val
            )}</pre></div>
          </div>
        `);
        });

        paramPanel.innerHTML = rows.length
          ? rows.join("")
          : `
        <div class="kv-item"><div class="k">Parameters</div><div class="v">(none)</div></div>
      `;
      }

      function showDebug(obj) {
        debugOut.style.display = "block";
        debugOut.textContent = JSON.stringify(obj, null, 2);
      }

      fileInput.addEventListener("change", () => {
        log("file input change");
        file = fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;
        processBtn.disabled = !file;
        setStatus(file ? `Selected: ${file.name}` : "Idle");
        debugOut.style.display = "none";
        debugOut.textContent = "";
      });

      processBtn.addEventListener("click", async () => {
        log("process click");
        if (!file) return;

        setStatus("Processing...");
        processBtn.disabled = true;

        try {
          const fd = new FormData();
          fd.append("file", file);

          log("POST", `${api.backendUrl}/edit-gxb/handle`);
          const res = await fetch(`${api.backendUrl}/edit-gxb/handle`, {
            method: "POST",
            body: fd,
          });

          if (!res.ok)
            throw new Error(
              `Backend error (${res.status}): ${await res.text()}`
            );

          const json = await res.json();
          showDebug(json);
          showParams(json.info);

          const stlUrl = `${api.backendUrl}${json.stl_url}`;
          log("Loading STL from", stlUrl);
          await viewer.loadStlFromUrl(stlUrl);

          setStatus("Done");
        } catch (e) {
          setStatus("Error");
          showParams({ error: e && e.message ? e.message : String(e) });
        } finally {
          processBtn.disabled = false;
        }
      });

      panel._dispose = () => {
        try {
          viewer.dispose();
        } catch (_) {}
        viewer = null;
      };
    }

    function renderTab(tab) {
      log("renderTab()", tab);

      if (panel._dispose) {
        try {
          panel._dispose();
        } catch (_) {}
        panel._dispose = null;
      }

      switch (tab) {
        case "home":
          return renderHome();
        case "edit-gxb":
          return renderEditGxb();
        case "tab-3":
          return renderPlaceholder("Tab 3");
        case "tab-4":
          return renderPlaceholder("Tab 4");
        case "tab-5":
          return renderPlaceholder("Tab 5");
        case "tab-6":
          return renderPlaceholder("Tab 6");
        default:
          return renderHome();
      }
    }

    navButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        log("nav click", btn.dataset.tab);
        setActive(btn.dataset.tab);
      });
    });

    setActive("home");
  })();
}
