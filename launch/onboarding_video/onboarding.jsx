// onboarding.jsx — POT Matchmaker "Getting Started" onboarding video.
// 10 scenes · 60.0s · 1920×1080.
//
// Reuses the launch-film visual system: it copies the theme constants, the
// Scene crossfade wrapper, useFeatureTransition (split-layout left-title /
// right-panel), and the UI-mock components (MatchCard, ChatBubble, SlotPill,
// email card, magic-link landing, mutual-match banner, Portrait) directly from
// our_version's video.jsx / video2.jsx. Those modules aren't loaded here, so
// the pieces we need are inlined for isolation — same code, same look.
//
// Depends on animations.jsx (Stage, Sprite, useSprite, useTimeline, Easing,
// clamp, interpolate, animate) which is loaded first in index.html.

const { useMemo } = React;

// ── Theme (shared with the launch film) ──────────────────────────────────────
const BG = 'rgb(8,8,8)';
const BG_LIGHT = 'rgb(250,248,245)';      // cream for the pay-off line
const FG = 'rgb(245,244,239)';
const FG_DARK = 'rgb(15,15,15)';
const FG_DIM = 'rgb(138,138,134)';
const FG_FAINT = 'rgb(90,90,86)';
const FG_FAINT_LT = 'rgb(106,101,92)';
const ORANGE = 'rgb(247,106,12)';         // #F76A0C
const ORANGE_DARK = 'rgb(122,58,20)';
const ORANGE_BG = 'rgb(58,30,10)';
const CARD = 'rgb(22,22,22)';
const CARD_BORDER = 'rgb(42,42,42)';
const GREEN = 'rgb(34,197,94)';
const GREEN_BG = 'rgb(15,42,24)';
const AMBER = 'rgb(245,158,11)';
const AMBER_BG = 'rgb(48,34,8)';
const AMBER_DARK = 'rgb(133,86,12)';
const VIOLET = 'rgb(167,139,250)';

const FONT_DISPLAY = "'Poppins', system-ui, sans-serif";
const FONT_BODY = "'Inter', system-ui, sans-serif";
const FONT_MONO = "'JetBrains Mono', ui-monospace, monospace";
const FONT_SERIF = "'Fraunces', Georgia, serif";

const DUR = 60.0;

// ── Scene wrapper (centered crossfade; splitMode disables global anim) ────────
function Scene({ start, end, fadeIn = 0.7, fadeOut = 0.7, splitMode = false, bg = null, children }) {
  const halfIn = fadeIn / 2;
  const halfOut = fadeOut / 2;
  return (
    <Sprite start={start - halfIn} end={end + halfOut} keepMounted={false}>
      {({ localTime, duration }) => {
        if (splitMode) {
          return (
            <div style={{ position: 'absolute', inset: 0, background: bg || 'transparent' }}>
              {typeof children === 'function' ? children({ localTime, duration }) : children}
            </div>
          );
        }
        let opacity = 1, scale = 1, blur = 0;
        if (localTime < fadeIn) {
          const k = clamp(localTime / fadeIn, 0, 1);
          opacity = Easing.easeInOutCubic(k);
          const z = Easing.easeOutCubic(k);
          scale = 1.07 - 0.07 * z;
          blur = (1 - z) * 10;
        } else if (localTime > duration - fadeOut) {
          const k = clamp((duration - localTime) / fadeOut, 0, 1);
          opacity = Easing.easeInOutCubic(k);
          const z = Easing.easeInCubic(k);
          scale = 1.00 + (1 - z) * 0.05;
          blur = (1 - z) * 7;
        }
        return (
          <div style={{
            position: 'absolute', inset: 0,
            opacity, transform: `scale(${scale})`, transformOrigin: 'center',
            filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : 'none',
            background: bg || 'transparent', willChange: 'opacity, transform, filter',
          }}>
            {typeof children === 'function' ? children({ localTime, duration }) : children}
          </div>
        );
      }}
    </Sprite>
  );
}

// ── Feature transition hook (left title crossfade + right panel slide) ────────
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

function FadeGroup({ children, opacity }) {
  return <div style={{ position: 'absolute', inset: 0, opacity, willChange: 'opacity' }}>{children}</div>;
}
function SlideGroup({ children, ty }) {
  return <div style={{ position: 'absolute', inset: 0, transform: `translateY(${ty}px)`, willChange: 'transform' }}>{children}</div>;
}

// ── Backgrounds ──────────────────────────────────────────────────────────────
function StageBG() {
  return <div style={{ position: 'absolute', inset: 0, background: BG }} />;
}
function PitchBlackBG() {
  return (
    <div style={{
      position: 'absolute', inset: 0,
      background: `
        repeating-linear-gradient(135deg, rgba(255,255,255,0.009) 0 1px, transparent 1px 60px),
        repeating-linear-gradient(45deg,  rgba(255,255,255,0.009) 0 1px, transparent 1px 60px),
        rgb(8,8,8)
      `,
    }} />
  );
}
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

// ── Brand logo (PNG) ─────────────────────────────────────────────────────────
function POTLogo({ height = 56, invert = false }) {
  return (
    <img src="pot-logo.png" alt="Proof of Talk" style={{
      height, width: 'auto', display: 'block',
      filter: invert ? 'invert(1)' : 'none', opacity: invert ? 0.94 : 1,
    }} />
  );
}

// ── Text reveal helpers ──────────────────────────────────────────────────────
function HighlightedTitle({
  parts, x, y, width, size = 88, font = FONT_DISPLAY, weight = 400,
  baseColor = FG, align = 'left', delay = 0, stagger = 0.10,
  lineHeight = 1.1, letterSpacing = '-0.02em', wordGap = '0.4em',
}) {
  const local = useSprite().localTime;
  const flat = useMemo(() => {
    const out = [];
    parts.forEach((p) => {
      p.text.split(' ').forEach((w) => {
        out.push({ text: w, color: p.color || baseColor, italic: !!p.italic, weight: p.weight || weight });
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
            display: 'inline-block', color: w.color,
            fontStyle: w.italic ? 'italic' : 'normal', fontWeight: w.weight,
            opacity: t, transform: `translateY(${(1 - t) * 20}px)`,
            whiteSpace: 'nowrap', marginRight: isLast ? 0 : wordGap,
            willChange: 'transform, opacity',
          }}>{w.text}</span>
        );
      })}
    </div>
  );
}

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
            whiteSpace: 'nowrap', marginRight: isLast ? 0 : wordGap,
          }}>{w}</span>
        );
      })}
    </div>
  );
}

// ── Feature header (centered title + subtitle), used by split scenes ──────────
function FeatureHeader({ title, subtitle, delay = 0, titleSize = 86 }) {
  return (
    <React.Fragment>
      <HighlightedTitle
        parts={[{ text: title, italic: true, weight: 600 }]}
        x={0} y={100} width={1920}
        size={titleSize} font={FONT_DISPLAY} weight={600}
        baseColor={FG} align="center"
        delay={delay + 0.05} stagger={0.10}
        letterSpacing="-0.025em" lineHeight={1.0} wordGap="0.5em"
      />
      <div style={{ position: 'absolute', left: 0, right: 0, top: 248 }}>
        <RevealText
          text={subtitle} x={240} y={0} width={1440}
          size={26} color={FG_DIM} font={FONT_BODY} align="center"
          delay={delay + 0.4} stagger={0.05} lineHeight={1.55}
        />
      </div>
    </React.Fragment>
  );
}

// ── Portrait (photo or initials placeholder) ─────────────────────────────────
function Portrait({ initials, size = 90, accent = false, imageSrc = null }) {
  if (imageSrc) {
    return (
      <div style={{
        width: size, height: Math.round(size * 1.35),
        borderRadius: 10, overflow: 'hidden',
        border: `2px solid ${accent ? ORANGE : 'rgba(255,255,255,0.15)'}`,
        flexShrink: 0, background: '#1a1a1a',
      }}>
        <img src={imageSrc} alt="" style={{
          width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center top', display: 'block',
        }} />
      </div>
    );
  }
  const grad = accent
    ? `linear-gradient(135deg, rgba(247,106,12,0.25), rgba(247,106,12,0.05))`
    : `linear-gradient(135deg, rgba(180,170,160,0.35), rgba(120,110,100,0.18))`;
  return (
    <div style={{
      width: size, height: size, borderRadius: 10,
      background: `${grad}, repeating-linear-gradient(135deg, rgba(255,255,255,0.03) 0 6px, rgba(255,255,255,0) 6px 12px), rgb(48,46,42)`,
      border: `1px solid ${accent ? ORANGE_DARK : 'rgb(58,58,58)'}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: FONT_BODY, fontWeight: 700, fontSize: size * 0.34,
      color: accent ? ORANGE : 'rgb(210,206,196)',
      boxShadow: 'inset 0 -16px 30px rgba(0,0,0,0.25)', flexShrink: 0,
    }}>{initials}</div>
  );
}

// ── Cursor + ripple (used for "tap" beats) ───────────────────────────────────
function Cursor({ x, y, tapAt, local, size = 34 }) {
  // tapAt: scene-local time the click lands. We pop a ripple at tapAt and
  // scale the cursor down briefly around it.
  const appear = Easing.easeOutCubic(clamp((local - (tapAt - 0.5)) / 0.4, 0, 1));
  const press = clamp((local - tapAt) / 0.18, 0, 1);
  const pressScale = 1 - 0.22 * Math.sin(press * Math.PI);
  const rippleT = Easing.easeOutCubic(clamp((local - tapAt) / 0.55, 0, 1));
  const showRipple = local >= tapAt && rippleT < 1;
  return (
    <div style={{ position: 'absolute', left: x, top: y, pointerEvents: 'none', zIndex: 30 }}>
      {showRipple && (
        <div style={{
          position: 'absolute', left: -6, top: -6,
          width: 12 + rippleT * 64, height: 12 + rippleT * 64,
          marginLeft: -(rippleT * 32), marginTop: -(rippleT * 32),
          borderRadius: 999, border: `2px solid ${ORANGE}`,
          opacity: (1 - rippleT) * 0.8,
        }} />
      )}
      <svg width={size} height={size} viewBox="0 0 24 24" style={{
        opacity: appear, transform: `scale(${appear * pressScale})`, transformOrigin: 'top left',
        filter: 'drop-shadow(0 4px 10px rgba(0,0,0,0.6))',
      }}>
        <path d="M4 2 L4 20 L9 15 L12.5 22 L15 21 L11.5 14 L18 14 Z"
          fill="#fff" stroke="rgba(0,0,0,0.6)" strokeWidth="1" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SCENE 01 · Title + hook — 0:00–0:05 (pure white)
// ════════════════════════════════════════════════════════════════════════════
function S01_Title() {
  const local = useSprite().localTime;
  return (
    <React.Fragment>
      <div style={{ position: 'absolute', inset: 0, background: '#ffffff' }} />
      {/* YOU'RE IN. — black heading, word by word */}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 300, textAlign: 'center' }}>
        <HighlightedTitle
          parts={[{ text: "YOU'RE IN.", weight: 700 }]}
          x={0} y={0} width={1920} size={96} align="center"
          baseColor={FG_DARK} delay={0.05} stagger={0.09} letterSpacing="0.01em"
        />
      </div>
      {/* Matchmaker — giant italic orange */}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 440, textAlign: 'center' }}>
        <HighlightedTitle
          parts={[{ text: 'Matchmaker', color: ORANGE, italic: true, weight: 500 }]}
          x={0} y={0} width={1920} size={180} align="center"
          baseColor={ORANGE} delay={0.5} stagger={0.07} letterSpacing="-0.03em"
        />
      </div>
      {/* Subtitle — grey italic */}
      <RevealText
        text="Somewhere in this room is the conversation that changes your year."
        x={0} y={700} width={1920} size={28} color={FG_FAINT_LT}
        font={FONT_BODY} italic align="center" delay={1.4} stagger={0.03}
      />
    </React.Fragment>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SCENE 02 · Ticket → redeemed → the email (magic link) — 0:05–0:12 (split)
// ════════════════════════════════════════════════════════════════════════════
function S02_Email() {
  const local = useSprite().localTime;
  const { leftOpacity, panelTy } = useFeatureTransition();
  const emailT = Easing.easeOutCubic(clamp((local - 0.4) / 0.5, 0, 1));
  const ctaT   = Easing.easeOutBack(clamp((local - 1.0) / 0.4, 0, 1));
  const capT   = Easing.easeOutCubic(clamp((local - 1.5) / 0.4, 0, 1));
  const tapAt  = 2.2;
  const tapPress = clamp((local - tapAt) / 0.18, 0, 1);
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        {/* LEFT PANEL */}
        <div style={{ position: 'absolute', left: 120, top: 360, width: 620 }}>
          <HighlightedTitle
            parts={[{ text: 'You bought your pass. You redeemed it.', italic: true, weight: 600 }]}
            x={0} y={0} width={620} size={64} font={FONT_DISPLAY} weight={600}
            baseColor={FG} align="left" delay={0.1} stagger={0.06}
            letterSpacing="-0.02em" lineHeight={1.08} wordGap="0.35em"
          />
        </div>
        <RevealText
          text="Then this lands in your inbox."
          x={120} y={620} width={620} size={26} color={FG_DIM}
          font={FONT_BODY} align="left" delay={0.9} stagger={0.04}
        />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        {/* Email card (RIGHT) */}
        <div style={{
          position: 'absolute', left: 880, top: 300, width: 880,
          background: CARD, border: `1px solid ${CARD_BORDER}`,
          borderRadius: 18, padding: '36px 40px',
          opacity: emailT, transform: `translateY(${(1 - emailT) * 16}px)`,
          boxShadow: '0 30px 90px rgba(0,0,0,0.55)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}><POTLogo height={30} /></div>
          <div style={{ marginTop: 10, fontFamily: FONT_MONO, fontSize: 12, color: FG_FAINT, letterSpacing: '0.1em' }}>
            From hello@proofoftalk.io
          </div>
          <div style={{
            marginTop: 30, fontFamily: FONT_DISPLAY, fontSize: 42, fontWeight: 500,
            color: FG, lineHeight: 1.15, letterSpacing: '-0.02em',
          }}>Your introductions are ready.</div>
          {/* CTA — the magic link */}
          <div style={{
            position: 'relative', marginTop: 34, display: 'inline-flex',
            opacity: clamp(ctaT, 0, 1),
            transform: `scale(${(0.85 + clamp(ctaT, 0, 1) * 0.15) * (1 - tapPress * 0.05)})`,
            transformOrigin: 'left',
          }}>
            <div style={{
              background: ORANGE, color: '#fff', padding: '18px 36px', borderRadius: 999,
              fontFamily: FONT_BODY, fontWeight: 700, fontSize: 18,
              boxShadow: `0 24px 60px rgba(247,106,12,${0.40 * clamp(ctaT, 0, 1) + tapPress * 0.2})`,
            }}>Open my matches →</div>
          </div>
          <div style={{
            marginTop: 18, fontFamily: FONT_BODY, fontSize: 16, color: FG_DIM,
            opacity: capT, transform: `translateY(${(1 - capT) * 8}px)`,
          }}>No app. No password yet. Just tap.</div>
        </div>
        {/* Cursor taps CTA */}
        <Cursor x={1000} y={555} tapAt={tapAt} local={local} />
      </SlideGroup>
    </React.Fragment>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SCENE 03 · Tap in → set a password — 0:12–0:18 (split)
// ════════════════════════════════════════════════════════════════════════════
function S03_Password() {
  const local = useSprite().localTime;
  const { leftOpacity, panelTy } = useFeatureTransition();
  const cardT  = Easing.easeOutCubic(clamp((local - 0.5) / 0.5, 0, 1));
  const fillT  = Easing.easeOutCubic(clamp((local - 1.1) / 0.4, 0, 1));
  const dots   = Math.round(8 * fillT);
  const tapAt  = 1.8;
  const tapPress = clamp((local - tapAt) / 0.18, 0, 1);
  const chipT  = Easing.easeOutBack(clamp((local - 2.3) / 0.45, 0, 1));
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <div style={{ position: 'absolute', left: 120, top: 380, width: 600 }}>
          <HighlightedTitle
            parts={[{ text: "One tap and you're in.", italic: true, weight: 600 }]}
            x={0} y={0} width={600} size={80} font={FONT_DISPLAY} weight={600}
            baseColor={FG} align="left" delay={0.1} stagger={0.07}
            letterSpacing="-0.02em" lineHeight={1.05} wordGap="0.35em"
          />
        </div>
        <RevealText
          text="Set a password to make the account yours."
          x={120} y={600} width={600} size={26} color={FG_DIM}
          font={FONT_BODY} align="left" delay={0.9} stagger={0.04}
        />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        {/* Password card (RIGHT) */}
        <div style={{
          position: 'absolute', left: 880, top: 320, width: 860,
          background: CARD, border: `1px solid ${CARD_BORDER}`,
          borderRadius: 18, padding: '36px 40px',
          opacity: cardT, transform: `translateY(${(1 - cardT) * 16}px)`,
          boxShadow: '0 30px 90px rgba(0,0,0,0.55)',
        }}>
          <div style={{ fontFamily: FONT_DISPLAY, fontSize: 36, fontWeight: 500, color: FG, letterSpacing: '-0.02em' }}>
            Welcome to Proof of Talk
          </div>
          <div style={{ marginTop: 30, fontFamily: FONT_MONO, fontSize: 12, color: FG_FAINT, letterSpacing: '0.16em' }}>
            CREATE A PASSWORD
          </div>
          <div style={{
            marginTop: 12, height: 60, borderRadius: 12,
            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.14)',
            display: 'flex', alignItems: 'center', padding: '0 20px',
            fontFamily: FONT_MONO, fontSize: 26, color: FG, letterSpacing: '0.3em',
          }}>{'•'.repeat(dots)}<span style={{ opacity: dots < 8 ? 1 : 0, color: ORANGE, letterSpacing: 0 }}>▍</span></div>
          {/* Save & continue CTA */}
          <div style={{
            position: 'relative', marginTop: 26, display: 'inline-flex',
            transform: `scale(${1 - tapPress * 0.05})`, transformOrigin: 'left',
          }}>
            <div style={{
              background: ORANGE, color: '#fff', padding: '16px 32px', borderRadius: 999,
              fontFamily: FONT_BODY, fontWeight: 700, fontSize: 17,
              boxShadow: `0 16px 40px rgba(247,106,12,${0.35 + tapPress * 0.2})`,
            }}>Save &amp; continue →</div>
          </div>
        </div>
        {/* Green "Account secured" chip */}
        <div style={{
          position: 'absolute', left: 880, top: 640,
          opacity: clamp(chipT, 0, 1), transform: `scale(${0.8 + clamp(chipT, 0, 1) * 0.2})`, transformOrigin: 'left',
        }}>
          <div style={{
            padding: '14px 24px', background: GREEN_BG, border: '1px solid rgba(34,197,94,0.45)',
            borderRadius: 10, fontFamily: FONT_BODY, fontWeight: 700, fontSize: 18, color: GREEN,
          }}>✓ Account secured</div>
        </div>
        <Cursor x={1000} y={560} tapAt={tapAt} local={local} />
      </SlideGroup>
    </React.Fragment>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SCENE 04 · Enrich your profile → unlock more — 0:18–0:25 (split)
// ════════════════════════════════════════════════════════════════════════════
function ProfileField({ label, value, delay = 0, y, typeDur = 1.1, pill = false }) {
  const local = useSprite().localTime;
  const enter = Easing.easeOutCubic(clamp((local - delay) / 0.5, 0, 1));
  const shown = Math.floor(value.length * Easing.easeOutCubic(clamp((local - delay - 0.15) / typeDur, 0, 1)));
  const pillT = Easing.easeOutBack(clamp((local - delay - 0.2) / 0.4, 0, 1));
  return (
    <div style={{
      position: 'absolute', left: 880, top: y, width: 880,
      opacity: enter, transform: `translateY(${(1 - enter) * 12}px)`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: FG_FAINT, letterSpacing: '0.16em' }}>{label}</div>
        {pill && (
          <div style={{
            padding: '7px 16px', borderRadius: 999,
            background: 'rgba(247,106,12,0.10)', border: `1px solid ${ORANGE_DARK}`,
            fontFamily: FONT_BODY, fontWeight: 700, fontSize: 13, color: ORANGE,
            opacity: clamp(pillT, 0, 1), transform: `scale(${0.8 + clamp(pillT, 0, 1) * 0.2})`,
          }}>↻ Regenerate with AI</div>
        )}
      </div>
      <div style={{
        marginTop: 12, background: CARD, border: `1px solid ${CARD_BORDER}`,
        borderRadius: 14, padding: '18px 22px',
        fontFamily: FONT_BODY, fontSize: 21, color: FG, lineHeight: 1.4, minHeight: 30,
      }}>
        {value.slice(0, shown)}<span style={{ opacity: shown < value.length ? 1 : 0, color: ORANGE }}>▍</span>
      </div>
    </div>
  );
}

function S04_Enrich() {
  const local = useSprite().localTime;
  const { leftOpacity, panelTy } = useFeatureTransition();
  // Progress bar fills 2.6→3.3; banner 3.4
  const barStart = 2.6, barDur = 0.7;
  const barT = Easing.easeOutCubic(clamp((local - barStart) / barDur, 0, 1));
  const pct = Math.round(40 + 55 * barT); // 40 → 95
  const bannerT = Easing.easeOutCubic(clamp((local - 3.4) / 0.5, 0, 1));
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <div style={{ position: 'absolute', left: 120, top: 360, width: 600 }}>
          <HighlightedTitle
            parts={[{ text: 'The more it knows, the more it opens up.', italic: true, weight: 600 }]}
            x={0} y={0} width={600} size={72} font={FONT_DISPLAY} weight={600}
            baseColor={FG} align="left" delay={0.1} stagger={0.06}
            letterSpacing="-0.02em" lineHeight={1.08} wordGap="0.3em"
          />
        </div>
        <RevealText
          text="Add your goals and a short write-up — unlock sharper matches and more of the room."
          x={120} y={680} width={620} size={25} color={FG_DIM}
          font={FONT_BODY} align="left" delay={1.0} stagger={0.035} lineHeight={1.5}
        />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        <ProfileField
          label="YOUR GOALS AT POT 2026"
          value="Raising a seed round · seeking infra VCs and custody partners"
          delay={0.7} y={250} typeDur={1.3}
        />
        <ProfileField
          label="YOUR WRITE-UP"
          value="Founder building post-MiCAR custody rails. At POT to meet investors who write early infra cheques and partners who already hold the licences."
          delay={1.7} y={470} typeDur={1.4} pill
        />
        {/* Progress banner */}
        <div style={{ position: 'absolute', left: 880, top: 770, width: 880 }}>
          <div style={{
            height: 10, borderRadius: 999, background: 'rgba(255,255,255,0.08)', overflow: 'hidden',
          }}>
            <div style={{ height: '100%', width: `${pct}%`, background: GREEN, borderRadius: 999 }} />
          </div>
          <div style={{
            marginTop: 16, display: 'inline-flex',
            opacity: bannerT, transform: `translateY(${(1 - bannerT) * 10}px)`,
          }}>
            <div style={{
              padding: '12px 22px', background: GREEN_BG, border: '1px solid rgba(34,197,94,0.45)',
              borderRadius: 10, fontFamily: FONT_BODY, fontWeight: 700, fontSize: 18, color: GREEN,
            }}>Profile {pct}% — matches refreshing ✓</div>
          </div>
        </div>
      </SlideGroup>
    </React.Fragment>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SCENE 05 · Your matches, ranked — 0:25–0:30 (split)
// ════════════════════════════════════════════════════════════════════════════
function S05_Matches() {
  const local = useSprite().localTime;
  const { leftOpacity, panelTy } = useFeatureTransition();
  const cardDelay = 0.8;
  const t = Easing.easeOutCubic(clamp((local - cardDelay) / 0.6, 0, 1));
  const shimmerT = Easing.easeInOutCubic(clamp((local - 1.5) / 0.65, 0, 1));
  const btnT = Easing.easeOutBack(clamp((local - 2.1) / 0.45, 0, 1));
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <div style={{ position: 'absolute', left: 120, top: 400, width: 560 }}>
          <HighlightedTitle
            parts={[{ text: 'Your matches.', italic: true, weight: 600 }]}
            x={0} y={0} width={560} size={80} font={FONT_DISPLAY} weight={600}
            baseColor={FG} align="left" delay={0.1} stagger={0.08}
            letterSpacing="-0.02em" lineHeight={1.05} wordGap="0.35em"
          />
        </div>
        <RevealText
          text="Ranked — with a reason for every one."
          x={120} y={560} width={560} size={26} color={FG_DIM}
          font={FONT_BODY} align="left" delay={0.9} stagger={0.04}
        />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        <div style={{
          position: 'absolute', left: 780, top: 330, width: 980,
          background: CARD, border: `1px solid ${ORANGE_DARK}`, borderRadius: 18,
          padding: '22px 28px', opacity: t, transform: `translateX(${(1 - t) * 40}px)`,
          boxShadow: '0 24px 70px rgba(0,0,0,0.5)', overflow: 'hidden',
        }}>
          {/* Header row: #1 Complementary · 82% */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ fontFamily: FONT_BODY, fontWeight: 700, fontSize: 18, color: FG_FAINT }}>#1</div>
            <div style={{
              padding: '7px 16px', borderRadius: 999,
              background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.14)',
              fontFamily: FONT_BODY, fontWeight: 700, fontSize: 14, color: FG,
            }}>Complementary</div>
            <div style={{ flex: 1 }} />
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontFamily: FONT_MONO, fontSize: 10, color: FG_FAINT, letterSpacing: '0.14em' }}>COMPATIBILITY</div>
              <div style={{ marginTop: 4, fontFamily: FONT_DISPLAY, fontSize: 32, fontWeight: 600, color: GREEN }}>82%</div>
            </div>
          </div>
          {/* Identity row */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 20, marginTop: 18 }}>
            <Portrait initials="MC" size={70} accent imageSrc="figures/mira.png" />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: FONT_BODY, fontWeight: 700, fontSize: 26, color: FG }}>Mira Chen</div>
              <div style={{ fontFamily: FONT_BODY, fontSize: 16, color: FG_DIM, marginTop: 2 }}>GP · Vega Ventures</div>
            </div>
          </div>
          {/* Why this meeting matters */}
          <div style={{
            marginTop: 16, background: 'rgba(247,106,12,0.08)', border: `1px solid ${ORANGE_DARK}`,
            borderRadius: 8, padding: '12px 16px',
            fontFamily: FONT_BODY, fontWeight: 700, fontSize: 15, color: ORANGE,
          }}>
            <span style={{ color: FG_DIM, fontWeight: 500 }}>Why this meeting matters — </span>
            She raises from the LPs you need.
          </div>
          {/* Action buttons */}
          <div style={{
            marginTop: 18, display: 'flex', gap: 14,
            opacity: clamp(btnT, 0, 1), transform: `scale(${0.9 + clamp(btnT, 0, 1) * 0.1})`, transformOrigin: 'left',
          }}>
            <div style={{
              padding: '13px 36px', borderRadius: 999, background: ORANGE, color: '#fff',
              fontFamily: FONT_BODY, fontWeight: 700, fontSize: 16,
            }}>Accept</div>
            <div style={{
              padding: '13px 36px', borderRadius: 999, background: 'transparent',
              border: '1px solid rgba(255,255,255,0.18)', color: FG_DIM,
              fontFamily: FONT_BODY, fontWeight: 600, fontSize: 16,
            }}>Decline</div>
          </div>
          {/* Shimmer sweep */}
          <div style={{ position: 'absolute', inset: 0, borderRadius: 18, overflow: 'hidden', pointerEvents: 'none' }}>
            <div style={{
              position: 'absolute', top: 0, bottom: 0, width: 220,
              left: -220 + shimmerT * (980 + 440),
              background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)',
              transform: 'skewX(-12deg)',
            }} />
          </div>
        </div>
      </SlideGroup>
    </React.Fragment>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SCENE 06 · Accept → both yes → messages unlock (THE key beat) — 0:30–0:39
// ════════════════════════════════════════════════════════════════════════════
function S06_Mutual() {
  const local = useSprite().localTime;
  // Headline 2 lines: 0.2 / line by line
  const h1 = Easing.easeOutCubic(clamp((local - 0.2) / 0.6, 0, 1));
  const h2 = Easing.easeOutCubic(clamp((local - 0.55) / 0.6, 0, 1));
  const tapAt = 1.3;
  const amberT = Easing.easeOutBack(clamp((local - 1.7) / 0.45, 0, 1));
  // Nodes appear 2.6; Mira flips 3.8; connector grows 3.8; banner 4.6; subline 5.3
  const nodeT = Easing.easeOutBack(clamp((local - 2.6) / 0.5, 0, 1));
  const flipT = Easing.easeInOutCubic(clamp((local - 3.8) / 0.6, 0, 1));
  const lineT = Easing.easeInOutCubic(clamp((local - 3.8) / 0.6, 0, 1));
  const bannerT = Easing.easeOutCubic(clamp((local - 4.6) / 0.55, 0, 1));
  const subT = Easing.easeOutCubic(clamp((local - 5.3) / 0.5, 0, 1));
  // Mira pending dots pulse before flip
  const miraIsCheck = flipT > 0.5;
  return (
    <React.Fragment>
      <PitchBlackBG />
      <Vignette />
      {/* Headline — 2 lines */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 140, textAlign: 'center',
        fontFamily: FONT_DISPLAY, fontSize: 64, fontWeight: 600, fontStyle: 'italic',
        color: FG, letterSpacing: '-0.02em', lineHeight: 1.15,
        opacity: h1, transform: `translateY(${(1 - h1) * 16}px)`,
      }}>Accept the people you want.</div>
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 232, textAlign: 'center',
        fontFamily: FONT_DISPLAY, fontSize: 64, fontWeight: 600, fontStyle: 'italic',
        color: FG, letterSpacing: '-0.02em', lineHeight: 1.15,
        opacity: h2, transform: `translateY(${(1 - h2) * 16}px)`,
      }}>Chat opens when you <span style={{ color: ORANGE }}>both</span> accept.</div>

      {/* Amber "awaiting" badge — real app copy */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 420, display: 'flex', justifyContent: 'center',
        opacity: clamp(amberT, 0, 1), transform: `translateY(${(1 - clamp(amberT, 0, 1)) * 8}px) scale(${0.85 + clamp(amberT, 0, 1) * 0.15})`,
      }}>
        <div style={{
          padding: '13px 24px', background: AMBER_BG, border: `1px solid ${AMBER_DARK}`,
          borderRadius: 999, fontFamily: FONT_BODY, fontWeight: 700, fontSize: 18, color: AMBER,
          display: 'inline-flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ width: 9, height: 9, borderRadius: 5, background: AMBER }} />
          You accepted · Awaiting their acceptance
        </div>
      </div>
      {/* Cursor taps Accept (near the amber badge area / standing in for the card button) */}
      <Cursor x={1130} y={445} tapAt={tapAt} local={local} />

      {/* Two avatar nodes with check/pending status + connector */}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 560, opacity: clamp(nodeT, 0, 1) }}>
        {/* You node */}
        <div style={{ position: 'absolute', left: 700, top: 0, textAlign: 'center', transform: `scale(${0.7 + clamp(nodeT, 0, 1) * 0.3})` }}>
          <Portrait initials="S" size={120} imageSrc="figures/you.png" />
          <div style={{ marginTop: 12, fontFamily: FONT_BODY, fontWeight: 700, fontSize: 20, color: FG }}>You ✓</div>
        </div>
        {/* Connector line — grows from You to Mira */}
        <div style={{
          position: 'absolute', left: 822, top: 78, width: 276, height: 3,
          background: `linear-gradient(90deg, ${ORANGE_DARK} 0%, ${ORANGE} 50%, ${ORANGE_DARK} 100%)`,
          transform: `scaleX(${lineT})`, transformOrigin: 'left',
        }} />
        {/* Mira node */}
        <div style={{ position: 'absolute', left: 1098, top: 0, textAlign: 'center', transform: `scale(${0.7 + clamp(nodeT, 0, 1) * 0.3})` }}>
          <Portrait initials="M" size={120} accent imageSrc="figures/mira.png" />
          <div style={{ marginTop: 12, fontFamily: FONT_BODY, fontWeight: 700, fontSize: 20, color: miraIsCheck ? FG : AMBER }}>
            {miraIsCheck ? 'Mira ✓' : (
              <span style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}>
                Mira
                {[0, 1, 2].map(i => {
                  const ph = (local * 2.2 + i * 0.22) % 1;
                  const o = 0.3 + 0.7 * Math.max(0, Math.sin(ph * Math.PI));
                  return <span key={i} style={{ width: 6, height: 6, borderRadius: 3, background: AMBER, opacity: o }} />;
                })}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Green mutual banner — real app copy */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 800, display: 'flex', justifyContent: 'center',
        opacity: bannerT, transform: `translateY(${(1 - bannerT) * 12}px)`,
      }}>
        <div style={{
          padding: '18px 30px', background: GREEN_BG, border: '1px solid rgba(34,197,94,0.5)',
          borderRadius: 12, fontFamily: FONT_BODY, fontWeight: 700, fontSize: 24, color: GREEN,
          boxShadow: `0 0 ${30 * bannerT}px rgba(34,197,94,0.25)`,
        }}>Mutual match — both accepted!</div>
      </div>
      {/* Sub-line */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 880, textAlign: 'center',
        fontFamily: FONT_BODY, fontSize: 22, color: FG_DIM,
        opacity: subT, transform: `translateY(${(1 - subT) * 10}px)`,
      }}>Now it's in your Messages.</div>
    </React.Fragment>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SCENE 07 · Message + book — 0:39–0:45 (split)
// ════════════════════════════════════════════════════════════════════════════
function SlotPill({ day, time, delay = 0, accent = false }) {
  const local = useSprite().localTime;
  const t = Easing.easeOutBack(clamp((local - delay) / 0.45, 0, 1));
  return (
    <div style={{
      padding: '14px 0', borderRadius: 10,
      background: accent ? 'rgba(247,106,12,0.14)' : 'rgba(255,255,255,0.04)',
      border: `1px solid ${accent ? ORANGE_DARK : CARD_BORDER}`, textAlign: 'center',
      opacity: clamp(t, 0, 1), transform: `scale(${0.85 + clamp(t, 0, 1) * 0.15})`,
    }}>
      <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: FG_FAINT, letterSpacing: '0.14em' }}>{day}</div>
      <div style={{ marginTop: 6, fontFamily: FONT_BODY, fontWeight: 600, fontSize: 22, color: accent ? ORANGE : FG }}>{time}</div>
    </div>
  );
}

function S07_MessageBook() {
  const local = useSprite().localTime;
  const { leftOpacity, panelTy } = useFeatureTransition();
  const headerT = Easing.easeOutCubic(clamp((local - 0.6) / 0.45, 0, 1));
  const bubbleT = Easing.easeOutCubic(clamp((local - 1.1) / 0.6, 0, 1));
  const msg = "Hi Mira — free to talk LPs on Day 1?";
  const shown = Math.floor(msg.length * Easing.easeOutCubic(clamp((local - 1.25) / 1.0, 0, 1)));
  const confirmT = Easing.easeOutCubic(clamp((local - 2.7) / 0.55, 0, 1));
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <div style={{ position: 'absolute', left: 120, top: 400, width: 580 }}>
          <HighlightedTitle
            parts={[{ text: 'Now you can write — and book.', italic: true, weight: 600 }]}
            x={0} y={0} width={580} size={68} font={FONT_DISPLAY} weight={600}
            baseColor={FG} align="left" delay={0.1} stagger={0.06}
            letterSpacing="-0.02em" lineHeight={1.08} wordGap="0.3em"
          />
        </div>
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        {/* Thread header */}
        <div style={{
          position: 'absolute', left: 780, top: 260, width: 980,
          display: 'flex', alignItems: 'center', gap: 16,
          opacity: headerT, transform: `translateY(${(1 - headerT) * 12}px)`,
        }}>
          <Portrait initials="MC" size={56} accent imageSrc="figures/mira.png" />
          <div>
            <div style={{ fontFamily: FONT_BODY, fontWeight: 700, fontSize: 24, color: FG }}>Mira Chen</div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
              <span style={{ width: 9, height: 9, borderRadius: 5, background: GREEN }} />
              <span style={{ fontFamily: FONT_BODY, fontSize: 14, color: GREEN, fontWeight: 600 }}>Mutual match</span>
            </div>
          </div>
        </div>
        {/* Custom message bubble (ENABLED composer) */}
        <div style={{
          position: 'absolute', left: 980, top: 370, width: 780,
          opacity: bubbleT, transform: `translateY(${(1 - bubbleT) * 14}px)`,
        }}>
          <div style={{
            background: 'rgba(247,106,12,0.10)', border: `1px solid ${ORANGE_DARK}`,
            borderRadius: 14, borderBottomRightRadius: 4, padding: '18px 22px',
            fontFamily: FONT_BODY, fontSize: 20, color: FG, lineHeight: 1.4,
          }}>{msg.slice(0, shown)}<span style={{ opacity: shown < msg.length ? 1 : 0, color: ORANGE }}>▍</span></div>
        </div>
        {/* Slot row */}
        <div style={{
          position: 'absolute', left: 780, top: 500, width: 980,
          background: CARD, border: `1px solid ${CARD_BORDER}`, borderRadius: 16, padding: '22px 26px',
        }}>
          <div style={{ fontFamily: FONT_BODY, fontSize: 15, color: FG_DIM }}>Both free at — tap to book</div>
          <div style={{ marginTop: 18, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
            <SlotPill day="Tue" time="14:15" delay={1.9} />
            <SlotPill day="Tue" time="16:00" delay={2.0} />
            <SlotPill day="Wed" time="09:45" delay={2.1} />
            <SlotPill day="Wed" time="11:30" delay={2.2} accent />
            <SlotPill day="Wed" time="15:00" delay={2.3} />
          </div>
        </div>
        {/* Confirmed card */}
        <div style={{
          position: 'absolute', left: 780, top: 720, width: 980,
          background: 'rgba(247,106,12,0.10)', border: `1px solid ${ORANGE_DARK}`,
          borderRadius: 16, padding: '20px 26px',
          opacity: confirmT, transform: `translateY(${(1 - confirmT) * 16}px)`,
        }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            fontFamily: FONT_MONO, fontSize: 12, color: ORANGE, letterSpacing: '0.18em',
          }}>
            <span style={{ width: 8, height: 8, borderRadius: 4, background: ORANGE }} />
            CONFIRMED
          </div>
          <div style={{ marginTop: 10, fontFamily: FONT_DISPLAY, fontSize: 34, fontWeight: 500, color: FG, letterSpacing: '-0.02em' }}>
            Wed · 11:30
          </div>
        </div>
      </SlideGroup>
    </React.Fragment>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SCENE 08 · Don't wait — Threads — 0:45–0:52 (split)
// ════════════════════════════════════════════════════════════════════════════
function ThreadRow({ topic, count, delay = 0, y }) {
  const local = useSprite().localTime;
  const t = Easing.easeOutCubic(clamp((local - delay) / 0.45, 0, 1));
  return (
    <div style={{
      position: 'absolute', left: 780, top: y, width: 980,
      background: CARD, border: `1px solid ${CARD_BORDER}`, borderRadius: 14,
      padding: '20px 26px', display: 'flex', alignItems: 'center', gap: 18,
      opacity: t, transform: `translateY(${(1 - t) * 12}px)`,
    }}>
      <div style={{ fontFamily: FONT_DISPLAY, fontSize: 26, fontWeight: 600, color: ORANGE }}>#</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: FONT_BODY, fontWeight: 700, fontSize: 22, color: FG }}>{topic}</div>
        {count != null && (
          <div style={{ fontFamily: FONT_BODY, fontSize: 14, color: FG_DIM, marginTop: 3 }}>{count} in this discussion</div>
        )}
      </div>
      <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: FG_FAINT, letterSpacing: '0.12em' }}>OPEN →</div>
    </div>
  );
}

function S08_Threads() {
  const local = useSprite().localTime;
  const { leftOpacity, panelTy } = useFeatureTransition();
  const inputT = Easing.easeOutBack(clamp((local - 2.0) / 0.4, 0, 1));
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <div style={{ position: 'absolute', left: 120, top: 380, width: 580 }}>
          <HighlightedTitle
            parts={[{ text: "Don't want to wait for a yes?", italic: true, weight: 600 }]}
            x={0} y={0} width={580} size={64} font={FONT_DISPLAY} weight={600}
            baseColor={FG} align="left" delay={0.1} stagger={0.06}
            letterSpacing="-0.02em" lineHeight={1.1} wordGap="0.3em"
          />
        </div>
        <RevealText
          text="Jump into Threads and start the conversation now."
          x={120} y={600} width={580} size={26} color={FG_DIM}
          font={FONT_BODY} align="left" delay={0.9} stagger={0.04} lineHeight={1.5}
        />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        {/* Section heading */}
        <div style={{
          position: 'absolute', left: 780, top: 200,
          fontFamily: FONT_DISPLAY, fontSize: 38, fontWeight: 500, color: FG, letterSpacing: '-0.02em',
        }}>Threads</div>
        <ThreadRow topic="Tokenisation of finance" count={14} delay={0.8} y={290} />
        <ThreadRow topic="Stablecoins & settlement" count={9} delay={1.1} y={400} />
        <ThreadRow topic="Compliance & RWA" count={null} delay={1.4} y={510} />
        {/* Open reply input */}
        <div style={{
          position: 'absolute', left: 780, top: 640, width: 980,
          padding: '18px 24px', background: 'rgba(255,255,255,0.03)',
          border: `1px solid ${ORANGE_DARK}`, borderRadius: 12,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          opacity: clamp(inputT, 0, 1), transform: `scale(${0.92 + clamp(inputT, 0, 1) * 0.08})`, transformOrigin: 'left',
        }}>
          <span style={{ fontFamily: FONT_MONO, fontSize: 15, color: FG_FAINT, letterSpacing: '0.02em' }}>Post a reply…</span>
          <span style={{
            padding: '8px 18px', borderRadius: 999, background: ORANGE, color: '#fff',
            fontFamily: FONT_BODY, fontWeight: 700, fontSize: 14,
          }}>Send</span>
        </div>
        <div style={{
          position: 'absolute', left: 780, top: 720, width: 980,
          fontFamily: FONT_BODY, fontSize: 15, color: FG_DIM, fontStyle: 'italic',
          opacity: clamp(inputT, 0, 1),
        }}>Anyone can join — no match needed.</div>
      </SlideGroup>
    </React.Fragment>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SCENE 09 · One line to remember (pay-off) — 0:52–0:56 (cream)
// ════════════════════════════════════════════════════════════════════════════
function S09_Payoff() {
  const local = useSprite().localTime;
  const l1 = Easing.easeOutBack(clamp((local - 0.2) / 0.5, 0, 1));
  const l2 = Easing.easeOutBack(clamp((local - 1.0) / 0.5, 0, 1));
  return (
    <React.Fragment>
      <div style={{ position: 'absolute', inset: 0, background: BG_LIGHT }} />
      <Vignette light />
      <div style={{
        position: 'absolute', left: 120, right: 120, top: 440, textAlign: 'center',
        fontFamily: FONT_SERIF, fontSize: 56, fontWeight: 500, color: FG_DARK,
        letterSpacing: '-0.02em', lineHeight: 1.25,
        opacity: clamp(l1, 0, 1), transform: `translateY(${(1 - clamp(l1, 0, 1)) * 28}px)`,
      }}>Accept who you want.</div>
      <div style={{
        position: 'absolute', left: 120, right: 120, top: 540, textAlign: 'center',
        fontFamily: FONT_SERIF, fontSize: 56, fontWeight: 500, fontStyle: 'italic',
        color: ORANGE, letterSpacing: '-0.02em', lineHeight: 1.25,
        opacity: clamp(l2, 0, 1), transform: `translateY(${(1 - clamp(l2, 0, 1)) * 28}px)`,
      }}>When they accept back, the conversation opens.</div>
    </React.Fragment>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// SCENE 10 · CTA — 0:56–1:00 (pitch black)
// ════════════════════════════════════════════════════════════════════════════
function S10_CTA() {
  const local = useSprite().localTime;
  const logoT = Easing.easeOutCubic(clamp(local / 0.6, 0, 1));
  const dateT = Easing.easeOutCubic(clamp((local - 0.5) / 0.5, 0, 1));
  const taglineT = Easing.easeOutCubic(clamp((local - 0.75) / 0.5, 0, 1));
  const btnT = Easing.easeOutBack(clamp((local - 1.2) / 0.5, 0, 1));
  return (
    <React.Fragment>
      <Vignette />
      {/* Big POT logo */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 330, display: 'flex', justifyContent: 'center',
        opacity: logoT, transform: `translateY(${(1 - logoT) * 20}px)`,
      }}>
        <POTLogo height={180} />
      </div>
      {/* Date line */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 610, textAlign: 'center',
        fontFamily: FONT_MONO, fontSize: 18, color: FG_DIM, letterSpacing: '0.28em',
        opacity: dateT, transform: `translateY(${(1 - dateT) * 12}px)`,
      }}>LOUVRE PALACE · PARIS · JUNE 2–3, 2026</div>
      {/* Tagline */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 700, textAlign: 'center',
        fontFamily: FONT_BODY, fontSize: 26, color: FG_DIM, letterSpacing: '-0.01em',
        opacity: taglineT, transform: `translateY(${(1 - taglineT) * 12}px)`,
      }}>Open your matches. They're already in the room.</div>
      {/* Orange pill */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 800, display: 'flex', justifyContent: 'center',
        opacity: clamp(btnT, 0, 1), transform: `scale(${0.85 + clamp(btnT, 0, 1) * 0.15})`,
      }}>
        <div style={{
          background: ORANGE, color: '#fff', padding: '22px 44px', borderRadius: 999,
          fontFamily: FONT_BODY, fontWeight: 700, fontSize: 20, letterSpacing: '0.01em',
          boxShadow: `0 24px 60px rgba(247,106,12,${0.5 * clamp(btnT, 0, 1)})`,
        }}>meet.proofoftalk.io →</div>
      </div>
    </React.Fragment>
  );
}

// ── Watermark (POT logo top-left; hidden on scenes 1 & 10) ───────────────────
const SCHEDULE = [
  [ 0.0,  5.0],   // 01 Title + hook
  [ 5.0, 12.0],   // 02 Ticket → email
  [12.0, 18.0],   // 03 Set password
  [18.0, 25.0],   // 04 Enrich profile
  [25.0, 30.0],   // 05 Matches ranked
  [30.0, 39.0],   // 06 Accept → mutual → messages unlock
  [39.0, 45.0],   // 07 Message + book
  [45.0, 52.0],   // 08 Threads
  [52.0, 56.0],   // 09 Pay-off line
  [56.0, 60.0],   // 10 CTA
];
const SCENES = [
  S01_Title, S02_Email, S03_Password, S04_Enrich, S05_Matches,
  S06_Mutual, S07_MessageBook, S08_Threads, S09_Payoff, S10_CTA,
];
const FEATURE_IDX = new Set([1, 2, 3, 4, 6, 7]); // split-layout scenes
const LIGHT_BG_SCENES = new Set([0, 8]);          // white / cream -> invert watermark
const HIDE_WATERMARK = new Set([0, 9]);           // scenes 01 & 10

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
      position: 'absolute', left: 60, top: 50, opacity: baseOp,
      transition: 'opacity 480ms cubic-bezier(0.4, 0, 0.2, 1)', pointerEvents: 'none',
    }}>
      <img src="pot-logo.png" alt="Proof of Talk" style={{
        height: 28, width: 'auto', display: 'block',
        filter: isLight ? 'invert(1)' : 'none', opacity: isLight ? 0.92 : 1,
      }} />
    </div>
  );
}

// ── Background music only (NO voiceover for the onboarding video yet) ─────────
// TODO: add voiceover.mp3 (ElevenLabs) and restore VO mux in render.mjs + here.
function BackgroundMusic() {
  const { time, playing } = useTimeline();
  const audioRef = React.useRef(null);
  const FADE_IN = 2.5, FADE_OUT = 3.0, MAX_VOL = 0.22; // gentle bed level
  React.useEffect(() => {
    const a = audioRef.current; if (!a) return;
    const fadeInVol = Math.min(1, time / FADE_IN);
    const fadeOutVol = Math.min(1, (DUR - time) / FADE_OUT);
    a.volume = Math.max(0, Math.min(fadeInVol, fadeOutVol)) * MAX_VOL;
  }, [time]);
  React.useEffect(() => {
    const a = audioRef.current; if (!a) return;
    if (playing) { const p = a.play(); if (p && p.catch) p.catch(() => {}); }
    else if (!a.paused) a.pause();
  }, [playing]);
  React.useEffect(() => {
    const a = audioRef.current; if (!a) return;
    if (Math.abs(a.currentTime - time) > 0.30) { try { a.currentTime = time; } catch (e) {} }
  }, [time]);
  return <audio ref={audioRef} src="music.mp3" preload="auto" loop style={{ display: 'none' }} />;
}

// Click-anywhere autoplay recovery (music only).
function AudioUnlock() {
  React.useEffect(() => {
    const handler = () => {
      document.querySelectorAll('audio').forEach(el => {
        el.muted = false; const p = el.play(); if (p && p.catch) p.catch(() => {});
      });
    };
    window.addEventListener('click', handler, { once: true, capture: true });
    window.addEventListener('keydown', handler, { once: true, capture: true });
    return () => {
      window.removeEventListener('click', handler, { capture: true });
      window.removeEventListener('keydown', handler, { capture: true });
    };
  }, []);
  return null;
}

function OnboardingApp() {
  return (
    <Stage width={1920} height={1080} duration={DUR}
      background={"rgb(8,8,8)"} persistKey="pot_onboarding_v1" autoplay loop>
      <StageBG />
      {SCHEDULE.map(([s, e], i) => {
        const SceneComp = SCENES[i];
        const isFeature = FEATURE_IDX.has(i);
        const fade = isFeature ? 1.0 : 0.7;
        return (
          <Scene key={i} start={s} end={e} fadeIn={fade} fadeOut={fade} splitMode={isFeature}>
            {() => <SceneComp />}
          </Scene>
        );
      })}
      <WatermarkLogo />
      <BackgroundMusic />
      <AudioUnlock />
    </Stage>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<OnboardingApp />);
