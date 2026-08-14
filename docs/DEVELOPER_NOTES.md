# Capital Management — Developer Notes

Technical history, known bugs, and deployment steps for the Capital Management feature (Share Agreement, Share Movement, Convertible Loan Note, Share Transfer, Shareholder). The end-user guide lives in `docs/CAPITAL_MANAGEMENT_SOP.md` — this file is for whoever maintains the app.

**Last reviewed:** 2026-08-14

---

## Known technical issues

| # | Issue | Effect |
|---|---|---|
| 1 | **No configurable approval workflow.** Status fields (Draft/Approved/Shares Issued/Active/Converted/etc.) are read-only and only change as a side effect of the whitelisted action functions. | By design. If a real approval chain is wanted later, it needs a proper Workflow doctype, not more ad-hoc status-setting. |
| 2 | **Found while testing the delete-blocking fix (session 6):** Share Movement's `bank_account` field is mandatory, but nothing requires a Share Agreement to have one set before "Issue Shares" runs. `issue_shares_from_agreement` passes `agreement.bank_account` straight through — if it's blank, the resulting Share Movement fails to insert with a `MandatoryError`. | Either make Share Agreement's `bank_account` field required, or have `issue_shares_from_agreement` validate it's set before attempting to create the Share Movement, with a clear error message instead of the raw MandatoryError. |

---

## Changelog

### 2026-08-14 (session 8) — Collapsed Share Transfer's validation to one place (code side)
Closed the backlog item of the same name. The two duplicate validation paths were:
1. This app's own `doc_events` hook (`hooks.py` → `share_transfer_customization/share_transfer_controller.py`).
2. A Server Script on production ("Share Transfer Multi-Currency Validation", Before Submit) doing overlapping checks with one real numeric difference (see session 3's changelog entry — already resolved there by keeping this repo's exchange-rate-multiplied convention and folding in the Server Script's "total amount > 0" check).

What was actually left to "collapse" was dead weight *within this file and hooks.py*, not new logic:
- `share_transfer_controller.py` had ~100 lines of fully commented-out code at the top — an old draft of `set_standard_accounts`/`calculate_rate_and_amount`/`create_custom_journal_entry` predating the live versions further down the same file. Deleted; the live functions were already confirmed (session 3) to be a complete superset of what the commented draft and the production Server Script both did.
- `hooks.py`'s `doc_events` section had a stray leading `# doc_events = {` / `# hooks.py` comment pair, a commented-out dead reference to a `Share Movement` validate hook using the old orphaned-function pattern from before Share Movement had a real controller class (session 1), a second fully-commented-out `doc_events` dict referencing a nonexistent `validate_share_transfer` function and wiring `create_custom_journal_entry` to `on_submit` (explicitly rejected by design — the comment right above it says why), and a dangling `"*": {...}` example fragment. All removed; one real `doc_events` dict remains.
- Verified via `frappe.get_hooks("doc_events")` and direct attribute checks after a clean `bench migrate` that nothing was lost — `set_standard_accounts`, `calculate_rate_and_amount`, `validate_accounts`, and `create_custom_journal_entry` all still resolve and are still wired exactly as before.

**What's not code-side and still needs doing**: disabling the actual "Share Transfer Multi-Currency Validation" Server Script *on production* — this session has no access to that environment (confirmed earlier: the local `sphynx` bench site is not verified to be the same as `sphynx.c.frappe.cloud`). That step is already tracked in the Production Deployment Checklist below; this changelog entry doesn't change that checklist, only closes the code-side half of the backlog item.

### 2026-08-14 (session 7) — Removed Share Register and Bulk Upload
Per explicit instruction, rather than "finish or remove" (the backlog item this closes) — removed.
- Confirmed zero data loss first: **Share Register** was `is_virtual: 1` with no backing table at all; **Bulk Upload** had a real table but 0 rows.
- Deleted both `DocType` records from the site (`frappe.delete_doc("DocType", ..., force=True)`, which also dropped Bulk Upload's now-empty table), then deleted both doctype folders from the app source entirely (`doctype/share_register/`, `doctype/bulk_upload/`).
- No other doctype, report, hooks.py entry, or fixture referenced either one — the only remaining references were documentation (SOP known-issues/troubleshooting rows, this file's Known Issues table), now removed/updated accordingly.
- Not related: `api/capital_management.py::get_share_register` is a same-named but unconnected function (a dead, never-called aggregation query predating this session) — left as-is, since it doesn't reference the Share Register doctype and removing it wasn't asked for.

### 2026-08-14 (session 6) — Production bug reports: delete blocking, auto-JE checkbox, CLN installments
Three bugs reported from production testing, all fixed and verified.

**1. Couldn't delete a cancelled/Draft Share Movement or Share Agreement while cross-linked.**
Root cause: `before_delete` is not an actual Frappe document hook — confirmed via `grep` against `frappe/model/`, zero matches. All three doctypes (Share Movement, Share Agreement, Convertible Loan Note) had defined one, and none of them ever ran; Frappe's real protection against deleting a submitted document is its own core `check_permission_and_not_submitted` (`frappe/model/delete_doc.py`). The actual blocker was Frappe's cross-document link check (`check_if_doc_is_linked` / `check_if_doc_is_dynamically_linked`), which runs *after* `on_trash` but *before* the row is actually removed — so a Share Agreement's `share_movement_ref` (or a CLN's `share_transfer_ref`), still pointing at the Share Movement being deleted, blocked the delete outright regardless of either document's own status.
- Removed the three dead `before_delete` methods.
- Added `ShareMovement.detach_from_source_document()`, called from both `on_cancel` (already existed for the Share Agreement case; extended to also cover Convertible Loan Note) and the new, more thorough `on_trash` — clearing the back-reference and resetting the source document's status *before* Frappe's link check runs, regardless of the Share Movement's own docstatus (Draft or Cancelled).
- Improved `ShareAgreement.on_trash`'s bare `except: pass` to at least `frappe.log_error`, for future debuggability.
- **Verified live** on the dev site with an isolated, fully-cleaned-up test fixture: created a Shareholder + Share Agreement + Share Movement, cancelled both, manually re-established the cross-link (simulating historical data from before this fix), and confirmed `frappe.delete_doc("Share Movement", ...)` now succeeds where it previously raised `LinkExistsError`. Also verified the Agreement itself could then be cancelled and deleted cleanly.
- **Found a second, unrelated bug while testing this**: Share Movement's `bank_account` is mandatory, but `issue_shares_from_agreement` doesn't check the source Share Agreement has one set before creating the Share Movement — surfaces as a raw `MandatoryError` instead of a clear message. Logged as Known Issue #3, not fixed (out of scope for what was asked this round).

**2. "Auto-create Journal Entry on Submit" checkbox did nothing.**
The field existed (default checked) but no code ever read it.
- `ShareMovement.on_submit()` now calls `create_journal_entry_from_share_movement` automatically when the checkbox is checked and no Journal Entry exists yet, catching and logging any failure (with a fallback message pointing to the manual Action) rather than blocking the submit.
- `ShareMovement.validate()` forces the checkbox off whenever `is_opening_entry == "Yes"` (opening entries never get a Journal Entry at all) — enforced server-side regardless of what the client sends.
- Added `read_only_depends_on` on the field for the same condition, and a client-side `auto_create_journal_entry` change handler showing an informational `msgprint` either way ("will be created automatically on submit" / "use Create Journal Entry after submitting yourself").
- The Share Movement intro banner (added session 5) now branches three ways: Opening Entry Draft, non-opening Draft with auto-create on, non-opening Draft with auto-create off — each with accurate guidance.

**3. CLN repayment only supported paying off the entire loan at once.**
Rebuilt as an installment model, mirroring the existing Interest Accruals pattern:
- New child doctype **CLN Repayment** (`repayment_date`, `principal_paid`, `interest_paid`, `penalty_paid`, `exchange_rate`, `journal_entry`, `remaining_principal`, `remaining_interest`, `currency`, `remarks`), analogous to CLN Interest Accrual.
- Convertible Loan Note's single-shot `repayment_journal_entry_ref` / `repayment_penalty_amount` fields (added session 4) removed — replaced with a `repayments` Table field and a `total_repaid` running-total field. `repayment_date` is repurposed to mean "fully repaid on" (only set once the balance hits zero), relabeled "Fully Repaid On".
- New `get_cln_outstanding_balance(cln_name)` — returns what's still owed (`principal_amount` minus `SUM(principal_paid)`, `accrued_interest` minus `SUM(interest_paid)` across prior installments), without mutating `principal_amount`/`accrued_interest` themselves.
- `record_cln_repayment` rewritten to accept `principal_amount`/`interest_amount` for *this installment* (each optional — omit either to default to paying it off in full, preserving the old "just repay it" behavior as the simple case). Validates neither exceeds what's outstanding. Posts a JE sized to this installment only (omitting the Loan Liability or Interest Payable line entirely if that portion is zero this time). Sets status to "Repaid" only once both outstanding amounts hit zero (0.01 epsilon).
- `ConvertibleLoanNote.on_cancel`/`on_trash` updated to iterate the `repayments` child table (cancelling/deleting every installment's JE) instead of the single removed field.
- Client-side "Record Repayment" button now fetches the current outstanding balance first (via `get_cln_outstanding_balance`), pre-fills principal/interest fields with the full outstanding amounts (editable down for a partial installment), and shows currency-aware labels. Button visibility condition simplified to just `status === 'Active'` — it doesn't need to check for an existing repayment JE anymore, since installments are supported until the loan reaches Repaid.

**Also (per explicit request):**
- **CLN currency symbols fixed** — all 9 Currency-type fields on Convertible Loan Note (`principal_amount`, `accrued_interest`, `qualified_financing_threshold`, `valuation_cap`, `par_value_per_share`, `total_converted_amount`, `conversion_price`, `repayment_penalty_amount` → now `total_repaid`, `total_accrued_from_table`) had `options: null`, always showing the site default currency symbol regardless of `loan_currency`. All now set to `options: "loan_currency"`. (CLN Interest Accrual's child table fields were already correct — confirmed no change needed there.)
- **Opening Entry field**: removed the `description` text from Share Agreement's and Share Movement's `is_opening_entry` field (per explicit request — the guidance now lives only in the user guide, not as an inline field description). Added the same field to Convertible Loan Note (didn't exist there before), wired into `record_cln_disbursement`: when `is_opening_entry == "Yes"`, skips Journal Entry creation entirely and just activates the loan, mirroring how Share Movement's Opening Entry already worked.
- **New "More Info" tab** added to Share Agreement (previously had no tabs at all), Share Movement, and Convertible Loan Note, with `is_opening_entry` moved there in all three — out of the main flow, since it's an edge case (migrated data), not a field someone fills in during a normal transaction.

### 2026-08-14 (session 5) — Issue Shares UX
- **"Issue Shares" on Share Agreement now redirects straight to the new Share Movement** (`frappe.set_route`) instead of showing a `msgprint` with a click-to-open button.
- **Added a persistent `frm.set_intro()` banner on Share Movement**: orange while it's a Draft ("submit it, then create its Journal Entry"), blue once submitted but before a Journal Entry exists (skipped for Opening Entries, which never get one). Lives in its own `frappe.ui.form.on('Share Movement', ...)` block at the top of the file, registered before the block that adds the Create Journal Entry button, so it doesn't fight over `refresh` ordering.

### 2026-08-14 (session 4) — CLN repayment
- **Built CLN cash repayment**, closing the former Known Issue #3 (there was previously no way to mark a loan "Repaid" — only conversion was supported).
  - New fields on Convertible Loan Note: `repayment_date`, `repayment_journal_entry_ref`, `repayment_penalty_amount` (References tab, alongside the existing disbursement/conversion reference fields).
  - New whitelisted function `record_cln_repayment(cln_name, repayment_date=None, penalty_amount=None)` in `api/capital_management.py`. Posts Dr Loan Liability (clearing principal) + Dr Interest Payable (clearing any accrued interest) + Dr Interest Expense (if an early repayment penalty applies, requires `early_repayment_allowed` checked and an Interest Expense Account set) / Cr Bank, sets status to "Repaid", and updates the lender's Shareholder totals via the same `recalculate_shareholder_totals` path used by disbursement/conversion.
  - New **Record Repayment** button on the CLN form (visible alongside Accrue Interest/Convert to Shares whenever status is "Active"), with a dialog for repayment date and an optional penalty amount (only shown if `early_repayment_allowed` is checked on the CLN).
  - `on_cancel`/`on_trash` extended to also cache, cancel, and clean up the repayment Journal Entry, matching how disbursement/conversion JEs were already handled.
- **Removed three Known Issues from the tracker per explicit instruction, not because the underlying facts changed** — for reference, since they're no longer tracked here:
  - The John Doe/Company B.V `company = Sphynx` Shareholder ambiguity (previously Issue #4) — still present in historical data; the user chose to handle new imports via the Opening Entry field rather than edit historical records.
  - The 12 orphaned Custom Field records found and removed from this dev site (previously Issue #5) — still worth checking production for its own independent set, since production has drifted from the repo all session.
  - Share Transfer's validation running from two places until the production Server Script is disabled (previously Issue #6).

### 2026-08-14 (session 3) — Currency/UX polish, Connections, root-cause migrate fix
- **Exchange Rate fields** on Share Agreement, Share Movement, and Convertible Loan Note now use `depends_on: eval:doc.transaction_currency != frappe.defaults.get_default('currency')` (CLN uses `loan_currency`), matching Share Transfer's existing field. CLN's field was also changed from unconditionally `reqd: 1` to not-required-at-field-level, consistent with how Share Transfer's equivalent field behaves (enforcement of "required when currencies differ" happens in code, not the field schema).
- **Share Agreement's Currency fields** (`rate_per_share`, `par_value_per_share`, `total_consideration`, `premium_amount`) now have `options: "transaction_currency"` so they render with the correct currency symbol — they previously always showed the site default currency symbol regardless of the agreement's actual transaction currency. Matches Share Movement's existing behavior.
- **New report: Shareholder Balance** (`upande_sphynx/upande_sphynx/report/shareholder_balance/`) — a point-in-time shares-held summary per shareholder/share class, computed from submitted Share Movement records (adapted from the dead `get_share_register` function in `api/capital_management.py`, which is still unused elsewhere). Filters: Company (required), As On Date (required), Shareholder, Share Class.
- **Disabled ERPNext's standard "Share Ledger" and "Share Balance" reports** via patch (`upande_sphynx.patches.v1_0.disable_default_share_reports`, sets `Report.disabled = 1`, reversible). Both only reflect Share Transfer activity (Share Balance reads `Shareholder.share_balance`, a child table ERPNext populates exclusively from Share Transfer) — neither ever saw Share Agreement/Share Movement/CLN activity, which is most of what this app tracks.
- **Found and removed 12 orphaned Custom Field records** on Share Agreement, Share Movement, Convertible Loan Note (see Known Issue #5).
- **Root-caused and fixed a `bench migrate` failure that had been silently aborting `sync_customizations()` on every single migrate run all session.** The Custom Field record named `Share Transfer-custom_issue_type` had its internal `fieldname` column still set to the old value `issue_type` — it was renamed at the docname level at some point but never internally, so every migrate attempted to re-insert a field with that name and collided on the primary key, aborting before reaching any doctype processed after Share Transfer alphabetically/positionally (which is why the Company and Shareholder customizations added earlier this session kept silently failing to apply until this was fixed). Fixed via `frappe.db.set_value("Custom Field", "Share Transfer-custom_issue_type", "fieldname", "custom_issue_type")`. **This is almost certainly also present on production** — check before assuming a clean migrate there.
- **`issue_type` in old client scripts wasn't a random typo** — it was the literal fieldname stored in that corrupted Custom Field record before whatever rename operation only updated the docname. This explains the "Share Issue" client script bug found earlier (it checked `frm.doc.issue_type`, which doesn't exist as the *current* field name, but clearly used to).
- **CLN now auto-fetches its exchange rate** on `loan_currency`/`company` change (`fetch_cln_exchange_rate` in `convertible_loan_note.js`), matching the convenience Share Agreement and Share Movement already had via their own merged Client Scripts.
- **Added Connections (Document Links)** to Share Agreement, Share Movement, Convertible Loan Note (plain `links` arrays in their own doctype JSON — no issue there, since these doctypes are owned by this app) and to Shareholder (which isn't owned by this app, so needed a different mechanism):
  - **`custom/<doctype>.json`'s `links` key is silently ignored** by Frappe's customization sync (`sync_customizations_for_doctype` in `frappe/modules/utils.py` only processes `custom_fields`, `property_setters`, `custom_perms` — confirmed by reading the source). Don't rely on it for Document Links to a doctype you don't own.
  - Instead, Shareholder's connections are added via `upande_sphynx.patches.v1_0.add_shareholder_connections`, inserting `DocType Link` rows directly.
  - **Do not set `custom=1`** on these rows despite that being the normal Customize Form convention. Confirmed via direct testing (`frappe.model.meta.Meta("Shareholder")`, bypassing all caching) that `custom=1` causes Frappe's `Meta.add_custom_links_and_actions()` to re-fetch and re-append every `custom=1` `DocType Link` row on top of the normal `Document.load_from_db()` load — which already includes them, since generic child-table loading (`frappe/model/document.py::load_from_db`) doesn't filter by the `custom` column at all. This only manifests as visible duplication when the target doctype (like Shareholder) has no *native* links of its own to distinguish "the normal load" from "the custom re-fetch" — both loads returned the exact same rows. Using `custom=0` avoids it, matching how Share Agreement/Share Movement/CLN's own native links already behave (no duplication observed there). Trade-off: if ERPNext ever ships a Shareholder doctype change that wipes/reloads its link table from scratch, these could be lost and would need re-adding (the patch's logic is idempotent — safe to re-run manually).

### 2026-08-14 (session 2) — Client/Server Script consolidation, Opening Entry, auto-synced totals, FX revaluation rewrite
- **Opening Entry** field (`is_opening_entry`, Select No/Yes) added to Share Agreement and Share Movement. `issue_shares_from_agreement` propagates it and sets `auto_create_journal_entry = 0`; `create_journal_entry_from_share_movement` refuses to run on an opening entry.
- **`recalculate_shareholder_totals()`** added to `api/capital_management.py`, wired into `ShareMovement.on_submit`/`on_cancel` and the CLN disbursement/conversion/cancel functions. Populates `Shareholder.custom_total_shares_held`/`custom_total_investment`, which were defined as fields but never written to by any code before this. Whitelisted wrapper `recompute_shareholder_totals(shareholder_name=None)` for manual/bulk recalculation (button on Shareholder form + Desk Page).
- **Client/Server Script consolidation**, cross-checked against the actual production site's script inventory (9 Client Scripts, 3 Server Scripts) rather than assumed from the dev site alone — an earlier pass in this same session had wrongly assumed the dev site's 9 experimental Share Transfer scripts reflected production; they didn't, and had to be redone:
  - Share Agreement (2 scripts), Share Movement (2 scripts), CLN (3 scripts): dev site content matched production exactly (with two already-fixed bugs: `exchange_rate_cln`, `share_movement_ref`→`share_transfer_ref`). Merged into each doctype's own `.js` file.
  - Share Transfer (2 Client Scripts + 2 Server Scripts on production, vs. 9 sprawling/conflicting scripts on the dev site): rebuilt `public/js/share_transfer.js` from the real production scripts. No `custom_issue_type`/Convertible-Loan toggle logic exists in production's live scripts at all (present in the doctype's fields, just not actively wired by any live script before this rebuild). JE creation logic moved from a Server Script (`custom_share_transfer.create_journal_entry`, called via `execute_api_method`) into `share_transfer_customization/share_transfer_controller.py::create_custom_journal_entry`, matching production's actual behavior: **auto-submits** the JE (the repo's prior version left it as a draft), puts a Shareholder **party on both lines** (debit=to_shareholder, credit=from_shareholder — the repo's prior version only put a party on the credit line), and sets `reference_type`/`reference_name` on each line (the repo's prior version had these commented out).
  - The before_submit Server Script ("Share Transfer Multi-Currency Validation") duplicated the repo's own `calculate_rate_and_amount`/`validate_accounts` with one real numeric difference: it set `doc.rate`/`doc.amount` to the transaction-currency values unconverted, while the repo multiplies by `exchange_rate` (company-currency semantics, matching ERPNext convention for those fields). Kept the repo's multiply-by-exchange-rate version; added the Server Script's `total_amount > 0` check to `calculate_rate_and_amount`, which the repo lacked.
  - All 15 relevant production-name-matching Client Scripts disabled (not deleted) on the dev site as they were migrated.
- **Company field: Share Capital Account** added (`custom/company.json`), Accounts tab, used by the FX revaluation task below.
- **Share Capital FX Revaluation** — the "Share Capital Currency Revaluation" Scheduler Event Server Script defined `def execute():` and never called it; it had been a complete no-op since creation (2025-11-06). It also called `frappe.utils.get_exchange_rate`, which doesn't exist (confirmed via `hasattr`) — would have crashed immediately even if called. Rewritten as `upande_sphynx/tasks.py::revalue_share_capital_fx`, registered via `hooks.py` `scheduler_events["yearly"]`. Extended scope to aggregate Share Transfer + Share Movement + Convertible Loan Note (the original only looked at Share Transfer). **The resulting Journal Entry is deliberately left as a draft, not auto-submitted** — the debit/credit direction (credit Share Capital on a base-currency increase, debit the Unrealized Exchange Gain/Loss account) is an implemented default, not a policy confirmed with an accountant. Manual dry-run trigger: `upande_sphynx.tasks.run_share_capital_fx_revaluation` (defaults `dry_run=1`).

### 2026-07-29 — Backend bug fixes
- Share Movement's controller was missing its core class entirely (only orphaned module-level functions) — would error on open/save/submit. Fixed: proper `class ShareMovement(Document)` with `validate`/`on_submit`/`on_cancel`/`before_delete`/`on_trash`.
- Share Agreement's `on_cancel`/`on_trash` used `frappe`/`_` without importing them — fixed.
- CLN's exchange rate was read via a nonexistent field (`cln.exchange_rate_cln`) in `record_cln_disbursement`/`accrue_cln_interest` — fixed to `cln.exchange_rate`.
- CLN's `share_transfer_ref` field was typed as a Link to Share Transfer but always held a Share Movement name — repointed the field's `options` to Share Movement.
- Added the missing `cancel_share_agreement`/`delete_share_agreement`/`cancel_share_movement`/`delete_share_movement` whitelisted functions that the bundled `.js` Cancel/Delete buttons were already calling.
- Reconciled Share Movement's `status`/`movement_type` option lists with what the validation code and reports actually expect (dropped dead conditions checking for option values that could never occur, e.g. `Share Subscription`, `Rights Issue`).

---

## Production deployment checklist

None of the above reaches the production Frappe Cloud site automatically — it was all built and verified on a local dev site (`sphynx.local`).

1. Deploy the updated `upande_sphynx` app code.
2. Run, in order: `bench --site <site> migrate`, `bench build --app upande_sphynx`, `bench --site <site> clear-cache`.
3. **Before assuming the migrate is clean**, check for the same `Share Transfer-custom_issue_type` corruption described above (Changelog, 2026-08-14 session 3) — it will abort `sync_customizations()` silently partway through otherwise:
   ```python
   frappe.db.get_value("Custom Field", "Share Transfer-custom_issue_type", "fieldname")
   # if this returns "issue_type" instead of "custom_issue_type":
   frappe.db.set_value("Custom Field", "Share Transfer-custom_issue_type", "fieldname", "custom_issue_type")
   frappe.db.commit()
   ```
4. Check production for its own set of orphaned Custom Fields on Share Agreement/Share Movement/Convertible Loan Note (Known Issue #5) — the 12 found on the dev site were dev-site-specific; production has drifted independently all session and may have different ones.
5. Disable these Client Scripts (leave them in place, just disabled, for rollback):
   - Share Agreement: "Share Agreement Buttons", "Share Agreement Account Filters"
   - Share Movement: "Share Movement Calculations", "Share Movement Account Filters"
   - Convertible Loan Note: "Convertible Loan Note Buttons", "Principal == Valuation", "Convertible Loan Note Account Filters"
   - Share Transfer: "Currency Share Management", "Share Management"
6. Disable these Server Scripts:
   - "Create Multi-Currency Journal Entry for Share Transfer" (API)
   - "Share Transfer Multi-Currency Validation" (Before Submit)
   - "Share Capital Currency Revaluation" (Scheduler Event) — was never functioning; disabling changes nothing observable.
7. Set the new **Share Capital Account** field on each Company before expecting the yearly FX revaluation task to do anything, and get accounting sign-off on the debit/credit direction (see Changelog) before treating its output as anything but a draft to review.
8. Clean up the two ambiguous Shareholder records behind Known Issue #4 (`company = Sphynx` on both "John Doe" and "Company B.V") if/when convenient — not blocking, since the Opening Entry field now handles new imports going forward.

---

## Lower-priority backlog

1. Clean up the John Doe/Company B.V `company = Sphynx` Shareholder data (see Changelog, session 4).
2. Delete the disabled, now-superseded Client Script records once confident the app-based replacements have run cleanly for a while.
