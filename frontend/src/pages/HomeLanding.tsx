import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

// Matchmaker app landing page (route: /). Long-scroll marketing page
// ported from Z's `launch/from_Z/matchmaker.html`. Cold visitors see the
// full page and the "Get your introductions" CTA → /register. Authenticated
// users auto-redirect to /matches (useEffect below) so returning attendees
// don't get re-pitched. Layout.tsx hides the Home nav link, mobile bottom
// tabs, and ChatWidget on this path so Z's design owns the canvas.
export default function HomeLanding() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const primaryHref = isAuthenticated ? "/matches" : "/register";
  const primaryLabel = isAuthenticated ? "View your matches" : "Get your introductions";

  // Auto-redirect logged-in users away from the marketing page.
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/matches", { replace: true });
    }
  }, [isAuthenticated, navigate]);
  useEffect(() => {
    const reveals = document.querySelectorAll<HTMLElement>(".z-landing .r:not(.in)");
    const revealObs = new IntersectionObserver(
      (es) => {
        es.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            revealObs.unobserve(e.target);
          }
        });
      },
      { threshold: 0.16, rootMargin: "0px 0px -8% 0px" }
    );
    reveals.forEach((el) => revealObs.observe(el));

    const ghosts = document.querySelectorAll<HTMLElement>(".z-landing .gcard.lit");
    const ghostObs = new IntersectionObserver(
      (es) => {
        es.forEach((e) => {
          if (e.isIntersecting && e.target.classList.contains("lit")) {
            const cards = Array.from(document.querySelectorAll(".z-landing .gcard.lit"));
            const order = cards.indexOf(e.target as Element);
            setTimeout(() => e.target.classList.add("resolved"), 850 + order * 650);
            ghostObs.unobserve(e.target);
          }
        });
      },
      { threshold: 0.55 }
    );
    ghosts.forEach((el) => ghostObs.observe(el));

    const counters = document.querySelectorAll<HTMLElement>(".z-landing [data-count]");
    const countObs = new IntersectionObserver(
      (es) => {
        es.forEach((e) => {
          if (e.isIntersecting) {
            const el = e.target as HTMLElement;
            const target = +(el.dataset.count || "0");
            const pre = el.dataset.prefix || "";
            const suf = el.dataset.suffix || "";
            const dur = 1500;
            const t0 = performance.now();
            const step = (now: number) => {
              const p = Math.min((now - t0) / dur, 1);
              const eased = 1 - Math.pow(1 - p, 3);
              const v = Math.round(target * eased);
              el.textContent = pre + (target >= 1000 ? v.toLocaleString("en-US") : v) + suf;
              if (p < 1) requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
            countObs.unobserve(el);
          }
        });
      },
      { threshold: 0.6 }
    );
    counters.forEach((el) => countObs.observe(el));

    return () => {
      revealObs.disconnect();
      ghostObs.disconnect();
      countObs.disconnect();
    };
  }, []);

  return (
    <div className="z-landing">
      <style>{`
        .z-landing {
          --ink: rgb(8,8,8);
          --cream: rgb(250,248,245);
          --orange: #F76A0C;
          --grey: rgba(255,255,255,.46);
          --grey-dim: rgba(255,255,255,.30);
          --line: rgba(255,255,255,.10);
          --serif: 'Fraunces', Georgia, serif;
          --display: 'Poppins', sans-serif;
          --body: 'Inter', sans-serif;
          --mono: 'JetBrains Mono', monospace;
          background: var(--ink);
          color: #fff;
          font-family: var(--body);
          -webkit-font-smoothing: antialiased;
          min-height: 100vh;
          position: relative;
          overflow-x: hidden;
        }
        .z-landing *, .z-landing *::before, .z-landing *::after { box-sizing: border-box; }
        .z-landing::before {
          content: ""; position: absolute; inset: 0; z-index: 1; pointer-events: none;
          background-image: repeating-linear-gradient(45deg, rgba(255,255,255,.009) 0 1px, transparent 1px 7px);
        }
        .z-landing::after {
          content: ""; position: absolute; inset: 0; z-index: 1; pointer-events: none; opacity: .5;
          background: radial-gradient(120% 80% at 50% 0%, transparent 55%, rgba(0,0,0,.6) 100%);
        }
        .z-landing .wrap { max-width: 1100px; margin: 0 auto; padding: 0 40px; position: relative; z-index: 2; }

        /* Hidden — top nav already shows the POT wordmark, so this
           would be a duplicate. Kept in the JSX in case we ever decide
           to bypass Layout again. */
        .z-landing .mark { display: none; }

        .z-landing .r { opacity: 0; transform: translateY(24px);
          transition: opacity 1s cubic-bezier(.16,1,.3,1), transform 1s cubic-bezier(.16,1,.3,1); }
        .z-landing .r.in { opacity: 1; transform: none; }
        .z-landing .d1 { transition-delay: .1s; }
        .z-landing .d2 { transition-delay: .22s; }
        .z-landing .d3 { transition-delay: .36s; }
        .z-landing .d4 { transition-delay: .5s; }

        /* min-height accounts for the 64px top nav so the hero doesn't
           overshoot the viewport. Top padding cut from 120px → 40px so
           the eyebrow lands just below the nav and the CTA is above the
           fold on a typical 800–900px viewport. */
        .z-landing .hero { min-height: calc(100vh - 64px); display: flex; flex-direction: column; justify-content: center; padding: 40px 0 60px; }
        .z-landing .eyebrow { font-family: var(--mono); font-size: 12px; letter-spacing: .34em; color: var(--grey); text-transform: uppercase; margin-bottom: 44px; }
        .z-landing .eyebrow .o { color: var(--orange); }
        .z-landing .hero h1 { font-family: var(--serif); font-weight: 300; font-size: clamp(40px,7vw,104px); line-height: 1.05; letter-spacing: -.022em; max-width: 16ch; margin: 0; }
        .z-landing .hero h1 em { font-style: italic; color: var(--orange); }
        .z-landing .hero h1 .dim { color: var(--grey-dim); }
        .z-landing .hero .sub { margin: 40px 0 0; max-width: 40ch; font-size: clamp(16px,1.4vw,20px); line-height: 1.6; color: rgba(255,255,255,.62); font-weight: 300; }
        .z-landing .cta-row { margin-top: 52px; display: flex; align-items: center; gap: 28px; flex-wrap: wrap; }
        .z-landing .btn { display: inline-flex; align-items: center; gap: 12px; background: var(--orange); color: #0a0500;
          font-family: var(--display); font-weight: 600; font-size: 15px; padding: 18px 34px; border-radius: 100px;
          text-decoration: none; transition: transform .4s cubic-bezier(.16,1,.3,1), box-shadow .4s ease; box-shadow: 0 0 0 rgba(247,106,12,0); border: 0; cursor: pointer; }
        .z-landing .btn:hover { transform: translateY(-2px); box-shadow: 0 18px 50px -12px rgba(247,106,12,.55); }
        .z-landing .btn .arr { transition: transform .4s cubic-bezier(.16,1,.3,1); }
        .z-landing .btn:hover .arr { transform: translateX(5px); }
        .z-landing .meta { font-family: var(--mono); font-size: 12px; letter-spacing: .18em; color: var(--grey); text-transform: uppercase; }

        /* Was 120px → 80px per section, so the gap between any two
           sections drops from ~240px to ~160px. Less dead-black space
           between e.g. "Watch Matchmaker pull them out of the noise"
           and "Why it matters here". */
        .z-landing section { padding: 80px 0; position: relative; }
        .z-landing .kicker { font-family: var(--mono); font-size: 12px; letter-spacing: .32em; color: var(--orange); text-transform: uppercase; margin-bottom: 32px; }

        .z-landing .wound h2 { font-family: var(--serif); font-weight: 300; font-style: italic; font-size: clamp(30px,4.8vw,66px);
          line-height: 1.14; letter-spacing: -.015em; max-width: 17ch; margin: 0; }
        .z-landing .wound h2 .hl { font-style: normal; }
        .z-landing .wound .body { margin: 40px 0 0; max-width: 48ch; font-size: 18px; line-height: 1.72; color: rgba(255,255,255,.56); font-weight: 300; }
        .z-landing .wound .body strong { color: #fff; font-weight: 500; }

        .z-landing .ghosts { margin-top: 78px; display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; }
        .z-landing .gcard { border: 1px solid var(--line); border-radius: 14px; padding: 24px 22px; position: relative; min-height: 158px;
          background: linear-gradient(180deg, rgba(255,255,255,.025), rgba(255,255,255,0)); overflow: hidden;
          transition: border-color 1.1s cubic-bezier(.16,1,.3,1), background 1.1s cubic-bezier(.16,1,.3,1); }
        .z-landing .gcard .av { width: 40px; height: 40px; border-radius: 50%; background: rgba(255,255,255,.08); margin-bottom: 16px;
          transition: background 1.1s cubic-bezier(.16,1,.3,1); }
        .z-landing .gcard .nm { height: 12px; width: 60%; border-radius: 3px; background: rgba(255,255,255,.16); margin-bottom: 10px;
          filter: blur(4px); transition: filter 1s cubic-bezier(.16,1,.3,1), background 1s ease, width 1s ease; }
        .z-landing .gcard .rl { height: 9px; width: 44%; border-radius: 3px; background: rgba(255,255,255,.10);
          filter: blur(4px); transition: filter 1s cubic-bezier(.16,1,.3,1), background 1s ease, width 1s ease; }
        .z-landing .gcard .tag { position: absolute; bottom: 22px; left: 22px; font-family: var(--mono); font-size: 9px;
          letter-spacing: .16em; color: var(--grey-dim); text-transform: uppercase; transition: color 1s ease; }
        .z-landing .gcard .flag { position: absolute; top: 20px; right: 20px; font-family: var(--mono); font-size: 9px;
          letter-spacing: .14em; color: var(--orange); opacity: 0; transition: opacity .9s ease .35s; }
        .z-landing .gcard .sweep { position: absolute; inset: 0; pointer-events: none; opacity: 0;
          background: linear-gradient(105deg, transparent 38%, rgba(247,106,12,.22) 50%, transparent 62%);
          transform: translateX(-110%); }
        .z-landing .gcard.resolved { border-color: rgba(247,106,12,.5);
          background: linear-gradient(180deg, rgba(247,106,12,.10), rgba(247,106,12,.02)); }
        .z-landing .gcard.resolved .av { background: linear-gradient(135deg, rgba(247,106,12,.55), rgba(247,106,12,.15)); }
        .z-landing .gcard.resolved .nm { filter: none; background: #fff; width: 56%; }
        .z-landing .gcard.resolved .rl { filter: none; background: rgba(255,255,255,.42); width: 70%; }
        .z-landing .gcard.resolved .tag { color: var(--orange); }
        .z-landing .gcard.resolved .flag { opacity: 1; }
        .z-landing .gcard.resolved .sweep { opacity: 1; animation: z-sweep 1.1s cubic-bezier(.16,1,.3,1) .15s forwards; }
        @keyframes z-sweep { from { transform: translateX(-110%); } to { transform: translateX(110%); } }
        .z-landing .ghost-note { margin: 34px 0 0; font-family: var(--mono); font-size: 12px; letter-spacing: .05em; color: var(--grey); }

        .z-landing .stakes h2 { font-family: var(--serif); font-weight: 300; font-size: clamp(30px,4.8vw,66px);
          line-height: 1.13; letter-spacing: -.018em; max-width: 18ch; margin: 0; }
        .z-landing .stakes h2 em { font-style: italic; color: var(--orange); }
        .z-landing .stats { margin-top: 74px; display: flex; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
        .z-landing .stat { flex: 1; padding: 46px 18px; border-right: 1px solid var(--line); }
        .z-landing .stat:last-child { border-right: 0; }
        .z-landing .stat .n { font-family: var(--serif); font-size: clamp(34px,5vw,60px); font-weight: 300; line-height: 1; }
        .z-landing .stat .n.o { color: var(--orange); }
        .z-landing .stat .l { margin-top: 14px; font-family: var(--mono); font-size: 11px; letter-spacing: .2em; color: var(--grey); text-transform: uppercase; }
        .z-landing .stakes .turn { margin: 54px 0 0; max-width: 46ch; font-size: 19px; line-height: 1.66; color: rgba(255,255,255,.62); font-weight: 300; }
        .z-landing .stakes .turn strong { color: #fff; font-weight: 500; }

        .z-landing .feat h2 { font-family: var(--serif); font-weight: 300; font-size: clamp(30px,4.6vw,60px); line-height: 1.12; letter-spacing: -.015em; max-width: 15ch; margin: 0; }
        .z-landing .feat h2 em { font-style: italic; color: var(--orange); }
        .z-landing .hero-feats { margin-top: 72px; display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
        .z-landing .hf { border: 1px solid var(--line); border-radius: 18px; padding: 44px 40px;
          background: linear-gradient(180deg, rgba(255,255,255,.028), rgba(255,255,255,0));
          transition: border-color .5s ease, transform .5s cubic-bezier(.16,1,.3,1); }
        .z-landing .hf:hover { border-color: rgba(247,106,12,.34); transform: translateY(-4px); }
        .z-landing .hf .ix { font-family: var(--mono); font-size: 12px; letter-spacing: .2em; color: var(--orange); }
        .z-landing .hf h3 { font-family: var(--serif); font-size: clamp(26px,3vw,38px); font-weight: 300; margin: 24px 0 16px; letter-spacing: -.01em; }
        .z-landing .hf p { font-size: 16px; line-height: 1.66; color: rgba(255,255,255,.54); font-weight: 300; margin: 0; }
        .z-landing .list { margin-top: 22px; display: grid; grid-template-columns: repeat(4,1fr); border: 1px solid var(--line); border-radius: 18px; overflow: hidden; }
        .z-landing .lf { padding: 34px 28px; border-right: 1px solid var(--line); }
        .z-landing .lf:last-child { border-right: 0; }
        .z-landing .lf .ix { font-family: var(--mono); font-size: 11px; letter-spacing: .2em; color: var(--orange); }
        .z-landing .lf h4 { font-family: var(--display); font-size: 18px; font-weight: 500; margin: 14px 0 8px; }
        .z-landing .lf p { font-size: 14px; line-height: 1.55; color: rgba(255,255,255,.46); font-weight: 300; margin: 0; }

        .z-landing .dream { background: var(--cream); color: var(--ink); padding: 110px 0; }
        .z-landing .dream::before { content: ""; position: absolute; inset: 0; pointer-events: none;
          background-image: repeating-linear-gradient(45deg, rgba(0,0,0,.012) 0 1px, transparent 1px 7px); }
        .z-landing .dream .kicker { color: var(--orange); }
        .z-landing .dream h2 { font-family: var(--serif); font-weight: 300; font-size: clamp(34px,5.4vw,76px);
          line-height: 1.1; letter-spacing: -.02em; max-width: 17ch; margin: 0; }
        .z-landing .dream h2 em { font-style: italic; color: var(--orange); }
        .z-landing .dream .under { margin: 38px 0 0; font-family: var(--serif); font-style: italic; font-weight: 300;
          font-size: clamp(20px,2.4vw,30px); color: rgba(8,8,8,.5); max-width: 24ch; line-height: 1.3; }

        .z-landing .close { text-align: center; padding: 110px 0 90px; }
        .z-landing .close .logo { font-family: var(--display); font-weight: 600; font-size: clamp(28px,4vw,46px); letter-spacing: -.01em; }
        .z-landing .close .logo .o { color: var(--orange); font-style: italic; font-family: var(--serif); font-weight: 400; }
        .z-landing .close .line { margin: 36px auto 0; font-family: var(--serif); font-weight: 300; font-style: italic;
          font-size: clamp(24px,3.4vw,42px); max-width: 17ch; line-height: 1.2; }
        .z-landing .close .datemeta { margin-top: 42px; font-family: var(--mono); font-size: 12px; letter-spacing: .26em; color: var(--grey); text-transform: uppercase; }
        .z-landing .close .btn { margin-top: 46px; }

        .z-landing footer { border-top: 1px solid var(--line); padding: 42px 0; }
        .z-landing footer .wrap { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; }
        .z-landing footer span { font-family: var(--mono); font-size: 11px; letter-spacing: .18em; color: var(--grey-dim); text-transform: uppercase; }

        @media (max-width: 880px) {
          .z-landing .wrap { padding: 0 24px; }
          .z-landing .mark { left: 24px; top: 28px; }
          .z-landing section { padding: 56px 0; }
          .z-landing .ghosts { grid-template-columns: 1fr 1fr; }
          .z-landing .hero-feats { grid-template-columns: 1fr; }
          .z-landing .list { grid-template-columns: 1fr 1fr; }
          .z-landing .lf:nth-child(2n) { border-right: 0; }
          .z-landing .lf:nth-child(1), .z-landing .lf:nth-child(2) { border-bottom: 1px solid var(--line); }
          .z-landing .stats { flex-direction: column; }
          .z-landing .stat { border-right: 0; border-bottom: 1px solid var(--line); }
          .z-landing .stat:last-child { border-bottom: 0; }
        }
        @media (max-width: 540px) {
          .z-landing .ghosts { grid-template-columns: 1fr; }
          .z-landing .list { grid-template-columns: 1fr; }
          .z-landing .lf { border-right: 0; border-bottom: 1px solid var(--line); }
          .z-landing .lf:last-child { border-bottom: 0; }
        }
      `}</style>

      <div className="mark">Proof of Talk</div>

      <header className="hero">
        <div className="wrap">
          <div className="eyebrow r in">Matchmaker <span className="o">·</span> Built into Proof of Talk 2026</div>
          <h1 className="r in d1">Four people here will change your year. <span className="dim">Miss them and you'll</span> <em>never even know.</em></h1>
          <p className="sub r in d2">Matchmaker finds them before you land, and tells you exactly why they matter.</p>
          <div className="cta-row r in d3">
            <Link to={primaryHref} className="btn">{primaryLabel} <span className="arr">→</span></Link>
            {!isAuthenticated && (
              <Link to="/login" className="meta" style={{ textDecoration: "none" }}>
                Sign in →
              </Link>
            )}
            <span className="meta">Louvre Palace · Paris · June 2–3, 2026</span>
          </div>
        </div>
      </header>

      <section className="wound">
        <div className="wrap">
          <div className="kicker r">The part nobody admits</div>
          <h2 className="r d1">You always fly home with a stack of cards <span className="hl">and a feeling you missed someone.</span></h2>
          <p className="body r d2">You did. They were in the room the whole time. You found them on LinkedIn a week too late, if you found them at all. <strong>A miss leaves no trace, so you never learn what it cost you.</strong></p>
          <div className="ghosts">
            <div className="gcard r d1"><div className="sweep"></div><div className="av"></div><div className="nm"></div><div className="rl"></div><div className="tag">In the room · unmet</div><div className="flag">Surfaced</div></div>
            <div className="gcard lit r d1"><div className="sweep"></div><div className="av"></div><div className="nm"></div><div className="rl"></div><div className="tag">In the room · unmet</div><div className="flag">Surfaced for you</div></div>
            <div className="gcard r d1"><div className="sweep"></div><div className="av"></div><div className="nm"></div><div className="rl"></div><div className="tag">In the room · unmet</div><div className="flag">Surfaced</div></div>
            <div className="gcard lit r d1"><div className="sweep"></div><div className="av"></div><div className="nm"></div><div className="rl"></div><div className="tag">In the room · unmet</div><div className="flag">Surfaced for you</div></div>
          </div>
          <p className="ghost-note r d2">Two of these would have mattered. Watch Matchmaker pull them out of the noise.</p>
        </div>
      </section>

      <section className="stakes">
        <div className="wrap">
          <div className="kicker r">Why it matters here</div>
          <h2 className="r d1">This is the densest room your industry will be in all year. <em>Which makes the meeting you miss the most expensive one you'll never have.</em></h2>
          <div className="stats r d2">
            <div className="stat"><div className="n" data-count="2500">0</div><div className="l">In the room</div></div>
            <div className="stat"><div className="n o" data-count="18" data-prefix="$" data-suffix="T">0</div><div className="l">Combined value</div></div>
            <div className="stat"><div className="n" data-count="93" data-suffix="%">0</div><div className="l">C-suite</div></div>
          </div>
          <p className="turn r d3">Every event sells you a room this size. None of them get you to the people in it who matter. <strong>That gap is the entire product.</strong></p>
        </div>
      </section>

      <section className="feat">
        <div className="wrap">
          <div className="kicker r">How it works</div>
          <h2 className="r d1">Six things, <em>handled before the doors open.</em></h2>
          <div className="hero-feats">
            <div className="hf r d1">
              <div className="ix">01 · The engine</div>
              <h3>AI Matchmaking</h3>
              <p>It reads every attendee and hands you the few who matter, ranked, with the reason spelled out, before you've left for the airport.</p>
            </div>
            <div className="hf r d2">
              <div className="ix">02 · The edge</div>
              <h3>AI Concierge</h3>
              <p>Ask anything about anyone in the room. Walk into every meeting fully briefed from one question, sourced from real data.</p>
            </div>
          </div>
          <div className="list">
            <div className="lf r d1"><div className="ix">03</div><h4>Auto Profile</h4><p>Your profile, drafted by the Concierge. One tap to publish.</p></div>
            <div className="lf r d2"><div className="ix">04</div><h4>Mutual Match</h4><p>Both sides say yes before the handshake. No cold intros.</p></div>
            <div className="lf r d3"><div className="ix">05</div><h4>Smart Booking</h4><p>One tap. Availability checked. Room and invite locked.</p></div>
            <div className="lf r d4"><div className="ix">06</div><h4>Magic Link</h4><p>One link, every meeting. No login, no app, no friction.</p></div>
          </div>
        </div>
      </section>

      <section className="dream">
        <div className="wrap">
          <div className="kicker r">What changes</div>
          <h2 className="r d1">You walk in Tuesday morning and the meeting that defines your year is <em>already on your calendar.</em></h2>
          <p className="under r d2">You stop working the room. The room was worked for you.</p>
        </div>
      </section>

      <section className="close">
        <div className="wrap">
          <div className="logo r">Proof <span className="o">of</span> Talk</div>
          <p className="line r d1">Your four are already in the room. Make sure you're the one who meets them.</p>
          <div className="datemeta r d2">Louvre Palace · Paris · June 2–3, 2026</div>
          <Link to={primaryHref} className="btn r d3">{primaryLabel} <span className="arr">→</span></Link>
        </div>
      </section>

      <footer>
        <div className="wrap">
          <span>Matchmaker · Built into Proof of Talk</span>
          <span>2,500 people · 2 days · 1 engine</span>
        </div>
      </footer>
    </div>
  );
}
