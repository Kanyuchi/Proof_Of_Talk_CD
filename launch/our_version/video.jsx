// video.jsx — Proof of Talk Matchmaker product video (scenes 1–6)
// Scenes follow the figma keyframes 01–15 (reference screenshots in /uploads).
// All scenes mounted into a single <Stage>, each gated by <Sprite start end>.

const { useMemo } = React;

// ── Theme ───────────────────────────────────────────────────────────────────
const BG = 'rgb(10,10,10)';
const BG_LIGHT = 'rgb(250,248,245)';      // cream for intro / numbers
const FG = 'rgb(245,244,239)';
const FG_DARK = 'rgb(15,15,15)';
const FG_DIM = 'rgb(138,138,134)';
const FG_FAINT = 'rgb(90,90,86)';
const FG_FAINT_LT = 'rgb(106,101,92)';
const ORANGE = 'rgb(247,106,12)';
const ORANGE_DARK = 'rgb(122,58,20)';
const ORANGE_BG = 'rgb(58,30,10)';
const CARD = 'rgb(22,22,22)';
const CARD_BORDER = 'rgb(42,42,42)';
const GREEN = 'rgb(34,197,94)';
const GREEN_BG = 'rgb(15,42,24)';
const BLUE = 'rgb(159,180,217)';
const VIOLET = 'rgb(167,139,250)';

const FONT_DISPLAY = "'Poppins', system-ui, sans-serif";
const FONT_BODY = "'Inter', system-ui, sans-serif";
const FONT_MONO = "'JetBrains Mono', ui-monospace, monospace";

// ── Scene wrapper ───────────────────────────────────────────────────────────
// Centered crossfade: at the boundary between scenes both are at ~50% opacity,
// so the transition is a true blend rather than a sequential hand-off.
//
// `splitMode` disables the global opacity/scale animation; children manage
// their own per-region transitions via useSprite() (used by feature scenes to
// crossfade the left title but vertically scroll the right panel).
function Scene({ start, end, fadeIn = 0.7, fadeOut = 0.7, splitMode = false, bg = null, children }) {
  const halfIn = fadeIn / 2;
  const halfOut = fadeOut / 2;
  return (
    <Sprite start={start - halfIn} end={end + halfOut} keepMounted={false}>
      {({ localTime, duration }) => {
        if (splitMode) {
          return (
            <div style={{
              position: 'absolute', inset: 0,
              background: bg || 'transparent',
            }}>
              {typeof children === 'function' ? children({ localTime, duration }) : children}
            </div>
          );
        }
        let opacity = 1;
        let scale = 1;
        let blur = 0;
        if (localTime < fadeIn) {
          const k        = clamp(localTime / fadeIn, 0, 1);
          const easedOp  = Easing.easeInOutCubic(k);
          const easedZoom = Easing.easeOutCubic(k);
          opacity = easedOp;
          scale   = 1.07 - 0.07 * easedZoom;   // 1.07 → 1.00
          blur    = (1 - easedZoom) * 10;        // 10px → 0px
        } else if (localTime > duration - fadeOut) {
          const k        = clamp((duration - localTime) / fadeOut, 0, 1);
          const easedOp  = Easing.easeInOutCubic(k);
          const easedZoom = Easing.easeInCubic(k);
          opacity = easedOp;
          scale   = 1.00 + (1 - easedZoom) * 0.05; // 1.00 → 1.05
          blur    = (1 - easedZoom) * 7;             // 0px → 7px
        }
        return (
          <div style={{
            position: 'absolute', inset: 0,
            opacity,
            transform: `scale(${scale})`,
            transformOrigin: 'center',
            filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : 'none',
            background: bg || 'transparent',
            willChange: 'opacity, transform, filter',
          }}>
            {typeof children === 'function' ? children({ localTime, duration }) : children}
          </div>
        );
      }}
    </Sprite>
  );
}

// ── Feature transition hook ─────────────────────────────────────────────────
// Inside a feature scene (Scene in splitMode), computes:
//   leftOpacity — crossfade for the left title region
//   panelTy     — vertical translate for the right panel (1080→0→-1080)
// fadeIn/fadeOut must match the parent Scene's fade values.
function useFeatureTransition(fadeIn = 1.0, fadeOut = 1.0) {
  const { localTime, duration } = useSprite();
  let leftOpacity = 1, panelTy = 0;
  if (localTime < fadeIn) {
    const eased = Easing.easeInOutCubic(clamp(localTime / fadeIn, 0, 1));
    leftOpacity = eased;
    panelTy = (1 - eased) * 1080;
  } else if (localTime > duration - fadeOut) {
    const eased = Easing.easeInOutCubic(clamp((duration - localTime) / fadeOut, 0, 1));
    leftOpacity = eased;
    panelTy = -(1 - eased) * 1080;
  }
  return { leftOpacity, panelTy };
}

// ── Background layers ───────────────────────────────────────────────────────
function StageBG() {
  return (
    <div style={{ position: 'absolute', inset: 0, background: BG }} />
  );
}

// Per-scene radial vignette (orange on dark, warm on cream)
function Vignette({ light = false }) {
  return (
    <div style={{
      position: 'absolute', inset: 0,
      background: light
        ? 'radial-gradient(70% 70% at 50% 30%, rgba(247,106,12,0.05) 0%, rgba(247,106,12,0) 70%)'
        : 'radial-gradient(60% 60% at 50% 50%, rgba(247,106,12,0.10) 0%, rgba(247,106,12,0) 65%)',
      pointerEvents: 'none',
    }} />
  );
}

// ── Chapter label (bottom-left) ─────────────────────────────────────────────
function ChapterLabel({ text, color = FG_FAINT }) {
  // v4: globally suppressed (no chrome on any scene). Restore by returning the div.
  return null;
  // eslint-disable-next-line no-unreachable
  return (
    <div style={{
      position: 'absolute', left: 60, bottom: 50,
      fontFamily: FONT_MONO, fontSize: 13, color, letterSpacing: '0.06em',
    }}>{text}</div>
  );
}

// ── Eyebrow (top, mono, small) ──────────────────────────────────────────────
function Eyebrow({ text, x = 60, y = 60, color = ORANGE, size = 13, delay = 0, weight = 700, letterSpacing = '0.16em' }) {
  const local = useSprite().localTime;
  const t = Easing.easeOutCubic(clamp((local - delay) / 0.5, 0, 1));
  return (
    <div style={{
      position: 'absolute', left: x, top: y,
      fontFamily: FONT_MONO, fontSize: size, color,
      letterSpacing, fontWeight: weight, textTransform: 'uppercase',
      opacity: t, transform: `translateY(${(1 - t) * 6}px)`,
    }}>{text}</div>
  );
}

// ── Pill (rounded badge) ────────────────────────────────────────────────────
function Pill({ text, x = null, y = 60, delay = 0, light = false }) {
  const local = useSprite().localTime;
  const t = Easing.easeOutCubic(clamp((local - delay) / 0.5, 0, 1));
  const style = {
    position: 'absolute', top: y,
    padding: '12px 24px',
    background: light ? 'rgba(247,106,12,0.10)' : ORANGE_BG,
    border: `1px solid ${ORANGE_DARK}`,
    borderRadius: 999,
    fontFamily: FONT_BODY, fontWeight: 700, fontSize: 14,
    color: ORANGE, letterSpacing: '0.16em',
    opacity: t, transform: `translateY(${(1 - t) * 8}px)`,
    display: 'inline-block',
  };
  if (x === null) {
    return (
      <div style={{ position: 'absolute', left: 0, right: 0, top: y, display: 'flex', justifyContent: 'center' }}>
        <div style={{ ...style, position: 'static' }}>{text}</div>
      </div>
    );
  }
  return <div style={{ ...style, left: x }}>{text}</div>;
}

// ── HighlightedTitle — mixed inline color/style runs, word-by-word reveal ──
// Pass `parts: [{text, color?, italic?, weight?}]`. Words within each part
// reveal sequentially across all parts.
function HighlightedTitle({
  parts, x, y, width, size = 88, font = FONT_DISPLAY, weight = 400,
  baseColor = FG, align = 'left',
  delay = 0, stagger = 0.10, lineHeight = 1.1, letterSpacing = '-0.02em',
  wordGap = '0.4em',
}) {
  const local = useSprite().localTime;
  const flat = useMemo(() => {
    const out = [];
    parts.forEach((p) => {
      const words = p.text.split(' ');
      words.forEach((w) => {
        out.push({
          text: w,
          color: p.color || baseColor,
          italic: !!p.italic,
          weight: p.weight || weight,
        });
      });
    });
    return out;
  }, [parts, baseColor, weight]);

  return (
    <div style={{
      position: 'absolute', left: x, top: y, width,
      fontFamily: font, fontSize: size, fontWeight: weight,
      color: baseColor, lineHeight, letterSpacing, textAlign: align,
    }}>
      {flat.map((w, i) => {
        const t = Easing.easeOutCubic(clamp((local - delay - i * stagger) / 0.70, 0, 1));
        const isLast = i === flat.length - 1;
        return (
          <span key={i} style={{
            display: 'inline-block',
            color: w.color,
            fontStyle: w.italic ? 'italic' : 'normal',
            fontWeight: w.weight,
            opacity: t,
            transform: `translateY(${(1 - t) * 20}px)`,
            whiteSpace: 'nowrap',
            marginRight: isLast ? 0 : wordGap,
            willChange: 'transform, opacity',
          }}>{w.text}</span>
        );
      })}
    </div>
  );
}

// Simple reveal-by-word for body text
function RevealText({ text, x, y, width, size = 22, color = FG_DIM, font = FONT_BODY, weight = 400, italic = false, align = 'left', delay = 0, stagger = 0.05, lineHeight = 1.5, letterSpacing = '0', wordGap = '0.3em' }) {
  const local = useSprite().localTime;
  const words = useMemo(() => text.split(' '), [text]);
  return (
    <div style={{
      position: 'absolute', left: x, top: y, width,
      fontFamily: font, fontSize: size, fontWeight: weight,
      fontStyle: italic ? 'italic' : 'normal',
      color, lineHeight, letterSpacing, textAlign: align,
    }}>
      {words.map((w, i) => {
        const t = Easing.easeOutCubic(clamp((local - delay - i * stagger) / 0.60, 0, 1));
        const isLast = i === words.length - 1;
        return (
          <span key={i} style={{
            display: 'inline-block', opacity: t,
            transform: `translateY(${(1 - t) * 10}px)`,
            whiteSpace: 'nowrap',
            marginRight: isLast ? 0 : wordGap,
          }}>{w}</span>
        );
      })}
    </div>
  );
}

// Counter ticker
function Counter({ from = 0, to = 2500, duration = 1.2, delay = 0, format = (n) => n.toLocaleString(), size = 220, color = FG, weight = 500, font = FONT_DISPLAY, letterSpacing = '-0.04em' }) {
  const local = useSprite().localTime;
  const t = Easing.easeOutCubic(clamp((local - delay) / duration, 0, 1));
  const val = Math.round(from + (to - from) * t);
  return (
    <span style={{
      fontFamily: font, fontSize: size, fontWeight: weight, color, letterSpacing,
      lineHeight: 1, fontVariantNumeric: 'tabular-nums',
      display: 'inline-block',
    }}>{format(val)}</span>
  );
}

// Proof of Talk wordmark (real brand logo, PNG asset)
function POTLogo({ height = 56, invert = false }) {
  return (
    <img
      src="pot-logo.png"
      alt="Proof of Talk"
      style={{
        height,
        width: 'auto',
        display: 'block',
        filter: invert ? 'invert(1)' : 'none',
        opacity: invert ? 0.94 : 1,
      }}
    />
  );
}

// ── SCENE 01 — Cards swarming + headline ────────────────────────────────────
const ATTENDEES = [
  { i: 'MC', n: 'Mira Chen', r: 'GP · Vega' },
  { i: 'KI', n: 'Karim Idrissi', r: 'Founder · ChainPort' },
  { i: 'YT', n: 'Yuki Tanabe', r: 'Strategy · Nomura' },
  { i: 'LB', n: 'Lena Becker', r: 'LP · Helvetia' },
  { i: 'DS', n: 'Diego Soto', r: 'CTO · Lattice' },
  { i: 'AR', n: 'Aisha Rahimi', r: 'Policy Lead' },
  { i: 'TV', n: 'Tomás Vidal', r: 'Founder · Aurum' },
  { i: 'HS', n: 'Hannah Schultz', r: 'MD · Brevan' },
  { i: 'RM', n: 'Rohan Mehta', r: 'Partner · Compass' },
  { i: 'SK', n: 'Sofia Kallio', r: 'ESMA' },
  { i: 'WZ', n: 'Wei Zhang', r: 'Treasury · Hashed' },
  { i: 'AO', n: 'Adaeze O.', r: 'Director' },
  { i: 'LO', n: 'Liam OConnor', r: 'Founder · Forge' },
  { i: 'ÉM', n: 'Élise Moreau', r: 'SocGen' },
  { i: 'NK', n: 'Noah Kim', r: 'GP · Kestrel' },
  { i: 'PI', n: 'Priya Iyer', r: 'CEO · Vellum' },
  { i: 'FA', n: 'Felix Ahlgren', r: 'UBS Digital' },
  { i: 'ML', n: 'Mei Lin', r: 'Founder · Orbit' },
];

// Scattered positions (manually placed, avoiding centre title band 380–620)
const CARD_POSITIONS = [
  { x: 100,  y: 360 },  // MC top left
  { x: 540,  y: 340 },  // KI
  { x: 980,  y: 380 },  // YT
  { x: 1340, y: 330 },  // LB
  { x: 1620, y: 380 },  // DS
  { x: 250,  y: 640 },  // AR
  { x: 670,  y: 580 },  // TV
  { x: 1280, y: 580 },  // HS
  { x: 1580, y: 650 },  // RM
  // bottom row
  { x: 60,   y: 880 },  // WZ
  { x: 380,  y: 1010 }, // AO
  { x: 480,  y: 870 },  // LO (offset to feel chaotic)
  { x: 880,  y: 890 },  // ÉM
  { x: 1180, y: 1010 }, // NK
  { x: 1500, y: 880 },  // PI
  { x: 1680, y: 1020 }, // ML... wait — clip if out-of-frame
  { x: 760,  y: 1010 }, // FA
];

function useCardCards() {
  return useMemo(() => CARD_POSITIONS.map((p, i) => {
    const seed = (i * 31 + 7) % 100;
    return {
      ...p,
      rot: ((seed * 11) % 100 - 50) * 0.08,    // -4 .. +4 deg
      blur: 1 + (i % 5) * 0.6,                  // ~1–3.5 px
      scale: 0.88 + ((seed % 24) / 100),        // ~0.88–1.12
      opacityBase: 0.4 + ((seed * 7) % 50) / 100,
      seed,
      att: ATTENDEES[i % ATTENDEES.length],
    };
  }), []);
}

function SwarmCard({ card, sceneT, dim = false }) {
  const driftX = Math.sin(sceneT * 0.55 + card.seed * 0.31) * 10;
  const driftY = Math.cos(sceneT * 0.45 + card.seed * 0.22) * 7;
  const rotDrift = Math.sin(sceneT * 0.35 + card.seed) * 0.8;
  const entryT = Easing.easeOutCubic(clamp((sceneT - card.seed * 0.012) / 0.85, 0, 1));
  return (
    <div style={{
      position: 'absolute',
      left: card.x + driftX, top: card.y + driftY,
      width: 300,
      transform: `rotate(${card.rot + rotDrift}deg) scale(${card.scale})`,
      transformOrigin: 'center',
      filter: `blur(${dim ? card.blur * 1.8 : card.blur}px)`,
      opacity: entryT * card.opacityBase * (dim ? 0.55 : 1),
      willChange: 'transform, opacity, filter',
    }}>
      <div style={{
        background: CARD,
        border: `1px solid ${CARD_BORDER}`,
        borderRadius: 14,
        padding: '14px 18px',
        display: 'flex', alignItems: 'center', gap: 14,
        boxShadow: '0 18px 50px rgba(0,0,0,0.55)',
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: 8,
          background: 'rgb(26,26,26)',
          border: `1px solid ${CARD_BORDER}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: FONT_BODY, fontWeight: 700, fontSize: 13, color: FG_DIM,
        }}>{card.att.i}</div>
        <div style={{ minWidth: 0, lineHeight: 1.25 }}>
          <div style={{ fontFamily: FONT_BODY, fontWeight: 600, fontSize: 15, color: FG, whiteSpace: 'nowrap' }}>{card.att.n}</div>
          <div style={{ fontFamily: FONT_BODY, fontSize: 12, color: FG_DIM, whiteSpace: 'nowrap' }}>{card.att.r}</div>
        </div>
      </div>
    </div>
  );
}

function Scene01() {
  const local = useSprite().localTime;
  return (
    <React.Fragment>
      <Vignette />
      {/* PROOF OF TALK eyebrow */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 360, textAlign: 'center',
        fontFamily: FONT_MONO, fontSize: 14, color: ORANGE,
        letterSpacing: '0.22em', fontWeight: 700, textTransform: 'uppercase',
        opacity: Easing.easeOutCubic(clamp((local - 0.2) / 0.5, 0, 1)),
        transform: `translateY(${(1 - clamp((local - 0.2) / 0.5, 0, 1)) * 8}px)`,
      }}>PROOF OF TALK</div>
      {/* Massive Matchmaker hero */}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 420, textAlign: 'center' }}>
        <HighlightedTitle
          parts={[{ text: 'Matchmaker.', color: ORANGE, italic: true, weight: 500 }]}
          x={0} y={0} width={1920}
          size={220} align="center"
          baseColor={ORANGE}
          delay={0.5}
          stagger={0.08}
          letterSpacing="-0.035em"
        />
      </div>
      <RevealText
        text="The AI that finds your people in a room of 2,500."
        x={0} y={760} width={1920}
        size={26} color={FG_DIM} font={FONT_BODY}
        align="center" delay={1.4} stagger={0.025}
      />
      <ChapterLabel text="00 · The Hook" />
    </React.Fragment>
  );
}

// ── SCENE 01 (legacy) — Cards swarming + headline ──────────────────────────
function Scene01Legacy() {
  const cards = useCardCards();
  const local = useSprite().localTime;
  return (
    <React.Fragment>
      <Vignette />
      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
        {cards.map((c, i) => <SwarmCard key={i} card={c} sceneT={local} />)}
      </div>
      {/* Centered headline with "business cards" highlighted in orange italic */}
      <HighlightedTitle
        parts={[
          { text: 'An 18-hour blur of' },
          { text: 'business cards.', color: ORANGE, italic: true },
        ]}
        x={0} y={465} width={1920}
        size={104} align="center"
        baseColor={FG}
        delay={0.4} stagger={0.05}
        letterSpacing="-0.025em"
      />
      <ChapterLabel text="01 · The Problem" />
    </React.Fragment>
  );
}

// ── SCENE 02 — Cards continue + 2,500 counter ───────────────────────────────
function Scene02() {
  const cards = useCardCards();
  const local = useSprite().localTime;
  const labelT = Easing.easeOutCubic(clamp((local - 1.1) / 0.55, 0, 1));
  const subT   = Easing.easeOutCubic(clamp((local - 1.8) / 0.55, 0, 1));
  return (
    <React.Fragment>
      <Vignette />
      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.3 }}>
        {cards.map((c, i) => <SwarmCard key={i} card={c} sceneT={local + 0.6} dim />)}
      </div>
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 0, bottom: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: 0,
      }}>
        <div style={{ lineHeight: 1 }}>
          <Counter from={0} to={2500} duration={1.3} delay={0.3}
            format={(n) => n.toLocaleString()}
            size={300} weight={700} color={FG} letterSpacing="-0.045em" />
        </div>
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: 38, fontWeight: 500, color: FG_DIM,
          letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: 16,
          opacity: labelT, transform: `translateY(${(1 - labelT) * 10}px)`,
        }}>people attending Proof of Talk 2026</div>
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: 26, fontWeight: 400, color: FG_FAINT,
          letterSpacing: '-0.01em', marginTop: 18,
          opacity: subT, transform: `translateY(${(1 - subT) * 8}px)`,
        }}>Two days. One room. You can speak to maybe twenty.</div>
      </div>
      <ChapterLabel text="01 · The Scale" />
    </React.Fragment>
  );
}

// ── SCENE 02 (legacy) — 2,500 counter ──────────────────────────────────────
function Scene02Legacy() {
  const cards = useCardCards();
  const local = useSprite().localTime;
  // Counter zoom + pop
  const counterT = Easing.easeOutBack(clamp((local - 0.3) / 0.7, 0, 1));
  return (
    <React.Fragment>
      <Vignette />
      {/* Cards still drift in background, more blurred */}
      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.6 }}>
        {cards.map((c, i) => <SwarmCard key={i} card={c} sceneT={local + 2.5} dim />)}
      </div>
      {/* Headline pinned smaller toward top */}
      <HighlightedTitle
        parts={[
          { text: 'An 18-hour blur of' },
          { text: 'business cards.', color: ORANGE, italic: true },
        ]}
        x={0} y={210} width={1920}
        size={72} align="center"
        baseColor={FG}
        delay={0} stagger={0.02}
        letterSpacing="-0.025em"
      />
      {/* Big counter */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 410,
        display: 'flex', justifyContent: 'center',
        opacity: clamp(counterT, 0, 1),
        transform: `scale(${0.85 + clamp(counterT, 0, 1) * 0.15})`,
        transformOrigin: 'center top',
      }}>
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: 320, fontWeight: 600,
          color: FG, letterSpacing: '-0.045em', lineHeight: 1,
        }}>
          <Counter from={0} to={2500} duration={1.1} delay={0.35} size={320} weight={600} />
        </div>
      </div>
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 830, textAlign: 'center',
        fontFamily: FONT_MONO, fontSize: 18, color: FG_DIM, letterSpacing: '0.22em',
        opacity: Easing.easeOutCubic(clamp((local - 1.4) / 0.5, 0, 1)),
        transform: `translateY(${(1 - clamp((local - 1.4) / 0.5, 0, 1)) * 10}px)`,
      }}>
        DECISION-MAKERS · TWO DAYS · ONE ROOM
      </div>
      <ChapterLabel text="01 · The Problem" />
    </React.Fragment>
  );
}

// ── SCENE 03 — $18T + 93% side-by-side, simultaneous (WHITE BG) ─────────────
function Scene03() {
  const local = useSprite().localTime;
  const enterT  = Easing.easeOutCubic(clamp((local - 0.2) / 0.5, 0, 1));
  const labelT  = Easing.easeOutCubic(clamp((local - 1.3) / 0.5, 0, 1));
  const theyT   = Easing.easeOutCubic(clamp((local - 4.0) / 0.5, 0, 1));
  return (
    <React.Fragment>
      <div style={{ position: 'absolute', inset: 0, background: '#ffffff' }} />
      <Vignette light />
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 0, bottom: 0,
        display: 'flex', alignItems: 'center',
      }}>
        {/* LEFT: $18T */}
        <div style={{
          flex: 1, textAlign: 'center',
          opacity: enterT, transform: `translateY(${(1 - enterT) * 20}px)`,
        }}>
          <Counter from={0} to={18} duration={1.5} delay={0.2}
            format={(n) => '$' + n + 'T'}
            size={240} weight={700} color={FG_DARK} letterSpacing="-0.04em" />
          <div style={{
            fontFamily: FONT_DISPLAY, fontSize: 28, fontWeight: 500, color: 'rgb(100,90,80)',
            letterSpacing: '0.04em', textTransform: 'uppercase', marginTop: 16,
            opacity: labelT, transform: `translateY(${(1 - labelT) * 10}px)`,
          }}>in combined asset value</div>
        </div>
        {/* Divider */}
        <div style={{ width: 1, background: 'rgba(0,0,0,0.1)', alignSelf: 'stretch', margin: '180px 0' }} />
        {/* RIGHT: 93% C-suite */}
        <div style={{
          flex: 1, textAlign: 'center',
          opacity: enterT, transform: `translateY(${(1 - enterT) * 20}px)`,
        }}>
          <Counter from={0} to={93} duration={1.5} delay={0.2}
            format={(n) => n + '%'}
            size={240} weight={700} color={ORANGE} font={FONT_DISPLAY} letterSpacing="-0.04em" />
          <div style={{
            fontFamily: FONT_DISPLAY, fontSize: 28, fontWeight: 600, fontStyle: 'italic',
            color: ORANGE, letterSpacing: '0.03em', textTransform: 'uppercase', marginTop: 16,
            opacity: labelT, transform: `translateY(${(1 - labelT) * 10}px)`,
          }}>C-suite</div>
        </div>
      </div>
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 140, textAlign: 'center',
        fontFamily: FONT_MONO, fontSize: 16, fontWeight: 700, color: 'rgb(120,110,100)',
        letterSpacing: '0.22em', textTransform: 'uppercase',
        opacity: theyT, transform: `translateY(${(1 - theyT) * 14}px)`,
      }}>June 2–3 · Louvre Palace, Paris</div>
      <ChapterLabel text="02 · The Scale" color={FG_FAINT_LT} />
    </React.Fragment>
  );
}

// ── SCENE 04 — "Make sure you find the right people." (WHITE BG) ────────────
function Scene04() {
  const local = useSprite().localTime;
  const labelT  = Easing.easeOutCubic(clamp((local - 0.1) / 0.4, 0, 1));
  const punchT  = Easing.easeOutCubic(clamp((local - 0.2) / 0.5, 0, 1));
  const bridgeT = Easing.easeOutCubic(clamp((local - 0.7) / 0.45, 0, 1));
  return (
    <React.Fragment>
      <div style={{ position: 'absolute', inset: 0, background: '#ffffff' }} />
      <Vignette light />
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 0, bottom: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: 0,
      }}>
        <div style={{
          fontFamily: FONT_MONO, fontSize: 14, fontWeight: 700, color: 'rgb(150,140,130)',
          letterSpacing: '0.22em', textTransform: 'uppercase', marginBottom: 28,
          opacity: labelT, transform: `translateY(${(1 - labelT) * 6}px)`,
        }}>June 2–3 · Louvre Palace, Paris</div>
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: 92, fontWeight: 700, fontStyle: 'italic',
          color: FG_DARK, letterSpacing: '-0.025em', lineHeight: 1.1, textAlign: 'center',
          opacity: punchT, transform: `translateY(${(1 - punchT) * 20}px)`,
        }}>Make sure you find <span style={{ color: ORANGE }}>the right people.</span></div>
        <div style={{
          marginTop: 36,
          fontFamily: FONT_DISPLAY, fontSize: 40, fontWeight: 500, color: FG_DARK,
          textAlign: 'center', letterSpacing: '-0.02em',
          opacity: bridgeT, transform: `translateY(${(1 - bridgeT) * 10}px)`,
        }}>We built an AI engine to surface the right people for you.</div>
      </div>
      <ChapterLabel text="02 · The Scale" color={FG_FAINT_LT} />
    </React.Fragment>
  );
}

// ── SCENE 05 — Introducing Proof of Talk Matchmaker (PURE WHITE) ──────────
function Scene05() {
  const local = useSprite().localTime;
  return (
    <React.Fragment>
      <div style={{ position: 'absolute', inset: 0, background: '#ffffff' }} />

      {/* INTRODUCING — top of stack */}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 120, textAlign: 'center' }}>
        <HighlightedTitle
          parts={[{ text: 'INTRODUCING', weight: 500 }]}
          x={0} y={0} width={1920}
          size={110} align="center"
          baseColor={FG_DARK}
          delay={0.05}
          stagger={0.08}
          letterSpacing="0.02em"
        />
      </div>

      {/* Proof of Talk logo */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 290,
        display: 'flex', justifyContent: 'center',
        opacity: Easing.easeOutCubic(clamp((local - 0.5) / 0.5, 0, 1)),
        transform: `translateY(${(1 - clamp((local - 0.5) / 0.5, 0, 1)) * 12}px)`,
      }}>
        <POTLogo height={100} invert />
      </div>

      {/* Matchmaker — big italic orange */}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 430, textAlign: 'center' }}>
        <HighlightedTitle
          parts={[{ text: 'Matchmaker', color: ORANGE, italic: true, weight: 500 }]}
          x={0} y={0} width={1920}
          size={200} align="center"
          baseColor={ORANGE}
          delay={0.85}
          stagger={0.07}
          letterSpacing="-0.03em"
        />
      </div>

      {/* Subtitle */}
      <RevealText
        text="Reads every attendee. Surfaces who matters to you. Tells you exactly why."
        x={0} y={700} width={1920}
        size={24} color={FG_FAINT_LT} font={FONT_BODY}
        align="center" delay={1.5} stagger={0.022}
      />

      {/* Louvre photo — fades in from below, full-bleed bottom */}
      {(() => {
        const LOUVRE_DELAY = 1.9;
        const LOUVRE_DUR = 1.4;
        const t = Easing.easeOutCubic(clamp((local - LOUVRE_DELAY) / LOUVRE_DUR, 0, 1));
        return (
          <div style={{
            position: 'absolute', left: 0, right: 0, bottom: 0,
            display: 'flex', justifyContent: 'center',
            opacity: t,
            transform: `translateY(${(1 - t) * 90}px)`,
            pointerEvents: 'none',
          }}>
            <img
              src="louvre.png"
              alt=""
              style={{ width: 1920, height: 'auto', display: 'block' }}
            />
          </div>
        );
      })()}

      <ChapterLabel text="03 · POT Matchmaker" color={FG_FAINT_LT} />
    </React.Fragment>
  );
}

// ── SCENE 06 — Numbers: $18T · 2,500 · 5 (LIGHT BG) ─────────────────────────
// Animated counter cell — ticks from 0 → target while caption fades in.
function NumberCell({ target, prefix = '', suffix = '', format = (n) => n.toLocaleString(), caption, color = FG_DARK, italic = false, delay = 0, countDur = 1.4, captionDelay = 0 }) {
  const local = useSprite().localTime;
  const opT = Easing.easeOutCubic(clamp((local - delay) / 0.35, 0, 1));
  const countT = Easing.easeOutCubic(clamp((local - delay) / countDur, 0, 1));
  const value = Math.round(target * countT);
  const captionT = Easing.easeOutCubic(clamp((local - captionDelay) / 0.5, 0, 1));
  return (
    <div style={{ textAlign: 'center', flex: 1, minWidth: 0 }}>
      <div style={{
        fontFamily: FONT_DISPLAY, fontSize: 240, fontWeight: 500,
        color, letterSpacing: '-0.04em', lineHeight: 1,
        fontStyle: italic ? 'italic' : 'normal',
        opacity: opT,
        transform: `translateY(${(1 - opT) * 18}px)`,
        fontVariantNumeric: 'tabular-nums',
        display: 'inline-block',
      }}>{prefix}{format(value)}{suffix}</div>
      <div style={{
        marginTop: 60,
        fontFamily: FONT_BODY, fontSize: 22, color: FG_FAINT_LT,
        letterSpacing: '0.01em', lineHeight: 1.3,
        opacity: captionT,
        transform: `translateY(${(1 - captionT) * 8}px)`,
      }}>{caption}</div>
    </div>
  );
}

function Scene06() {
  const local = useSprite().localTime;
  return (
    <React.Fragment>
      <div style={{ position: 'absolute', inset: 0, background: BG_LIGHT }} />
      <Vignette light />
      <div style={{
        position: 'absolute', left: 120, right: 120, top: 350,
        display: 'flex', alignItems: 'flex-start', gap: 60,
      }}>
        <NumberCell target={18} prefix="$" suffix="T" caption="in assets, in one room" delay={0.05} countDur={1.2} captionDelay={1.05} />
        <NumberCell target={2500} caption="decision-makers" delay={0.35} countDur={1.4} captionDelay={1.55} />
        <NumberCell target={5} caption="conversations that matter" color={ORANGE} italic delay={0.75} countDur={1.1} captionDelay={1.75} />
      </div>
      <ChapterLabel text="04 · The Numbers" color={FG_FAINT_LT} />
    </React.Fragment>
  );
}

window.PotVideo_PartOne = {
  Scene, useFeatureTransition, StageBG, Vignette, ChapterLabel, Eyebrow, Pill, HighlightedTitle, RevealText, Counter, POTLogo,
  Scene01, Scene02, Scene03, Scene04, Scene05, Scene06,
  BG, BG_LIGHT, FG, FG_DARK, FG_DIM, FG_FAINT, FG_FAINT_LT,
  ORANGE, ORANGE_DARK, ORANGE_BG, CARD, CARD_BORDER, GREEN, GREEN_BG, BLUE, VIOLET,
  FONT_DISPLAY, FONT_BODY, FONT_MONO,
  ATTENDEES,
};
