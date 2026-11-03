/**
 * Mazic — Client Web Canvas 2.5D 0x72, Vision Directionnelle & Raycasting à Oubli Progressif
 */

(function () {
  "use strict";

  const SCALE = 3; // 16x16 -> 48x48 px écran
  const TILE_SIZE = 16;
  const SCALED_TILE = TILE_SIZE * SCALE; // 48 px

  // Types de tuiles
  const VOID = 0;
  const FLOOR = 1;
  const WALL = 2;
  const DOOR_CLOSED = 3;
  const DOOR_OPEN = 4;

  // Gestionnaire d'Assets d'images 0x72_DungeonTilesetII
  class AssetLoader {
    constructor() {
      this.cache = new Map();
      this.pending = new Map();
      this.failed = new Set();
    }

    getImage(name) {
      if (!name) return null;
      if (this.failed.has(name)) {
        return null;
      }
      if (this.cache.has(name)) {
        return this.cache.get(name);
      }
      if (this.pending.has(name)) {
        return null;
      }

      const img = new Image();
      img.src = `/assets/frames/${name}.png`;
      this.pending.set(name, img);

      img.onload = () => {
        this.cache.set(name, img);
        this.pending.delete(name);
      };
      img.onerror = () => {
        this.pending.delete(name);
        this.failed.add(name);
      };
      return null;
    }

    get(name) {
      return this.getImage(name);
    }

    // Résolution de frame animée automatique
    getAnimFrame(baseName, animType, frameCount, fps = 8) {
      const frameIdx = Math.floor((performance.now() / 1000) * fps) % frameCount;
      const fullName = `${baseName}_${animType}_anim_f${frameIdx}`;
      return this.getImage(fullName) || this.getImage(`${baseName}_idle_anim_f0`);
    }
  }

  // Moteur Principal de Jeu
  class MazicGame {
    constructor() {
      this.canvas = document.getElementById("game-canvas");
      this.ctx = this.canvas.getContext("2d");
      this.minimapCanvas = document.getElementById("minimap-canvas");
      this.minimapCtx = this.minimapCanvas ? this.minimapCanvas.getContext("2d") : null;

      this.assets = new AssetLoader();
      this.voice = new VoiceProximityEngine();

      this.ws = null;
      this.myId = null;
      this.tunnelUrl = null;
      this.selectedSkin = "wizzard_m";

      // Donjon et Grille
      this.dungeon = null;
      this.grid = null; // number[][]
      this.tiles = null; // { [ty]: { [tx]: { fl, wb, wt, wl, wr, pr } } }
      this.width = 56;
      this.height = 56;

      // État du monde répliqué
      this.players = {};
      this.monsters = [];
      this.projectiles = [];
      this.crystals = [];
      this.fountains = [];
      this.portal = null;
      this.gameStatus = "RUNNING";
      this.events = [];

      // Vision Directionnelle & Oubli Progressif (last_seen)
      this.tileLastSeen = []; // [ty][tx] -> timestamp (ms)
      this.entityLastSeen = new Map(); // entityId -> timestamp (ms)
      this.visibleTilesSet = new Set(); // clés "tx,ty" vues à la frame courante

      // Entrées utilisateur
      this.keys = {};
      this.mousePos = { x: 0, y: 0 };
      this.worldMouse = { x: 0, y: 0 };
      this.aimAngle = 0.0;
      this.mouseLeftDown = false;
      this.spellCooldowns = { 1: 0, 2: 0, 3: 0, 4: 0 };

      // Caméra
      this.camX = 0;
      this.camY = 0;

      // Visualisation d'ondes sonores (radar de pas / micro)
      this.soundWaves = []; // { x, y, radius, maxRadius, color, alpha }

      this.initEvents();
      this.initVoiceUI();
      this.connectWebSocket();
      this.startLoop();
    }

    initEvents() {
      window.addEventListener("resize", () => this.resizeCanvas());
      this.resizeCanvas();

      window.addEventListener("keydown", (e) => {
        this.keys[e.key.toLowerCase()] = true;
        this.keys[e.code] = true;

        if (e.key === "1") this.triggerSpell(1);
        if (e.key === "2") this.triggerSpell(2);
        if (e.key === "3") this.triggerSpell(3);
        if (e.key === "4") this.triggerSpell(4);
        if (e.key.toLowerCase() === "e") this.triggerInteract();
      });

      window.addEventListener("keyup", (e) => {
        this.keys[e.key.toLowerCase()] = false;
        this.keys[e.code] = false;
      });

      this.canvas.addEventListener("mousemove", (e) => {
        const rect = this.canvas.getBoundingClientRect();
        this.mousePos.x = e.clientX - rect.left;
        this.mousePos.y = e.clientY - rect.top;

        // Conversion en coordonnées monde
        this.worldMouse.x = (this.mousePos.x - this.canvas.width / 2) / SCALE + this.camX;
        this.worldMouse.y = (this.mousePos.y - this.canvas.height / 2) / SCALE + this.camY;

        const me = this.getMe();
        if (me) {
          this.aimAngle = Math.atan2(this.worldMouse.y - me.y, this.worldMouse.x - me.x);
        }
      });

      this.canvas.addEventListener("mousedown", (e) => {
        if (e.button === 0) {
          this.mouseLeftDown = true;
          this.triggerAttack();
        }
      });

      this.canvas.addEventListener("mouseup", (e) => {
        if (e.button === 0) {
          this.mouseLeftDown = false;
        }
      });

      // Empêcher le menu contextuel sur le canvas
      this.canvas.addEventListener("contextmenu", (e) => e.preventDefault());
    }

    resizeCanvas() {
      const container = this.canvas.parentElement;
      if (!container) return;
      this.canvas.width = container.clientWidth;
      this.canvas.height = container.clientHeight;
      this.ctx.imageSmoothingEnabled = false;
    }

    initVoiceUI() {
      const micBtn = document.getElementById("btn-mic");
      const vuFill = document.getElementById("vu-fill");
      const vuStatus = document.getElementById("vu-status");
      const testLoopBtn = document.getElementById("btn-voice-test");
      const transformTestBtn = document.getElementById("btn-transform-test");
      const botTestBtn = document.getElementById("btn-bot-test");
      const resetBtn = document.getElementById("btn-reset-game");
      const copyLinkBtn = document.getElementById("btn-copy-link");
      const skinSelect = document.getElementById("skin-select");

      if (micBtn) {
        micBtn.addEventListener("click", async () => {
          this.voice.ensureAudioContext();
          if (this.voice.isMicActive) {
            this.voice.stopMicrophone();
            micBtn.classList.remove("active");
            micBtn.textContent = "🎤 Activer Micro Proximité";
          } else {
            const ok = await this.voice.startMicrophone();
            if (ok) {
              micBtn.classList.add("active");
              micBtn.textContent = "🔴 Micro Actif (Émission)";
            }
          }
        });
      }

      this.voice.onRmsUpdate = (rms, isLoud) => {
        if (vuFill) {
          vuFill.style.width = Math.min(100, Math.round(rms * 100 * 2.5)) + "%";
          if (rms > 0.06) {
            vuFill.style.background = "#ef4444";
          } else if (rms > 0.02) {
            vuFill.style.background = "#f59e0b";
          } else {
            vuFill.style.background = "#10b981";
          }
        }
        if (vuStatus) {
          if (rms > 0.06) {
            vuStatus.textContent = "⚠️ BRUIT FORT — Les monstres vous entendent !";
            vuStatus.style.color = "#ef4444";
          } else if (rms > 0.02) {
            vuStatus.textContent = "Murmure détecté";
            vuStatus.style.color = "#f59e0b";
          } else {
            vuStatus.textContent = "Silence absolu";
            vuStatus.style.color = "#94a3b8";
          }
        }
      };

      if (testLoopBtn) {
        testLoopBtn.addEventListener("click", () => {
          this.voice.ensureAudioContext();
          const active = this.voice.toggleSelfTestMode();
          if (active) {
            testLoopBtn.classList.add("active");
            testLoopBtn.textContent = "🔊 Test Monstre ACTIF (Écouteurs !)";
          } else {
            testLoopBtn.classList.remove("active");
            testLoopBtn.textContent = "🔊 Tester ma Voix de Monstre";
          }
        });
      }

      if (transformTestBtn) {
        transformTestBtn.addEventListener("click", () => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: "force_transform" }));
          }
        });
      }

      if (botTestBtn) {
        botTestBtn.addEventListener("click", () => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: "spawn_bot_ally" }));
          }
        });
      }

      if (resetBtn) {
        resetBtn.addEventListener("click", () => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: "reset_game" }));
          }
        });
      }

      if (copyLinkBtn) {
        copyLinkBtn.addEventListener("click", () => {
          const url = this.tunnelUrl || window.location.origin;
          navigator.clipboard.writeText(url).then(() => {
            copyLinkBtn.textContent = "✅ Lien Copié !";
            setTimeout(() => {
              copyLinkBtn.textContent = "🔗 Inviter des Amis";
            }, 2500);
          });
        });
      }

      if (skinSelect) {
        skinSelect.addEventListener("change", (e) => {
          this.selectedSkin = e.target.value;
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
              type: "join",
              name: "Joueur_" + (this.myId ? this.myId.substring(0, 4) : "1"),
              skin: this.selectedSkin,
            }));
          }
        });
      }
    }

    connectWebSocket() {
      const loc = window.location;
      const proto = loc.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${proto}//${loc.host}/ws/main`;

      const statusBadge = document.getElementById("connection-status");
      if (statusBadge) {
        statusBadge.textContent = "Connexion...";
        statusBadge.style.color = "#f59e0b";
      }

      this.ws = new WebSocket(wsUrl);
      this.voice.setWebSocket(this.ws);

      this.ws.onopen = () => {
        if (statusBadge) {
          statusBadge.textContent = "Connecté";
          statusBadge.style.color = "#10b981";
        }
        this.ws.send(JSON.stringify({
          type: "join",
          name: "Joueur_" + Math.floor(Math.random() * 900 + 100),
          skin: this.selectedSkin,
        }));
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleServerMessage(data);
        } catch (err) {
          console.error("[WS] Erreur parsing message:", err);
        }
      };

      this.ws.onclose = () => {
        if (statusBadge) {
          statusBadge.textContent = "Déconnecté (Reconnexion...)";
          statusBadge.style.color = "#ef4444";
        }
        setTimeout(() => this.connectWebSocket(), 2000);
      };

      this.ws.onerror = (err) => {
        console.error("[WS] Erreur socket:", err);
      };
    }

    handleServerMessage(data) {
      if (data.type === "init") {
        this.myId = data.player_id;
        this.tunnelUrl = data.tunnel_url;
        this.initDungeon(data.dungeon);
      } else if (data.type === "state") {
        this.updateState(data.state);
      } else if (data.type === "voice_frame") {
        const speaker = this.players[data.from_id];
        const me = this.getMe();
        if (data.from_id !== this.myId) {
          this.voice.handleVoiceFrame(data.from_id, data.pcm_b64, me, speaker, this.grid);
          // Onde sonore visuelle autour de celui qui parle
          if (speaker) {
            this.triggerSoundWave(speaker.x, speaker.y, 45, speaker.is_monster ? "#ef4444" : "#06b6d4");
          }
        }
      }
    }

    initDungeon(dungeonData) {
      this.dungeon = dungeonData;
      this.width = dungeonData.width || 56;
      this.height = dungeonData.height || 56;
      this.grid = dungeonData.grid;
      this.tiles = dungeonData.tiles;

      // Initialiser la matrice de mémoire visuelle
      this.tileLastSeen = [];
      for (let y = 0; y < this.height; y++) {
        const row = new Float64Array(this.width);
        row.fill(-Infinity);
        this.tileLastSeen.push(row);
      }
      this.entityLastSeen.clear();
    }

    updateState(state) {
      if (!state) return;

      if (Array.isArray(state.players)) {
        this.players = Object.fromEntries(state.players.map((p) => [p.id, p]));
      } else {
        this.players = state.players || {};
      }
      this.monsters = state.monsters || [];
      this.projectiles = state.projectiles || [];
      this.crystals = state.crystals || [];
      this.fountains = state.fountains || [];
      this.portal = state.portal || null;
      this.gameStatus = state.game_status || state.status || "RUNNING";

      // Mises à jour de tuiles dynamiques (sort Brise-Mur, porte ouverte...)
      const tileUpdates = state.tile_updates || state.pending_tile_updates;
      if (tileUpdates && Array.isArray(tileUpdates)) {
        for (const up of tileUpdates) {
          const { tx, ty, tile } = up;
          if (this.tiles && this.tiles[ty]) {
            this.tiles[ty][tx] = tile;
          }
          if (this.grid && this.grid[ty]) {
            if (up.cell_value !== undefined) {
              this.grid[ty][tx] = up.cell_value;
            } else if (up.tile && up.tile.t !== undefined) {
              this.grid[ty][tx] = up.tile.t;
            }
          }
        }
      }

      // Événements sonores et de combat
      if (state.events && Array.isArray(state.events)) {
        for (const ev of state.events) {
          this.handleGameEvent(ev);
        }
      }

      this.updateHUD();
    }

    handleGameEvent(ev) {
      const ex = ev.x !== undefined ? ev.x : (ev.tx !== undefined ? ev.tx * 16 + 8 : null);
      const ey = ev.y !== undefined ? ev.y : (ev.ty !== undefined ? ev.ty * 16 + 8 : null);
      if (ex === null || ey === null) return;

      if (ev.type === "hit") {
        this.triggerSoundWave(ex, ey, 35, "#ef4444");
      } else if (ev.type === "door" || ev.type === "door_open" || ev.type === "door_close") {
        this.triggerSoundWave(ex, ey, 50, "#f59e0b");
      } else if (ev.type === "spell" || ev.type === "spell_cast") {
        this.triggerSoundWave(ex, ey, 60, "#8b5cf6");
      }
    }

    triggerSoundWave(x, y, maxRadius, color) {
      this.soundWaves.push({
        x: x,
        y: y,
        radius: 4,
        maxRadius: maxRadius,
        color: color || "#38bdf8",
        alpha: 1.0,
      });
    }

    getMe() {
      return this.players[this.myId] || null;
    }

    triggerAttack() {
      this.sendInput({ attack: true });
    }

    triggerSpell(slot) {
      this.sendInput({ spell: slot });
    }

    triggerInteract() {
      this.sendInput({ interact: true });
    }

    sendInput(extra = {}) {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

      let vx = 0;
      let vy = 0;
      if (this.keys["z"] || this.keys["w"] || this.keys["arrowup"]) vy -= 1;
      if (this.keys["s"] || this.keys["arrowdown"]) vy += 1;
      if (this.keys["q"] || this.keys["a"] || this.keys["arrowleft"]) vx -= 1;
      if (this.keys["d"] || this.keys["arrowright"]) vx += 1;

      // Normalisation du vecteur de marche
      if (vx !== 0 && vy !== 0) {
        const inv = 1 / Math.SQRT2;
        vx *= inv;
        vy *= inv;
      }

      const sneak = !!(this.keys["shift"] || this.keys["shiftleft"] || this.keys["shiftright"]);

      const payload = {
        type: "input",
        vx: vx,
        vy: vy,
        aim_angle: this.aimAngle,
        attack: !!(extra.attack || this.mouseLeftDown),
        spell: extra.spell || 0,
        interact: !!extra.interact,
        sneak: sneak,
        mic_rms: this.voice.currentRms || 0.0,
      };

      this.ws.send(JSON.stringify(payload));
    }

    // --- Moteur de Vision Directionnelle & Raycasting à Oubli Progressif ---
    updateVision(now) {
      const me = this.getMe();
      if (!me || !this.grid) return;

      this.visibleTilesSet.clear();

      const isMonster = !!me.is_monster;
      const hasArcaneSight = Boolean(me.arcane_sight_active || (me.arcane_sight_until && me.arcane_sight_until > now / 1000));

      // Paramètres du cône
      const fovAngle = isMonster ? (120 * Math.PI) / 180 : (78 * Math.PI) / 180;
      const maxDist = hasArcaneSight ? 14 * 16 : isMonster ? 12 * 16 : 9.5 * 16;
      const numRays = 160;
      const halfFov = fovAngle / 2;

      // 1. Cône de lampe torche orienté vers la souris
      for (let i = 0; i < numRays; i++) {
        const rayAngle = me.aim_angle - halfFov + (i / (numRays - 1)) * fovAngle;
        const cos = Math.cos(rayAngle);
        const sin = Math.sin(rayAngle);

        for (let dist = 4; dist <= maxDist; dist += 2) {
          const rx = me.x + cos * dist;
          const ry = me.y + sin * dist;
          const tx = Math.floor(rx / 16);
          const ty = Math.floor(ry / 16);

          if (tx < 0 || tx >= this.width || ty < 0 || ty >= this.height) break;

          this.tileLastSeen[ty][tx] = now;
          this.visibleTilesSet.add(`${tx},${ty}`);

          const cell = this.grid[ty][tx];
          // Mur ou porte fermée bloque la lumière
          if (cell === WALL || cell === DOOR_CLOSED) {
            break;
          }
        }
      }

      // 2. Halo corporel à 360° (pour voir ses pieds et les murs immédiats)
      const haloDist = isMonster ? 4.5 * 16 : 1.6 * 16;
      const haloRays = 48;
      for (let i = 0; i < haloRays; i++) {
        const ang = (i / haloRays) * Math.PI * 2;
        const cos = Math.cos(ang);
        const sin = Math.sin(ang);

        for (let dist = 2; dist <= haloDist; dist += 2) {
          const rx = me.x + cos * dist;
          const ry = me.y + sin * dist;
          const tx = Math.floor(rx / 16);
          const ty = Math.floor(ry / 16);

          if (tx < 0 || tx >= this.width || ty < 0 || ty >= this.height) break;

          this.tileLastSeen[ty][tx] = now;
          this.visibleTilesSet.add(`${tx},${ty}`);

          const cell = this.grid[ty][tx];
          if (cell === WALL || cell === DOOR_CLOSED) {
            break;
          }
        }
      }

      // 3. Détection des entités visibles (avec ligne de vue directe libre)
      const portalList = [];
      if (this.portal) {
        if (!this.portal.id) this.portal.id = "portal_main";
        portalList.push(this.portal);
      }

      const fountainsList = this.fountains.map((f, idx) => {
        if (!f.id) f.id = "fountain_" + idx;
        return f;
      });

      const projectilesList = this.projectiles.map((p, idx) => {
        if (!p.id) p.id = "proj_" + idx;
        return p;
      });

      const allEntities = [
        ...Object.values(this.players),
        ...this.monsters,
        ...this.crystals,
        ...fountainsList,
        ...projectilesList,
        ...portalList,
      ];

      for (const ent of allEntities) {
        if (!ent) continue;
        const etx = Math.floor(ent.x / 16);
        const ety = Math.floor(ent.y / 16);

        if (this.visibleTilesSet.has(`${etx},${ety}`)) {
          this.entityLastSeen.set(ent.id, now);
        }
      }
    }

    // --- Boucle de Rendu & Logique ---
    startLoop() {
      let lastInputSend = 0;

      const loop = (timestamp) => {
        // Envoi régulier des entrées à ~30 Hz
        if (timestamp - lastInputSend > 33) {
          this.sendInput();
          lastInputSend = timestamp;
        }

        this.updateCamera();
        this.updateVision(timestamp);
        this.updateSoundWaves();
        this.render(timestamp);

        requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    }

    updateCamera() {
      const me = this.getMe();
      if (me) {
        // Suivi fluide de la caméra
        this.camX += (me.x - this.camX) * 0.15;
        this.camY += (me.y - this.camY) * 0.15;
      }
    }

    updateSoundWaves() {
      for (let i = this.soundWaves.length - 1; i >= 0; i--) {
        const sw = this.soundWaves[i];
        sw.radius += 1.8;
        sw.alpha = Math.max(0, 1.0 - sw.radius / sw.maxRadius);
        if (sw.radius >= sw.maxRadius) {
          this.soundWaves.splice(i, 1);
        }
      }
    }

    render(now) {
      const ctx = this.ctx;
      const w = this.canvas.width;
      const h = this.canvas.height;

      // 1. Fond noir absolu
      ctx.fillStyle = "#050508";
      ctx.fillRect(0, 0, w, h);

      if (!this.dungeon || !this.tiles) {
        ctx.fillStyle = "#94a3b8";
        ctx.font = "16px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Chargement du labyrinthe d'Arcane...", w / 2, h / 2);
        return;
      }

      ctx.save();
      // Centrage de la caméra
      ctx.translate(Math.floor(w / 2), Math.floor(h / 2));
      ctx.scale(SCALE, SCALE);
      ctx.translate(-Math.floor(this.camX), -Math.floor(this.camY));

      // Calcul des tuiles visibles à l'écran (Frustum Culling)
      const minTx = Math.max(0, Math.floor((this.camX - w / (2 * SCALE)) / 16) - 1);
      const maxTx = Math.min(this.width - 1, Math.ceil((this.camX + w / (2 * SCALE)) / 16) + 1);
      const minTy = Math.max(0, Math.floor((this.camY - h / (2 * SCALE)) / 16) - 2);
      const maxTy = Math.min(this.height - 1, Math.ceil((this.camY + h / (2 * SCALE)) / 16) + 2);

      // --- PASSE 1 : Sols & Bases de Murs (wb) ---
      for (let ty = minTy; ty <= maxTy; ty++) {
        for (let tx = minTx; tx <= maxTx; tx++) {
          const lastSeen = this.tileLastSeen[ty] ? this.tileLastSeen[ty][tx] : -Infinity;
          const elapsed = now - lastSeen;

          // Oubli progressif en 6.0 secondes
          let alpha = 0.0;
          if (this.visibleTilesSet.has(`${tx},${ty}`)) {
            alpha = 1.0;
          } else if (elapsed < 6000) {
            alpha = Math.max(0, 1.0 - elapsed / 6000.0) * 0.75;
          }

          if (alpha <= 0.01) continue;

          ctx.globalAlpha = alpha;
          const tile = this.tiles[ty] ? this.tiles[ty][tx] : null;
          if (!tile) continue;

          const px = tx * 16;
          const py = ty * 16;

          // Sol (fl)
          if (tile.fl) {
            const img = this.assets.getImage(tile.fl);
            if (img) ctx.drawImage(img, px, py);
          }

          // Décoration au sol (pr)
          if (tile.pr && tile.pr !== "column") {
            const img = this.assets.getImage(tile.pr);
            if (img) ctx.drawImage(img, px, py);
          }

          // Base de mur ou porte (wb)
          if (tile.wb) {
            const img = this.assets.getImage(tile.wb);
            if (img) ctx.drawImage(img, px, py);
          }

          // Rebords latéraux (wl / wr)
          if (tile.wl) {
            const img = this.assets.getImage(tile.wl);
            if (img) ctx.drawImage(img, px, py);
          }
          if (tile.wr) {
            const img = this.assets.getImage(tile.wr);
            if (img) ctx.drawImage(img, px, py);
          }
        }
      }

      // --- PASSE 2 : Entités triées par Y (Y-sorting) ---
      const renderList = [];

      // Portail
      if (this.portal) {
        if (!this.portal.id) this.portal.id = "portal_main";
        renderList.push({
          type: "portal",
          y: this.portal.y,
          ent: this.portal,
        });
      }

      // Cristaux d'Arcane
      for (const cr of this.crystals) {
        if (!cr.collected) {
          renderList.push({
            type: "crystal",
            y: cr.y,
            ent: cr,
          });
        }
      }

      // Fontaines runiques
      this.fountains.forEach((f, idx) => {
        if (!f.id) f.id = "fountain_" + idx;
        renderList.push({
          type: "fountain",
          y: f.y,
          ent: f,
        });
      });

      // Projectiles
      this.projectiles.forEach((p, idx) => {
        if (!p.id) p.id = "proj_" + idx;
        renderList.push({
          type: "projectile",
          y: p.y,
          ent: p,
        });
      });

      // Monstres IA
      for (const m of this.monsters) {
        renderList.push({
          type: "monster",
          y: m.y,
          ent: m,
        });
      }

      // Joueurs
      for (const pl of Object.values(this.players)) {
        renderList.push({
          type: "player",
          y: pl.y,
          ent: pl,
        });
      }

      // Tri par Y pour perspective 2.5D
      renderList.sort((a, b) => a.y - b.y);

      for (const item of renderList) {
        this.renderEntity(ctx, item, now);
      }

      // --- PASSE 3 : Rebords supérieurs de murs 2.5D (wt) en Premier Plan ---
      // Couvre la tête des personnages passant derrière un mur au Sud !
      for (let ty = minTy; ty <= maxTy; ty++) {
        for (let tx = minTx; tx <= maxTx; tx++) {
          const lastSeen = this.tileLastSeen[ty] ? this.tileLastSeen[ty][tx] : -Infinity;
          const elapsed = now - lastSeen;

          let alpha = 0.0;
          if (this.visibleTilesSet.has(`${tx},${ty}`)) {
            alpha = 1.0;
          } else if (elapsed < 6000) {
            alpha = Math.max(0, 1.0 - elapsed / 6000.0) * 0.75;
          }

          if (alpha <= 0.01) continue;

          const tile = this.tiles[ty] ? this.tiles[ty][tx] : null;
          if (tile && tile.wt) {
            ctx.globalAlpha = alpha;
            const img = this.assets.getImage(tile.wt);
            if (img) {
              // wt est ancré au sommet du mur (px, py)
              ctx.drawImage(img, tx * 16, ty * 16);
            }
          }
        }
      }

      // --- PASSE 4 : Ondes sonores & Éclairage d'ambiance ---
      this.renderSoundWaves(ctx);

      ctx.restore();

      // Dessin de la minimap
      this.renderMinimap();
    }

    renderEntity(ctx, item, now) {
      const { type, ent } = item;
      const lastSeen = this.entityLastSeen.get(ent.id) || -Infinity;
      const elapsed = now - lastSeen;
      const etx = Math.floor(ent.x / 16);
      const ety = Math.floor(ent.y / 16);
      const inSight = this.visibleTilesSet.has(`${etx},${ety}`);

      // Les monstres et joueurs s'effacent en 1.2s hors de vue
      let alpha = inSight ? 1.0 : Math.max(0, 1.0 - elapsed / 1200.0);

      // Si c'est moi-même, je suis toujours visible
      if (type === "player" && ent.id === this.myId) {
        alpha = 1.0;
      }

      if (alpha <= 0.01) return;
      ctx.globalAlpha = alpha;

      const px = Math.floor(ent.x);
      const py = Math.floor(ent.y);

      if (type === "player") {
        this.renderPlayer(ctx, ent, px, py);
      } else if (type === "monster") {
        this.renderMonster(ctx, ent, px, py);
      } else if (type === "crystal") {
        const img = this.assets.getImage("flask_big_blue");
        if (img) {
          ctx.drawImage(img, px - 8, py - 12);
        }
      } else if (type === "fountain") {
        const frame = Math.floor((performance.now() / 200) % 3);
        const top = this.assets.getImage(`wall_fountain_mid_red_anim_f${frame}`);
        const basin = this.assets.getImage(`wall_fountain_basin_red_anim_f${frame}`);
        if (top) ctx.drawImage(top, px - 8, py - 16);
        if (basin) ctx.drawImage(basin, px - 8, py);
      } else if (type === "projectile") {
        const pImg = this.assets.getImage(ent.skin || "FB001");
        if (pImg) {
          ctx.save();
          ctx.translate(px, py);
          ctx.rotate(ent.angle || 0);
          ctx.drawImage(pImg, -8, -8);
          ctx.restore();
        }
      } else if (type === "portal") {
        const ladder = this.assets.getImage("floor_ladder");
        if (ladder) ctx.drawImage(ladder, px - 8, py - 8);
      }
    }

    renderPlayer(ctx, p, px, py) {
      const isMe = p.id === this.myId;
      const isMonster = !!p.is_monster;
      const skin = isMonster ? "big_demon" : (p.skin || "wizzard_m");
      const anim = p.anim || (Math.hypot(p.vx || 0, p.vy || 0) > 0.1 ? "run" : "idle");

      const img = this.assets.getAnimFrame(skin, anim, 4, 8);

      ctx.save();
      ctx.translate(px, py);

      // Orientation vers la gauche
      if (p.facing_left) {
        ctx.scale(-1, 1);
      }

      if (img) {
        // Ancrage aux pieds : le sprite fait 16x28 ou 16x20
        ctx.drawImage(img, -8, -24);
      } else {
        // Fallback géométrique propre en attendant le chargement
        ctx.fillStyle = isMonster ? "#ef4444" : "#3b82f6";
        ctx.fillRect(-6, -18, 12, 18);
      }
      ctx.restore();

      // Barre de vie au-dessus de la tête
      if (p.hp !== undefined) {
        const barW = 20;
        const barH = 3;
        const hpPct = Math.max(0, Math.min(1, p.hp / (p.max_hp || 100)));

        ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
        ctx.fillRect(px - barW / 2, py - 29, barW, barH);
        ctx.fillStyle = isMonster ? "#ef4444" : "#10b981";
        ctx.fillRect(px - barW / 2, py - 29, barW * hpPct, barH);
      }

      // Nom du joueur
      ctx.font = "8px sans-serif";
      ctx.textAlign = "center";
      ctx.fillStyle = isMe ? "#f59e0b" : isMonster ? "#fca5a5" : "#e2e8f0";
      ctx.fillText(p.name || "Aventurier", px, py - 32);

      // Indicateur visuel de visée (lampe torche)
      if (isMe) {
        ctx.save();
        ctx.strokeStyle = isMonster ? "rgba(239, 68, 68, 0.35)" : "rgba(251, 191, 36, 0.35)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(px, py - 12);
        ctx.lineTo(px + Math.cos(this.aimAngle) * 32, py - 12 + Math.sin(this.aimAngle) * 32);
        ctx.stroke();
        ctx.restore();
      }
    }

    renderMonster(ctx, m, px, py) {
      const skin = m.skin || "chort";
      const anim = m.anim || "idle";
      const img = this.assets.getAnimFrame(skin, anim, 4, 8);

      ctx.save();
      ctx.translate(px, py);
      if (m.facing_left) {
        ctx.scale(-1, 1);
      }
      if (img) {
        ctx.drawImage(img, -8, -20);
      } else {
        ctx.fillStyle = "#dc2626";
        ctx.fillRect(-6, -16, 12, 16);
      }
      ctx.restore();

      // Barre de vie du monstre
      if (m.hp !== undefined) {
        const barW = 16;
        const barH = 2;
        const hpPct = Math.max(0, Math.min(1, m.hp / (m.max_hp || 60)));
        ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
        ctx.fillRect(px - barW / 2, py - 24, barW, barH);
        ctx.fillStyle = "#ef4444";
        ctx.fillRect(px - barW / 2, py - 24, barW * hpPct, barH);
      }
    }

    renderSoundWaves(ctx) {
      for (const sw of this.soundWaves) {
        ctx.save();
        ctx.strokeStyle = sw.color;
        ctx.globalAlpha = sw.alpha;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(sw.x, sw.y, sw.radius, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }
    }

    renderMinimap() {
      if (!this.minimapCtx || !this.grid) return;
      const mctx = this.minimapCtx;
      const mw = this.minimapCanvas.width;
      const mh = this.minimapCanvas.height;

      mctx.fillStyle = "#07090e";
      mctx.fillRect(0, 0, mw, mh);

      const cellW = mw / this.width;
      const cellH = mh / this.height;

      for (let y = 0; y < this.height; y++) {
        for (let tx = 0; tx < this.width; tx++) {
          const lastSeen = this.tileLastSeen[y] ? this.tileLastSeen[y][tx] : -Infinity;
          if (lastSeen === -Infinity) continue; // Inexploré

          const cell = this.grid[y][tx];
          if (cell === WALL) {
            mctx.fillStyle = "#334155";
            mctx.fillRect(tx * cellW, y * cellH, cellW, cellH);
          } else if (cell === FLOOR || cell === DOOR_OPEN) {
            mctx.fillStyle = "#0f172a";
            mctx.fillRect(tx * cellW, y * cellH, cellW, cellH);
          } else if (cell === DOOR_CLOSED) {
            mctx.fillStyle = "#f59e0b";
            mctx.fillRect(tx * cellW, y * cellH, cellW, cellH);
          }
        }
      }

      // Afficher les positions des joueurs explorés
      const me = this.getMe();
      if (me) {
        mctx.fillStyle = me.is_monster ? "#ef4444" : "#10b981";
        mctx.beginPath();
        mctx.arc((me.x / 16) * cellW, (me.y / 16) * cellH, 2.5, 0, Math.PI * 2);
        mctx.fill();
      }
    }

    updateHUD() {
      const me = this.getMe();
      if (!me) return;

      const hpFill = document.getElementById("hp-bar-fill");
      const hpText = document.getElementById("hp-val");
      const manaFill = document.getElementById("mana-bar-fill");
      const manaText = document.getElementById("mana-val");
      const crystalCount = document.getElementById("crystal-count");
      const statusBadge = document.getElementById("role-badge");
      const voiceModeText = document.getElementById("voice-mode-text");

      if (hpFill && hpText) {
        const hp = Math.max(0, Math.round(me.hp || 0));
        const maxHp = Math.round(me.max_hp || 100);
        hpText.textContent = `${hp} / ${maxHp}`;
        hpFill.style.width = `${Math.min(100, (hp / maxHp) * 100)}%`;
      }

      if (manaFill && manaText) {
        const mana = Math.max(0, Math.round(me.mana || 0));
        const maxMana = Math.round(me.max_mana || 100);
        manaText.textContent = `${mana} / ${maxMana}`;
        manaFill.style.width = `${Math.min(100, (mana / maxMana) * 100)}%`;
      }

      if (crystalCount) {
        const collected = this.crystals.filter((c) => c.collected).length;
        crystalCount.textContent = `${collected} / 5`;
      }

      if (statusBadge) {
        if (me.is_monster) {
          statusBadge.textContent = "👹 MONSTRE DÉMONIAQUE (ESPRIT DE RUCHE)";
          statusBadge.className = "status-badge monster";
        } else {
          statusBadge.textContent = "🛡️ SURVIVANT HUMAIN";
          statusBadge.className = "status-badge human";
        }
      }

      if (voiceModeText) {
        if (me.is_monster) {
          voiceModeText.textContent = "👁️ Télépathie de Ruche (Monstres) + Râles Démoniaques (Humains)";
          voiceModeText.style.color = "#fca5a5";
        } else {
          voiceModeText.textContent = "🗣️ Voix Humaine (Proximité + Occlusion Murs)";
          voiceModeText.style.color = "#38bdf8";
        }
      }
    }
  }

  // Démarrer dès que le DOM est prêt
  window.addEventListener("DOMContentLoaded", () => {
    window.game = new MazicGame();
  });
})();
