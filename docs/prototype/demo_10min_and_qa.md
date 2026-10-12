# NextBest: 10-minute demonstration and 5-minute Q&A

Presenter preparation, based on the verified prototype checkpoint.
The separate three-minute Medibank video will follow its supplied format.
One presenter can deliver this whole sequence.

## Before starting the timer

- Open the verified packaged app and keep its server terminal running.
- Use the browser's Home page. Set a readable zoom and keep the sidebar available.
- In Journey Coach, click Start again, then return Home.
- In Bill Explainer, click Clear, then return Home.
- Keep this runbook on another screen or print it. Use only the synthetic examples.
- The timings below include clicking, reading the screen and short pauses.

## 0:00-0:45 | Home: the student and the problem

Show: NextBest Home.

Say:

"Imagine an international student preparing to book a GP appointment. They need
to understand what to ask the clinic, where to check the policy information, and
later, what the bill actually shows.

NextBest brings these moments together: a short lesson, a link to the policy
source, and a bill explanation. This is a university prototype. I will demonstrate
the working flow using synthetic information."

## 0:45-2:45 | Journey Coach: practise before the appointment

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

## 2:45-4:15 | Navigator: check the source and its context

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

## 4:15-7:15 | Bill Explainer: separate printed facts from comparisons

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

## 7:15-8:30 | Dashboard: what the evidence establishes

Do:

1. Open Dashboard from the sidebar.
2. Point to Reports with recorded passing checks: 6 of 6.
3. Show the Independent evaluation table.

Say:

"The Dashboard makes the evidence visible. These six reports record engineering
checks for the implemented components. They are not six independent studies.

Separately, the packaged demonstration was checked in a fresh environment with
its dependencies installed from saved wheels. The tested flows passed without
provider calls.

Independent evaluation is shown separately. We have not established held-out bill
extraction accuracy or learning effectiveness in this workflow. The frozen bill
inputs and ground truth are still awaiting handoff. We will report those results
when the agreed evaluation has actually been run."

## 8:30-9:30 | Scope and intended delivery

Show: Return Home.

Say:

"The intended product is a learning layer in channels students already use.
The Streamlit app lets us demonstrate that idea; integration with Medibank or
university systems has not been implemented.

The working scope is deliberately small: three lessons, a fixed-topic source
browser, and synthetic bill examples. It does not decide claim eligibility,
assess symptoms or process real personal invoices. It is currently English-only.

The design hypothesis is that a short, relevant activity at a useful moment may
be more helpful than presenting all the information at once. This demonstration
shows the workflow. Further evaluation is needed to test that hypothesis."

## 9:30-10:00 | Close with the next decision

Say:

"The prototype now connects preparation, source checking and bill explanation
in one reproducible demonstration. The next steps are the independent evaluation
and review of the content and delivery approach.

For Medibank, the useful decision is which existing student touchpoint would be
most suitable for this learning flow, and whether the content and boundaries
are appropriate to take forward. Thank you."

## Timing and recovery

- Reach Bill Explainer by 4:15 and Dashboard by 7:15. Do not spend time opening all topics.
- If running late, shorten the final scope explanation. Keep the unknown-value and
  evidence limitations because they explain the system's behaviour.
- If the saved AI example fails, state that it did not load and select
  GP visit: text example. Describe this explicitly as the local rules fallback demo,
  not as a successful AI replay.
- If the app stops, use the ZIP launcher to restart once. If that fails, explain
  the observed failure and use any previously prepared, clearly labelled screenshots.
- Do not change rules, sources or the evaluation set during the presentation.

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
The demonstrated flows passed engineering checks, including a fresh-environment run.
Held-out extraction accuracy is pending and cannot be inferred from those checks.

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
