# NextBest: Medibank final demonstration, 2 November 2026

BA403, 12:00 to 1:30 pm. Ten-minute face-to-face slot. Medibank representatives attend.
The brief for this session: show how the solution works and how it addresses the
Medibank challenge. This runbook replaces the source-only notes in
`demo_10min_and_qa.md` for this session.

| Presenter | Owns on the day |
|---|---|
| Bikram | Opening, Bill Explainer, close and the ask |
| Minhaj | Journey Coach, Navigator, pilot measures |
| Aayush | Ask NextBest and the safety boundary |

The person speaking does not drive the laptop. The next presenter drives, so every
hand-over is also a seat change, not a pause.

---

## The pitch in one sentence

NextBest teaches the few OSHC ideas students get wrong, at the moments they already
pass through, and never tells a student something about their own cover that only
Medibank can confirm.

Three claims we can defend on screen:

1. **Before need:** a three-minute, voluntary lesson with a scenario and a takeaway card.
2. **At the moment of need:** a practical next step for a GP visit, a bill or a question.
3. **Safe by construction:** every chat message is checked before anything is answered,
   and personal cover, symptoms and emergencies always go to the right human service.

---

## Before the day

| When | Who | Task |
|---|---|---|
| Fri 30 Oct | Aayush | Review PR for `demo/final-integration`: `scripts/make_invoices.py` (Bikram must not read it) and the symptom handoff change in `oshc/care_navigation.py` |
| Fri 30 Oct | Minhaj | Confirm the telemetry and Coach string port matches your Week 9 intent. Ask a fluent Hindi reader to check `oshc/coach_strings.py` |
| Fri 30 Oct | Reviewer | Merge to `main` once CI is green |
| Sat 31 Oct | Bikram | On the demo laptop: pull `main`, run `.\setup.ps1`, confirm all tests pass |
| Sat 31 Oct | Bikram | Live check with a new filename: `python scripts/check_live_chat.py --live --out docs/prototype/live_connection_2026-10-31.json`. Exit code 0 is required. Then `python -m oshc.llm_budget status` and note the remaining allowance |
| Sat 31 Oct | All | Full timed rehearsal, twice. Record the second run as a screen capture (Win+Alt+R) as the backup |
| Sun 1 Nov | Bikram | Final report goes first. No code changes after Saturday's rehearsal |

If Hindi review has not happened by Saturday, show the language switch but say the
strings are a draft. Do not present unreviewed Hindi as reviewed.

---

## Room setup (arrive 11:30)

1. Laptop on charger, HDMI tested on the room screen, notifications off, browser zoom 125%.
2. Phone hotspot ready as a second network.
3. Start live mode with clean pilot counts:
   ```powershell
   .\Start_NextBest.ps1 -ResetCounts
   ```
4. Open `http://127.0.0.1:8502`. On Ask NextBest, confirm there is no missing-key
   warning. Ask one warm-up question, then click **Clear chat**. (The Ask page records
   no pilot counts, so this does not change the dashboard.)
5. Leave the app on **Home**. Keep this runbook printed.

---

## Run sheet

Times include clicking and pauses. Hold the checkpoints: Coach by 1:00, Bill Explainer
by 4:00, Ask by 6:00, dashboard by 8:15.

### 0:00 to 1:00 · Bikram · Home

**Say:**
"We read first-person accounts from international students where OSHC went wrong.
Of 36 that showed a real comprehension gap, 20 came down to two things: what is
covered, and how to claim. Most OSHC education reaches students as a website or an
orientation talk, at a point when they have no reason to care yet.

NextBest is not another app. It is a set of short learning moments designed to sit in
channels Medibank and universities already own: the offer letter, the pre-departure
email, the student portal, and the moment a student is holding a bill. Today it runs as
a web prototype, so you can see the whole flow in ten minutes."

### 1:00 to 3:15 · Minhaj · Journey Coach

**Do:**
1. Open **Journey Coach**. Point to the three progress tiles at 0.
2. Choose the moment **Before an appointment**. Show the **Learn** tab briefly.
3. **Practise** tab. Choose *"Nothing. Direct billing guarantees every charge is paid in
   full."* and click **Check my answer**. Read the feedback.
4. Choose *"Whether any out-of-pocket expenses may apply."* and check again.
5. **Take action** tab. Tick the three steps, **Save my checklist**, point to
   **Keep my next-step card**.
6. Switch **Language** to **हिन्दी (draft)**, then back to English.

**Say:**
"A student picks the moment they are in. Here, Linh has found a clinic that offers
Medibank OSHC Direct Billing. I will choose the answer most students assume. The
feedback corrects it and points to the guide page it comes from.

The student leaves with three practical checks and a card they can keep. No login,
nothing typed, and nothing in the lesson is sent to an AI provider. It takes about
three minutes, and it is voluntary: the reward is the takeaway card, not a tick box.

The language switch changes the interface only. The lesson itself stays in the
guide's English until a reviewed translation exists, because a mistranslated cover
statement is a compliance risk, not a typo."

### 3:15 to 4:00 · Minhaj · Navigator

**Do:** Click **Read the original page in Navigator**. Show PDF page 28. Scroll up to
**GP appointment** and the **healthdirect Service Finder** button.

**Say:**
"Every lesson is traceable to the page of the Medibank member guide it came from.
Navigator also turns the guide into steps: what to ask a GP clinic before booking, and
a link to healthdirect's official Service Finder. The link carries no question,
location or identity."

### 4:00 to 6:00 · Bikram · Bill Explainer

**Do:**
1. Open **Bill Explainer**. Choose **Paid receipt: dated service lines**, click
   **Read this bill**.
2. Point to **Insurer benefit shown: Not shown**, then to the explanation lines about
   AUD 245.00 settled and the AUD 0.00 balance.
3. Choose **GP visit: text example**, **Read this bill**.
4. Turn on **Show a reference comparison**. Line 1, item 23: choose
   **Published 100% benefit**. Point to AUD 90.00 against AUD 45.05.

**Say:**
"This is the moment our research says students get stuck: they paid a clinic and
think that means they were covered. The receipt shows AUD 245 settled and a zero
balance. NextBest explains that a zero balance is the clinic's account, not the
student's insurance gap, and it shows the insurer benefit as unknown rather than
guessing. Unknown is not zero.

On a GP bill, the student can compare one line with the published MBS reference:
a 90 dollar charge against a 45 dollar 5 cent reference. That explains why a gap can
exist. It is not a prediction of what Medibank will pay, and the app says so. The bill
is read on this computer; nothing is sent to an AI provider."

### 6:00 to 8:15 · Aayush · Ask NextBest

**Do:**
1. Open **Ask NextBest**. Type: *What documents are generally required to submit a
   medical claim online?* Wait for the full answer. Open the first source and
   **Response checks**.
2. Type: *Am I covered for physiotherapy?* Show the referral to Medibank.
3. Type: *I have a cold, where should I go?* Show the healthdirect handoff and the
   **Understand GP, pharmacy and telehealth options** button.

**Say:**
"Students will always ask in their own words, so this page takes any question. Each
answer needs three separate checks: the question is screened, the answer is written
only from guide passages, and a second review checks the draft before it is shown. If
any check fails, the student sees fixed wording instead of a draft. Each checked answer
costs a little over one cent on the smallest Claude model.

Now the boundary. Whether I am covered for physio is a question about one person's
policy. NextBest does not guess; it sends the student to Medibank, which is the only
party that can answer it.

And a symptom question never gets triage. It gets healthdirect's 24-hour line, the
official Symptom Checker, and an explanation of GP, pharmacy and telehealth options.
Emergency wording always goes to 000 first."

### 8:15 to 9:00 · Minhaj · Project dashboard

**Do:** Open **Project dashboard**, **Overview**. Point to **Pilot measures on this
computer**.

**Say:**
"How would Medibank know it works? The clicks we just made are already counted: one
Coach visit, one scenario started, one answered correctly, one bill read. Each event is
a random visit number, an event name and a page. No question text, bill content or name
is stored.

In a pilot we would add a short scenario quiz before and after, a one-question
confidence check, and drop-off points. Medibank's own measure would be fewer basic
OSHC queries in a student's first six weeks. We have not measured learning with real
students yet; that needs ethics approval and a pilot partner."

### 9:00 to 10:00 · Bikram · Close and the ask

**Say:**
"So: learn before you need it, a clear next step when you do, and nothing that
pretends to be a coverage decision.

We would like three things from Medibank. First, one touchpoint for a pilot; we
suggest a link in the pre-departure email to the 'Before you arrive' moment. Second, a
content review of the three lessons by your OSHC team. Third, an agreed path for the
four pilot measures, so a pilot can show whether students actually understand more.
Thank you."

---

## If something breaks

| Problem | Action | Say |
|---|---|---|
| Venue Wi-Fi fails before Ask | Ctrl+C, then `.\Start_NextBest.ps1 -Offline`. In Ask, use the starter **How do I make a claim?**, then the physio and cold questions. All three work offline | "Without the network, Ask uses curated answers from the same guide passages." |
| A live answer abstains | Do not retype variations. Move to the physio question | "When a check cannot be satisfied, it abstains rather than guessing. That is the design." |
| App stops | Restart with the same command once | |
| Restart fails | Play the recorded rehearsal from the matching timestamp | "This is the run we recorded on Saturday." |
| Running long at 6:00 | Drop the MBS comparison step | |
| Running long at 8:15 | Shorten the dashboard to one sentence; keep the ask | |

Offline mode is stricter: first-person questions such as "What documents do I need"
return a clarification. Use the starter buttons and the scripted questions.

---

## Q&A bank

Answer only what is asked. The named person answers first.

**Isn't this another app? (Bikram)**
No. The brief rules out a new app, and the learning moments are designed to be linked
from channels you already own. The web prototype is how we demonstrate the flow. The
integration into those channels is not built.

**How would it reach students? (Bikram)**
Through the offer letter and pre-departure email for the Coach, the university portal
for Navigator, and the claims help pages for the Bill Explainer. Each lesson stands
alone, so a link can point at one moment.

**How do you stop the AI giving coverage or medical advice? (Aayush)**
Rules run before any model call: emergency, symptom, personal-policy and privacy
requests stop locally. Allowed questions then need three model checks, and every
cited passage must match the verified guide word for word. A failed check returns fixed
wording.

**What does the AI see? (Aayush)**
Only the current screened question and the public guide passages selected for it.
Not earlier turns, not bills, not lessons. Questions and answers are not cached to disk.

**How accurate is it? (Aayush)**
On 24 unseen harmful or out-of-scope probes, the earlier source-only chat refused all
24, and it refused 6 of 20 legitimate questions. The live model path has not had an
independent safety evaluation, and we do not claim one. We chose to refuse too much
rather than too little.

**Can it handle other languages? (Minhaj)**
The interface switches to Hindi as a draft. We deliberately use static, reviewed
strings rather than machine translation, so a translation can never change what a
cover statement says. Adding a language is a content review task, not a code change.

**Did students learn anything? (Minhaj)**
Not measured yet. The prototype records completion signals. A learning claim needs a
pilot with pre/post scenarios and ethics approval.

**What happens when the member guide changes? (Bikram)**
The guide is pinned by its file hash. If the file changes, guide-backed pages stop and
say the source cannot be verified, until someone re-checks the lessons against the new
edition.

**Can a student upload a real bill? (Bikram)**
Not in this prototype. Bills are read locally and identifying fields are removed, but
real patient documents would need hosting, access and retention controls we have not
built.

**What would it cost to run? (Aayush)**
A checked chat answer costs about one to one and a half US cents on Claude Haiku in our
rehearsal. Lessons, Navigator and the Bill Explainer make no model calls.

**What did you find hardest? (any)**
Keeping the system honest about what it does not know: unknown is not zero, a receipt is
not a benefit, and a guide passage is not a coverage decision.

---

## Numbers you may quote, and their source

| Number | Source |
|---|---|
| 20 of 36 gap accounts about what is covered or how to claim (C2 + C4, 55.6%) | `oshc-master-data-v7.1.xlsx`, recode of 21 Sep 2026 |
| 24/24 unseen refusals, 6/20 false refusals (source-only chat) | `docs/prototype/release_summary_2026-10-15.json`, shown on Dashboard Results |
| 23/25 independent retrieval labels in the top five | `docs/prototype/independent_retrieval_2026-10-15.json`, shown on Dashboard Results |
| About USD 0.012 per checked live answer | `docs/prototype/campus_demo_verification_2026-10-15.json` |
| AUD 90.00 charge, AUD 45.05 MBS 100% benefit, AUD 44.95 difference | GP text example with `corpus/MBS-XML-20260801.XML` |
| Software tests passing | Run `python -m pytest` on the demo laptop on Saturday and quote that count |

Do not quote kappa, classifier or bill-extraction F1 unless asked. If asked, quote them
with their limits from the Dashboard Results tab.
