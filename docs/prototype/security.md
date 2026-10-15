# Bill and chat data security

This describes implemented local-demo controls, not a security certification.

Live chat update: custom general questions now use Haiku. The earlier source-only
chat evaluation is historical. Its scores do not validate this generated-answer
path. See `live_chat.md` for the mandatory input and output checks.

## Data flow

Browser on this computer → local Streamlit process → in-memory text extraction
→ numeric/date/item fields → minimised session result → optional user download.
Public guide and MBS snapshots are read locally. Bills and their original
descriptions are not sent to any model or external service.

Live chat flow: current question → local privacy/emergency checks → Haiku semantic
input review → verified public passages → Haiku draft → deterministic citation and
output checks → separate Haiku safety/faithfulness review → complete answer.
Local privacy screening is best effort, not an anonymisation guarantee. The provider
receives locally admitted question text. Do not include private or health details.

Clear personal symptom disclosures receive a fixed clinical handoff locally before
live provider or guide access. Emergency rules take priority. Healthdirect links
contain no question, location or identity parameters; details entered on the external
service are covered by its privacy terms. The app does not assess symptom severity
or select a healthcare service from symptoms. Navigator choices are selected by
the student, and Coach practice and checklists do not make model calls.

## Implemented measures

- The server binds to 127.0.0.1. CORS and XSRF checks are enabled. Usage telemetry
  is disabled. Explicit live flags and the persistent budget control model calls.
  Saved bill examples are cache-only even when chat is online.
- Uploads are bounded to 10 MiB, 20 pages and 100,000 extracted characters.
  Non-PDF, damaged, encrypted and image-only PDF inputs fail closed. No cloud OCR,
  automatic email, claim submission or third-party storage is used.
- Names, government/member identifiers, addresses, provider identity and original
  service descriptions are not fields retained by the bill UI. This is field
  minimisation rather than a claim that regex name detection is perfect.
- Original source text is not stored in `be_result`, displayed or downloaded.
  Downloads contain only selected numeric/date/item fields, fixed explanatory
  text and any explicitly requested public MBS comparison.
- Bill processing does not write uploaded files to disk, call the event logger,
  use a shared cache or send invoice content to a provider. The input widget and
  selected upload temporarily hold original input in browser/server RAM.
- Clear removes bill result and input widget state. Closing a session is subject
  to Streamlit's session lifecycle; no instant RAM erasure or OS swap guarantee
  is claimed. Browser downloads are under the user's control after creation.
- Chat locally screens common identifying patterns before provider/source access, withholds rejected text,
  removes raw guardrail trigger spans, keeps at most ten turns in session memory
  and provides Clear chat. It does not export or log conversation content. Live
  questions and drafts bypass disk cache. The budget retains usage and random
  accounting IDs, not stable hashes of private questions or transcript text.
- Uploaded text is treated as data. It cannot modify prompts, run code, choose
  tools or send messages. Curated answers use a fixed catalogue with evidence
  anchors; arbitrary uploaded narrative cannot become an answer.
- Third-party guide/MBS bytes and offline package files are checked with SHA-256.
  Hashes detect changed bytes; they are not cryptographic publisher signatures.

## Supported presentation claim

The prototype minimises retained data and processes invented invoices locally.
Bill reading makes no external model call. Live chat sends the current locally
screened question and selected public passages to Anthropic over the server-side
API; previous turns and uploads are not sent. No draft is displayed until checks
pass. Provider retention depends on the account and contract; this app does not
claim zero provider retention. See the provider's
[API retention documentation](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention).
Real patient data is not approved for this prototype.

## Production controls not implemented

This is not a multi-user hosted service: authentication, role-based access,
TLS termination, encrypted persistent storage, enterprise audit/incident response,
formal retention/deletion SLAs, penetration testing and legal/privacy review have
not been completed. Localhost transport is not an assertion of encrypted traffic.
Scanned bills/photos are rejected because OCR has not been validated. A public
deployment or real-student trial needs those controls and an independent review.

## Verification

The bill/privacy tests check that synthetic names, IDs and descriptions cannot
survive in retained UI results. Chat tests trap provider calls, block source
access for rejected inputs and verify bounded/cleared transcripts. The packaged
demo verifier traps provider/ledger access and checks unchanged package bytes.
