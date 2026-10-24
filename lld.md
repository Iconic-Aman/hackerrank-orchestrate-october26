# Ghost Data Audit Agent — Low Level Design (LLD)

> Detail inside the boxes of [`agent_design.md`](./agent_design.md): data models, function signatures, config formats, algorithms, gates and tests.
> Built from 4 real sample cases: `case_01`, `case_11`, `case_14`, `case_31`.

**Markers used in this doc**

- ✅ **Confirmed** by the sample data
- 🔶 **Hypothesis**: fits the samples, but must be checked against more data before it is trusted

---

## 1. What the Samples Taught Us

### 1.1 Confirmed facts

| # | Fact | Proof in samples | Design impact |
|---|------|------------------|---------------|
| ✅ C1 | `audit_at` is **inclusive** (`captured_at <= audit_at`) | `evidence_03` captured `2026-10-01T12:00:00Z`, same as `audit_at` of case_11 and case_14, and it is cited | Use `<=` everywhere |
| ✅ C2 | `INCOMPLETE`: findings cite an evidence id. Remediation and verification use empty string `""` | case_11, case_14 | Empty value is `""`, not null |
| ✅ C3 | `COMPLETE`: every verification step cites an evidence id | case_01, case_31 | Gate 9 enforces it |
| ✅ C4 | Step order follows the operation table in the problem statement. Inside one operation: `system_id`, then `resource_id` ascending | case_11 findings: analytics_platform before support_platform | Order comes from `operations.yaml` |
| ✅ C5 | The finding type depends on the rule action: `DELETE` → `REPORT_REMAINING_RECORD`. `REDACT` or `ANONYMIZE` → `REPORT_EXPOSED_PII`. Active flow → `REPORT_ACTIVE_DATA_FLOW`. Active backup → `REPORT_RESTORE_RISK` | case_11, case_14 | Decision table in `operations.yaml` |
| ✅ C6 | **Verification covers every resource of the user, even ones that were already fine.** `account_4248` was `NOT_FOUND` (no finding, no fix) but still gets `VERIFY_RECORD_ABSENT` in case_11 | case_11 step 9 | Verification is built from the whole resource set, not only from findings |
| ✅ C7 | Retained records get `VERIFY_RECORD_PRESENT` (security audit records) | case_11, 14, 31 | Retained records are part of the resource set |
| ✅ C8 | Evidence files are **shared by many users**. The handover file has lines for novak.tomasz and y.tanaka32 | `evidence_03` | Match line by line. Never "file belongs to user" |
| ✅ C9 | An **empty snapshot is proof of absence**: `account_service` has `"records": []` in `evidence_51` | case_31 step 1 | Parsers must record **coverage** (which stores a file snapshots), even when empty |
| ✅ C10 | Tombstone: `subject_reference` holds the user id. Fields `name`, `email`, `phone`, `email_hash` all null means `REDACTED`. Real values mean exposed | `tombstone_440` vs `tombstone_9178` | The user-id column has a different name per file. Find it by values |
| ✅ C11 | `file_id` in `evidence_files.csv` is the value used as `evidence_id` | all samples | Evidence ids come only from the manifest |
| ✅ C12 | Rules file has 4 columns: `rule_id, data_category, condition, required_action`. Actions: `DELETE`, `REDACT`, `ANONYMIZE`, `RETAIN`. The condition is **free text** | `deletion_rules.csv` | Conditions need an evaluation step (see §6) |
| ✅ C13 | Evidence formats seen: SQL (SQLite, several tables per file), pipe-table text (handover), JSON bundle (`snapshots → data_store → records`), log | evidence rows | One parser per format, all produce the same `Fact` |
| ✅ C14 | `system_activity.csv` has **no user column** | schema | Activity cannot be joined by user. Join by `resource_id` only |

### 1.2 Hypotheses to verify

| # | Hypothesis | Why we think so | How to verify |
|---|------------|-----------------|---------------|
| 🔶 H1 | The resource set of a user is found from **any** snapshot at or before `audit_at`, not only from the latest one | case_31: `account_4857` is in the answer, but `evidence_51` has no account records. It must have been seen earlier | grep `account_4857` and `account_001` across all files |
| 🔶 H2 | Cited evidence = the **latest snapshot at or before `audit_at` that covers the resource's store** | case_01 cites `evidence_54` (captured the day before). case_11, 14, 31 cite the file captured at `audit_at` | Check more COMPLETE samples |
| 🔶 H3 | Evidence captured **after** `audit_at` is ignored | `evidence_93` (09-16) and `evidence_61` (09-17) are later than case_31's `audit_at` (09-15) and case_01's (09-03) | Check what those files hold for the same users |
| 🔶 H4 | A backup category with action `RETAIN` means "keep the backup but block restore" | case_14 | Check other backup cases |
| 🔶 H5 | `DATA_FLOW` is a resource kind that has **no rule row**. It is handled by kind, not by rule | no `DATA_FLOW` in rules, but case_11 disables a flow | Look at other flow cases |
| 🔶 H6 | Primary and replica copies of one record are **one resource**: `(system_id, resource_id)`. Present in any copy means present | case_01: one step although `evidence_54` has primary and replica tables | Find a case where only the replica still holds the record |
| 🔶 H7 | SQL tables do not name a `system_id`. It must be learned from `resource_id` prefix ↔ system, using lines that have both (handover, JSON) and `system_activity.target_system` | `customer_profiles_failover_replica` has no system name, answer says `account_service` | Check the learned map covers every resource id |
| 🔶 H8 | Retained records may keep only the stable user reference. Other identifiers must be removed | problem statement: "retained records contain only the identifiers permitted by the rules" | Look at a retained record that has an email |

---

## 2. Core Data Models (Pydantic)

> `str` where a closed list would be tempting. Allowed values come from `operations.yaml` and `schema_map`, so the models stay generic.

```python
# agent/models.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field

ResourceKey = tuple[str, str]            # (system_id, resource_id)

# ---------- dataset inputs ----------
class Request(BaseModel):
    case_id: str
    email: str
    requested_at: datetime
    reported_status: str
    reported_at: datetime
    audit_at: datetime
    request_text: str

class IdentityRow(BaseModel):
    user_id: str
    values: dict[str, str]               # {"email": ..., "phone": ..., "name": ..., "email_hash": ...}
    updated_at: datetime

class AuditEvent(BaseModel):
    audit_id: str
    user_id: str
    event_time: datetime
    field_name: str                      # kind of identifier
    old_value: str
    new_value: str

class ActivityEvent(BaseModel):
    activity_id: str
    event_time: datetime
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    reported_result: str                 # a CLAIM, never proof
    details: str

class Rule(BaseModel):
    rule_id: str
    category: str
    condition_text: str
    action: str                          # DELETE | REDACT | ANONYMIZE | RETAIN (values from data)

class EvidenceFile(BaseModel):
    file_id: str
    path: str
    origin: str
    captured_at: datetime

# ---------- identity ----------
class Identifier(BaseModel):
    kind: str                            # email | phone | name | email_hash | user_id
    raw: str                             # exactly as stored
    norm: str                            # normalized for matching
    strength: str                        # "strong" | "weak" (from config)
    source_ref: str                      # identity row key or audit_id
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    contested: bool = False              # now owned by a DIFFERENT user (edge case I4)

class ResolvedUser(BaseModel):
    user_ids: list[str]
    identifiers: list[Identifier]

# ---------- evidence ----------
class Coverage(BaseModel):
    """A snapshot says: 'I describe this store at this time'. Even if it has 0 rows."""
    file_id: str
    system_id: str
    collection: str                      # table / data_store collection / section
    captured_at: datetime
    row_count: int

class Fact(BaseModel):
    """One row, line or record from any evidence file, in one common shape."""
    file_id: str
    system_id: str
    collection: str
    resource_id: str
    category: str | None                 # e.g. USER_PROFILE, if the file says it
    raw_state: str | None                # token from the file, e.g. NOT_FOUND, IDENTIFIABLE
    fields: dict[str, str | None]        # every column / key / cell
    locator: str                         # "line 12" | "table:rowid" | "$.snapshots[1].records[0]"
    confidence: float = 1.0
    quote: str | None = None             # required for LLM-extracted facts

# ---------- match + state ----------
class Observation(BaseModel):
    fact: Fact
    matched: list[Identifier]            # which identifiers hit
    via: str                             # "identifier" | "user_id"

class ResourceState(BaseModel):
    key: ResourceKey
    category: str
    kind: str                            # record | flow | restore_path (from category_kinds)
    state: str                           # ABSENT | PRESENT | IDENTIFIABLE | REDACTED | ANONYMIZED | ACTIVE | UNVERIFIED ...
    as_of: datetime | None               # captured_at of the winning snapshot
    evidence_id: str | None              # file_id of the winning snapshot
    exposed_fields: list[str] = []
    conflicts: list[str] = []            # e.g. "activity said SUCCESS, evidence says PRESENT"

class Treatment(BaseModel):
    key: ResourceKey
    rule_id: str | None
    action: str                          # from the rule, or from kind for flows/restore
    kind: str
    target_state: str                    # state the resource must reach

class Finding(BaseModel):
    key: ResourceKey
    operation: str                       # REPORT_*
    state: str
    evidence_id: str

class Step(BaseModel):
    step_no: int
    phase: str
    system_id: str
    resource_id: str
    operation: str
    state: str
    evidence_id: str                     # "" when not applicable (C2)

class Flag(BaseModel):
    code: str                            # UNMAPPED_CATEGORY | UNREADABLE_EVIDENCE | LOW_CONFIDENCE | ...
    case_id: str | None
    stage: str
    message: str

class CaseResult(BaseModel):
    case_id: str
    status: str
    steps: list[Step]
    flags: list[Flag]
    stage_reached: str
```

---

## 3. Dataset-Level Index (built once)

Evidence does not depend on the case, so it is parsed **once**, not 518 times.

```python
class DatasetIndex(BaseModel):
    requests: list[Request]
    identities: dict[str, IdentityRow]               # by user_id
    audit_log: dict[str, list[AuditEvent]]           # by user_id, sorted by event_time
    activity_by_resource: dict[str, list[ActivityEvent]]
    rules_by_category: dict[str, list[Rule]]
    files: dict[str, EvidenceFile]
    schema_map: SchemaMap                            # §5.2
    category_kinds: dict[str, str]                   # category -> kind
    compiled_rules: dict[str, CompiledRule]          # rule_id -> predicate
    coverage: list[Coverage]
    facts_by_resource: dict[ResourceKey, list[Fact]]
    facts_by_token: dict[str, list[Fact]]            # inverted index: normalized token -> facts
    owners_by_ident: dict[str, set[str]]             # normalized value -> user_ids that own it now
```

**Why this matters:** one case is then a set of dictionary lookups. A full 518-case run stays fast and cheap, and the LLM sees each image or PDF once.

---

## 4. Stage Signatures

> S0 and S3 are dataset-level. S1, S2, S4–S9 run per case. S10 runs once at the end.

| Stage | Function | Input | Output |
|-------|----------|-------|--------|
| S0 | `build_schema_map(dataset_dir) -> SchemaMap` | all CSVs, evidence files | frozen `schema_map.generated.yaml`, `category_kinds`, `compiled_rules`, `state_vocab` |
| S3 | `build_evidence_index(dataset_dir, schema_map) -> EvidenceIndex` | manifest + files | `coverage`, `facts_by_resource`, `facts_by_token` |
| S1 | `classify_request(req, activity) -> RequestClass` | one request | `is_deletion`, `reason`, `confidence` |
| S2 | `resolve_identity(req, idx) -> ResolvedUser` | request email, identities, audit log | user ids + identifiers |
| S4 | `match_observations(user, idx, audit_at) -> list[Observation]` | user + index | facts that belong to this user |
| S5 | `resolve_states(obs, idx, audit_at) -> list[ResourceState]` | observations | one state per resource at `audit_at` |
| S6 | `derive_treatments(states, idx) -> tuple[list[Treatment], list[Flag]]` | states + rules | required treatment per resource |
| S7 | `compare(states, treatments) -> list[Finding]` | | findings |
| S8 | `decide_status(is_deletion, findings, states, treatments) -> str` | | `COMPLETE` / `INCOMPLETE` / `NOT_APPLICABLE` |
| S9 | `build_plan(status, findings, states, treatments, ops_cfg) -> list[Step]` | | ordered steps |
| S10 | `write_output(results, requests, path)` | all case results | validated `output.csv` |

```python
# agent/pipeline.py  (shape only)
def run_case(req: Request, idx: DatasetIndex, cfg: Config) -> CaseResult:
    ctx = CaseContext(req=req)
    for stage in STAGES:                       # list of (name, fn, gate)
        try:
            out = stage.fn(ctx, idx, cfg)
            gate = stage.gate(ctx, out, idx, cfg)
            ctx.record(stage.name, out, gate)
            if not gate.ok:
                return fallback_result(ctx, gate)      # flag, never crash the run
        except Exception as e:
            return fallback_result(ctx, error=e)
        if stage.name == "S1" and not ctx.is_deletion:
            return CaseResult(case_id=req.case_id, status="NOT_APPLICABLE", steps=[], ...)
    return ctx.to_result()
```

---

## 5. Config File Formats

### 5.1 `operations.yaml`

```yaml
phases: [FINDING, REMEDIATION, VERIFICATION]        # phase order

operations:                                          # order = position inside its phase
  REPORT_REMAINING_RECORD: {phase: FINDING,      state: PRESENT,    order: 1}
  REPORT_EXPOSED_PII:      {phase: FINDING,      state: PRESENT,    order: 2}
  REPORT_ACTIVE_DATA_FLOW: {phase: FINDING,      state: ACTIVE,     order: 3}
  REPORT_RESTORE_RISK:     {phase: FINDING,      state: ACTIVE,     order: 4}
  DISABLE_DATA_FLOW:       {phase: REMEDIATION,  state: DISABLED,   order: 1}
  BLOCK_RESTORE:           {phase: REMEDIATION,  state: BLOCKED,    order: 2}
  DELETE_RECORD:           {phase: REMEDIATION,  state: ABSENT,     order: 3}
  REDACT_RECORD:           {phase: REMEDIATION,  state: REDACTED,   order: 4}
  ANONYMIZE_RECORD:        {phase: REMEDIATION,  state: ANONYMIZED, order: 5}
  VERIFY_RECORD_ABSENT:    {phase: VERIFICATION, state: ABSENT,     order: 1}
  VERIFY_RECORD_PRESENT:   {phase: VERIFICATION, state: PRESENT,    order: 2}
  VERIFY_RECORD_REDACTED:  {phase: VERIFICATION, state: REDACTED,   order: 3}
  VERIFY_RECORD_ANONYMIZED:{phase: VERIFICATION, state: ANONYMIZED, order: 4}
  VERIFY_DATA_FLOW_DISABLED:{phase: VERIFICATION,state: DISABLED,   order: 5}
  VERIFY_RESTORE_BLOCKED:  {phase: VERIFICATION, state: BLOCKED,    order: 6}

# kind + rule action  ->  what to report, what to do, what to verify
treatments:
  - {kind: record,       action: DELETE,    target: ABSENT,     finding: REPORT_REMAINING_RECORD, fix: DELETE_RECORD,    verify: VERIFY_RECORD_ABSENT}
  - {kind: record,       action: REDACT,    target: REDACTED,   finding: REPORT_EXPOSED_PII,      fix: REDACT_RECORD,    verify: VERIFY_RECORD_REDACTED}
  - {kind: record,       action: ANONYMIZE, target: ANONYMIZED, finding: REPORT_EXPOSED_PII,      fix: ANONYMIZE_RECORD,  verify: VERIFY_RECORD_ANONYMIZED}
  - {kind: record,       action: RETAIN,    target: PRESENT,    finding: null,                    fix: null,              verify: VERIFY_RECORD_PRESENT}
  - {kind: flow,         action: "*",       target: DISABLED,   finding: REPORT_ACTIVE_DATA_FLOW, fix: DISABLE_DATA_FLOW, verify: VERIFY_DATA_FLOW_DISABLED}
  - {kind: restore_path, action: "*",       target: BLOCKED,    finding: REPORT_RESTORE_RISK,     fix: BLOCK_RESTORE,     verify: VERIFY_RESTORE_BLOCKED}

strength:                  # a stronger state satisfies a weaker requirement (edge case P7)
  REDACTED: 1
  ANONYMIZED: 2
  ABSENT: 3

evidence_id_empty: ""      # value for remediation and future verification steps (C2)
```

> The operation names here come from the problem statement table. They live **only** in this file.

### 5.2 `schema_map.generated.yaml` (written by S0, reviewed by a human, then frozen)

```yaml
formats:                                   # file -> parser
  - {match: {suffix: ".sql"},  parser: sql}
  - {match: {suffix: ".json"}, parser: json_snapshots}
  - {match: {suffix: ".txt"},  parser: pipe_table}
  - {match: {suffix: ".log"},  parser: log_lines}
  - {match: {suffix: ".pdf"},  parser: pdf_text}
  - {match: {suffix: ".png"},  parser: image_vision}

csv_roles:                                 # logical name -> real column, found by values
  identities:  {user_id: user_id, email: email, phone: phone, name: name, email_hash: email_hash, updated_at: updated_at}
  audit_log:   {field_kind: field_name, old: old_value, new: new_value, at: event_time}
  activity:    {id: activity_id, at: event_time, type: event_type, target: target_system, resource: resource_id}

identifier_kinds:                          # kind -> normalizer + strength
  email:      {normalize: [strip, lower],            strength: strong}
  phone:      {normalize: [digits_only],             strength: strong}
  email_hash: {normalize: [strip, lower],            strength: strong}
  user_id:    {normalize: [strip],                   strength: strong}
  name:       {normalize: [casefold, collapse_ws],   strength: weak}

email_hash: {algorithm: null, input_normalize: []}     # discovered by S0 (see §6.1)

state_vocab:                               # raw token in evidence -> logical state
  NOT_FOUND:    ABSENT
  FOUND:        PRESENT
  IDENTIFIABLE: IDENTIFIABLE
  ACTIVE:       ACTIVE
  # more tokens are added after profiling every evidence file

user_id_columns:                           # per format: names that hold the user reference (by value overlap)
  json_snapshots: [subject_reference, user_id]
  sql:            [user_id]

resource_system_map:                       # learned: resource id prefix -> system (H7)
  account:   account_service
  search:    search_service
  analytics: analytics_platform
  support:   support_platform
  data_flow: integration_service
  backup:    backup_service
  audit_record: security_service
  tombstone: identity_service
```

> The `resource_system_map` above is what the samples show. S0 **learns** it from co-occurrence, and the generated file is the only place it lives.

### 5.3 `category_kinds.generated.yaml`

```yaml
USER_PROFILE: record
SEARCH_INDEX_ENTRY: record
SUPPORT_MESSAGE: record
ANALYTICS_PROFILE: record
SECURITY_AUDIT_LOG: record
ACCOUNT_TOMBSTONE: record
DATA_FLOW: flow              # not in the rules file (H5)
BACKUP_ARCHIVE: restore_path # rule says RETAIN, kind overrides (H4)
```

S0 proposes this with the LLM (one call for all categories), a human approves it, and it is frozen.

### 5.4 `rules_compiled.generated.yaml`

Rule conditions are free text. S0 compiles each into a small predicate:

```yaml
rule_01: {when: always}
rule_05: {when: manual_review, text: "Conversation contains shared customer, agent, or order context"}
rule_07: {when: state_is, states: [IDENTIFIABLE]}          # "Record is still attributable to a user"
rule_12: {when: manual_review, text: "Record is within the supplied retention period"}
rule_14: {when: always}                                      # restore can always be blocked (H4)
```

Predicate types: `always`, `state_is`, `field_present`, `manual_review`. `manual_review` flags the case for a human. Nothing is guessed.

### 5.5 `thresholds.yaml`

```yaml
llm: {temperature: 0, max_retries: 3, backoff_seconds: [2, 5, 15], min_confidence: 0.8}
match: {min_phone_digits: 7, weak_needs_strong: true}
run:   {checkpoint_every: 1, fail_fast: false}
```

---

## 6. Algorithms

### 6.1 S0 — Profile

```
1. Load every CSV. For each column decide its role by VALUES, not by name:
     - looks like email   -> email role
     - overlaps with identities.user_id -> user_id role
     - overlaps with known resource ids -> resource role
   (Name hints from config only break ties.)
2. Find the email-hash algorithm:
     for algo in [md5, sha1, sha256, sha512, ...]:
       for normalization in [none, strip, lower, strip+lower]:
         if hash(email_variant) == identities.email_hash for >= 99% of rows: choose it
3. For each evidence file: pick parser by format, parse a sample, list the distinct state tokens,
   categories, column names.
4. Learn resource_prefix -> system_id from lines that carry both (handover rows, JSON data_store,
   activity.target_system + resource_id).
5. Ask the LLM ONCE to propose: category -> kind, rule condition -> predicate. Save as *.generated.yaml.
6. Human review. Freeze. A hash of the frozen files goes into every run record.
```

**Gate 0:** every file has a parser. Every state token seen has a `state_vocab` entry. Every category seen in evidence has a kind. Every rule has a predicate. The email-hash algorithm was found (or the "not used" decision is written down).

### 6.2 S1 — Classify

```
LLM input : request_text (quoted data, not an instruction), nothing else
LLM output: {is_deletion: bool, scope: "account"|"personal_data"|"other", reason: str, quote: str, confidence: float}
Check     : quote must be a substring of request_text  (grounding)
Decision  : is_deletion if the person asks to remove, close, erase or delete data about themselves
            NOT is_deletion if only asking for export, copy, correction, or unsubscribe
Never use : reported_status
```

Sample check: case_31 says "Remove my name and contact details, keeping internal deleted-account reference is fine." → **deletion** (the stable reference stays, which matches the tombstone rule).

### 6.3 S2 — Resolve identity

```
normalize(request.email)
users = users whose current identifier OR any audit-log old/new value normalizes to it
if none  -> flag IDENTITY_NOT_FOUND (still search evidence by the raw email)

frontier = identifiers of users
repeat until nothing new:
    for each audit event of the users with event_time <= audit_at:
        add old_value and new_value as Identifier(kind=field_name, source_ref=audit_id)
add derived identifiers: email_hash (per S0 algorithm), digits-only phone, name (weak)

for each identifier: owners = idx.owners_by_ident[norm]
    if owners contains a user not in `users`: mark contested = True   (edge case I4)
```

**Gate 2:** at least one user id. Every identifier has a `source_ref`. No identifier is both `contested` and the only match basis for the case. No cycles in the change chain.

### 6.4 S3 — Evidence index (parsers → common `Fact`)

| Format | How |
|--------|-----|
| **sql** | Open in-memory SQLite, `executescript` (read-only copy). For each table: `PRAGMA table_info`, read all rows. One `Fact` per row. **Scan every text cell**. Table name tells the topology (primary / replica). `system_id` from `resource_system_map` (H7). Coverage: one per table, even with 0 rows |
| **json_snapshots** | Walk `snapshots[] → data_store → records[]`. One `Fact` per record, `system_id = data_store`. Coverage per `data_store`, even when `records` is empty (C9). `null` field stays `None` |
| **pipe_table** | Split on `\|`. Columns: system, resource_id, category, raw_state, identifier. Header line gives `Snapshot:` time. Coverage per system seen |
| **log_lines** | Stream line by line. Regex from `parsers.yaml` pulls time, resource, state. Unknown lines go to the LLM parser once and are cached |
| **pdf_text** | Text extraction. If empty, rasterize and use the vision parser |
| **image_vision** | LLM returns `[{system, resource_id, category, state, quote}]`. Cached by file hash. Each `quote` must contain the value it claims |

All parsers also fill `facts_by_token`: for every fact, extract tokens (emails, digit runs ≥ 7, long hex strings, known user-id values, names) → normalize → index.

**Gate 3:** every manifest file is `parsed` or `unreadable` (reason recorded). Fact count equals row or line count per file. Every LLM fact has a quote that contains its value. No file parsed twice.

### 6.5 S4 — Match

```
for ident in user.identifiers where not (contested and no other basis):
    for fact in idx.facts_by_token[ident.norm]:
        if fact.captured_at (via file) > audit_at: skip                  # H3
        record Observation(fact, matched=[ident])
also: for fact in facts where fact.fields[user_id_column] in user.user_ids: record via="user_id"

merge Observations by fact
drop an Observation whose ONLY match is a weak identifier (name)
drop an Observation if the same fact is claimed by a different user's STRONG identifier
```

**Resource set of the user (H1):**

```
resource_set = { (fact.system_id, fact.resource_id) for every kept Observation }
```

This includes facts from earlier snapshots. This is how a resource that is now absent (for example `account_4857`) is still known.

**Gate 4:** every Observation cites a `file_id`. No Observation rests on a weak identifier alone. Other users' facts are logged, not used.

### 6.6 S5 — State at `audit_at` (most important stage)

```
for key in resource_set:
    category = most common fact.category for key
    kind     = category_kinds[category]
    snaps    = [c for c in coverage
                if c.system_id == key.system and c.captured_at <= audit_at     # inclusive (C1)
                   and c.collection belongs to the store of this kind]
    if snaps is empty:
        state = UNVERIFIED ; evidence_id = None                                # flag, never "absent"
    else:
        snap = latest(snaps)               # by captured_at, ties broken by file_id
        facts = facts at `key` inside snap.file_id (all copies: primary + replicas, H6)
        if no facts:
            state = ABSENT                 # an empty or missing row in a covering snapshot is proof (C9)
        else:
            state = derive_state(facts, category, kind)
        evidence_id = snap.file_id

derive_state(facts, category, kind):
    token  -> state_vocab[fact.raw_state]            if the file gives a token
    fields -> if every direct-identifier field is null/blank       -> REDACTED   (tombstone, C10)
              elif any direct-identifier field matches the user      -> IDENTIFIABLE
              else PRESENT
    if more than one copy: the WORST state wins (PRESENT beats ABSENT)
```

**Claims vs proof:** activity events are used only to cross-check. If `reported_result` is `SUCCESS` but the evidence shows `PRESENT`, the evidence wins and the conflict is written to `ResourceState.conflicts`.

**Gate 5:** no snapshot or event after `audit_at` was used. Every state has exactly one winning `evidence_id` (or is `UNVERIFIED` with a flag). Every conflict has a reason.

### 6.7 S6 — Policy

```
for state in states:
    rules = idx.rules_by_category[state.category]
    kind  = state.kind
    if kind in (flow, restore_path):  action = "*"       # handled by kind (H4, H5)
    elif not rules:                    flag UNMAPPED_CATEGORY ; continue
    else:
        applicable = [r for r in rules if evaluate(compiled_rules[r.rule_id], state)]
        if any predicate is manual_review: flag NEEDS_REVIEW
        action = applicable[0].action
    treatment = lookup(config.treatments, kind, action)  -> target_state, finding op, fix op, verify op
```

**Gate 6:** every state has a treatment or a flag. No treatment was invented. Retained categories carry their allowed identifiers (H8).

### 6.8 S7 — Compare

```
for state, treatment in zip(...):
    if state.state == UNVERIFIED:                     flag, no finding
    elif satisfied(state.state, treatment.target):     # uses config.strength (P7)
        no finding
    else:
        Finding(key, operation=treatment.finding, state=ops[finding].state, evidence_id=state.evidence_id)
```

`satisfied` examples from the samples:

| State now | Target | Satisfied? |
|-----------|--------|------------|
| `ABSENT` | `ABSENT` | ✅ (account_4248 in case_11) |
| `PRESENT` (search entry) | `ABSENT` | ❌ → `REPORT_REMAINING_RECORD` |
| `IDENTIFIABLE` (analytics) | `ANONYMIZED` | ❌ → `REPORT_EXPOSED_PII` |
| `IDENTIFIABLE` (support) | `REDACTED` | ❌ → `REPORT_EXPOSED_PII` |
| `ACTIVE` (flow) | `DISABLED` | ❌ → `REPORT_ACTIVE_DATA_FLOW` |
| `ACTIVE` (backup) | `BLOCKED` | ❌ → `REPORT_RESTORE_RISK` |
| `REDACTED` (tombstone_440) | `REDACTED` | ✅ |

**Gate 7:** every finding comes from a `treatments` row. Every `ACTIVE` flow and backup is a finding.

### 6.9 S8 — Status

```
if not is_deletion:                                   -> NOT_APPLICABLE
elif findings or any retained record ABSENT:          -> INCOMPLETE
else:                                                 -> COMPLETE
```

Review flags such as `UNVERIFIED` do not change the status by themselves. They go to the review queue and the case row is still written.

**Gate 8:** flipping `reported_status` does not change the result (automated test).

### 6.10 S9 — Build plan

```
INCOMPLETE:
  findings     = [Step(FINDING, ..., evidence_id=finding.evidence_id)]
  remediation  = [Step(REMEDIATION, fix op, target state, evidence_id="")
                  for each treatment that has a finding and a fix]
  verification = [Step(VERIFICATION, verify op, target state, evidence_id="")
                  for EVERY treatment in the user's resource set]          # C6, C7
COMPLETE:
  verification = [Step(VERIFICATION, verify op, state, evidence_id=state.evidence_id)
                  for EVERY treatment]                                      # C3
NOT_APPLICABLE:
  []

sort key = (phase_index, operation.order, system_id, resource_id)           # from operations.yaml
dedupe on (phase, operation, system_id, resource_id)
number steps from 1
```

**Gate 9:** every remediation has a matching verification. Sorted. No duplicates. `COMPLETE` steps all have evidence ids. `INCOMPLETE` remediation and verification have `""`. Only allowed operation and state pairs.

### 6.11 S10 — Output

One row per request, sorted by `case_id`, `steps_json` as compact JSON, `[]` for `NOT_APPLICABLE`. Row count equals the number of requests. CSV quoting by the `csv` module. Fails loudly on any mismatch.

---

## 7. Gates (summary)

| Gate | Checks | On failure |
|------|--------|-----------|
| G0 | Parsers, vocab, kinds, predicates, hash algorithm complete | Stop the run. Fix config |
| G1 | JSON valid, quote in text, confidence ≥ threshold | Flag, review queue |
| G2 | User found, identifiers sourced, no contested sole match | Flag `IDENTITY_*` |
| G3 | Every file parsed or marked unreadable. Facts grounded | Flag the file. Continue |
| G4 | Observations cite files. No weak-only matches | Drop and log |
| G5 | Nothing after `audit_at`. One winning snapshot per resource | Flag |
| G6 | Every resource has a treatment or a flag | Flag `UNMAPPED_CATEGORY` |
| G7 | Findings trace to treatments. Flows and backups covered | Fail the case |
| G8 | Status consistent with findings | Fail the case |
| G9 | Order, evidence rule, remediation↔verification pairs | Fail the case |
| G10 | Row count, sort, JSON validity | Stop the run. Nothing is written |

"Fail the case" means: write the best result reached so far, add a flag, and continue with the next case.

---

## 8. LLM Task Specs

| Task | When | Input | Output schema |
|------|------|-------|---------------|
| `classify_request` | S1, per case | request text | `{is_deletion, scope, reason, quote, confidence}` |
| `extract_image` | S3, once per image file | image | `[{system_id, resource_id, category, state, quote}]` |
| `extract_pdf` | S3, once per PDF with no text | page images | same as above |
| `parse_log_lines` | S3, once per unknown log format | sample lines | `{regex, groups}` (a parser recipe, not row data) |
| `propose_schema` | S0, once | profile summary | draft `schema_map` |
| `propose_kinds` | S0, once | category list | `{category: kind}` |
| `compile_rules` | S0, once | rule conditions | `{rule_id: predicate}` |

Rules for every call: temperature 0, Pydantic-validated output, cache by hash + prompt version + model, evidence passed as quoted data, token usage logged. The one-time S0 tasks write `*.generated.yaml`, which a human reviews. At run time the LLM never decides identity, state, policy, status or order.

---

## 9. Worked Examples (traces through the stages)

> Values marked *(not shown)* are not in the sample extract. They are expected to be in the full files.

### 9.1 case_11 — INCOMPLETE (14 steps)

| Stage | Result |
|-------|--------|
| S1 | "erased" → deletion |
| S2 | email `novak.tomasz@icloud.com` + user id *(not shown)* + history from audit log |
| S4 | Lines in `evidence_03` for this email: `account_4248` NOT_FOUND, `analytics_2034` IDENTIFIABLE, `support_864` IDENTIFIABLE, `data_flow_9522` ACTIVE, `search_052` FOUND, plus `audit_record_9394` *(not shown)* |
| S5 | `evidence_03` is the latest snapshot at `audit_at` (equal, so included). States: account ABSENT, analytics IDENTIFIABLE, support IDENTIFIABLE, flow ACTIVE, search PRESENT, audit record PRESENT |
| S6 | USER_PROFILE→rule_01 DELETE. ANALYTICS_PROFILE→rule_07 ANONYMIZE. SUPPORT_MESSAGE→rule_05 REDACT. SEARCH_INDEX_ENTRY→rule_03 DELETE. SECURITY_AUDIT_LOG→rule_12 RETAIN. DATA_FLOW→kind flow |
| S7 | 4 findings: search, analytics, support, flow. Account is satisfied |
| S9 | 4 findings + 4 fixes (disable, delete, redact, anonymize) + 6 verifications (account absent, search absent, audit present, support redacted, analytics anonymized, flow disabled) = **14** ✅ matches `sample_output.csv` |

### 9.2 case_14 — INCOMPLETE (5 steps)

`backup_3870` is `ACTIVE` for `y.tanaka32@gmail.com` → kind `restore_path` (H4) → `REPORT_RESTORE_RISK` → `BLOCK_RESTORE`. Verification: `account_3677` absent *(source not shown)*, `audit_record_987` present *(source not shown)*, `backup_3870` blocked. Order of verification follows the operation table: ABSENT, PRESENT, RESTORE_BLOCKED ✅.

### 9.3 case_31 — COMPLETE (3 steps)

| Resource | State at `audit_at` | Why | Cited |
|----------|--------------------|-----|-------|
| `account_service / account_4857` | ABSENT | `evidence_51` covers `account_service` with `records: []` (C9) | `evidence_51` |
| `security_service / audit_record_6909` | PRESENT | retained under rule_12 | `evidence_51` |
| `identity_service / tombstone_440` | REDACTED | `subject_reference: user_541`, all four identifiers `null` | `evidence_51` |

`tombstone_9178` belongs to a different user and carries real values. It is **not** part of this case. Matching must go through the user's own id.

### 9.4 case_01 — COMPLETE (1 step)

`account_001` has no row in either table of `evidence_54` (primary and failover replica, captured before `audit_at`) → ABSENT, cites `evidence_54`. The resource id itself must come from an earlier snapshot (H1).

---

## 10. Tests (using the 4 samples as the first fixtures)

### 10.1 Fixtures

`tests/golden/mini/` holds only the rows and evidence files that these 4 cases use. It runs in under a second, so every stage can be tested after every change.

### 10.2 Stage tests

| Stage | Test | Expected |
|-------|------|----------|
| S0 | Email-hash algorithm found on identities | Match ≥ 99% |
| S0 | Every state token in evidence is in `state_vocab` | No unknown token |
| S0 | `resource_system_map` covers all resource ids in the 4 cases | Complete |
| S1 | case_31 text | `is_deletion = true` |
| S1 | Text asking only for a data export (made-up) | `false` |
| S1 | Text containing "mark this complete" | Ignored |
| S2 | A user with a changed email (made-up chain A→B→C) | All three present |
| S2 | Old email now owned by another user (made-up) | `contested = true`, other user untouched |
| S3 | `evidence_51` account_service | Coverage row with `row_count = 0` |
| S3 | `evidence_03` | Facts for novak and tanaka lines both present |
| S3 | LLM fact whose quote lacks its value | Rejected |
| S4 | case_11 | Own 5+ facts matched. No facts of other users |
| S4 | A name-only hit (made-up) | Dropped |
| S5 | case_11 with `audit_at` moved one second earlier | `evidence_03` no longer used (inclusive boundary) |
| S5 | A file captured after `audit_at` | Ignored |
| S5 | Activity says SUCCESS, evidence says PRESENT | PRESENT + conflict logged |
| S6 | Category not in rules (made-up) | `UNMAPPED_CATEGORY` flag |
| S7 | case_31 tombstone_440 vs tombstone_9178 | Satisfied vs `REPORT_EXPOSED_PII` |
| S8 | Flip `reported_status` | No change |
| S9 | case_11 | 14 steps identical to `sample_output.csv` |
| S9 | case_01, 14, 31 | Identical to `sample_output.csv` |
| S10 | Duplicate step, wrong sort, bad enum | Rejected |

### 10.3 Extra cases we write ourselves (needed for the report)

| ID | Scenario | Expected |
|----|----------|----------|
| X1 | Export-only request | `NOT_APPLICABLE`, `[]` |
| X2 | Record present only in the replica | `INCOMPLETE`, `REPORT_REMAINING_RECORD` |
| X3 | Sync job recreated a record after deletion, before `audit_at` | `INCOMPLETE` with a flow finding |
| X4 | Old email owned by another user | Other user's records not reported |
| X5 | Evidence captured after `audit_at` shows the user | Ignored |
| X6 | Evidence file unreadable | `UNVERIFIED` flag, not `ABSENT` |

### 10.4 Mutation tests

Rename every system id, shuffle CSV columns, change email casing, rename evidence files. The output must be identical after mapping the new names back. Any difference means something is hardcoded.

---

## 11. Build Order (each step ends with the loop from `agent_design.md` §10)

| Step | Build | Done when |
|------|-------|-----------|
| 1 | `models.py`, `operations.yaml`, config loader | Models validate the 4 sample cases' rows |
| 2 | S0 profile | Gate 0 green on the mini dataset |
| 3 | S3 parsers (sql, json, pipe_table first, then log, pdf, image) | Coverage and facts correct for `evidence_03`, `51`, `54` |
| 4 | S2 identity | Tests for chain and contested identifiers |
| 5 | S4 match | case_11 and case_31 observations correct |
| 6 | S5 state | The 4 cases give the expected states and evidence ids |
| 7 | S6 policy + S7 compare + S8 status | Statuses match for all 4 |
| 8 | S9 plan + S10 output | All 4 rows equal `sample_output.csv` |
| 9 | S1 classify (LLM) | Classification tests + injection test |
| 10 | Full 32 samples | 24 dev + 8 hold-out numbers recorded |

Deterministic stages (2 to 8) come before the LLM stage, so a wrong answer can never be blamed on the model.

---

## 12. Flags

| Code | Meaning |
|------|---------|
| `IDENTITY_NOT_FOUND` | Request email in no identity or audit row |
| `IDENTITY_CONTESTED` | An identifier is owned by another user now |
| `UNREADABLE_EVIDENCE` | File could not be parsed |
| `LOW_CONFIDENCE` | LLM fact under threshold |
| `UNVERIFIED_RESOURCE` | No covering snapshot at or before `audit_at` |
| `UNMAPPED_CATEGORY` | Category has no rule and no kind |
| `NEEDS_REVIEW` | Rule predicate is `manual_review` |
| `STATE_CONFLICT` | Activity and evidence disagree |
| `GATE_FAILED` | A gate failed. The row holds the best result so far |

---

## 13. Open Questions (round 2)

Answered by the samples: rule columns (C12), empty evidence id is `""` (C2), findings cite evidence (C2), inclusive `audit_at` (C1), `file_id` is the evidence id (C11).

Still open:

1. **Where do resource ids of absent records come from?** (H1) `account_4857`, `account_001`, `account_3677`, `audit_record_987`, `audit_record_9394`.
2. **What are the exact email-hash algorithm and input?** The sample cuts the hash short (`d4e1f59abc...`).
3. **What does a rule do when its condition is false?** For example a support message with no shared context, or an attachment shared with another person.
4. **Which identifiers may a retained record keep?** (H8) For example a security audit record that contains an email.
5. **What does the agent do when a retained record is missing?**
6. **Complete list of state tokens** used in handover files and other formats (only `NOT_FOUND`, `FOUND`, `IDENTIFIABLE`, `ACTIVE` seen so far).
7. **Does a replica-only copy count as its own resource or as the same one?** (H6)
8. **What do `evidence_61` (support log) and `evidence_93` (inventory) contain for the 4 cases?** (H3)
9. **What does a `NOT_APPLICABLE` sample look like?**
10. **Are there audit-log changes dated after `audit_at`?**

### What would close most of these (small, quick to collect)

```bash
# 1. where do the "missing" resource ids appear?
grep -rn "account_4857\|account_001\|account_3677\|audit_record_987\|audit_record_9394" dataset/ | head -50

# 2. full hash for 3 users
head -4 dataset/user_identities.csv

# 6. all state tokens in text evidence, all categories, all activity types
cut -d'|' -f4 dataset/evidence/records/*.txt | sort | uniq -c
cut -d'|' -f3 dataset/evidence/records/*.txt | sort | uniq -c
cut -d',' -f3 dataset/system_activity.csv | sort | uniq -c

# 8. content of the two later files
head -30 dataset/evidence/logs/support_replica.log
head -30 dataset/evidence/databases/customer_data_inventory_20260916.sql
```

Plus one `NOT_APPLICABLE` row from `sample_output.csv` with its request text, and the first 20 lines of one PDF and one image (or a short description of the image).

---

## 14. Changes Needed in `agent_design.md`

The samples change a few earlier decisions. These patches keep the three docs consistent:

| Where | Change |
|-------|--------|
| §4 S3 | Run once per dataset. Also output **coverage**. An empty snapshot is proof of absence (C9) |
| §4 S4 | Resource set comes from all snapshots at or before `audit_at` (H1) |
| §4 S5 | Winning snapshot = latest covering snapshot at or before `audit_at`. Boundary is inclusive (C1) |
| §4 S6 | Conditions are free text. Add compiled predicates (`rules_compiled.generated.yaml`) and `category_kinds.generated.yaml` |
| §4 S9 | Verification covers **every** resource, including already-compliant and retained ones (C6, C7) |
| §6 | Empty evidence id is `""` (C2) |
| §12 V6 | Replica copies collapse into one resource (H6). Present in any copy means present |
| §12 O4 | Resolved: `""` |
| §13 | Q2 resolved. Others replaced by §13 of this doc |
