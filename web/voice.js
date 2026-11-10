/**
 * Mazic — Voice Proximity & Esprit de Ruche Engine
 * Web Audio API + WebSocket Audio Relay (PCM16 Base64) + Occlusion Murs + DemonicScrambler
 * + Bruitages d'environnement synthétisés et spatialisés en stéréo (relatifs au regard).
 */

// --- Spatialisation stéréo partagée (voix ET bruitages) ---
// Le panoramique est relatif à l'angle de la lampe torche du joueur local (me.aim_angle) :
// une source à droite du faisceau sort dans l'oreille droite, à gauche dans l'oreille gauche,
// pile dans l'axe au centre. Les sources derrière le joueur sont légèrement assourdies.
const REAR_COS_THRESHOLD = -0.2;
const REAR_LOWPASS_FACTOR = 0.6;
const REAR_LOWPASS_MAX_HZ = 5000;
// Occlusion par les murs (identique pour la voix humaine et les bruitages)
const WALL_LOWPASS_1_HZ = 850;
const WALL_GAIN_1 = 0.65;
const WALL_LOWPASS_2_HZ = 340;
const WALL_GAIN_2 = 0.35;
const OPEN_AIR_LOWPASS_HZ = 16000;
// Bruitages
const SFX_RANGE_TILES = 14;
const SFX_ROLLOFF = 1.6;
const SFX_MASTER_GAIN = 0.55;
const SFX_TYPES = new Set([
  "monster_step", "door_open", "door_close", "spell_cast", "attack", "hit", "wall_break",
]);

/**
 * Calcule les paramètres spatiaux d'une source (sx, sy) entendue par `me`.
 * @returns {{distTiles:number, pan:number, isBehind:boolean}}
 */
function computeSpatialParams(me, sx, sy) {
  const distTiles = Math.hypot(sx - me.x, sy - me.y) / 16;
  const sourceAngle = Math.atan2(sy - me.y, sx - me.x);
  const relAngle = sourceAngle - (me.aim_angle || 0);
  const distFactor = Math.min(1.0, distTiles / 2.5);
  const pan = Math.max(-1, Math.min(1, Math.sin(relAngle) * distFactor));
  const isBehind = Math.cos(relAngle) < REAR_COS_THRESHOLD;
  return { distTiles, pan, isBehind };
}

/** Abaisse légèrement la coupure du passe-bas pour une source située derrière le joueur. */
function applyRearOcclusion(freq, isBehind) {
  return isBehind ? Math.min(freq * REAR_LOWPASS_FACTOR, REAR_LOWPASS_MAX_HZ) : freq;
}

/** Occlusion murale commune : retourne {freq, gainFactor} selon le nombre de murs traversés. */
function wallOcclusion(wallCount) {
  if (wallCount === 1) return { freq: WALL_LOWPASS_1_HZ, gainFactor: WALL_GAIN_1 };
  if (wallCount >= 2) return { freq: WALL_LOWPASS_2_HZ, gainFactor: WALL_GAIN_2 };
  return { freq: OPEN_AIR_LOWPASS_HZ, gainFactor: 1.0 };
}

class VoiceProximityEngine {
  constructor() {
    this.audioCtx = null;
    this.micStream = null;
    this.micSource = null;
    this.micProcessor = null;
    this.currentRms = 0.0;
    this.isMicActive = false;
    this.ws = null;
    this.peers = new Map(); // from_id -> PeerAudioChannel
    this.selfTestActive = false;
    this.selfTestNode = null;
    this.selfTestDelay = null;
    this.sampleRate = 16000; // Fréquence cible pour les trames vocales
    this.onRmsUpdate = null; // Callback UI (rms, isLoud)
    this.onStatusUpdate = null; // Callback UI
    this._noiseBuffer = null; // Bruit blanc partagé pour les bruitages synthétisés
    this._sfxBlockedLogged = false;
  }

  /**
   * Initialise le contexte audio après une interaction utilisateur
   */
  ensureAudioContext() {
    if (!this.audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new AudioContextClass();
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
    return this.audioCtx;
  }

  setWebSocket(ws) {
    this.ws = ws;
  }

  /**
   * Active le micro et démarre la capture PCM16 + calcul RMS
   */
  async startMicrophone() {
    this.ensureAudioContext();
    if (this.isMicActive) return true;

    try {
      this.micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });

      this.micSource = this.audioCtx.createMediaStreamSource(this.micStream);
      
      // Utilisation d'un ScriptProcessorNode (compatible 100% tous navigateurs, localhost et https)
      const bufferSize = 2048;
      this.micProcessor = this.audioCtx.createScriptProcessor(bufferSize, 1, 1);

      this.micProcessor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Calcul du RMS
        let sum = 0.0;
        for (let i = 0; i < inputData.length; i++) {
          const val = inputData[i];
          sum += val * val;
        }
        const rms = Math.sqrt(sum / inputData.length);
        this.currentRms = Math.min(1.0, rms * 3.5); // Amplification légère pour l'affichage et le gameplay

        if (this.onRmsUpdate) {
          this.onRmsUpdate(this.currentRms, this.currentRms > 0.015);
        }

        // Si la voix dépasse le seuil de bruit, downsampler et envoyer via WebSocket ou Loopback
        if (this.currentRms > 0.012) {
          const downsampled = this.downsampleBuffer(inputData, this.audioCtx.sampleRate, this.sampleRate);
          const pcm16 = this.floatTo16BitPCM(downsampled);
          const b64 = this.arrayBufferToBase64(pcm16.buffer);

          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
              type: "voice_frame",
              pcm_b64: b64,
            }));
          }

          if (this.selfTestActive && this.selfTestChannel) {
            this.selfTestChannel.setRoutingMode("DEMONIC");
            this.selfTestChannel.queueAudioChunk(b64);
          }
        }
      };

      this.micSource.connect(this.micProcessor);
      // Connecter à une destination silencieuse pour faire tourner le processor
      const muteGain = this.audioCtx.createGain();
      muteGain.gain.value = 0.0;
      this.micProcessor.connect(muteGain);
      muteGain.connect(this.audioCtx.destination);

      this.isMicActive = true;
      if (this.onStatusUpdate) {
        this.onStatusUpdate("Microphone activé — Voix transmise");
      }
      return true;
    } catch (err) {
      console.error("[VoiceEngine] Erreur accès microphone:", err);
      if (this.onStatusUpdate) {
        this.onStatusUpdate("Erreur microphone: " + (err.message || err));
      }
      return false;
    }
  }

  stopMicrophone() {
    if (this.micStream) {
      this.micStream.getTracks().forEach(t => t.stop());
      this.micStream = null;
    }
    if (this.micProcessor) {
      this.micProcessor.disconnect();
      this.micProcessor = null;
    }
    if (this.micSource) {
      this.micSource.disconnect();
      this.micSource = null;
    }
    this.isMicActive = false;
    this.currentRms = 0.0;
    if (this.onRmsUpdate) this.onRmsUpdate(0.0, false);
    if (this.onStatusUpdate) this.onStatusUpdate("Microphone désactivé");
  }

  /**
   * Mode Self-Test Loopback : renvoie la propre voix d'Henri à travers le DemonicScrambler
   * avec un délai de 180ms pour qu'il puisse entendre l'effet sans second joueur !
   */
  toggleSelfTestMode(enable) {
    this.ensureAudioContext();
    if (enable === undefined) {
      this.selfTestActive = !this.selfTestActive;
    } else {
      this.selfTestActive = enable;
    }

    if (!this.selfTestActive) {
      if (this.selfTestChannel) {
        this.selfTestChannel.destroy();
        this.selfTestChannel = null;
      }
      return false;
    }

    if (!this.isMicActive) {
      this.startMicrophone().then(ok => {
        if (ok) this.setupSelfTestPipeline();
      });
    } else {
      this.setupSelfTestPipeline();
    }
    return true;
  }

  setupSelfTestPipeline() {
    if (this.selfTestChannel) {
      this.selfTestChannel.destroy();
    }
    this.selfTestChannel = new PeerAudioChannel("self_test", this.audioCtx);
    // Configuré en mode Monstre vers Humain avec délai de 180ms
    this.selfTestChannel.isSelfTest = true;
    this.selfTestChannel.setRoutingMode("DEMONIC");
  }

  /**
   * Réception d'une trame vocale via WebSocket
   */
  handleVoiceFrame(fromId, pcmB64, mePlayer, speakerPlayer, grid) {
    if (!pcmB64 || !mePlayer) return;
    this.ensureAudioContext();

    let channel = this.peers.get(fromId);
    if (!channel) {
      channel = new PeerAudioChannel(fromId, this.audioCtx);
      this.peers.set(fromId, channel);
    }

    // Calcul de l'acoustique spatiale
    const speaker = speakerPlayer || { x: mePlayer.x, y: mePlayer.y, is_monster: false };
    const walls = this.countWallsBetween(grid, mePlayer.x, mePlayer.y, speaker.x, speaker.y);
    channel.updateAcoustics(mePlayer, speaker, walls);

    // Décodage et lecture du PCM16
    const pcmData = this.base64ToArrayBuffer(pcmB64);
    const float32 = this.pcm16ToFloat32(new Int16Array(pcmData));
    channel.queueAudioChunk(float32, this.sampleRate);
  }

  /**
   * Compte le nombre de murs traversés par le segment (x0, y0) -> (x1, y1)
   */
  countWallsBetween(grid, x0, y0, x1, y1) {
    if (!grid || !grid.length) return 0;
    const h = grid.length;
    const w = grid[0].length;

    let tx0 = Math.floor(x0 / 16);
    let ty0 = Math.floor(y0 / 16);
    const tx1 = Math.floor(x1 / 16);
    const ty1 = Math.floor(y1 / 16);

    const dx = Math.abs(tx1 - tx0);
    const dy = Math.abs(ty1 - ty0);
    const sx = tx0 < tx1 ? 1 : -1;
    const sy = ty0 < ty1 ? 1 : -1;
    let err = dx - dy;

    let walls = 0;
    const maxSteps = 40;
    let steps = 0;

    while (steps++ < maxSteps) {
      if (tx0 === tx1 && ty0 === ty1) break;
      const e2 = 2 * err;
      if (e2 > -dy) {
        err -= dy;
        tx0 += sx;
      }
      if (e2 < dx) {
        err += dx;
        ty0 += sy;
      }
      if (tx0 >= 0 && tx0 < w && ty0 >= 0 && ty0 < h) {
        const cell = grid[ty0][tx0];
        // WALL = 2, DOOR_CLOSED = 3
        if (cell === 2 || cell === 3) {
          walls++;
        }
      }
    }
    return walls;
  }

  // --- Bruitages d'environnement synthétisés & spatialisés (aucun fichier externe) ---

  /**
   * Joue un bruitage spatialisé en stéréo relatif au regard du joueur local.
   * Même panoramique (me.aim_angle), même atténuation par la distance et même
   * occlusion murale (850 Hz derrière 1 mur, 340 Hz derrière 2+) que la voix humaine.
   * @param {string} type  monster_step | door_open | door_close | spell_cast | attack | hit | wall_break
   * @param {number} x     position monde de la source (px)
   * @param {number} y
   * @param {object} me    joueur local (x, y, aim_angle)
   * @param {number[][]} grid grille du donjon pour l'occlusion
   * @returns {boolean} true si le son a été planifié
   */
  playSpatialSound(type, x, y, me, grid) {
    if (!SFX_TYPES.has(type)) {
      throw new Error(`[VoiceEngine] Bruitage inconnu : ${type}`);
    }
    if (!me) {
      throw new Error("[VoiceEngine] playSpatialSound appelé sans joueur local");
    }
    // Politique d'autoplay des navigateurs : aucun son possible tant que l'utilisateur
    // n'a pas interagi avec la page (l'AudioContext est créé au premier clic/touche).
    if (!this.audioCtx || this.audioCtx.state !== "running") {
      if (!this._sfxBlockedLogged) {
        console.info("[VoiceEngine] Bruitages en attente d'une interaction utilisateur (autoplay).");
        this._sfxBlockedLogged = true;
      }
      return false;
    }

    const { distTiles, pan, isBehind } = computeSpatialParams(me, x, y);
    if (distTiles > SFX_RANGE_TILES) return false;

    const walls = this.countWallsBetween(grid, me.x, me.y, x, y);
    const occ = wallOcclusion(walls);
    let gain = Math.pow(Math.max(0, 1.0 - distTiles / SFX_RANGE_TILES), SFX_ROLLOFF) * occ.gainFactor;
    if (gain <= 0.001) return false;
    const freq = applyRearOcclusion(occ.freq, isBehind);

    const ctx = this.audioCtx;
    const t0 = ctx.currentTime + 0.005;

    // Chaîne : bus -> passe-bas (murs/arrière) -> gain distance -> panoramique -> sortie
    const bus = ctx.createGain();
    const lowpass = ctx.createBiquadFilter();
    lowpass.type = "lowpass";
    lowpass.frequency.value = freq;
    const distGain = ctx.createGain();
    distGain.gain.value = gain * SFX_MASTER_GAIN;
    const panner = ctx.createStereoPanner();
    panner.pan.value = pan;
    bus.connect(lowpass);
    lowpass.connect(distGain);
    distGain.connect(panner);
    panner.connect(ctx.destination);

    const duration = this._synthesize(type, bus, t0);
    setTimeout(() => {
      bus.disconnect();
      panner.disconnect();
    }, (duration + 0.3) * 1000);
    return true;
  }

  /** Construit le bruitage dans `bus` à partir de t0 et retourne sa durée totale (s). */
  _synthesize(type, bus, t0) {
    switch (type) {
      case "monster_step": {
        // Pas lourd (thump grave) + frottement, grognement sourd occasionnel
        this._tone(bus, t0, 0.18, "sine", 75, 38, 0.9, 0.005);
        this._noise(bus, t0, 0.12, "lowpass", 320, 120, 0.7, 0.5);
        if (Math.random() < 0.15) {
          this._tone(bus, t0 + 0.05, 0.75, "sawtooth", 52, 44, 0.22, 0.12, 380, { rate: 9, depth: 6 });
          return 0.85;
        }
        return 0.2;
      }
      case "door_open": {
        // Grincement : dent de scie glissante filtrée avec vibrato
        this._tone(bus, t0, 0.6, "sawtooth", 170, 430, 0.16, 0.06, 1800, { rate: 17, depth: 28 });
        this._noise(bus, t0 + 0.55, 0.12, "lowpass", 700, 200, 0.7, 0.35);
        return 0.7;
      }
      case "door_close": {
        // Claquement sourd
        this._noise(bus, t0, 0.25, "lowpass", 900, 180, 0.7, 0.8);
        this._tone(bus, t0, 0.3, "sine", 95, 50, 0.9, 0.004);
        return 0.32;
      }
      case "spell_cast": {
        // Déflagration magique : souffle filtré montant + harmonique
        this._noise(bus, t0, 0.42, "bandpass", 500, 2600, 2.0, 0.6);
        this._tone(bus, t0, 0.36, "triangle", 220, 880, 0.3, 0.02);
        this._tone(bus, t0, 0.25, "sine", 110, 70, 0.5, 0.005);
        return 0.45;
      }
      case "attack": {
        // Trait d'énergie : zap descendant bref
        this._tone(bus, t0, 0.13, "square", 1400, 340, 0.16, 0.003, 4200);
        this._noise(bus, t0, 0.06, "highpass", 2200, 2200, 0.7, 0.18);
        return 0.15;
      }
      case "hit": {
        // Impact
        this._noise(bus, t0, 0.1, "lowpass", 1800, 400, 0.7, 0.7);
        this._tone(bus, t0, 0.12, "sine", 160, 70, 0.6, 0.003);
        return 0.14;
      }
      case "wall_break": {
        // Effondrement de pierre : grondement + éclats
        this._noise(bus, t0, 1.1, "lowpass", 900, 120, 0.7, 0.9);
        this._tone(bus, t0, 0.9, "sine", 60, 32, 0.8, 0.01);
        for (let i = 0; i < 5; i++) {
          const off = 0.05 + Math.random() * 0.6;
          this._noise(bus, t0 + off, 0.07, "bandpass", 1500 + Math.random() * 1500, 900, 3.0, 0.35);
        }
        return 1.15;
      }
      default:
        throw new Error(`[VoiceEngine] Bruitage non synthétisable : ${type}`);
    }
  }

  /** Enveloppe percussive : montée linéaire puis décroissance exponentielle. */
  _envelope(gainNode, t0, dur, peak, attack) {
    gainNode.gain.setValueAtTime(0.0001, t0);
    gainNode.gain.linearRampToValueAtTime(peak, t0 + attack);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  }

  /** Oscillateur à glissement de fréquence f0 -> f1, filtrage et vibrato optionnels. */
  _tone(bus, t0, dur, wave, f0, f1, peak, attack, lowpassHz = null, vibrato = null) {
    const ctx = this.audioCtx;
    const osc = ctx.createOscillator();
    osc.type = wave;
    osc.frequency.setValueAtTime(f0, t0);
    osc.frequency.exponentialRampToValueAtTime(f1, t0 + dur);
    const env = ctx.createGain();
    this._envelope(env, t0, dur, peak, attack);

    let head = osc;
    if (lowpassHz !== null) {
      const f = ctx.createBiquadFilter();
      f.type = "lowpass";
      f.frequency.value = lowpassHz;
      osc.connect(f);
      head = f;
    }
    head.connect(env);
    env.connect(bus);

    if (vibrato !== null) {
      const lfo = ctx.createOscillator();
      lfo.frequency.value = vibrato.rate;
      const lfoGain = ctx.createGain();
      lfoGain.gain.value = vibrato.depth;
      lfo.connect(lfoGain);
      lfoGain.connect(osc.frequency);
      lfo.start(t0);
      lfo.stop(t0 + dur + 0.05);
    }
    osc.start(t0);
    osc.stop(t0 + dur + 0.05);
  }

  /** Bruit blanc filtré (fréquence de coupure glissante f0 -> f1). */
  _noise(bus, t0, dur, filterType, f0, f1, q, peak) {
    const ctx = this.audioCtx;
    if (!this._noiseBuffer) {
      const len = ctx.sampleRate;
      this._noiseBuffer = ctx.createBuffer(1, len, ctx.sampleRate);
      const data = this._noiseBuffer.getChannelData(0);
      for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    }
    const src = ctx.createBufferSource();
    src.buffer = this._noiseBuffer;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = filterType;
    filter.Q.value = q;
    filter.frequency.setValueAtTime(f0, t0);
    filter.frequency.exponentialRampToValueAtTime(f1, t0 + dur);
    const env = ctx.createGain();
    this._envelope(env, t0, dur, peak, 0.004);
    src.connect(filter);
    filter.connect(env);
    env.connect(bus);
    src.start(t0, Math.random() * 0.5);
    src.stop(t0 + dur + 0.05);
  }

  // --- Utilitaires de conversion audio PCM ---
  downsampleBuffer(buffer, inputRate, outputRate) {
    if (outputRate === inputRate) return buffer;
    const ratio = inputRate / outputRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
      let accum = 0, count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      result[offsetResult] = count > 0 ? accum / count : 0;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  floatTo16BitPCM(float32Array) {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return new Int16Array(buffer);
  }

  pcm16ToFloat32(int16Array) {
    const float32 = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF);
    }
    return float32;
  }

  arrayBufferToBase64(buffer) {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
  }

  base64ToArrayBuffer(base64) {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }
}


/**
 * Pipeline Audio dédié à un interlocuteur distant
 * Gère la spatialisation 2D, l'atténuation/occlusion des murs et le DemonicScrambler
 */
class PeerAudioChannel {
  constructor(peerId, audioCtx) {
    this.peerId = peerId;
    this.audioCtx = audioCtx;
    this.nextPlayTime = 0;

    // Nœuds de base
    this.entryGain = audioCtx.createGain();
    this.masterGain = audioCtx.createGain();
    this.pannerNode = audioCtx.createStereoPanner ? audioCtx.createStereoPanner() : null;
    this.wallFilter = audioCtx.createBiquadFilter();
    this.wallFilter.type = "lowpass";
    this.wallFilter.frequency.value = 16000;

    // Construction du DemonicScrambler
    this.scrambler = new DemonicScrambler(audioCtx);

    // Sélecteur de chaîne (Normal vs Monstre Démoniaque)
    this.normalGain = audioCtx.createGain();
    this.demonicGain = audioCtx.createGain();

    // Connexions du graphe :
    // entryGain -> normalGain -> wallFilter
    // entryGain -> scrambler -> demonicGain -> wallFilter
    // wallFilter -> masterGain -> pannerNode -> destination
    this.entryGain.connect(this.normalGain);
    this.normalGain.connect(this.wallFilter);

    this.entryGain.connect(this.scrambler.input);
    this.scrambler.output.connect(this.demonicGain);
    this.demonicGain.connect(this.wallFilter);

    if (this.pannerNode) {
      this.wallFilter.connect(this.masterGain);
      this.masterGain.connect(this.pannerNode);
      this.pannerNode.connect(audioCtx.destination);
    } else {
      this.wallFilter.connect(this.masterGain);
      this.masterGain.connect(audioCtx.destination);
    }

    // Delay de 180ms si self-test loopback
    this.isSelfTest = false;
  }

  /**
   * Met à jour les paramètres acoustiques selon les 3 régimes
   */
  updateAcoustics(me, speaker, wallCount) {
    // Panoramique stéréo relatif à l'angle de la lampe torche (me.aim_angle)
    const { distTiles, pan, isBehind } = computeSpatialParams(me, speaker.x, speaker.y);

    if (this.pannerNode && this.pannerNode.pan) {
      this.pannerNode.pan.setTargetAtTime(pan, this.audioCtx.currentTime, 0.05);
    }

    const meIsMonster = !!me.is_monster;
    const speakerIsMonster = !!speaker.is_monster;

    if (!meIsMonster && !speakerIsMonster) {
      // REGIME A : Survivant -> Survivant
      // Portée 13 cases, occlusion murs (mêmes valeurs que les bruitages spatialisés)
      this.normalGain.gain.setTargetAtTime(1.0, this.audioCtx.currentTime, 0.05);
      this.demonicGain.gain.setTargetAtTime(0.0, this.audioCtx.currentTime, 0.05);

      let gain = Math.max(0, 1.0 - distTiles / 13.0);
      gain = Math.pow(gain, 1.6);

      const occ = wallOcclusion(wallCount);
      gain *= occ.gainFactor;
      const freq = applyRearOcclusion(occ.freq, isBehind);
      this.wallFilter.frequency.setTargetAtTime(freq, this.audioCtx.currentTime, 0.05);
      this.masterGain.gain.setTargetAtTime(gain, this.audioCtx.currentTime, 0.05);

    } else if (meIsMonster && speakerIsMonster) {
      // REGIME B : Monstre -> Monstre (« Esprit de Ruche »)
      // Télépathie totale : portée infinie dans le donjon, voix claire + léger reverb/chorus
      // (pas d'occlusion arrière : la voix est « dans la tête », seul le panoramique s'applique)
      this.normalGain.gain.setTargetAtTime(1.0, this.audioCtx.currentTime, 0.05);
      this.demonicGain.gain.setTargetAtTime(0.0, this.audioCtx.currentTime, 0.05);

      this.wallFilter.frequency.setTargetAtTime(16000, this.audioCtx.currentTime, 0.05);
      this.masterGain.gain.setTargetAtTime(0.95, this.audioCtx.currentTime, 0.05);

    } else if (!meIsMonster && speakerIsMonster) {
      // REGIME C : Monstre -> Survivant
      // Voix Démoniaque Incompréhensible & Terrifiante via DemonicScrambler
      this.normalGain.gain.setTargetAtTime(0.0, this.audioCtx.currentTime, 0.05);
      this.demonicGain.gain.setTargetAtTime(1.2, this.audioCtx.currentTime, 0.05);

      let gain = Math.max(0, 1.0 - distTiles / 15.0);
      gain = Math.pow(gain, 1.4);

      let freq = 8000;
      if (wallCount === 1) {
        freq = 700;
        gain *= 0.70;
      } else if (wallCount >= 2) {
        freq = 300;
        gain *= 0.40;
      }
      freq = applyRearOcclusion(freq, isBehind);
      this.wallFilter.frequency.setTargetAtTime(freq, this.audioCtx.currentTime, 0.05);
      this.masterGain.gain.setTargetAtTime(gain, this.audioCtx.currentTime, 0.05);

    } else {
      // Monstre qui écoute un humain qui crie
      this.normalGain.gain.setTargetAtTime(1.0, this.audioCtx.currentTime, 0.05);
      this.demonicGain.gain.setTargetAtTime(0.0, this.audioCtx.currentTime, 0.05);

      let gain = Math.max(0, 1.0 - distTiles / 16.0);
      gain = Math.pow(gain, 1.5);
      let freq = wallCount >= 1 ? 900 : 14000;
      freq = applyRearOcclusion(freq, isBehind);
      this.wallFilter.frequency.setTargetAtTime(freq, this.audioCtx.currentTime, 0.05);
      this.masterGain.gain.setTargetAtTime(gain, this.audioCtx.currentTime, 0.05);
    }
  }

  /**
   * Configure explicitement le mode de routage audio (ex: DEMONIC pour Loopback)
   */
  setRoutingMode(mode) {
    if (mode === "DEMONIC") {
      this.normalGain.gain.setTargetAtTime(0.0, this.audioCtx.currentTime, 0.05);
      this.demonicGain.gain.setTargetAtTime(1.2, this.audioCtx.currentTime, 0.05);
      this.wallFilter.frequency.setTargetAtTime(16000, this.audioCtx.currentTime, 0.05);
      this.masterGain.gain.setTargetAtTime(0.95, this.audioCtx.currentTime, 0.05);
      if (this.pannerNode && this.pannerNode.pan) {
        this.pannerNode.pan.setTargetAtTime(0, this.audioCtx.currentTime, 0.05);
      }
    } else {
      this.normalGain.gain.setTargetAtTime(1.0, this.audioCtx.currentTime, 0.05);
      this.demonicGain.gain.setTargetAtTime(0.0, this.audioCtx.currentTime, 0.05);
    }
  }

  /**
   * Planifie la lecture d'un chunk audio reçu (Float32Array ou base64 string)
   */
  queueAudioChunk(chunk, sampleRate = 16000) {
    if (!chunk) return;

    let float32Data = chunk;
    if (typeof chunk === "string") {
      const binaryString = window.atob(chunk);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const int16Array = new Int16Array(bytes.buffer);
      float32Data = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Data[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF);
      }
    }

    if (!float32Data || float32Data.length === 0) return;

    const buffer = this.audioCtx.createBuffer(1, float32Data.length, sampleRate);
    buffer.getChannelData(0).set(float32Data);

    const source = this.audioCtx.createBufferSource();
    source.buffer = buffer;

    const now = this.audioCtx.currentTime;
    if (this.nextPlayTime < now) {
      this.nextPlayTime = now + (this.isSelfTest ? 0.18 : 0.02); // 180ms pour loopback, 20ms sinon
    }

    source.connect(this.entryGain);
    source.start(this.nextPlayTime);
    this.nextPlayTime += buffer.duration;
  }

  destroy() {
    try {
      this.entryGain.disconnect();
      this.masterGain.disconnect();
      this.wallFilter.disconnect();
      if (this.pannerNode) this.pannerNode.disconnect();
      this.scrambler.destroy();
    } catch (e) {
      // Ignorer
    }
  }
}


/**
 * Processeur de Voix Démoniaque Incompréhensible & Terrifiante
 * Double Ring Modulator (porteuse 42 Hz modulée par LFO 7.5 Hz + seconde porteuse 67 Hz)
 * + Distorsion non-linéaire + Filtre guttural 110-480 Hz + Sub-bass grondant
 */
class DemonicScrambler {
  constructor(audioCtx) {
    this.audioCtx = audioCtx;

    this.input = audioCtx.createGain();
    this.output = audioCtx.createGain();

    // 1. Ring Modulator Principal : Porteuse sinusoïdale à 42 Hz
    this.carrier1 = audioCtx.createOscillator();
    this.carrier1.type = "sine";
    this.carrier1.frequency.value = 42;

    // LFO chaotique à 7.5 Hz qui module la fréquence de la porteuse 1 (hachage des syllabes)
    this.lfo = audioCtx.createOscillator();
    this.lfo.type = "sine";
    this.lfo.frequency.value = 7.5;
    this.lfoGain = audioCtx.createGain();
    this.lfoGain.gain.value = 16.0; // Déviation de ±16 Hz
    this.lfo.connect(this.lfoGain);
    this.lfoGain.connect(this.carrier1.frequency);

    // Multiplicateur pour Carrier 1
    this.ringGain1 = audioCtx.createGain();
    this.ringGain1.gain.value = 0.0;
    this.carrier1.connect(this.ringGain1.gain);

    // 2. Ring Modulator Secondaire : Porteuse dissonante à 67 Hz (déplacement spectral hors formants)
    this.carrier2 = audioCtx.createOscillator();
    this.carrier2.type = "sawtooth";
    this.carrier2.frequency.value = 67;
    this.ringGain2 = audioCtx.createGain();
    this.ringGain2.gain.value = 0.0;
    this.carrier2.connect(this.ringGain2.gain);

    // 3. Distorsion non-linéaire (WaveShaper)
    this.shaper = audioCtx.createWaveShaper();
    this.shaper.curve = this.makeDistortionCurve(35);
    this.shaper.oversample = "4x";

    // 4. Filtre Passe-Bande Guttural (110 Hz - 480 Hz)
    this.gutturalFilter = audioCtx.createBiquadFilter();
    this.gutturalFilter.type = "bandpass";
    this.gutturalFilter.frequency.value = 280;
    this.gutturalFilter.Q.value = 1.4;

    // 5. Grondement Sub-Bass (Lowpass 85 Hz avec boost)
    this.subFilter = audioCtx.createBiquadFilter();
    this.subFilter.type = "lowpass";
    this.subFilter.frequency.value = 85;
    this.subGain = audioCtx.createGain();
    this.subGain.gain.value = 1.8;

    // 6. Mélangeur
    this.mixGain = audioCtx.createGain();
    this.mixGain.gain.value = 1.3;

    // Câblage du graphe :
    // input -> ringGain1 -> shaper
    // input -> ringGain2 -> shaper
    this.input.connect(this.ringGain1);
    this.input.connect(this.ringGain2);

    this.ringGain1.connect(this.shaper);
    this.ringGain2.connect(this.shaper);

    // Sortie distordue vers filtre guttural et sub-bass
    this.shaper.connect(this.gutturalFilter);
    this.gutturalFilter.connect(this.mixGain);

    this.shaper.connect(this.subFilter);
    this.subFilter.connect(this.subGain);
    this.subGain.connect(this.mixGain);

    this.mixGain.connect(this.output);

    // Démarrage des oscillateurs
    this.lfo.start();
    this.carrier1.start();
    this.carrier2.start();
  }

  makeDistortionCurve(amount) {
    const k = typeof amount === 'number' ? amount : 50;
    const n_samples = 44100;
    const curve = new Float32Array(n_samples);
    const deg = Math.PI / 180;
    for (let i = 0; i < n_samples; ++i) {
      const x = (i * 2) / n_samples - 1;
      curve[i] = ((3 + k) * x * 20 * deg) / (Math.PI + k * Math.abs(x));
    }
    return curve;
  }

  destroy() {
    try {
      this.lfo.stop();
      this.carrier1.stop();
      this.carrier2.stop();
      this.input.disconnect();
      this.output.disconnect();
    } catch (e) {
      // Ignorer
    }
  }
}

// Export global pour être utilisé dans game.js et index.html
window.VoiceProximityEngine = VoiceProximityEngine;
