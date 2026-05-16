// app.jsx — v6 · 14 scenes · 50s

const { Scene, StageBG, POTLogo, Scene01, Scene02, Scene03, Scene04, Scene05, Scene06, FG, ORANGE, FONT_DISPLAY, FONT_MONO, BG } = window.PotVideo_PartOne;
const { SceneHowItWorks, Scene07, Scene08, Scene09, Scene10, Scene11, Scene12, Scene13, Scene14Availability, Scene15, Scene16, SceneIntro07, SceneIntro08, SceneIntro09, SceneIntro10, SceneIntro11, SceneIntro12 } = window.PotVideo_PartTwo;

const DUR = 76.3;
const FX = 1.1;
const FX_FEATURE = 1.4;
const FX_INTRO   = 0.7;

const SCHEDULE = [
  [ 0.00,  4.01],   // Scene05        — Introducing Matchmaker    (4.01s)
  [ 4.01,  7.98],   // Scene02        — Scale / cards swarming    (3.97s)
  [ 7.98, 13.24],   // Scene03        — Stats / June 2-3          (5.26s)
  [13.24, 17.24],   // Scene04        — Find the right people     (4.00s)
  [17.24, 20.01],   // SceneHowItWorks — How it works bridge       (2.77s)
  [20.01, 23.01],   // SceneIntro07   — AI Matchmaking             (3.00s)
  [23.01, 27.61],   // Scene07        — My Matches                (4.60s)
  [27.61, 30.61],   // SceneIntro08   — AI Concierge               (3.00s)
  [30.61, 35.81],   // Scene08        — AI Concierge              (5.20s)
  [35.81, 38.81],   // SceneIntro09   — Auto Profile               (3.00s)
  [38.81, 43.71],   // Scene09        — Profile, written for you  (4.90s)
  [43.71, 46.71],   // SceneIntro10   — Mutual Match               (3.00s)
  [46.71, 50.01],   // Scene10        — Mutual match              (3.30s)
  [50.01, 53.01],   // SceneIntro11   — Smart Booking              (3.00s)
  [53.01, 56.21],   // Scene11        — One-tap booking           (3.20s)
  [56.21, 59.21],   // SceneIntro12   — Magic Link                 (3.00s)
  [59.21, 62.16],   // Scene12        — Magic link                (2.95s)
  [62.16, 67.04],   // Scene13        — Impact                    (4.88s)
  [67.04, 71.16],   // Scene14Availability                        (4.12s)
  [71.16, 76.30],   // Scene15        — CTA                       (5.14s)
];

const SCENES = [
  Scene05,
  Scene02, Scene03, Scene04,
  SceneHowItWorks,
  SceneIntro07, Scene07,
  SceneIntro08, Scene08,
  SceneIntro09, Scene09,
  SceneIntro10, Scene10,
  SceneIntro11, Scene11,
  SceneIntro12, Scene12,
  Scene13, Scene14Availability, Scene15,
];

const FEATURE_IDX    = new Set([6, 8, 10, 12, 14, 16]);
const INTRO_IDX      = new Set([5, 7, 9, 11, 13, 15]);
const LIGHT_BG_SCENES = new Set([0, 2, 3, 18]);
const HIDE_WATERMARK  = new Set([0, 19]);

function WatermarkLogo() {
  const { time } = useTimeline();
  let idx = 0;
  for (let i = 0; i < SCHEDULE.length; i++) {
    if (time >= SCHEDULE[i][0] && time < SCHEDULE[i][1]) { idx = i; break; }
  }
  const isLight = LIGHT_BG_SCENES.has(idx);
  const hidden = HIDE_WATERMARK.has(idx);
  const opIn = Math.min(1, time / 1.0);
  const opOut = Math.min(1, (DUR - time) / 1.0);
  const baseOp = Math.max(0, Math.min(opIn, opOut)) * (hidden ? 0 : 0.85);
  return (
    <div style={{
      position: 'absolute', left: 60, top: 50,
      opacity: baseOp,
      transition: 'opacity 480ms cubic-bezier(0.4, 0, 0.2, 1)',
      pointerEvents: 'none',
    }}>
      <img src="pot-logo.png" alt="Proof of Talk"
        style={{
          height: 28, width: 'auto', display: 'block',
          filter: isLight ? 'invert(1)' : 'none',
          opacity: isLight ? 0.92 : 1,
        }} />
    </div>
  );
}


function BackgroundMusic() {
  const { time, playing } = useTimeline();
  const audioRef = React.useRef(null);
  const FADE_IN  = 2.5;
  const FADE_OUT = 3.0;
  const MAX_VOL  = 0.28;
  const DUCK_VOL = 0.08;
  const VO_START = 1.0;
  const VO_END   = 67.24;
  const DUCK_FADE = 1.5;
  React.useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    const fadeInVol  = Math.min(1, time / FADE_IN);
    const fadeOutVol = Math.min(1, (DUR - time) / FADE_OUT);
    const toDuck   = Math.max(0, Math.min(1, (time - VO_START) / DUCK_FADE));
    const fromDuck = Math.max(0, Math.min(1, (time - VO_END)   / DUCK_FADE));
    const duck     = Math.max(0, toDuck - fromDuck);
    const targetVol = MAX_VOL - (MAX_VOL - DUCK_VOL) * duck;
    a.volume = Math.max(0, Math.min(fadeInVol, fadeOutVol)) * targetVol;
  }, [time]);
  React.useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    if (playing) { const p = a.play(); if (p && p.catch) p.catch(() => {}); }
    else if (!a.paused) a.pause();
  }, [playing]);
  React.useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    if (Math.abs(a.currentTime - time) > 0.30) {
      try { a.currentTime = time; } catch (e) {}
    }
  }, [time]);
  return <audio ref={audioRef} src="music.mp3" preload="auto" loop style={{ display: 'none' }} />;
}

function SyncedAudio() {
  const { time, playing } = useTimeline();
  const audioRef = React.useRef(null);
  const [needsTap, setNeedsTap] = React.useState(false);
  React.useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    a.volume = 1.0; a.muted = false;
  }, []);
  React.useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    if (playing) {
      const p = a.play();
      if (p && p.catch) p.catch(() => setNeedsTap(true));
    } else if (!a.paused) a.pause();
  }, [playing]);
  React.useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    if (Math.abs(a.currentTime - time) > 0.30) {
      try { a.currentTime = time; } catch (e) {}
    }
  }, [time]);
  const handleTap = () => {
    const a = audioRef.current;
    if (!a) return;
    a.muted = false; a.volume = 1.0;
    a.play().then(() => setNeedsTap(false)).catch(() => {});
  };
  return (
    <React.Fragment>
      <audio ref={audioRef} src="voiceover.mp3" preload="auto" style={{ display: 'none' }} />
      {needsTap && (
        <div onClick={handleTap} style={{
          position: 'fixed', bottom: 24, left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(247,106,12,0.95)', color: '#fff',
          padding: '12px 22px', borderRadius: 999,
          fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
          letterSpacing: '0.16em', textTransform: 'uppercase',
          cursor: 'pointer', boxShadow: '0 8px 24px rgba(247,106,12,0.35)',
          zIndex: 1000,
        }}>► Tap to enable sound</div>
      )}
    </React.Fragment>
  );
}

function VideoApp() {
  return (
    <Stage width={1920} height={1080} duration={DUR}
      background={"rgb(10,10,10)"} persistKey="potvideo_v9" autoplay loop>
      <StageBG />
      {SCHEDULE.map(([s, e], i) => {
        const SceneComp = SCENES[i];
        const isFeature = FEATURE_IDX.has(i);
        const isIntro   = INTRO_IDX.has(i);
        const fade = isFeature ? FX_FEATURE : isIntro ? FX_INTRO : FX;
        return (
          <Scene key={i} start={s} end={e} fadeIn={fade} fadeOut={fade} splitMode={isFeature}>
            {() => <SceneComp />}
          </Scene>
        );
      })}
      <WatermarkLogo />
      <BackgroundMusic />
      <SyncedAudio />
    </Stage>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<VideoApp />);
