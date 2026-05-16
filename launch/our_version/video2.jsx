// video2.jsx — Scenes 07–16. Depends on PotVideo_PartOne globals.

const {
  Scene, useFeatureTransition, Vignette, ChapterLabel, Eyebrow, Pill, HighlightedTitle, RevealText, Counter, POTLogo,
  BG, BG_LIGHT, FG, FG_DARK, FG_DIM, FG_FAINT, FG_FAINT_LT,
  ORANGE, ORANGE_DARK, ORANGE_BG, CARD, CARD_BORDER, GREEN, GREEN_BG, BLUE, VIOLET,
  FONT_DISPLAY, FONT_BODY, FONT_MONO,
} = window.PotVideo_PartOne;

const BG_WARM = 'rgb(16, 10, 6)';
const FONT_SERIF = "'Fraunces', Georgia, serif";

// Near-black with subtle diagonal crosshatch texture. Used for scenes 0–37s.
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

// Warm orange-tinted ambient background (kept for reference).
function WarmBG() {
  return (
    <div style={{
      position: 'absolute', inset: 0,
      background: `
        radial-gradient(55% 60% at 75% 25%, rgba(247,106,12,0.14) 0%, transparent 65%),
        repeating-linear-gradient(135deg, rgba(255,255,255,0.016) 0 6px, transparent 6px 14px),
        ${BG_WARM}
      `,
    }} />
  );
}

// ── Portrait: shows a real photo if imageSrc provided, otherwise gradient placeholder ──
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
          width: '100%', height: '100%',
          objectFit: 'cover', objectPosition: 'center top',
          display: 'block',
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
      boxShadow: 'inset 0 -16px 30px rgba(0,0,0,0.25)',
      flexShrink: 0,
    }}>{initials}</div>
  );
}

// ── Feature header (centered) ───────────────────────────────────────────────
function FeatureHeader({ index, title, subtitle, delay = 0, titleSize = 86 }) {
  return (
    <React.Fragment>
      <HighlightedTitle
        parts={[{ text: title, italic: true, weight: 600 }]}
        x={0} y={100} width={1920}
        size={titleSize} font={FONT_DISPLAY} weight={600}
        baseColor={FG}
        align="center"
        delay={delay + 0.05}
        stagger={0.10}
        letterSpacing="-0.025em"
        lineHeight={1.0}
        wordGap="0.5em"
      />
      <div style={{ position: 'absolute', left: 0, right: 0, top: 248 }}>
        <RevealText
          text={subtitle}
          x={240} y={0} width={1440}
          size={26} color={FG_DIM} font={FONT_BODY}
          align="center"
          delay={delay + 0.4} stagger={0.05} lineHeight={1.55}
        />
      </div>
    </React.Fragment>
  );
}

// ── SCENE 07 — My Matches ───────────────────────────────────────────────────
function MatchCard({ rank, initials, name, role, score, tags, why, accent = false, delay = 0, y, imageSrc = null, zOffset = 0, matchType = 'Complementary', matchTypeDescriptor = 'One party has what the other needs' }) {
  const local = useSprite().localTime;
  const t = Easing.easeOutCubic(clamp((local - delay) / 0.6, 0, 1));
  const isBack = zOffset > 0;
  return (
    <div style={{
      position: 'absolute', left: 550 + zOffset, top: y, width: 820,
      background: isBack ? 'rgb(6,6,6)' : CARD,
      border: `1px solid ${accent ? ORANGE_DARK : isBack ? 'rgba(255,255,255,0.07)' : CARD_BORDER}`,
      borderRadius: 16,
      padding: '14px 22px',
      opacity: t,
      transform: `translateX(${(1 - t) * 40}px)`,
      boxShadow: `0 ${20 + zOffset}px ${60 + zOffset * 2}px rgba(0,0,0,${0.4 + zOffset * 0.012})`,
      zIndex: 3 - Math.round(zOffset / 12),
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
        <div style={{ fontFamily: FONT_BODY, fontWeight: 700, fontSize: 16, color: FG_FAINT, width: 28 }}>#{rank}</div>
        <div style={{
          padding: '7px 16px', borderRadius: 999,
          background: 'rgba(255,255,255,0.06)',
          border: '1px solid rgba(255,255,255,0.14)',
          fontFamily: FONT_BODY, fontWeight: 700, fontSize: 13, color: FG,
        }}>{matchType}</div>
        <div style={{ fontFamily: FONT_BODY, fontSize: 13, color: FG_DIM }}>{matchTypeDescriptor}</div>
        <div style={{ flex: 1 }} />
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: FONT_MONO, fontSize: 10, color: FG_FAINT, letterSpacing: '0.14em' }}>COMPATIBILITY</div>
          <div style={{ marginTop: 4, fontFamily: FONT_BODY, fontSize: 18, fontWeight: 700, color: ORANGE }}>Good match</div>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 20, marginTop: 18 }}>
        <Portrait initials={initials} size={70} accent={accent} imageSrc={imageSrc} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: FONT_BODY, fontWeight: 700, fontSize: 24, color: FG }}>{name}</div>
          <div style={{ fontFamily: FONT_BODY, fontSize: 15, color: FG_DIM, marginTop: 2 }}>{role}</div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
            {tags.map((tag, i) => (
              <div key={i} style={{
                padding: '5px 12px', borderRadius: 999,
                background: 'rgba(167,139,250,0.10)',
                border: '1px solid rgba(167,139,250,0.30)',
                fontFamily: FONT_BODY, fontSize: 12, color: VIOLET,
              }}>{tag}</div>
            ))}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: FONT_MONO, fontSize: 10, color: FG_FAINT, letterSpacing: '0.14em' }}>COMPATIBILITY</div>
          <div style={{ marginTop: 4, fontFamily: FONT_DISPLAY, fontSize: 32, fontWeight: 600, color: GREEN, fontVariantNumeric: 'tabular-nums' }}>{score}%</div>
        </div>
      </div>
      <div style={{
        marginTop: 14,
        background: 'rgba(247,106,12,0.08)',
        border: `1px solid ${ORANGE_DARK}`,
        borderRadius: 8,
        padding: '10px 14px',
        fontFamily: FONT_BODY, fontWeight: 700, fontSize: 13, color: ORANGE,
      }}><span style={{ color: FG_DIM, fontWeight: 500 }}>Why this meeting matters — </span>{why}</div>
      {/* Shimmer sweep */}
      {(() => {
        const shimmerT = Easing.easeInOutCubic(clamp((local - (delay + 0.75)) / 0.65, 0, 1));
        return (
          <div style={{ position: 'absolute', inset: 0, borderRadius: 16, overflow: 'hidden', pointerEvents: 'none' }}>
            <div style={{
              position: 'absolute', top: 0, bottom: 0, width: 220,
              left: -220 + shimmerT * (820 + 440),
              background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.055), transparent)',
              transform: 'skewX(-12deg)',
            }} />
          </div>
        );
      })()}
    </div>
  );
}

function FadeGroup({ children, opacity }) {
  return (
    <div style={{ position: 'absolute', inset: 0, opacity, willChange: 'opacity' }}>
      {children}
    </div>
  );
}
function SlideGroup({ children, ty }) {
  return (
    <div style={{ position: 'absolute', inset: 0, transform: `translateY(${ty}px)`, willChange: 'transform' }}>
      {children}
    </div>
  );
}

function Scene07() {
  const { leftOpacity, panelTy } = useFeatureTransition();
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <FeatureHeader
          index={1}
          title="My Matches."
          subtitle="Your top introductions, ranked. Ready before you land."
          delay={0}
        />
        <ChapterLabel text="" />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        <MatchCard
          rank={1} initials="MC" name="Mira Chen" role="GP · Vega Ventures" score={82}
          tags={['Investment & Capital Markets', 'Tokenisation']}
          why="She raises funds from the LPs you need."
          imageSrc="figures/mira.png" accent
          matchType="Complementary"
          matchTypeDescriptor="One party has what the other needs"
          delay={1.0} y={310} zOffset={0}
        />
        <MatchCard
          rank={2} initials="KI" name="Karim Idrissi" role="Founder · ChainPort" score={71}
          tags={['Infrastructure & Scaling']}
          why="Building the bridge your thesis needs in EMEA."
          imageSrc="figures/karim.png"
          matchType="Non-Obvious"
          matchTypeDescriptor="Different sectors, similar underlying problems"
          delay={1.9} y={560} zOffset={12}
        />
        <MatchCard
          rank={3} initials="ÉM" name="Élise Moreau" role="Head of Token Ops · SocGen" score={64}
          tags={['Tokenisation of Finance']}
          why="Cleared the regulatory path you are still mapping."
          imageSrc="figures/elise.png"
          matchType="Deal Ready"
          matchTypeDescriptor="Both parties positioned to transact"
          delay={2.8} y={810} zOffset={24}
        />
      </SlideGroup>
    </React.Fragment>
  );
}

// ── SCENE 08 — AI Concierge ─────────────────────────────────────────────────
function ChatBubble({ side = 'right', label, text, delay = 0, y, accent = false, width = 560 }) {
  const local = useSprite().localTime;
  const enter = Easing.easeOutCubic(clamp((local - delay) / 0.5, 0, 1));
  const charT = clamp((local - delay - 0.15) / 1.8, 0, 1);
  const shown = Math.floor(text.length * Easing.easeOutCubic(charT));
  const COL_LEFT = 560;
  const COL_WIDTH = 800;
  const left = side === 'right' ? COL_LEFT + COL_WIDTH - width : COL_LEFT;
  return (
    <div style={{
      position: 'absolute', left, top: y, width,
      opacity: enter, transform: `translateY(${(1 - enter) * 14}px)`,
    }}>
      <div style={{
        fontFamily: FONT_MONO, fontSize: 11, color: FG_FAINT, letterSpacing: '0.18em',
        textAlign: side === 'right' ? 'right' : 'left',
        marginBottom: 10,
      }}>{label}</div>
      <div style={{
        background: accent ? 'rgba(247,106,12,0.10)' : 'rgba(255,255,255,0.04)',
        border: `1px solid ${accent ? ORANGE_DARK : 'rgba(255,255,255,0.12)'}`,
        borderRadius: 14,
        padding: '20px 24px',
        fontFamily: FONT_BODY, fontSize: 20, color: FG, lineHeight: 1.4,
        minHeight: 64,
      }}>{text.slice(0, shown)}<span style={{ opacity: shown < text.length ? 1 : 0, color: accent ? ORANGE : FG }}>▍</span></div>
    </div>
  );
}

function TypingPill({ delay = 0, x, y }) {
  const local = useSprite().localTime;
  const t = Easing.easeOutCubic(clamp((local - delay) / 0.35, 0, 1));
  return (
    <div style={{
      position: 'absolute', left: x, top: y,
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '10px 16px',
      background: 'rgba(247,106,12,0.10)',
      border: `1px solid ${ORANGE_DARK}`,
      borderRadius: 999,
      opacity: t, transform: `translateY(${(1 - t) * 8}px) scale(${0.9 + t * 0.1})`,
    }}>
      {[0, 1, 2].map(i => {
        const ph = (local * 2.2 + i * 0.2) % 1;
        const o = 0.35 + 0.65 * Math.max(0, Math.sin(ph * Math.PI));
        return <div key={i} style={{ width: 8, height: 8, borderRadius: 4, background: ORANGE, opacity: o }} />;
      })}
    </div>
  );
}

function Scene08() {
  const { leftOpacity, panelTy } = useFeatureTransition();
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <FeatureHeader
          index={2}
          title="Concierge."
          subtitle="Ask anything about anyone. With receipts."
          delay={0}
        />
        <ChapterLabel text="05 · How it works" />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        <ChatBubble side="right" label="YOU" text="Prep me for my meeting with Mira." y={310} delay={0.9} />
        <ChatBubble
          side="left" label="CONCIERGE"
          text="Mira leads Vega Series B fund — her thesis overlaps her last three checks. Lead with the LP angle."
          y={455} delay={2.2} width={620} accent
        />
        <ChatBubble side="right" label="YOU" text="What does she care about most?" y={660} delay={3.6} />
        <TypingPill x={560} y={830} delay={2.7} />
        {/* Static input placeholder — mirrors real app's ChatPanel.tsx:180 */}
        <div style={{
          position: 'absolute', left: 560, top: 940, width: 800,
          padding: '16px 22px',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.10)',
          borderRadius: 12,
          fontFamily: FONT_MONO, fontSize: 14, color: FG_FAINT, letterSpacing: '0.02em',
        }}>Ask about attendees, meetings, connections…</div>
      </SlideGroup>
    </React.Fragment>
  );
}

// ── SCENE 09 — Profile, drafted by Concierge chat ─────────────────────────
function ProfileField({ label, value, delay = 0, y }) {
  const local = useSprite().localTime;
  const enter = Easing.easeOutCubic(clamp((local - delay) / 0.55, 0, 1));
  const shown = Math.floor(value.length * Easing.easeOutCubic(clamp((local - delay - 0.2) / 1.1, 0, 1)));
  return (
    <div style={{
      position: 'absolute', left: 460, top: y, width: 1000,
      opacity: enter, transform: `translateY(${(1 - enter) * 12}px)`,
    }}>
      <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: FG_FAINT, letterSpacing: '0.18em' }}>{label}</div>
      <div style={{
        marginTop: 12,
        background: CARD, border: `1px solid ${CARD_BORDER}`,
        borderRadius: 14, padding: '18px 22px',
        fontFamily: FONT_BODY, fontSize: 22, color: FG, lineHeight: 1.4,
      }}>
        {value.slice(0, shown)}<span style={{ opacity: shown < value.length ? 1 : 0, color: ORANGE }}>▍</span>
      </div>
    </div>
  );
}

function Scene09() {
  const local = useSprite().localTime;
  const { leftOpacity, panelTy } = useFeatureTransition();
  // Timing — beats at 0.7s / 1.6s / 2.1s / 2.5s / 3.5s / 3.9s
  const btnRowT  = Easing.easeOutBack(clamp((local - 1.6) / 0.45, 0, 1));
  const ctaTapT  = Easing.easeInOutCubic(clamp((local - 2.1) / 0.25, 0, 1));
  const chipsT   = local - 2.5; // stagger handled inline
  const chipTapT = Easing.easeInOutCubic(clamp((local - 3.5) / 0.25, 0, 1));
  const bannerT  = Easing.easeOutCubic(clamp((local - 3.9) / 0.55, 0, 1));
  const chips = [
    'Find LPs writing $5–25M tickets in DeFi infra.',
    'Meet builders shipping post-MiCAR tokenisation rails.',
    'Source GP co-investors for Q4 raise.',
  ];
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <FeatureHeader
          index={3}
          title="Drafted for you."
          subtitle="One tap. Your profile sharpens. Matches refresh."
          delay={0}
          titleSize={92}
        />
        <ChapterLabel text="" />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        {/* Concierge bubble — proactive ProfilePromptOffer */}
        <ChatBubble
          side="left" label="CONCIERGE"
          text="Your profile is 62% complete — I can draft your conference goals based on your role. It'll sharpen your matches."
          y={310} delay={0.7} width={780} accent
        />
        {/* Button row — Yes, draft my goals + Maybe later */}
        <div style={{
          position: 'absolute', left: 560, top: 510,
          display: 'inline-flex', gap: 14,
          opacity: clamp(btnRowT, 0, 1),
          transform: `scale(${0.85 + clamp(btnRowT, 0, 1) * 0.15})`, transformOrigin: 'left',
        }}>
          <div style={{
            position: 'relative',
            padding: '14px 26px', borderRadius: 999,
            background: ORANGE, color: '#fff',
            fontFamily: FONT_BODY, fontWeight: 700, fontSize: 16,
            boxShadow: `0 16px 40px rgba(247,106,12,${0.35 + ctaTapT * 0.2})`,
            transform: `scale(${1 - ctaTapT * 0.05})`,
          }}>
            [ Yes, draft my goals ]
          </div>
          <div style={{
            padding: '14px 26px', borderRadius: 999,
            background: 'transparent',
            border: '1px solid rgba(255,255,255,0.18)',
            fontFamily: FONT_BODY, fontWeight: 600, fontSize: 16, color: FG_DIM,
          }}>
            [ Maybe later ]
          </div>
        </div>
        {/* Three candidate chips — stagger in 0.15s apart */}
        {chips.map((chipText, i) => {
          const tChip = Easing.easeOutCubic(clamp((chipsT - i * 0.15) / 0.35, 0, 1));
          const isSelected = i === 1;
          const selectedT = isSelected ? chipTapT : 0;
          return (
            <div key={i} style={{
              position: 'absolute', left: 560, top: 620 + i * 80, width: 800,
              padding: '18px 22px', borderRadius: 12,
              background: isSelected ? 'rgba(247,106,12,0.10)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${isSelected && selectedT > 0.2 ? ORANGE_DARK : 'rgba(255,255,255,0.12)'}`,
              fontFamily: FONT_BODY, fontSize: 18, color: FG,
              opacity: tChip,
              transform: `translateY(${(1 - tChip) * 10}px) scale(${isSelected ? 1 + selectedT * 0.02 : 1})`,
            }}>{chipText}</div>
          );
        })}
        {/* Green confirmation banner */}
        <div style={{
          position: 'absolute', left: 0, right: 0, top: 900,
          display: 'flex', justifyContent: 'center',
          opacity: bannerT, transform: `translateY(${(1 - bannerT) * 10}px)`,
        }}>
          <div style={{
            padding: '14px 24px',
            background: GREEN_BG, border: '1px solid rgba(34,197,94,0.45)',
            borderRadius: 10,
            fontFamily: FONT_BODY, fontWeight: 700, fontSize: 18, color: GREEN,
          }}>✓ Saved. Matches refreshing.</div>
        </div>
      </SlideGroup>
    </React.Fragment>
  );
}

// ── SCENE 10 — Mutual match ─────────────────────────────────────────────────
function Avatar({ initials, name, x, y, accent = false, delay = 0, imageSrc = null }) {
  const local = useSprite().localTime;
  const t = Easing.easeOutBack(clamp((local - delay) / 0.55, 0, 1));
  return (
    <div style={{
      position: 'absolute', left: x, top: y, textAlign: 'center',
      opacity: clamp(t, 0, 1), transform: `scale(${0.7 + clamp(t, 0, 1) * 0.3})`,
    }}>
      <Portrait initials={initials} size={160} accent={accent} imageSrc={imageSrc} />
      <div style={{ marginTop: 16, fontFamily: FONT_BODY, fontWeight: 700, fontSize: 22, color: FG }}>{name}</div>
    </div>
  );
}

function Scene10() {
  const local = useSprite().localTime;
  const { leftOpacity, panelTy } = useFeatureTransition();
  const lineT = Easing.easeInOutCubic(clamp((local - 1.0) / 0.5, 0, 1));
  const dotT = Easing.easeOutBack(clamp((local - 1.4) / 0.45, 0, 1));
  const matchT = Easing.easeOutCubic(clamp((local - 1.85) / 0.5, 0, 1));
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <FeatureHeader
          index={4}
          title="Mutual match."
          subtitle="The yes happens before the handshake."
          delay={0}
        />
        <ChapterLabel text="05 · How it works" />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        <Avatar initials="S" name="You" x={620} y={360} delay={0.7} imageSrc="figures/you.png" />
        <Avatar initials="M" name="Mira" x={1140} y={360} accent delay={0.9} imageSrc="figures/mira.png" />
        <div style={{
          position: 'absolute', left: 800, top: 440, width: 340, height: 2,
          background: `linear-gradient(90deg, ${ORANGE_DARK} 0%, ${ORANGE} 50%, ${ORANGE_DARK} 100%)`,
          transform: `scaleX(${lineT})`, transformOrigin: 'left',
        }} />
        <div style={{
          position: 'absolute', left: 960, top: 418,
          width: 44, height: 44, borderRadius: 22,
          background: ORANGE,
          boxShadow: `0 0 ${30 * dotT}px rgba(247,106,12,0.7)`,
          opacity: dotT, transform: `scale(${0.4 + dotT * 0.6})`,
        }} />
        <div style={{
          position: 'absolute', left: 0, right: 0, top: 680, display: 'flex', justifyContent: 'center',
          opacity: matchT, transform: `translateY(${(1 - matchT) * 10}px)`,
        }}>
          <div style={{
            padding: '18px 28px', width: 540,
            background: GREEN_BG, border: '1px solid rgba(34,197,94,0.45)',
            borderRadius: 10,
            textAlign: 'center',
            fontFamily: FONT_BODY, fontWeight: 700, fontSize: 22, color: GREEN,
          }}>Mutual match — both accepted!</div>
        </div>
      </SlideGroup>
    </React.Fragment>
  );
}

// ── SCENE 11 — One-tap booking ──────────────────────────────────────────────
function SlotPill({ day, time, delay = 0, accent = false }) {
  const local = useSprite().localTime;
  const t = Easing.easeOutBack(clamp((local - delay) / 0.45, 0, 1));
  return (
    <div style={{
      padding: '16px 0', borderRadius: 10,
      background: accent ? 'rgba(247,106,12,0.14)' : 'rgba(255,255,255,0.04)',
      border: `1px solid ${accent ? ORANGE_DARK : CARD_BORDER}`,
      textAlign: 'center',
      opacity: clamp(t, 0, 1), transform: `scale(${0.85 + clamp(t, 0, 1) * 0.15})`,
    }}>
      <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: FG_FAINT, letterSpacing: '0.14em' }}>{day}</div>
      <div style={{ marginTop: 6, fontFamily: FONT_BODY, fontWeight: 600, fontSize: 24, color: accent ? ORANGE : FG }}>{time}</div>
    </div>
  );
}

function Scene11() {
  const local = useSprite().localTime;
  const { leftOpacity, panelTy } = useFeatureTransition();
  const confirmT = Easing.easeOutCubic(clamp((local - 2.0) / 0.55, 0, 1));
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <FeatureHeader
          index={5}
          title="One-tap booking."
          subtitle="One tap. Slot picked. Calendar synced."
          delay={0}
        />
        <ChapterLabel text="05 · How it works" />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        <div style={{
          position: 'absolute', left: 510, top: 320, width: 900,
          background: CARD, border: `1px solid ${CARD_BORDER}`,
          borderRadius: 16, padding: '28px 30px',
        }}>
          <div style={{ fontFamily: FONT_BODY, fontSize: 15, color: FG_DIM }}>Both free at — tap to book</div>
          <div style={{ marginTop: 22, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
            <SlotPill day="Tue" time="14:15" delay={0.9} />
            <SlotPill day="Tue" time="16:00" delay={1.0} />
            <SlotPill day="Wed" time="09:45" delay={1.1} />
            <SlotPill day="Wed" time="11:30" delay={1.2} accent />
            <SlotPill day="Wed" time="15:00" delay={1.3} />
          </div>
        </div>
        <div style={{
          position: 'absolute', left: 510, top: 610, width: 900,
          background: 'rgba(247,106,12,0.10)', border: `1px solid ${ORANGE_DARK}`,
          borderRadius: 16, padding: '24px 30px',
          opacity: confirmT, transform: `translateY(${(1 - confirmT) * 16}px)`,
        }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            fontFamily: FONT_MONO, fontSize: 12, color: ORANGE, letterSpacing: '0.18em',
          }}>
            <span style={{ width: 8, height: 8, borderRadius: 4, background: ORANGE }} />
            CONFIRMED
          </div>
          <div style={{ marginTop: 12, fontFamily: FONT_DISPLAY, fontSize: 36, fontWeight: 500, color: FG, letterSpacing: '-0.02em' }}>
            Wed · 11:30 · Salon Mollien
          </div>
          <div style={{ marginTop: 8, fontFamily: FONT_BODY, fontSize: 16, color: FG_DIM }}>
            Locked in. They'll see it in their matches too.
          </div>
        </div>
      </SlideGroup>
    </React.Fragment>
  );
}

// ── SCENE 12 — Magic Link: email → landing transition ─────────────────────
function Scene12() {
  const local = useSprite().localTime;
  const { leftOpacity, panelTy } = useFeatureTransition();
  // Beats: email in 0.0s, CTA pop 0.5s, cursor tap 1.0s, card exit 1.0s, landing in 1.4s, mini cards stagger 1.7s
  const emailInT = Easing.easeOutCubic(clamp(local / 0.5, 0, 1));
  const btnT     = Easing.easeOutBack(clamp((local - 0.5) / 0.4, 0, 1));
  const tapT     = Easing.easeInOutCubic(clamp((local - 1.0) / 0.25, 0, 1));
  const exitT    = Easing.easeInCubic(clamp((local - 1.0) / 0.4, 0, 1));
  const landingT = Easing.easeOutCubic(clamp((local - 1.4) / 0.5, 0, 1));
  const miniBase = local - 1.7;
  // Email visibility: appears (emailInT) then exits (1-exitT)
  const emailOpacity = Math.max(0, emailInT - exitT);
  const emailTy = (1 - emailInT) * 16 - exitT * 80;
  const miniCards = [
    { rank: 1, name: 'Mira Chen', role: 'GP · Vega Ventures', type: 'Complementary' },
    { rank: 2, name: 'Karim Idrissi', role: 'Founder · ChainPort', type: 'Non-Obvious' },
    { rank: 3, name: 'Élise Moreau', role: 'Head of Token Ops · SocGen', type: 'Deal Ready' },
  ];
  return (
    <React.Fragment>
      <FadeGroup opacity={leftOpacity}>
        <PitchBlackBG />
        <Vignette />
        <FeatureHeader
          index={6}
          title="Magic link."
          subtitle="One link. No password."
          delay={0}
        />
        <ChapterLabel text="" />
      </FadeGroup>
      <SlideGroup ty={panelTy}>
        {/* Minimal email card — exits at 1.0s */}
        {emailOpacity > 0.01 && (
          <div style={{
            position: 'absolute', left: 510, top: 360, width: 900,
            background: CARD, border: `1px solid ${CARD_BORDER}`,
            borderRadius: 18, padding: '36px 40px',
            opacity: emailOpacity, transform: `translateY(${emailTy}px)`,
            boxShadow: '0 30px 90px rgba(0,0,0,0.55)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <POTLogo height={32} />
            </div>
            <div style={{ marginTop: 8, fontFamily: FONT_MONO, fontSize: 12, color: FG_FAINT, letterSpacing: '0.1em' }}>
              From hello@proofoftalk.io
            </div>
            <div style={{
              marginTop: 36,
              fontFamily: FONT_DISPLAY, fontSize: 44, fontWeight: 500, color: FG,
              lineHeight: 1.15, letterSpacing: '-0.02em',
            }}>Your introductions are ready, Mira.</div>
            <div style={{
              marginTop: 36, display: 'inline-flex', position: 'relative',
              opacity: btnT, transform: `scale(${(0.85 + btnT * 0.15) * (1 - tapT * 0.06)})`, transformOrigin: 'left',
            }}>
              <div style={{
                background: ORANGE, color: '#fff',
                padding: '18px 36px', borderRadius: 999,
                fontFamily: FONT_BODY, fontWeight: 700, fontSize: 18,
                boxShadow: `0 24px 60px rgba(247,106,12,${0.45 * btnT})`,
              }}>Open my matches →</div>
            </div>
          </div>
        )}
        {/* Magic-link landing — drops in after email exits */}
        {landingT > 0.01 && (
          <div style={{
            position: 'absolute', left: 510, top: 320, width: 900,
            opacity: landingT, transform: `translateY(${(1 - landingT) * 24}px)`,
          }}>
            <div style={{
              fontFamily: FONT_DISPLAY, fontSize: 58, fontWeight: 500, color: FG,
              letterSpacing: '-0.02em', lineHeight: 1.1,
            }}>Welcome, Mira</div>
            <div style={{
              marginTop: 32, display: 'flex', flexDirection: 'column', gap: 14,
            }}>
              {miniCards.map((c, i) => {
                const tCard = Easing.easeOutCubic(clamp((miniBase - i * 0.12) / 0.4, 0, 1));
                return (
                  <div key={i} style={{
                    background: CARD, border: `1px solid ${CARD_BORDER}`,
                    borderRadius: 12, padding: '16px 22px',
                    display: 'flex', alignItems: 'center', gap: 16,
                    opacity: tCard, transform: `translateX(${(1 - tCard) * 24}px)`,
                  }}>
                    <div style={{ fontFamily: FONT_BODY, fontWeight: 700, fontSize: 14, color: FG_FAINT, width: 26 }}>#{c.rank}</div>
                    <div style={{
                      padding: '5px 12px', borderRadius: 999,
                      background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.14)',
                      fontFamily: FONT_BODY, fontWeight: 700, fontSize: 12, color: FG,
                    }}>{c.type}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontFamily: FONT_BODY, fontWeight: 700, fontSize: 18, color: FG }}>{c.name}</div>
                      <div style={{ fontFamily: FONT_BODY, fontSize: 13, color: FG_DIM }}>{c.role}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </SlideGroup>
    </React.Fragment>
  );
}

// ── SCENE 13 — Impact ──────────────────────────────────────────────────────
function Scene13() {
  const local = useSprite().localTime;
  const l1 = Easing.easeOutBack(clamp((local - 0.2) / 0.55, 0, 1));
  const l2 = Easing.easeOutBack(clamp((local - 1.2) / 0.55, 0, 1));
  return (
    <React.Fragment>
      <Vignette />
      <div style={{
        position: 'absolute', left: 120, right: 120, top: 380, textAlign: 'center',
        fontFamily: FONT_SERIF, fontSize: 88, fontWeight: 500, color: FG,
        letterSpacing: '-0.025em', lineHeight: 1.2,
        opacity: clamp(l1, 0, 1), transform: `translateY(${(1 - l1) * 30}px)`,
      }}>Tell us what you need.</div>
      <div style={{
        position: 'absolute', left: 120, right: 120, top: 540, textAlign: 'center',
        fontFamily: FONT_SERIF, fontSize: 88, fontWeight: 500, fontStyle: 'italic',
        color: ORANGE, letterSpacing: '-0.025em', lineHeight: 1.2,
        opacity: clamp(l2, 0, 1), transform: `translateY(${(1 - l2) * 30}px)`,
      }}>We'll tell you who to meet.</div>
      <ChapterLabel text="06 · The Impact" />
    </React.Fragment>
  );
}

// ── SCENE 14 — Availability ──────────────────────────────────────────────────
function Scene14Availability() {
  const local = useSprite().localTime;
  const buildT = Easing.easeOutCubic(clamp((local - 0.2) / 0.55, 0, 1));
  const logoT  = Easing.easeOutCubic(clamp((local - 1.4) / 0.5, 0, 1));

  return (
    <React.Fragment>
      <div style={{ position: 'absolute', inset: 0, background: BG_LIGHT }} />
      <Vignette light />

      {/* "Built Into" */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 280, textAlign: 'center',
        fontFamily: FONT_SERIF, fontSize: 60, fontWeight: 400,
        color: FG_DARK, letterSpacing: '-0.02em',
        opacity: buildT, transform: `translateY(${(1 - buildT) * 16}px)`,
      }}>Built Into</div>

      {/* "Matchmaker" — big orange italic */}
      <HighlightedTitle
        parts={[{ text: 'Matchmaker', color: ORANGE, italic: true, weight: 500 }]}
        x={0} y={420} width={1920}
        size={180} align="center"
        baseColor={ORANGE}
        delay={0.55}
        stagger={0.07}
        letterSpacing="-0.03em"
      />

      {/* POT Logo */}
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 180,
        display: 'flex', justifyContent: 'center',
        opacity: logoT, transform: `translateY(${(1 - logoT) * 12}px)`,
      }}>
        <POTLogo height={80} invert />
      </div>

      <ChapterLabel text="07 · Availability" color={FG_FAINT_LT} />
    </React.Fragment>
  );
}

// ── SCENE 15 — CTA (v4): logo + Louvre date + Secure your seat button ───────
function Scene15() {
  const local = useSprite().localTime;
  const logoT = Easing.easeOutCubic(clamp(local / 0.7, 0, 1));
  const dateT = Easing.easeOutCubic(clamp((local - 0.6) / 0.55, 0, 1));
  const taglineT = Easing.easeOutCubic(clamp((local - 0.85) / 0.55, 0, 1));
  const btnT = Easing.easeOutBack(clamp((local - 1.35) / 0.55, 0, 1));
  return (
    <React.Fragment>
      <Vignette />

      {/* Big POT logo */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 320,
        display: 'flex', justifyContent: 'center',
        opacity: logoT,
        transform: `translateY(${(1 - logoT) * 22}px)`,
      }}>
        <POTLogo height={200} />
      </div>

      {/* Louvre date line */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 620, textAlign: 'center',
        fontFamily: FONT_MONO, fontSize: 18, color: FG_DIM, letterSpacing: '0.28em',
        opacity: dateT,
        transform: `translateY(${(1 - dateT) * 12}px)`,
      }}>LOUVRE PALACE · PARIS · JUNE 2–3, 2026</div>

      {/* Tagline above button */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 720, textAlign: 'center',
        fontFamily: FONT_BODY, fontSize: 28, color: FG_DIM, letterSpacing: '-0.01em',
        opacity: taglineT, transform: `translateY(${(1 - taglineT) * 12}px)`,
      }}>Your matches are already in the room.</div>

      {/* Orange pill button */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 820,
        display: 'flex', justifyContent: 'center',
        opacity: clamp(btnT, 0, 1),
        transform: `scale(${0.85 + clamp(btnT, 0, 1) * 0.15})`,
      }}>
        <div style={{
          background: ORANGE, color: '#fff',
          padding: '22px 44px', borderRadius: 999,
          fontFamily: FONT_BODY, fontWeight: 700, fontSize: 20,
          letterSpacing: '0.01em',
          boxShadow: `0 24px 60px rgba(247,106,12,${0.5 * clamp(btnT, 0, 1)})`,
        }}>Claim your ticket →</div>
      </div>
    </React.Fragment>
  );
}

// ── SCENE 15 (v3 legacy — had proofoftalk.io text + divider) ───────────────
function Scene15V3Legacy() {
  const local = useSprite().localTime;
  const lineT = Easing.easeInOutCubic(clamp((local - 0.85) / 0.55, 0, 1));
  return (
    <React.Fragment>
      <Vignette />

      {/* POT logo upper third */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 280,
        display: 'flex', justifyContent: 'center',
        opacity: Easing.easeOutCubic(clamp(local / 0.6, 0, 1)),
        transform: `translateY(${(1 - clamp(local / 0.6, 0, 1)) * 18}px)`,
      }}>
        <POTLogo height={150} />
      </div>

      {/* Orange divider */}
      <div style={{
        position: 'absolute', left: '50%', top: 480,
        width: 320 * lineT, height: 1, background: ORANGE,
        transform: 'translateX(-50%)',
      }} />

      {/* proofoftalk.io hero */}
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 530, textAlign: 'center',
        fontFamily: FONT_DISPLAY, fontSize: 120, fontWeight: 500, color: ORANGE,
        letterSpacing: '-0.025em', fontStyle: 'italic',
        opacity: Easing.easeOutCubic(clamp((local - 1.0) / 0.55, 0, 1)),
        transform: `translateY(${(1 - clamp((local - 1.0) / 0.55, 0, 1)) * 14}px)`,
      }}>proofoftalk.io</div>

      <div style={{
        position: 'absolute', left: 0, right: 0, top: 730, textAlign: 'center',
        fontFamily: FONT_MONO, fontSize: 16, color: FG_DIM, letterSpacing: '0.24em',
        opacity: Easing.easeOutCubic(clamp((local - 1.4) / 0.5, 0, 1)),
      }}>LOUVRE PALACE · PARIS · JUNE 2–3, 2026</div>

      <div style={{
        position: 'absolute', left: 0, right: 0, top: 810, textAlign: 'center',
        fontFamily: FONT_BODY, fontSize: 18, color: FG_FAINT_LT, fontStyle: 'italic',
        opacity: Easing.easeOutCubic(clamp((local - 1.85) / 0.5, 0, 1)),
      }}>Secure your seat.</div>

      <ChapterLabel text="07 · Where" />
    </React.Fragment>
  );
}

// ── SCENE 15 (legacy v2) — used by v2 snapshot ──────────────────────────────
function Scene15Legacy() {
  const local = useSprite().localTime;
  return (
    <React.Fragment>
      <Vignette />

      <div style={{
        position: 'absolute', left: 0, right: 0, top: 260,
        display: 'flex', justifyContent: 'center',
        opacity: Easing.easeOutCubic(clamp(local / 0.6, 0, 1)),
        transform: `translateY(${(1 - clamp(local / 0.6, 0, 1)) * 18}px)`,
      }}>
        <POTLogo height={180} />
      </div>

      <div style={{
        position: 'absolute', left: 0, right: 0, top: 510, textAlign: 'center',
        fontFamily: FONT_DISPLAY, fontSize: 120, fontWeight: 500, color: ORANGE,
        letterSpacing: '-0.025em', fontStyle: 'italic',
        opacity: Easing.easeOutCubic(clamp((local - 0.75) / 0.55, 0, 1)),
        transform: `translateY(${(1 - clamp((local - 0.75) / 0.55, 0, 1)) * 14}px)`,
      }}>proofoftalk.io</div>

      <div style={{
        position: 'absolute', left: 0, right: 0, top: 710, textAlign: 'center',
        fontFamily: FONT_MONO, fontSize: 16, color: FG_DIM, letterSpacing: '0.24em',
        opacity: Easing.easeOutCubic(clamp((local - 1.1) / 0.5, 0, 1)),
      }}>LOUVRE PALACE · PARIS · JUNE 2–3, 2026</div>

      <div style={{
        position: 'absolute', left: 0, right: 0, top: 790, textAlign: 'center',
        fontFamily: FONT_MONO, fontSize: 13, color: FG_FAINT, letterSpacing: '0.18em',
        opacity: Easing.easeOutCubic(clamp((local - 1.6) / 0.5, 0, 1)),
      }}>SECURE YOUR PLACE AT PROOFOFTALK.IO</div>
    </React.Fragment>
  );
}

// ── SCENE 16 — Closer (NEW) ─────────────────────────────────────────────────
function Scene16() {
  const local = useSprite().localTime;
  const line1T = Easing.easeOutCubic(clamp((local - 0.2) / 0.65, 0, 1));
  const line2T = Easing.easeOutCubic(clamp((local - 1.2) / 0.65, 0, 1));
  const logoT = Easing.easeOutCubic(clamp((local - 2.0) / 0.5, 0, 1));

  return (
    <React.Fragment>
      <Vignette />

      <div style={{
        position: 'absolute', left: 0, right: 0, top: 320, textAlign: 'center',
        fontFamily: FONT_DISPLAY, fontSize: 160, fontWeight: 400, fontStyle: 'italic',
        color: FG, letterSpacing: '-0.03em', lineHeight: 1,
        opacity: line1T, transform: `translateY(${(1 - line1T) * 22}px)`,
      }}>The right room.</div>

      <div style={{
        position: 'absolute', left: 0, right: 0, top: 510, textAlign: 'center',
        fontFamily: FONT_DISPLAY, fontSize: 160, fontWeight: 400, fontStyle: 'italic',
        color: ORANGE, letterSpacing: '-0.03em', lineHeight: 1,
        opacity: line2T, transform: `translateY(${(1 - line2T) * 22}px)`,
      }}>Now — the right people.</div>

      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 100,
        display: 'flex', justifyContent: 'center',
        opacity: logoT,
      }}>
        <POTLogo height={56} />
      </div>
    </React.Fragment>
  );
}

// ── SCENE: How It Works — bridge between problem and features ───────────────
function SceneHowItWorks() {
  const local = useSprite().localTime;
  const titleT = Easing.easeOutCubic(clamp((local - 0.2) / 0.65, 0, 1));
  return (
    <React.Fragment>
      <PitchBlackBG />
      <Vignette />
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 0, bottom: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          textAlign: 'center',
          fontFamily: FONT_DISPLAY, fontSize: 88, fontWeight: 400, fontStyle: 'italic',
          color: FG, letterSpacing: '-0.025em', lineHeight: 1.1,
          opacity: titleT, transform: `translateY(${(1 - titleT) * 16}px)`,
          maxWidth: 1400, padding: '0 60px',
        }}>Six features. Everything set up before the doors open.</div>
      </div>
    </React.Fragment>
  );
}

// ── SCENE INTROS — 4s cinematic title cards before each feature ─────────────
function SceneIntro({ title, subtitle }) {
  const local  = useSprite().localTime;
  const lineT  = Easing.easeOutCubic(clamp((local - 0.2) / 0.45, 0, 1));
  const introT = Easing.easeOutCubic(clamp((local - 0.55) / 0.85, 0, 1));
  const subT   = Easing.easeOutCubic(clamp((local - 1.2) / 0.6, 0, 1));
  const blurPx = ((1 - introT) * 14).toFixed(1);
  return (
    <React.Fragment>
      <PitchBlackBG />
      <Vignette />
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 0, bottom: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: 0,
      }}>
        {/* Orange accent line — draws left to right */}
        <div style={{
          width: 80, height: 2, background: ORANGE,
          transformOrigin: 'left center',
          transform: `scaleX(${lineT})`,
          marginBottom: 32, alignSelf: 'center',
        }} />
        {/* Title — zooms in from 108% while blur dissolves to sharp */}
        <div style={{
          fontFamily: FONT_SERIF, fontSize: 120, fontWeight: 600,
          color: FG, letterSpacing: '-0.03em', lineHeight: 1, textAlign: 'center',
          opacity: introT,
          filter: `blur(${blurPx}px)`,
          transform: `scale(${1.08 - introT * 0.08})`,
          willChange: 'opacity, filter, transform',
        }}>{title}</div>
        {/* Subtitle — slides up */}
        <div style={{
          marginTop: 32,
          fontFamily: FONT_BODY, fontSize: 26, color: FG_DIM,
          letterSpacing: '0.01em', lineHeight: 1.5, textAlign: 'center',
          maxWidth: 900,
          opacity: subT, transform: `translateY(${(1 - subT) * 14}px)`,
        }}>{subtitle}</div>
      </div>
    </React.Fragment>
  );
}

function SceneIntro07() { return <SceneIntro title="AI Matchmaking" subtitle="Your highest-value conversations, ranked and ready before you land." />; }
function SceneIntro08() { return <SceneIntro title="AI Concierge" subtitle="Ask anything about anyone in the room. Instant prep, sourced from real data." />; }
function SceneIntro09() { return <SceneIntro title="Drafted for you" subtitle="Concierge drafts. You approve. Matches refresh." />; }
function SceneIntro10() { return <SceneIntro title="Mutual Match" subtitle="Both sides say yes before the handshake. No awkward cold intros." />; }
function SceneIntro11() { return <SceneIntro title="Smart Booking" subtitle="One tap. Shared availability checked. Meeting locked in." />; }
function SceneIntro12() { return <SceneIntro title="Magic Link" subtitle="One link. Every meeting. No login, no app, no friction." />; }

window.PotVideo_PartTwo = {
  SceneHowItWorks,
  Scene07, Scene08, Scene09, Scene10, Scene11, Scene12,
  Scene13, Scene14Availability, Scene15, Scene16,
  SceneIntro07, SceneIntro08, SceneIntro09, SceneIntro10, SceneIntro11, SceneIntro12,
  Portrait,
};
