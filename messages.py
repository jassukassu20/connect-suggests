"""Customer messages in Finnish, Swedish, Norwegian and English.

Deterministic templates on purpose: every sentence is backed by a piece of evidence, nothing is invented,
and the same suggestion always produces the same text (audit trail). An LLM can rephrase, but never adds facts.
"""
from __future__ import annotations

from datetime import date

LINK = "https://connect.fonecta.fi/s/{token}"
WD = {"fi": ["ma", "ti", "ke", "to", "pe", "la", "su"], "sv": ["mån", "tis", "ons", "tor", "fre", "lör", "sön"],
      "nb": ["man", "tir", "ons", "tor", "fre", "lør", "søn"], "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
MON_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

T = {
    "fi": {
        "hi": "Hei {first}!", "closed": "kiinni", "open": "{h}",
        "intro_n": "Googlessa {name} näyttää {n} juhlapäivälle tavalliset aukioloajat. Ehdotamme:",
        "intro_1": "Googlessa {name} näyttää {dm} ({day}) tavalliset aukioloajat {shown}. Ehdotamme:",
        "cta_sms": "Hyväksy kaikki: vastaa KYLLÄ. Muokkaa tai hylkää: {link}",
        "cta_email": "Hyväksy yhdellä painalluksella – kirjautumista ei tarvita.",
        "btn": ["Hyväksy", "Muokkaa", "Ei kiitos"],
        "subject": "{name}: tarkistetaanko juhlapyhien aukioloajat?",
        "why": {"owner_answer": "kerroitte näin viimeksi", "mall": "{mall} on silloin {state}",
                "ly1": "viime vuonna {state}", "ly2": "vuonna {year} {state}",
                "review": "asiakas valitti suljetusta ovesta viime vuonna",
                "analytics": "viime vuonna asiakkaiden klikkaukset putosivat {pct} %", "analytics_all": "viime vuonna klikkaukset loppuivat lähes kokonaan",
                "pilot": "hyväksyitte saman viime vuonna", "peers": "{pct} % vastaavista on kiinni",
                "peers_open": "useimmat vastaavat auki {state}", "google_edit": "Google-käyttäjä ehdotti tätä",
                "google_edit_now": "Google-käyttäjä ehdotti tätä"},
        "auto_intro": "Päivitimme pysyvän lupasi mukaisesti juhlapyhien ajat ({name}):",
        "auto_cta": "Jos jokin on väärin, muuta tai peru: {link}",
        "ask": "Oletteko auki {dm} ({day})? Google näyttää nyt {shown}. Vastaa 1 = tavalliset ajat, 2 = kiinni, 3 = muu aika ({link})",
        "reg": "Asiakkaat kertovat, että aukioloaikanne ovat muuttuneet (\"{quote}\"), mutta Google näyttää vanhat ajat. Päivitetäänkö: {prop}? {link}",
        "season": "Asiakkaiden mukaan olette tauolla (\"{quote}\"), mutta Google näyttää teidät avoinna. Merkitäänkö kiinni kevääseen asti? {link}",
        "confirm": "Valmis! Uudet ajat näkyvät nyt: {where}. Kiitos {first}!",
        "standing": "Hoidetaanko juhlapyhät jatkossa puolestanne? Ilmoitamme aina etukäteen ja voit perua. Vastaa JATKOSSA.",
        "dm": lambda d: f"{d.day}.{d.month}.",
    },
    "sv": {
        "hi": "Hej {first}!", "closed": "stängt", "open": "{h}",
        "intro_n": "På Google visar {name} vanliga öppettider för {n} helgdagar. Vi föreslår:",
        "intro_1": "På Google visar {name} vanliga öppettider {dm} ({day}): {shown}. Vi föreslår:",
        "cta_sms": "Godkänn allt: svara JA. Ändra eller avböj: {link}",
        "cta_email": "Godkänn med ett klick – ingen inloggning behövs.",
        "btn": ["Godkänn", "Ändra", "Nej tack"],
        "subject": "{name}: ska vi uppdatera era helgtider?",
        "why": {"owner_answer": "så svarade ni senast", "mall": "{mall} har då {state}",
                "ly1": "i fjol {state}", "ly2": "år {year} {state}",
                "review": "en kund klagade på stängd dörr i fjol",
                "analytics": "i fjol sjönk kundernas klick med {pct} %", "analytics_all": "i fjol uteblev nästan alla kundklick",
                "pilot": "ni godkände samma i fjol", "peers": "{pct} % av liknande har stängt",
                "peers_open": "de flesta liknande har öppet {state}", "google_edit": "en Google-användare föreslog detta",
                "google_edit_now": "en Google-användare föreslog detta"},
        "auto_intro": "Enligt ert stående godkännande har vi uppdaterat helgtiderna för {name}:",
        "auto_cta": "Om något är fel, ändra eller ångra: {link}",
        "ask": "Har ni öppet {dm} ({day})? Google visar nu {shown}. Svara 1 = vanliga tider, 2 = stängt, 3 = annan tid ({link})",
        "reg": "Kunder skriver att era öppettider har ändrats (\"{quote}\"), men Google visar de gamla. Ska vi uppdatera till: {prop}? {link}",
        "season": "Enligt kunder har ni säsongsuppehåll (\"{quote}\"), men Google visar öppet. Ska vi markera stängt till våren? {link}",
        "confirm": "Klart! De nya tiderna syns nu på: {where}. Tack {first}!",
        "standing": "Vill du att vi sköter helgtiderna åt dig framöver? Vi meddelar alltid i förväg och du kan ångra. Svara FRAMÖVER.",
        "dm": lambda d: f"{d.day}/{d.month}",
    },
    "nb": {
        "hi": "Hei {first}!", "closed": "stengt", "open": "{h}",
        "intro_n": "På Google viser {name} vanlige åpningstider for {n} helligdager. Vi foreslår:",
        "intro_1": "På Google viser {name} vanlige åpningstider {dm} ({day}): {shown}. Vi foreslår:",
        "cta_sms": "Godkjenn alt: svar JA. Endre eller avslå: {link}",
        "cta_email": "Godkjenn med ett klikk – ingen innlogging.",
        "btn": ["Godkjenn", "Endre", "Nei takk"],
        "subject": "{name}: skal vi oppdatere åpningstidene for høytiden?",
        "why": {"owner_answer": "slik svarte dere sist", "mall": "{mall} har da {state}",
                "ly1": "i fjor {state}", "ly2": "i {year} {state}",
                "review": "en kunde klaget på stengt dør i fjor",
                "analytics": "i fjor falt kundeklikkene med {pct} %", "analytics_all": "i fjor uteble nesten alle kundeklikk",
                "pilot": "dere godkjente det samme i fjor", "peers": "{pct} % av lignende har stengt",
                "peers_open": "de fleste lignende har åpent {state}", "google_edit": "en Google-bruker foreslo dette",
                "google_edit_now": "en Google-bruker foreslo dette"},
        "auto_intro": "I tråd med den faste tillatelsen din har vi oppdatert høytidstidene for {name}:",
        "auto_cta": "Hvis noe er feil, endre eller angre: {link}",
        "ask": "Har dere åpent {dm} ({day})? Google viser nå {shown}. Svar 1 = vanlige tider, 2 = stengt, 3 = annen tid ({link})",
        "reg": "Kunder skriver at åpningstidene er endret (\"{quote}\"), men Google viser de gamle. Skal vi oppdatere til: {prop}? {link}",
        "season": "Ifølge kunder har dere sesongpause (\"{quote}\"), men Google viser åpent. Skal vi markere stengt til våren? {link}",
        "confirm": "Ferdig! De nye tidene vises nå på: {where}. Takk {first}!",
        "standing": "Skal vi ta oss av helligdagene for deg fremover? Vi varsler alltid på forhånd, og du kan angre. Svar FREMOVER.",
        "dm": lambda d: f"{d.day}.{d.month}.",
    },
    "en": {
        "hi": "Hi {first}!", "closed": "closed", "open": "{h}",
        "intro_n": "Google shows regular hours for {name} on {n} holidays. We suggest:",
        "intro_1": "Google shows regular hours for {name} on {dm} ({day}): {shown}. We suggest:",
        "cta_sms": "Approve all: reply YES. Edit or decline: {link}",
        "cta_email": "Approve with one tap – no login needed.",
        "btn": ["Approve", "Edit", "No thanks"],
        "subject": "{name}: shall we update your holiday hours?",
        "why": {"owner_answer": "what you told us last time", "mall": "{mall} is {state}",
                "ly1": "last year {state}", "ly2": "in {year} {state}",
                "review": "a customer found a closed door last year",
                "analytics": "customer clicks fell {pct}% that day last year", "analytics_all": "customer clicks almost stopped that day last year",
                "pilot": "you approved the same last year", "peers": "{pct}% of similar businesses close",
                "peers_open": "most similar businesses open {state}", "google_edit": "a Google user suggested this",
                "google_edit_now": "a Google user suggested this"},
        "auto_intro": "As you allowed, we updated the holiday hours for {name}:",
        "auto_cta": "If anything is wrong, change or undo: {link}",
        "ask": "Are you open on {day} {dm}? Google now shows {shown}. Reply 1 = regular hours, 2 = closed, 3 = other ({link})",
        "reg": "Customers say your opening hours have changed (\"{quote}\"), but Google shows the old ones. Update to: {prop}? {link}",
        "season": "Customers say you're on a seasonal break (\"{quote}\"), but Google shows you open. Mark closed until spring? {link}",
        "confirm": "Done! Your new hours now show on: {where}. Thanks {first}!",
        "standing": "Want us to handle public holidays for you from now on? We'll always tell you first and you can undo. Reply FROM NOW ON.",
        "dm": lambda d: f"{d.day} {MON_EN[d.month - 1]}",
    },
}


def nice(h):
    def t(x):
        hh, mm = x.split(":")
        return str(int(hh)) + ("" if mm == "00" else "." + mm)
    return ", ".join("–".join(t(x) for x in iv.split("-")) for iv in h.split(","))


def state(h, lang):
    return T[lang]["closed"] if h == "closed" else T[lang]["open"].format(h=nice(h))


def reason(item, lang, case):
    """Short, strongest supporting reason for one date."""
    t = T[lang]["why"]
    for e in item["evidence"]:
        if not e.get("supports"):
            continue
        ty = e["type"]
        if ty == "mall":
            return t["mall"].format(mall=e["name"], state=state(e["hours"], lang))
        if ty in ("ly1", "ly2"):
            return t[ty].format(state=state(e["hours"], lang), year=e["date"][:4])
        if ty == "analytics":
            return t["analytics_all"] if e["drop_pct"] >= 90 else t["analytics"].format(pct=e["drop_pct"])
        if ty == "peers":
            if item["proposed"] == "closed":
                return t["peers"].format(pct=e["closed_pct"])
            return t["peers_open"].format(state=state(item["proposed"], lang))
        if ty == "pilot" and e["decision"] in ("ACCEPTED", "EDITED"):
            return t["pilot"]
        if ty in t:
            return t[ty]
    return ""


def item_line(item, lang, case, bullet="• "):
    d = date.fromisoformat(item["date"])
    r = reason(item, lang, case)
    return f"{bullet}{WD[lang][d.weekday()]} {T[lang]['dm'](d)} {state(item['proposed'], lang)}" + (f" ({r})" if r else "")


def compose(case, token="AB12CD"):
    msgs = {}
    link = LINK.format(token=token)
    for lang in ("fi", "sv", "nb", "en"):
        t = T[lang]
        first = case["contact"].get("contact_first_name") or ""
        items = case["items"]
        head = t["hi"].format(first=first)
        out = {"lang": lang}
        if case["mode"] in ("SUGGEST", "AUTO_APPLY") and items:
            shown_items = items if len(items) <= 6 else items[:6]
            if case["mode"] == "AUTO_APPLY":
                body = [head, t["auto_intro"].format(name=case["name"])] + \
                       [item_line(i, lang, case) for i in shown_items if i.get("auto")] + [t["auto_cta"].format(link=link)]
                pend = [i for i in shown_items if not i.get("auto")]
                if pend:
                    body.insert(-1, t["intro_n"].format(name=case["name"], n=len(pend)))
                    for i in pend:
                        body.insert(-1, item_line(i, lang, case))
            else:
                if len(items) == 1:
                    d = date.fromisoformat(items[0]["date"])
                    intro = t["intro_1"].format(name=case["name"], day=items[0]["day_name"]["local"] if lang != "en" else
                                                items[0]["day_name"]["en"], dm=t["dm"](d), shown=state(items[0]["shown"], lang))
                else:
                    intro = t["intro_n"].format(name=case["name"], n=len(items))
                body = [head, intro] + [item_line(i, lang, case) for i in shown_items]
                if len(items) > 6:
                    body.append(f"+{len(items) - 6} …")
                body.append(t["cta_sms"].format(link=link))
            out["sms"] = "\n".join(body)
            out["email_subject"] = t["subject"].format(name=case["name"])
            out["email_lines"] = [item_line(i, lang, case, bullet="") for i in items]
            out["email_cta"] = t["cta_email"]
            out["buttons"] = t["btn"]
        elif case["mode"] == "ASK" and case["asks"]:
            a = case["asks"][0]
            d = date.fromisoformat(a["date"])
            out["sms"] = head + " " + t["ask"].format(day=a["day_name"]["local"] if lang != "en" else a["day_name"]["en"],
                                                      dm=t["dm"](d), shown=state(a["shown"], lang), link=link)
        if case["mode"] in ("SUGGEST", "AUTO_APPLY") and case.get("asks"):
            a = case["asks"][0]
            d = date.fromisoformat(a["date"])
            out["ask_sms"] = t["ask"].format(day=a["day_name"]["local"] if lang != "en" else a["day_name"]["en"],
                                             dm=t["dm"](d), shown=state(a["shown"], lang), link=link)
        for h in case.get("health", []):
            if h["type"] == "REGULAR_HOURS_CHANGED":
                prop = state(h["proposed_hours"], lang) if h.get("proposed_hours") else "?"
                if h.get("sunday_closed"):
                    prop = f"{WD[lang][0]}–{WD[lang][5]} {prop}, {WD[lang][6]} {T[lang]['closed']}"
                out["health_sms"] = head + " " + t["reg"].format(quote=h["quote"][:60], prop=prop, link=link)
            elif h["type"] == "SEASONAL_BREAK":
                out["health_sms"] = head + " " + t["season"].format(quote=h["quote"][:60], link=link)
        out["confirm_tpl"] = t["confirm"]
        out["standing_tpl"] = t["standing"]
        msgs[lang] = out
    return msgs
