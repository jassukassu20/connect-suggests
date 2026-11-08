"""Generate the voice-over, one clip per line (Kokoro TTS, voice af_heart). Writes video/vo/<id>.wav + vo/durations.json"""
import json
import os

import soundfile as sf
from kokoro_onnx import Kokoro

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vo")
os.makedirs(OUT, exist_ok=True)

# (id, spoken text, subtitle text, speed)
LINES = [
    # PROBLEM
    ("p1", "It's Christmas Day. Google says your favourite café is open.", "It's Christmas Day. Google says your favourite café is open.", 1.0),
    ("p2", "You drive there… and the door is locked.", "You drive there… and the door is locked.", 0.92),
    ("p3", "Busy owners forget to update their holiday hours. In Fonecta's challenge data, almost half of all holiday listings will show the wrong hours this season.",
     "Busy owners forget to update their holiday hours. In Fonecta's challenge data, almost half of all holiday listings will show the wrong hours this season.", 1.05),
    # SOLUTION
    ("s1", "So we built Connect Suggests.", "So we built Connect Suggests.", 1.0),
    ("s2", "Before every holiday, Connect checks every listing. When the hours will be wrong, the owner gets one short message, with the right hours, and the reason why.",
     "Before every holiday, Connect checks every listing. When the hours will be wrong, the owner gets one short message, with the right hours and the reason why.", 1.05),
    ("s3", "One tap. And it's live everywhere people search.", "One tap. And it's live everywhere people search.", 1.0),
    ("s4", "Connect suggests. The customer approves.", "Connect suggests. The customer approves.", 0.95),
    # DEMO
    ("d1", "Let me show you. This is Kahvila Aurora, a café in Helsinki. Aleksi hasn't entered any holiday hours, so four days will be wrong.",
     "Let me show you. This is Kahvila Aurora, a café in Helsinki. Aleksi hasn't entered any holiday hours, so four days will be wrong.", 1.05),
    ("d2", "Connect works out the right hours from real clues. What he did last year. What similar cafés do. And one signal most people miss: on days a business was secretly closed, customer clicks drop by half. So we spot closures, even when the owner never told us.",
     "Connect works out the right hours from real clues: what he did last year, what similar cafés do. And one signal most people miss: on days a business was secretly closed, customer clicks drop by half. So we spot closures, even when the owner never told us.", 1.07),
    ("d3", "Aleksi gets one text, in his own language, at the time he prefers.", "Aleksi gets one text, in his own language, at the time he prefers.", 1.03),
    ("d4", "No login. No app. This year he closes at twelve on Christmas Eve, so he just changes it. And he lets Connect handle holidays from now on.",
     "No login. No app. This year he closes at 12 on Christmas Eve, so he just changes it. And he lets Connect handle holidays from now on.", 1.03),
    ("d5", "Done. The change goes through the Yext API that Connect already runs on, and Aleksi sees exactly where it goes live, and how fast.",
     "Done. The change goes through the Yext API that Connect already runs on, and Aleksi sees exactly where it goes live, and how fast.", 1.05),
    ("d6", "And it learns. Next Christmas, his own answer comes back automatically.", "And it learns. Next Christmas, his own answer comes back automatically.", 1.0),
    ("d7", "A brand-new customer, with zero history? Connect still helps. And when it isn't sure, it asks, instead of guessing.",
     "A brand-new customer with zero history? Connect still helps. And when it isn't sure, it asks instead of guessing.", 1.03),
    ("d8", "And if reviews say a business has closed for good, Connect sends nothing. A person checks first.",
     "And if reviews say a business has closed for good, Connect sends nothing. A person checks first.", 1.03),
    # IMPACT
    ("i1", "Across all three thousand Connect customers in the challenge data, that's twenty-seven hundred owners helped, with one message each.",
     "Across all 3,000 Connect customers in the challenge data, that's 2,700 owners helped, with one message each.", 1.05),
    ("i2", "Tested on businesses the model had never seen, it protects sixty-nine percent of at-risk searches. Copying last year protects fifty-seven.",
     "Tested on businesses the model had never seen, it protects 69% of at-risk searches. Copying last year protects 57%.", 1.03),
    ("i3", "For Fonecta, that means customers who see Connect working for them, and stay. And the same loop works for review replies, posts, and opening hours.",
     "For Fonecta, that means customers who see Connect working for them, and stay. And the same loop works for review replies, posts and opening hours.", 1.05),
    ("i4", "Connect suggests. The customer approves. And nobody walks to a closed door again.",
     "Connect suggests. The customer approves. And nobody walks to a closed door again.", 0.95),
]

if __name__ == "__main__":
    k = Kokoro("/tmp/kk.onnx", "/tmp/voices.bin")
    dur = {}
    for lid, text, sub, sp in LINES:
        s, sr = k.create(text, voice="af_heart", speed=sp, lang="en-us")
        sf.write(os.path.join(OUT, f"{lid}.wav"), s, sr)
        dur[lid] = round(len(s) / sr, 3)
    json.dump({"durations": dur, "lines": [{"id": a, "sub": c} for a, b, c, d in LINES]}, open(os.path.join(OUT, "durations.json"), "w"), indent=1)
    print(dur, "total", round(sum(dur.values()), 1))
