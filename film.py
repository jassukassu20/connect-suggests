"""Record the pitch video: intro scenes + live demo with a human-like cursor and zooms, timed to the voice-over.
Writes video/film_raw.webm and video/timeline.json (start time of every voice line)."""
import asyncio
import glob
import json
import math
import os
import random
import time

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "file://" + os.path.join(os.path.dirname(HERE), "app", "connect_story.html")
DUR = json.load(open(os.path.join(HERE, "vo", "durations.json")))["durations"]
W, H = 1600, 900
random.seed(7)

INJECT = r"""
(()=>{
const st=document.createElement('style');st.textContent=`
#cur{position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483647;pointer-events:none;transform:translate(-3px,-2px);filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
.rip{position:fixed;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;border:3px solid rgba(14,122,85,.85);z-index:2147483646;pointer-events:none;animation:rip .55s ease-out forwards}
@keyframes rip{from{transform:scale(.3);opacity:1}to{transform:scale(1.4);opacity:0}}
#chap{position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:2147483645;background:rgba(22,32,28,.92);color:#fff;font:700 13px Inter,sans-serif;letter-spacing:.14em;padding:8px 16px;border-radius:99px;transition:opacity .4s;opacity:0}
#chap i{font-style:normal;color:#7ee2b8;font-weight:600;letter-spacing:.04em;margin-left:8px}
#film{position:fixed;inset:0;z-index:2147483600;display:flex;align-items:center;justify-content:center;font-family:Inter,sans-serif;transition:opacity .7s}
#film .sc{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .6s}
#film .sc.on{opacity:1}
.fx{opacity:0;transform:translateY(18px);transition:opacity .6s ease,transform .6s ease}.fx.on{opacity:1;transform:none}
body{transition:transform .9s cubic-bezier(.4,0,.2,1)}
`;document.head.appendChild(st);
const c=document.createElement('div');c.id='cur';c.innerHTML='<svg viewBox="0 0 24 24" width="26" height="26"><path d="M3 2l7.5 19 2.4-7.6L20.5 11z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
document.documentElement.appendChild(c);
document.addEventListener('mousemove',e=>{c.style.left=e.clientX+'px';c.style.top=e.clientY+'px'},true);
const ch=document.createElement('div');ch.id='chap';document.documentElement.appendChild(ch);
const f=document.createElement('div');f.id='film';f.innerHTML=`
<div class="sc" id="sc-prob" style="background:radial-gradient(1200px 700px at 30% 20%,#1f3d33,#0b1612);color:#eef3ef">
  <div style="display:flex;gap:90px;align-items:center">
    <div id="pA" class="fx" style="width:430px">
      <div style="font:600 22px Inter;color:#9fc7b6;margin-bottom:16px">Christmas Day · 11:00</div>
      <div style="background:#fff;color:#16201c;border-radius:22px;padding:24px;box-shadow:0 30px 60px rgba(0,0,0,.35)">
        <div style="background:#f1f3f4;border-radius:99px;padding:10px 16px;color:#666;font-size:16px;margin-bottom:16px">🔍 café near me</div>
        <div style="font:700 26px 'Space Grotesk',Inter">Kahvila Aurora</div>
        <div style="color:#e37400;font-size:16px;margin:4px 0">★★★★★ <span style="color:#666">4.7 · Café · Helsinki</span></div>
        <div style="font-size:22px;font-weight:700;color:#188038;margin-top:10px">Open now · until 18:00</div>
      </div>
    </div>
    <div id="pB" class="fx" style="text-align:center">
      <svg width="260" height="330" viewBox="0 0 260 330"><rect x="30" y="10" width="200" height="310" rx="10" fill="#5b3a29"/><rect x="48" y="30" width="164" height="120" rx="6" fill="#2a1b13"/><rect x="48" y="170" width="164" height="130" rx="6" fill="#4a2f21"/>
      <rect x="150" y="160" width="46" height="40" rx="6" fill="#c9a227"/><path d="M158 160v-14a15 15 0 0130 0v14" stroke="#c9a227" stroke-width="7" fill="none"/></svg>
      <div style="font:800 64px 'Space Grotesk',Inter;color:#ff6b4a;transform:rotate(-8deg);margin-top:-200px;border:6px solid #ff6b4a;border-radius:14px;padding:4px 22px;display:inline-block;background:rgba(11,22,18,.75)">CLOSED</div>
    </div>
  </div>
  <div id="pC" class="fx" style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#0b1612">
    <div style="font:700 150px 'Space Grotesk',Inter;color:#ff8a65;line-height:1">≈ 1 in 2</div>
    <div style="font:500 34px Inter;color:#eef3ef;margin-top:18px;text-align:center;max-width:900px;line-height:1.35">holiday listings will show the <b>wrong hours</b> this season</div>
    <div style="font:500 17px Inter;color:#7f948b;margin-top:26px">49 % of business × holiday rows · Fonecta Connect challenge data (simulated)</div>
  </div>
</div>
<div class="sc" id="sc-sol" style="background:#f6f4ef;color:#16201c;flex-direction:column">
  <div id="sA" class="fx" style="display:flex;align-items:center;gap:18px"><div style="width:74px;height:74px;border-radius:20px;background:#0e7a55;color:#fff;display:grid;place-items:center;font-size:40px">✓</div><div style="font:700 76px 'Space Grotesk',Inter;letter-spacing:-.02em">Connect Suggests</div></div>
  <div style="display:flex;gap:22px;margin-top:56px">
    ${[['🔍','Detect','wrong hours before the holiday'],['💬','One message','right hours + the reason'],['👆','One tap','approve, edit or say no'],['🌍','Live everywhere','search, maps, assistants']].map((x,i)=>`<div id="s${i}" class="fx" style="width:250px;background:#fffdf9;border:1px solid #e6e1d7;border-radius:22px;padding:26px 22px;box-shadow:0 14px 30px rgba(40,30,10,.06)"><div style="font-size:40px">${x[0]}</div><div style="font:700 25px 'Space Grotesk',Inter;margin-top:12px">${x[1]}</div><div style="font-size:17px;color:#66726d;margin-top:6px;line-height:1.4">${x[2]}</div></div>`).join('')}
  </div>
  <div id="sT" class="fx" style="font:700 46px 'Space Grotesk',Inter;margin-top:56px">Connect suggests. <span style="color:#0e7a55">The customer approves.</span></div>
</div>
<div class="sc" id="sc-end" style="background:radial-gradient(1200px 700px at 30% 20%,#1f3d33,#0b1612);color:#eef3ef;flex-direction:column">
  <div class="fx" id="eA" style="display:flex;align-items:center;gap:16px"><div style="width:60px;height:60px;border-radius:16px;background:#2fbf8a;color:#06241a;display:grid;place-items:center;font-size:32px">✓</div><div style="font:700 60px 'Space Grotesk',Inter">Connect Suggests</div></div>
  <div class="fx" id="eB" style="font:700 54px 'Space Grotesk',Inter;margin-top:34px;text-align:center;line-height:1.15">Connect suggests.<br><span style="color:#2fbf8a">The customer approves.</span></div>
  <div class="fx" id="eC" style="font:500 19px Inter;color:#9fb3ab;margin-top:44px">Working prototype · Since AI 2026 × Fonecta · simulated challenge data</div>
</div>`;
document.documentElement.appendChild(f);
window.FILM={
 scene(id){document.querySelectorAll('#film .sc').forEach(s=>s.classList.toggle('on',s.id===id));f.style.opacity=id?1:0;f.style.pointerEvents=id?'auto':'none'},
 show(id){document.getElementById(id).classList.add('on')},
 hide(id){document.getElementById(id).classList.remove('on')},
 chap(t,sub){ch.innerHTML=t+(sub?'<i>'+sub+'</i>':'');ch.style.opacity=t?1:0},
 zoom(x,y,s){document.body.style.transformOrigin=(x+window.scrollX)+'px '+(y+window.scrollY)+'px';document.body.style.transform='scale('+s+')'},
 unzoom(){document.body.style.transform='none'},
 ripple(x,y){const r=document.createElement('div');r.className='rip';r.style.left=x+'px';r.style.top=y+'px';document.documentElement.appendChild(r);setTimeout(()=>r.remove(),700)}
};
})();
"""


class Film:
    def __init__(self, pg):
        self.pg = pg
        self.x, self.y = W * 0.55, H * 0.6
        self.t0 = None
        self.timeline = {}

    def now(self):
        return time.monotonic() - self.t0

    async def js(self, code, *a):
        return await self.pg.evaluate(code, *a)

    async def move(self, x, y, dur=None):
        """Human-like move: eased curve with a slight arc and tiny jitter, ending exactly on target."""
        x0, y0 = self.x, self.y
        dist = math.hypot(x - x0, y - y0)
        dur = dur or min(1.1, 0.35 + dist / 1400)
        n = max(12, int(dur * 60))
        # control point off the straight line → natural arc
        mx, my = (x0 + x) / 2, (y0 + y) / 2
        nx, ny = -(y - y0), (x - x0)
        ln = math.hypot(nx, ny) or 1
        bend = random.uniform(-0.18, 0.18) * dist
        cx, cy = mx + nx / ln * bend, my + ny / ln * bend
        t_start = time.monotonic()
        for i in range(1, n + 1):
            t = i / n
            e = t * t * (3 - 2 * t)  # smoothstep ease-in-out
            px = (1 - e) ** 2 * x0 + 2 * (1 - e) * e * cx + e * e * x
            py = (1 - e) ** 2 * y0 + 2 * (1 - e) * e * cy + e * e * y
            if i < n:
                px += random.uniform(-0.6, 0.6)
                py += random.uniform(-0.6, 0.6)
            await self.pg.mouse.move(px, py)
            target = t_start + dur * t
            sl = target - time.monotonic()
            if sl > 0:
                await asyncio.sleep(sl)
        self.x, self.y = x, y

    async def box(self, loc):
        await loc.scroll_into_view_if_needed()
        b = await loc.bounding_box()
        return b

    async def to(self, loc, dx=None, dy=None, dur=None):
        b = await self.box(loc)
        x = b["x"] + b["width"] * (dx if dx is not None else random.uniform(0.4, 0.6))
        y = b["y"] + b["height"] * (dy if dy is not None else random.uniform(0.4, 0.6))
        await self.move(x, y, dur)
        return x, y

    async def click(self, loc, dx=None, dy=None, dur=None, pause=0.12):
        x, y = await self.to(loc, dx, dy, dur)
        await asyncio.sleep(pause)
        await self.js("([x,y])=>FILM.ripple(x,y)", [x, y])
        await self.pg.mouse.down()
        await asyncio.sleep(0.07)
        await self.pg.mouse.up()
        await asyncio.sleep(0.15)

    async def zoom_on(self, loc, s=1.35):
        b = await loc.bounding_box()
        await self.js("([x,y,s])=>FILM.zoom(x,y,s)", [b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, s])
        await asyncio.sleep(0.95)

    async def unzoom(self):
        await self.js("()=>FILM.unzoom()")
        await asyncio.sleep(0.95)

    async def line(self, lid, act=None, gap=0.45, lead=0.0):
        """Speak line `lid` (timestamp recorded) while running `act(at)`; return when line + gap is over."""
        start = self.now() + lead
        if lead:
            await asyncio.sleep(lead)
        self.timeline[lid] = round(start, 3)

        async def at(sec):
            d = start + sec - self.now()
            if d > 0:
                await asyncio.sleep(d)
        if act:
            await act(at)
        rest = start + DUR[lid] + gap - self.now()
        if rest > 0:
            await asyncio.sleep(rest)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--font-render-hinting=none"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, record_video_dir=HERE, record_video_size={"width": W, "height": H})
        pg = await ctx.new_page()
        f = Film(pg)
        f.t0 = time.monotonic()
        await pg.goto(PAGE)
        await pg.evaluate(INJECT)
        await pg.evaluate("FILM.scene('sc-prob')")
        await pg.mouse.move(f.x, f.y)
        await asyncio.sleep(0.6)
        lead_in = f.now()
        js = f.js
        L = pg.locator

        # ---------------- PROBLEM ----------------
        await js("()=>FILM.chap('THE PROBLEM')")

        async def p1(at):
            await at(0.1); await js("()=>FILM.show('pA')")
        await f.line("p1", p1, gap=0.25)

        async def p2(at):
            await at(1.35); await js("()=>FILM.show('pB')")
        await f.line("p2", p2, gap=0.6)

        async def p3(at):
            await at(2.6); await js("()=>FILM.show('pC')")
        await f.line("p3", p3, gap=0.6)

        # ---------------- SOLUTION ----------------
        await js("()=>{FILM.scene('sc-sol');FILM.chap('THE SOLUTION')}")

        async def s1(at):
            await at(0.15); await js("()=>FILM.show('sA')")
        await f.line("s1", s1, gap=0.3, lead=0.5)

        async def s2(at):
            await at(0.6); await js("()=>FILM.show('s0')")
            await at(4.6); await js("()=>FILM.show('s1')")
        await f.line("s2", s2, gap=0.25)

        async def s3(at):
            await at(0.1); await js("()=>FILM.show('s2')")
            await at(1.0); await js("()=>FILM.show('s3')")
        await f.line("s3", s3, gap=0.3)

        async def s4(at):
            await at(0.1); await js("()=>FILM.show('sT')")
        await f.line("s4", s4, gap=0.8)

        # ---------------- DEMO ----------------
        await js("()=>{FILM.scene(null);FILM.chap('LIVE DEMO','working prototype · simulated data')}")
        await asyncio.sleep(0.5)

        async def d1(at):
            await f.click(L("text=Start the demo"), dur=0.9)
            await at(4.2)
            await f.to(L(".row").nth(1), 0.3, 0.5, 0.7)
            await at(5.6)
            await f.zoom_on(L(".lst"), 1.3)
            await f.to(L(".lst .hr").nth(1), 0.75, 0.5, 0.6)
        await f.line("d1", d1, gap=0.4, lead=0.3)

        async def d2(at):
            await f.unzoom()
            await f.click(L("#next"), dur=0.6)
            await at(2.9)
            await f.to(L(".row .why").nth(0), 0.5, 0.5, 0.7)
            await at(4.4)
            await f.to(L(".evc").nth(2), 0.5, 0.4, 0.7)
            await at(6.4)
            await f.to(L(".evc").nth(1), 0.4, 0.45, 0.7)
            await f.zoom_on(L(".evc").nth(1), 1.55)
            await at(13.6)
            await f.unzoom()
        await f.line("d2", d2, gap=0.4)

        async def d3(at):
            await f.click(L("#next"), dur=0.6)
            await at(1.0)
            await f.zoom_on(L(".phone"), 1.15)
            await f.to(L(".bub.in").first, 0.6, 0.35, 0.8)
        await f.line("d3", d3, gap=0.5)

        async def d4(at):
            await f.unzoom()
            await f.click(L("#next"), dur=0.6)
            await at(2.4)
            await f.zoom_on(L(".phone"), 1.18)
            await f.click(L(".oi").nth(0).locator("button").nth(1), dur=0.7)
            await at(4.6)
            t = L(".oi").nth(0).locator("input[type=time]").nth(1)
            await f.click(t, 0.35, 0.5, 0.6)
            await t.fill("12:00")
            await at(6.8)
            await f.click(L(".perm input"), dur=0.8)
        await f.line("d4", d4, gap=0.3)

        async def d5(at):
            await f.click(L(".save"), dur=0.6)
            await at(1.4)
            await f.unzoom()
            await at(2.8)
            await f.zoom_on(L(".phone"), 1.15)
            await f.to(L(".pubs div").nth(0), 0.8, 0.5, 0.8)
            await at(6.4)
            await f.to(L(".pubs div").nth(2), 0.8, 0.5, 0.6)
        await f.line("d5", d5, gap=0.4)

        async def d6(at):
            await f.unzoom()
            await f.click(L("#next"), dur=0.6)
            await at(2.0)
            await f.zoom_on(L(".cards .row").nth(0), 1.45)
            await f.to(L(".cards .row").nth(0), 0.35, 0.5, 0.6)
            await at(3.5)
            await f.unzoom()
        await f.line("d6", d6, gap=0.2)

        async def d7(at):
            await f.click(L("#n-home"), dur=0.45)
            await pg.mouse.wheel(0, 520)
            await asyncio.sleep(0.3)
            await f.click(L(".story", has_text="Brand-new"), dur=0.5)
            await at(2.9)
            await f.click(L("#next"), dur=0.6)
            await asyncio.sleep(0.25)
            co = L(".callout.b")
            await js("()=>{document.querySelector('.stage').style.paddingBottom='420px'}")
            await co.evaluate("e=>e.scrollIntoView({block:'center',behavior:'smooth'})")
            await asyncio.sleep(0.6)
            await f.to(co, 0.5, 0.5, 0.5)
            await f.zoom_on(co, 1.3)
        await f.line("d7", d7, gap=0.25)

        async def d8(at):
            await f.unzoom()
            await js("()=>{document.querySelector('.stage').style.paddingBottom='';window.scrollTo(0,0)}")
            await f.click(L("#n-home"), dur=0.45)
            await pg.mouse.wheel(0, 900)
            await asyncio.sleep(0.35)
            await f.click(L(".story", has_text="When not to send"), dur=0.55)
            await at(3.9)
            await f.click(L("#next"), dur=0.6)
            await asyncio.sleep(0.3)
            await f.to(L(".callout.r"), 0.5, 0.5, 0.6)
            await at(5.6)
            await f.click(L("#next"), dur=0.45)
            await asyncio.sleep(0.4)
            await f.to(L(".evc").nth(0), 0.5, 0.5, 0.6)
        await f.line("d8", d8, gap=1.6)

        # ---------------- IMPACT ----------------
        await js("()=>FILM.chap('BUSINESS IMPACT','simulated challenge data')")

        async def i1(at):
            await f.click(L("#n-impact"), dur=0.6)
            await at(1.2)
            await f.to(L(".big div").nth(1), 0.5, 0.5, 0.8)
        await f.line("i1", i1, gap=0.3)

        async def i2(at):
            await pg.mouse.wheel(0, 260)
            await asyncio.sleep(0.4)
            await f.zoom_on(L(".cmp").first, 1.3)
            await f.to(L(".barrow").nth(3), 0.7, 0.5, 0.8)
        await f.line("i2", i2, gap=0.4)

        async def i3(at):
            await f.unzoom()
            await pg.mouse.wheel(0, 420)
            await asyncio.sleep(0.4)
            await f.to(L(".grid2").nth(1).locator(".cmp").first, 0.5, 0.5, 0.9)
        await f.line("i3", i3, gap=0.4)

        async def i4(at):
            await js("()=>{FILM.chap('');FILM.scene('sc-end')}")
            await at(0.2); await js("()=>FILM.show('eA')")
            await at(1.4); await js("()=>FILM.show('eB')")
            await at(3.2); await js("()=>FILM.show('eC')")
        await f.line("i4", i4, gap=2.2)

        f.timeline["_end"] = round(f.now(), 3)
        f.timeline["_lead_in"] = round(lead_in, 3)
        json.dump(f.timeline, open(os.path.join(HERE, "timeline.json"), "w"), indent=1)
        await ctx.close()
        await b.close()
    vids = sorted(glob.glob(os.path.join(HERE, "*.webm")), key=os.path.getmtime)
    os.replace(vids[-1], os.path.join(HERE, "film_raw.webm"))
    print(json.dumps(f.timeline))


asyncio.run(main())
