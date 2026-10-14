# NextBest: 10-minute demonstration and 5-minute Q&A

Presenter preparation, based on the verified prototype checkpoint.
The separate three-minute Medibank video will follow its supplied format.
One presenter can deliver this whole sequence.

## Before starting the timer

- Open the verified packaged app and keep its server terminal running.
- Use the browser's Home page. Set a readable zoom and keep the sidebar available.
- In Journey Coach, click Start again, then return Home.
- In Bill Explainer, click Clear, then return Home.
- In Ask a question, clear the question box so the page opens empty, then return Home.
  Confirm the How well does this work panel shows numbers and not the warning; if it
  shows the warning, the recorded report is missing and the panel will not state any
  accuracy. Run scripts/prototype_check_ask_ui.py before presenting.
- Keep this runbook on another screen or print it. Use only the synthetic examples.
- The timings below include clicking, reading the screen and short pauses.

## 0:00-0:40 | Home: the student and the problem

Show: NextBest Home.

Say:

"Imagine an international student preparing to book a GP appointment. They need
to understand what to ask the clinic, where to check the policy information, and
later, what the bill actually shows.

NextBest brings these moments together: a short lesson, a link to the policy
source, a bill explanation, and a question box for anything we did not anticipate.
This is a university prototype. I will demonstrate the working flow using
synthetic information."

## 0:40-2:20 | Journey Coach: practise before the appointment

Do:

1. Click Start Journey Coach.
2. Set Choose a moment to Before an appointment.
3. Point to the short lesson and Your next step.
4. Deliberately choose the option beginning "Nothing. Direct billing guarantees..."
   and click Check my answer.
5. Choose "Whether any out-of-pocket expenses may apply." and check again.
6. Click Read the original page in Navigator. Show physical PDF page 28.

Say:

"The student chooses the moment that matches their situation. Here, it is before
an appointment. The lesson focuses on a practical question to ask the clinic,
rather than asking the student to read a whole guide first.

I will deliberately choose an incorrect answer to show the feedback. The lesson
explains why direct billing should not be treated as a guarantee that every charge
is paid. I can now try the question again.

The feedback is connected to the saved policy source. This button takes us to the
original page, so the explanation can be checked in context.

There are three authored English lessons in this version. The student selects
the moment manually. The progress indicator records practice in this session;
it does not show that learning effectiveness has been established."

## 2:20-3:25 | Navigator: check the source and its context

Do:

1. In Navigator, change Browse the guide to Find a topic.
2. Choose Ambulance services. Show the extracted column and original PDF page 25.
3. Point to the guide's saved date. Keep publisher links unopened during the demo.

Say:

"Navigator puts a relevant policy excerpt beside the original page. The reader
can inspect the wording and the surrounding conditions instead of relying on
an unsupported generated answer.

This demonstration uses a verified copy of the Medibank guide saved on
28 September 2026. It does not claim that the publisher has made no changes since then.

The topics are fixed in this version. Navigator is a source browser, not a
personal coverage or symptom-assessment chatbot. A production version would
need an agreed process for reviewing source updates."

## 3:25-5:30 | Bill Explainer: separate printed facts from comparisons

Do:

1. Open Bill Explainer from the sidebar.
2. Select GP visit: saved AI reading, then click Read this bill.
3. Show the two rows and total charge AUD 105.00.
4. Point to Insurer benefit shown and Gap shown: both are Not shown.
5. Open View source text briefly, then close it.
6. Turn on Show a reference comparison.
7. For line 1, item 23, choose Published 100% benefit.
8. Show the published amount AUD 45.05 and illustrative difference AUD 44.95.
9. Point to Total unavailable for the whole-bill comparison.

Say:

"Now the student has a bill. This is a synthetic example, and the saved AI reading
replays an earlier model response. No new AI request is being made in this demo.

The bill shows two lines and a total charge of 105 dollars. It does not show an
insurer benefit or a gap. We keep those values unknown. Missing information does
not mean zero, and it does not mean that an insurer refused the claim.

We can inspect the source text to check the extracted fields. The extraction
pipeline checks proposed fields against the source, but those checks cannot
guarantee that every row was found or every document was understood correctly.

This separate section is an educational MBS comparison. I explicitly choose a
published reference for the first line. The charge is 90 dollars and the reference
is 45 dollars and 5 cents, so the illustrative difference is 44 dollars and 95 cents.

That is not a prediction of this person's insurance payment. The other line has
no usable comparison, so the app leaves the whole-bill comparison unavailable.
It also keeps the original benefit and gap fields unknown."

## 5:30-7:25 | Ask a question: the student's own words, and the refusals

Do:

1. Open Ask a question from the sidebar.
2. Click the starter "How do I claim money back after seeing a doctor?"
3. Show the passage list. Expand Show the original page on the first result.
4. In the question box, type: am I covered for physio
5. Show the refusal. Point out that no excerpt appears at all.
6. Clear it and type: when is ambulance treatment covered
7. Show the 000 escalation. Then open the collapsed panel beneath it.
8. Open How well does this work, and where does it fail. Show the two rows.

Say:

"Everything so far has been a path we chose for the student. But a student with a
question in their head cannot use a fixed topic list, so this page takes the
question as they would type it.

Our own wireframe from August specified this box, and it specified something we
have deliberately not built. The wireframe said the system should return short
generated answers. This page returns the passage from the guide instead, with the
original page beside it. It does not write a sentence of its own.

That is a safety decision, not an unfinished feature. If the search picks the
wrong passage, the student sees an unhelpful paragraph. If a generated answer had
picked the wrong passage, the student would see a confident, fluent statement about
their cover that the document does not support. We bounded the failure by
construction rather than hoping to measure it away later.

Now the refusals, which are the part worth your attention.

I ask whether I am covered for physiotherapy. That is a question about one person's
policy, which is personal financial product advice, so the boundary filter stops it
before anything is searched, and no excerpt is shown at all. It sends me to Medibank,
which is the only party that can actually answer it.

Next I ask when ambulance treatment is covered. The system escalates to 000. That is
a false refusal: it is a general question about how a service is paid for, the guide
answers it on page 25, and ambulance services is one of Navigator's own six topics.
The word ambulance is on our emergency list, and the list is deliberately wide,
because a missed emergency is worse than a refused question. So the same question is
answered by clicking a topic and refused by typing it.

We did not discover that by reading the code. We measured it. The panel at the
bottom of this page is the prototype stating its own accuracy. On the gold question
set, written in the guide's own vocabulary, the right page is in the top five
96 per cent of the time. Asked the way a student asks, that falls to 79 per cent, a
drop of 17 points on the same corpus with the same search. Word-overlap search
rewards the reader who already knows the document's vocabulary, which is the opposite
of the person who needs the help. And across both sets, two of 40 legitimate
questions were refused at the boundary.

Neither probe set is held out. We wrote and labelled both, so 79 per cent is the
optimistic end, and the panel says so on screen."

## 7:25-8:35 | Dashboard: what the evidence establishes

Do:

1. Open Dashboard from the sidebar.
2. On Recorded checks, point to Reports with recorded passing checks: 7 of 7.
3. Open the Measured in-house tab. Point to the student-wording figure and its delta.
4. Open the Independent evaluation tab. Show that every row reads Not linked here.

Say:

"The Dashboard makes the evidence visible, and it keeps three different kinds of
claim apart, because collapsing them is how a prototype starts overclaiming.

The first tab is recorded engineering checks: seven reports saying this code did
what we described, on a recorded date. They are not seven studies. Separately, the
packaged demonstration was checked in a fresh environment with dependencies
installed from saved wheels, and the tested flows passed without provider calls.

The second tab is what we have actually measured. Those are real numbers on probe
sets we wrote ourselves, which makes them the optimistic end of the range rather
than evidence of accuracy in the field.

The third tab is independent evaluation, and every row on it says not linked here.
We have not established held-out retrieval, held-out guardrail performance,
held-out bill extraction accuracy or learning effectiveness. The frozen bill inputs
are still awaiting handoff. Anything not established by our own gate date will be
reported as not established, with the reason, rather than left out."

## 8:35-9:20 | Scope and intended delivery

Show: Return Home.

Say:

"The intended product is a learning layer in channels students already use.
The Streamlit app lets us demonstrate that idea; integration with Medibank or
university systems has not been implemented.

The working scope is deliberately small: three lessons, a fixed-topic source
browser, synthetic bill examples, and a question box that quotes the guide rather
than answering in its own words. It does not decide claim eligibility, assess
symptoms or process real personal invoices. It is currently English-only.

The design hypothesis is that a short, relevant activity at a useful moment may
be more helpful than presenting all the information at once. This demonstration
shows the workflow. Further evaluation is needed to test that hypothesis."

## 9:20-10:00 | Close with the next decision

Say:

"The prototype now connects preparation, source checking and bill explanation
in one reproducible demonstration. The next steps are the independent evaluation
and review of the content and delivery approach.

For Medibank, the useful decision is which existing student touchpoint would be
most suitable for this learning flow, and whether the content and boundaries
are appropriate to take forward. Thank you."

## Timing and recovery

- Reach Bill Explainer by 3:25, Ask a question by 5:30 and Dashboard by 7:25.
  Do not spend time opening all topics or all passages.
- If running late, shorten the final scope explanation first, then the Journey Coach
  wrong-answer step. Keep the unknown-value and evidence limitations because they
  explain the system's behaviour.
- In the Ask segment, the two refusals matter more than the working answer. If you
  have time for only one thing there, do the ambulance question and name it as a
  false refusal we measured.
- If the saved AI example fails, state that it did not load and select
  GP visit: text example. Describe this explicitly as the local rules fallback demo,
  not as a successful AI replay.
- If the app stops, use the ZIP launcher to restart once. If that fails, explain
  the observed failure and use any previously prepared, clearly labelled screenshots.
- If a question in the Ask segment returns nothing, say the search found no passage
  sharing enough wording, which is one of the three failures named in the panel, and
  move to the next question. Do not retype variations hunting for a result.
- If anyone in the room types a symptom question such as "I have a cold, where do I
  go", it will NOT be refused: it returns irrelevant policy passages. Do not be
  surprised by it on screen. Say that the first layer matches symptom words rather
  than symptom phrasing, that we measured it at four refusals in eighteen probes, and
  that it is the reason the generated-answer surface is switched off. Raising it
  yourself is stronger than being caught by it, so prefer answer 19 in the Q&A bank.
- Do not change rules, sources or the evaluation set during the presentation. In
  particular do not edit the emergency word list to make the ambulance question work:
  it is the finding, and the held-out run has not happened yet.

## Five-minute Q&A: short answers to practise

These are preparation questions. Answer only those asked; do not recite the list.

**1. Is this another app students must install?**
No. Streamlit is our demonstration environment; the proposed learning flow would
sit in existing channels, but that integration is not built yet.

**2. What is personalised today?**
Students manually choose one of three moments. Automatic personalisation and
multiple languages are not implemented in this version.

**3. Where is AI actually used?**
AI interprets a synthetic bill, and this demo replays its saved response.
The lessons, source search and reference calculations do not require live generation.

**4. Why replay a response instead of making a live API call?**
It makes the demonstration repeatable without network dependence or new spending.
A cached example demonstrates integration, not accuracy on unseen invoices.

**5. How do you stop the model inventing financial amounts?**
Local validators check proposed extracted fields against the input and reject
unsupported values. They reduce unsupported output but cannot prove completeness or accuracy.

**6. Does AUD 44.95 mean the student's actual gap?**
No. It is the difference for one line using an explicitly selected published
reference; actual entitlement and payment are not established.

**7. Why show unknown values?**
The document does not provide those amounts. Replacing missing information with
zero or an estimate could give the reader a misleading impression.

**8. How accurate is the system?**
It depends which part, and only one part has a number. For finding the right passage
in the guide: the right page is in the top five 96 per cent of the time when the
question uses the guide's wording, and 79 per cent when it uses a student's. Both
probe sets are ours, so neither is held out. Held-out extraction accuracy and
held-out guardrail performance are pending and cannot be inferred from engineering
checks.

**9. Have you shown that students learn more?**
No. The practice activity works, but we have not measured learning effectiveness.
Any future learner study would need an appropriate design and approval.

**10. Is the policy information always current?**
This demo uses a dated, verified snapshot. A deployed service would need a reviewed
source-update process rather than assuming the saved document remains current.

**11. Can someone upload their real bill?**
This prototype is for synthetic documents only. The demonstration does not establish
the controls or validation needed for a service handling real personal invoices.

**12. What has the AI testing cost?**
The recorded provider spend for the connection and synthetic extraction checks is
USD 0.002689. That is a development-check total, not a production cost per student.

**13. What is the most important next step?**
Run the agreed evaluation on the frozen independent inputs and report failures
honestly. In parallel, review the proposed content and delivery touchpoint with Medibank.

**14. Why can a student not just chat with it?**
They can type any question. What the system will not do is write its own answer. It
shows the passage from the guide and the original page. Our architecture plan sets a
condition for the generated-answer surface, which is refusal recall on a held-out
probe set at or above 0.90, and that run has not happened. Until it does, the module
that would compose prose is switched off and unreachable from the page.

**15. Is that not just avoiding the hard problem?**
It is choosing which failure we are willing to ship. A wrong passage wastes the
student's time. A wrong generated sentence about their cover could cost them money or
send them to the wrong place, and it would read as authoritative while doing it. We
can defend the first today and not the second.

**16. You said 96 per cent and 79 per cent. Why the difference?**
Same corpus, same search, different phrasing. The gold questions are written in the
guide's own vocabulary and the dev probes are written the way a student asks. The
search matches words, so it rewards the reader who already knows the document's
language, which is exactly the person who does not need it. We treat that 17-point
gap as a finding about the guide, not only about our search.

**17. Can you name a case where it fails?**
Three. "What is a gap payment" lands on the premium pages, because the guide uses the
word gap for two unrelated things. Vague questions such as "where do I go if I am sick
on the weekend" land in the glossary, which matches a little of everything. And a
question sharing no words with its answer returns nothing useful at all.

**18. Your own system refused a question the guide answers. Is that a bug?**
It is a deliberate trade with a measured price. The emergency word list is wide on
purpose, so "when is ambulance treatment covered" is stopped on the word ambulance
even though it is a billing question the guide answers on page 25. Across both probe
sets, two of 40 legitimate questions were refused that way. We would rather refuse a
billing question than miss someone in an emergency, and we are not tuning the list
before the held-out run measures it.

**19. Your August wireframe suggested "I have a cold, where do I go?" as a starter
question. What happens if a student asks that?**
It is not refused, and that is a gap in our boundary filter that we found in review
this week rather than in the evaluation. Our first layer matches a closed list of
symptom words, so it stops fever, rash and pain, and it lets cold, cough, flu, sore
throat, vomiting and toothache through. On eighteen symptom-framed probes it refused
four. Our architecture sets the ship condition at refusal recall of 0.90, so that
layer alone is well short of it.

Two things keep this from being a live hazard today, and neither is luck. The page
does not write answers, so a symptom question that slips the gate returns irrelevant
policy passages rather than triage advice. And the second layer that is designed to
catch what a word list cannot, an LLM rubric classifier, is specified and written but
not yet wired into the flow. That is the work, and it is why the conversational answer
surface is still switched off.

We are deliberately not patching the word list with the examples I just gave you. The
held-out probe run has not happened, and tuning the gate on probes we have already
seen would make that measurement worthless.

**20. Is the question text stored anywhere?**
No. It is matched against the saved guide on the local machine. It is not written to
disk, not logged, and not sent to any provider. The page keeps two counters for the
browser session, which hold integers, and the tests assert that no question text
reaches them.

**21. How did you find that gap, if your tests pass?**
By probing the running system instead of trusting the tests. Our clinical tests use
the same symptom words the pattern already matches, so they passed while the gate
leaked. We had the same failure earlier in the project: the bill matcher passed
eighteen tests while a fuzzy-match function returned a perfect score for any query
whose words were a subset of the candidate. In both cases the tests encoded what we
intended rather than what the code did. That is the argument for the held-out runs
being done by someone who did not write the thing being measured.
