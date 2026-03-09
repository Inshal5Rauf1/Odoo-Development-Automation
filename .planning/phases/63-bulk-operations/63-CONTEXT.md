# Phase 63: Bulk Operations - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate performant bulk processing code — batched `@api.model_create_multi`, bulk action wizards with domain-based selection + preview + confirmation, and chunked `_process_batch()` helpers with `bus.bus` progress notifications. Covers three operation types: `state_transition`, `create_related`, and spec support for `update_fields` (deferred implementation).

Pipeline: Spec with `bulk_operations` array → Bulk preprocessor (order=85) builds wizard models + line models → Jinja renders wizard TransientModel + line model + form view + JS progress listener → Stub zones for Logic Writer → Semantic validate → Pass/fail

</domain>

<decisions>
## Implementation Decisions

### Bulk spec format

**Dedicated `bulk_operations` array at module level.** Not a per-model flag — bulk operations are explicit features, not toggles.

```json
{
  "module_name": "uni_admission",
  "bulk_operations": [
    {
      "id": "bulk_admit",
      "name": "Bulk Admission",
      "source_model": "admission.application",
      "wizard_model": "admission.bulk.admit.wizard",
      "operation": "state_transition",
      "source_domain": [["state", "=", "approved"]],
      "target_state": "admitted",
      "action_method": "action_admit",
      "preview_fields": ["name", "program_id", "cgpa", "merit_rank"],
      "side_effects": [
        "Create uni.student record for each admitted applicant",
        "Create uni.enrollment for first semester courses",
        "Send admission notification email"
      ],
      "batch_size": 50,
      "allow_partial": true
    },
    {
      "id": "bulk_challan",
      "name": "Generate Fee Challans",
      "source_model": "uni.student",
      "wizard_model": "fee.bulk.challan.wizard",
      "operation": "create_related",
      "source_domain": [["enrollment_status", "=", "active"]],
      "create_model": "fee.invoice",
      "create_fields": {
        "student_id": "source.id",
        "fee_structure_id": "wizard.fee_structure_id",
        "term_id": "wizard.term_id",
        "due_date": "wizard.due_date"
      },
      "preview_fields": ["name", "program_id", "department_id"],
      "batch_size": 100,
      "allow_partial": true
    },
    {
      "id": "bulk_attendance",
      "name": "Bulk Mark Attendance",
      "source_model": "uni.enrollment",
      "wizard_model": "attendance.bulk.wizard",
      "operation": "create_related",
      "source_domain": [],
      "create_model": "attendance.record",
      "wizard_fields": [
        {"name": "date", "type": "Date", "required": true},
        {"name": "course_id", "type": "Many2one", "comodel": "uni.course", "required": true},
        {"name": "section", "type": "Char"}
      ],
      "preview_fields": ["student_id", "course_id"],
      "batch_size": 200,
      "allow_partial": false
    }
  ]
}
```

**Three operation types:**
- `state_transition` → bulk move records to a new state via `action_method()`. Requires `target_state` and `action_method`.
- `create_related` → bulk create records in `create_model` linked to source records. Requires `create_model` and `create_fields` mapping.
- `update_fields` → bulk update specific fields. **Deferred** — spec format supports it but not building in Phase 63.

**Spec fields:**
- `wizard_fields`: Extra fields on the wizard TransientModel (date, course, etc.) that the user fills before processing. Become wizard model fields.
- `create_fields` mapping: `"source.id"` = source record's id, `"wizard.fee_structure_id"` = wizard's field value. Belt generates the mapping code.
- `allow_partial`: `true` = failed records skipped and reported; `false` = any failure rolls back entire batch (all-or-nothing).
- `side_effects`: String descriptions for Logic Writer context (stub report).
- `preview_fields`: Determines table columns in preview step.

### Wizard flow & preview

**Three-step wizard: Select → Preview → Process → Done.**

State machine:
```python
state = fields.Selection([
    ('select', 'Select Records'),
    ('preview', 'Preview'),
    ('process', 'Processing'),
    ('done', 'Complete'),
], default='select')
```

**Step 1 — Select:**
User enters wizard fields and optionally refines domain filter. Belt generates a domain builder from spec's `source_domain` plus wizard field filters. Shows live `record_count` (computed via `search_count()`).

**Step 2 — Preview:**
Shows sample records (first 10) + summary stats (total count, estimated time, batch size). Preview records stored as `One2many` to wizard line model.

Wizard line model (TransientModel):
```python
class BulkChallanWizardLine(models.TransientModel):
    _name = 'fee.bulk.challan.wizard.line'
    wizard_id = fields.Many2one('fee.bulk.challan.wizard', ondelete='cascade')
    student_id = fields.Many2one('uni.student')
    program_id = fields.Many2one(related='student_id.program_id')
    department_id = fields.Many2one(related='student_id.department_id')
    selected = fields.Boolean(default=True)
```

**Step 3 — Process:**
Wizard calls `_process_all()` which chunks records and processes in batches. Progress shown via `bus.bus`.

**Step 4 — Done:**
Summary: processed count, succeeded count, failed count (clickable), duration. Error log with per-record failure details. "View Created Records" action button + Close.

**Wizard model structure:**
```python
class BulkChallanWizard(models.TransientModel):
    _name = 'fee.bulk.challan.wizard'
    _description = 'Generate Fee Challans'

    state = fields.Selection([...], default='select')
    fee_structure_id = fields.Many2one('fee.structure', required=True)
    term_id = fields.Many2one('academic.term', required=True)
    due_date = fields.Date(required=True)

    record_count = fields.Integer(compute='_compute_record_count')
    preview_line_ids = fields.One2many('fee.bulk.challan.wizard.line', 'wizard_id')

    # Results
    success_count = fields.Integer(readonly=True)
    fail_count = fields.Integer(readonly=True)
    error_log = fields.Text(readonly=True)

    def action_preview(self):
        # --- BUSINESS LOGIC START ---
        # TODO: implement preview assembly
        pass
        # --- BUSINESS LOGIC END ---
        self.state = 'preview'
        return self._reopen_wizard()

    def action_process(self):
        self.state = 'process'
        self._process_all()
        self.state = 'done'
        return self._reopen_wizard()

    def _process_all(self):
        # --- BUSINESS LOGIC START ---
        # TODO: implement batch processing
        pass
        # --- BUSINESS LOGIC END ---

    def _reopen_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
```

Stub zones in `action_preview()` and `_process_all()` for Logic Writer. `_process_single()` also gets a stub zone.

### Batch processing strategy

**Commit per batch if `allow_partial=true`. All-or-nothing if `false`.**

```python
def _process_all(self):
    domain = self._get_processing_domain()
    records = self.env[self._source_model].search(domain)

    total = len(records)
    success = 0
    errors = []
    batch_size = self._batch_size

    for i in range(0, total, batch_size):
        batch = records[i:i + batch_size]

        if self._allow_partial:
            for record in batch:
                try:
                    self._process_single(record)
                    success += 1
                except Exception as e:
                    errors.append(f"{record.display_name}: {str(e)}")
                    _logger.warning("Bulk %s failed for %s: %s",
                                    self._name, record, e)
            self.env.cr.commit()
        else:
            try:
                for record in batch:
                    self._process_single(record)
                    success += 1
            except Exception as e:
                self.env.cr.rollback()
                raise UserError(
                    _("Batch processing failed at record '%s': %s\n"
                      "All changes have been rolled back.")
                    % (record.display_name, str(e))
                )

        self._notify_progress(processed=i + len(batch), total=total)

    self.write({
        'success_count': success,
        'fail_count': len(errors),
        'error_log': '\n'.join(errors) if errors else False,
    })
```

**Key decisions:**
- `allow_partial=true`: commit after each batch. Batches 1-4 committed even if batch 5 fails. Failed records logged, not retried.
- `allow_partial=false`: no intermediate commits. Single transaction. Any failure rolls back everything.
- **No retry policy.** Failed records are logged and reported in "done" step. Re-run wizard with domain filtering failed records if needed.
- `_process_single()` is always the stub zone. Structural loop, batching, error handling, progress are all template-generated. Logic Writer only implements what happens to ONE record.

**Batch size defaults:**
- `state_transition`: 50 (action methods trigger workflows/notifications — heavier)
- `create_related`: 100 (creates are lighter than workflow transitions)
- `update_fields`: 200 (simple field writes, lightest)
- Spec can override `batch_size` per operation.

**Stub report context for Logic Writer:**
```json
{
  "id": "bulk_challan_wizard__process_single",
  "method_type": "bulk_process",
  "processing_context": {
    "operation": "create_related",
    "source_model": "uni.student",
    "create_model": "fee.invoice",
    "create_fields_mapping": {
      "student_id": "source.id",
      "fee_structure_id": "wizard.fee_structure_id",
      "term_id": "wizard.term_id",
      "due_date": "wizard.due_date"
    },
    "side_effects": [
      "Send challan notification email to student"
    ]
  }
}
```

### Progress & notifications

**bus.bus for browser contexts. Logger fallback for cron/API.**

```python
def _notify_progress(self, processed, total):
    percentage = int((processed / total) * 100) if total else 100

    try:
        self.env['bus.bus']._sendone(
            f'bulk_progress_{self.env.uid}',
            'bulk_operation_progress',
            {
                'wizard_id': self.id,
                'wizard_model': self._name,
                'processed': processed,
                'total': total,
                'percentage': percentage,
                'operation_name': self._description,
            }
        )
    except Exception:
        pass  # no browser connected

    if percentage % 25 == 0:
        _logger.info("Bulk %s: %d/%d (%d%%)",
                     self._description, processed, total, percentage)
```

**Granularity: per-batch, NOT per-record.** At batch_size=100 with 2000 records, that's 20 bus.bus messages. Per-record would flood the bus.

**Client-side JS (generated as static asset):**
```javascript
/** @odoo-module **/
import { registry } from "@web/core/registry";

registry.category("bus.listeners").add("bulk_operation_progress", {
    listener(message) {
        const { percentage, processed, total, operation_name } = message;
        const progressEl = document.querySelector('.o_bulk_progress');
        if (progressEl) {
            progressEl.querySelector('.progress-bar').style.width = `${percentage}%`;
            progressEl.querySelector('.progress-text').textContent =
                `${operation_name}: ${processed} / ${total} (${percentage}%)`;
        }
    }
});
```

**Wizard form view progress bar (visible during 'process' state):**
```xml
<div class="o_bulk_progress"
     attrs="{'invisible': [('state', '!=', 'process')]}">
    <div class="progress">
        <div class="progress-bar progress-bar-striped progress-bar-animated"
             role="progressbar" style="width: 0%"/>
    </div>
    <span class="progress-text">Starting...</span>
</div>
```

**Estimated time calculation:**
```python
def _compute_estimated_time(self):
    for record in self:
        if record.record_count and record._batch_size:
            batches = math.ceil(record.record_count / record._batch_size)
            avg = {'state_transition': 2.0, 'create_related': 1.0, 'update_fields': 0.5}
            record.estimated_time = batches * avg.get(record._operation_type, 1.5)
```

Logger fallback: logs at 25% intervals to avoid spam. bus.bus fires at every batch.

### Preprocessor

```python
@register_preprocessor(order=85)
def process_bulk_operations(spec, models, context):
    bulk_ops = spec.get('bulk_operations', [])
    if not bulk_ops:
        return

    context['has_bulk'] = True
    context['bulk_operations'] = bulk_ops

    for op in bulk_ops:
        wizard = _build_wizard_model(op)
        wizard_line = _build_wizard_line_model(op)
        models.append(wizard)
        if op.get('preview_fields'):
            models.append(wizard_line)

        context.setdefault('extra_actions', []).append({
            'name': op['name'],
            'model': op['wizard_model'],
            'view_mode': 'form',
            'target': 'new',
        })
```

**Order 85:** After approval (80) because bulk operations may trigger approval actions, but before portal (95) because portal doesn't need to know about bulk wizards.

### New templates

```
templates/shared/
├── bulk_wizard_model.py.j2      # TransientModel with state machine
├── bulk_wizard_line.py.j2       # wizard line TransientModel
├── bulk_wizard_views.xml.j2     # multi-step form view
└── bulk_wizard_js.js.j2         # bus.bus progress listener
```

### Claude's Discretion

- BulkOperationSpec / BulkWizardFieldSpec Pydantic model exact structure
- Validation error codes (E24+) for bulk operation validation
- Exact field names on generated wizard model attributes (`_source_model`, `_batch_size`, `_allow_partial` etc.)
- renderer_context.py integration (has_bulk flag, manifest files list)
- Whether to extend existing `wizards` render stage or add a separate bulk render function
- Test fixture design

</decisions>

<specifics>
## Specific Ideas

- "Records matching: 1,847 students" — live search_count as wizard fields change (computed field)
- Wizard line model with `selected = fields.Boolean(default=True)` — users can deselect records in preview
- "View Created Challans" action button in done state → opens tree view filtered to created records
- `_reopen_wizard()` helper returns `act_window` back to same wizard for state transitions
- Error log with per-record failure details: "{record.display_name}: {error_message}" format
- `_transient_max_hours` on wizard for cleanup

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `preprocessors/_registry.py`: Decorator-based registry with `@register_preprocessor(order=N)` — use at order=85
- `import_wizard.py.j2`: Multi-step state machine + preview pattern (upload→preview→done) — adapt for select→preview→process→done
- `archival_wizard.py.j2`: Batch processing loop with `BATCH_SIZE` + commit pattern
- `model.py.j2`: Already generates `@api.model_create_multi` and `_post_create_processing()` stubs for `is_bulk` models
- `production.py` preprocessor: Already handles `bulk: true` flag → `is_bulk`, `has_create_override` (order=50)
- `logic_writer/stub_detector.py`: Recognizes `BUSINESS LOGIC START/END` markers — will detect wizard stub zones

### Established Patterns
- Preprocessor: pure function takes `spec dict`, returns enriched `spec dict` (immutable)
- Pydantic models for spec validation (PortalSpec, ChainSpec, ExtensionSpec as precedents)
- Frozen dataclasses for immutable data structures
- Stub zones: `# --- BUSINESS LOGIC START ---` / `# --- BUSINESS LOGIC END ---` markers
- Render stages: STAGE_NAMES list, each stage has a `render_*()` function

### Integration Points
- `spec_schema.py`: Add `BulkOperationSpec` (new Pydantic model), `bulk_operations` field on `ModuleSpec`
- `renderer.py`: Render within `wizards` stage (stage 7) or add separate `render_bulk()` function
- `renderer_context.py`: Add `has_bulk` flag, bulk wizard context assembly
- `validation/semantic.py`: New E-codes for bulk operation validation (source model exists, create model exists, field mappings valid)
- `knowledge/wizards.md`: Add bulk wizard section (no existing bulk/batch coverage)
- Preprocessor order sequence: ...80 (approval) → **85 (bulk_operations)** → 90 (notifications) → 95 (portal) → 100 (webhooks)

</code_context>

<deferred>
## Deferred Ideas

- `update_fields` operation type — spec format supports it but not building in Phase 63. Add when needed.
- Wizard line selection filtering (users deselecting individual records in preview) — basic `selected` field generated but no processing logic
- Scheduled bulk operations (cron-triggered bulk wizards) — separate phase
- Bulk import from CSV into wizard (combines import_wizard + bulk_wizard patterns)
- Mobile-specific bulk operation UI
- Bulk operation history/audit log (who ran what bulk operation when)
- Retry failed records button in done state

</deferred>

---

*Phase: 63-bulk-operations*
*Context gathered: 2026-03-09*
