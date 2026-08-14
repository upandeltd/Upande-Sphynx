# Capital Management — User Guide

**App:** Upande Sphynx
**Who this is for:** Anyone in Accounts who issues shares, records investor loans, transfers shares between shareholders, or needs to check who owns what.
**Last reviewed:** 2026-08-14

---

## 1. What Capital Management does

This part of the system keeps track of your company's shares and the money raised for them. It covers four everyday situations:

- **A new investor buys shares** → recorded as a **Share Agreement**, which produces a **Share Movement**.
- **An investor lends money that will turn into shares later** → recorded as a **Convertible Loan Note**.
- **Shares move from one existing shareholder to another, or the company buys shares back** → recorded as a **Share Transfer** (or, for a buyback, a **Share Movement**).
- **You need to know who owns what, and how much they've invested** → answered by the **Shareholder** record and two reports.

Everything ties back to the **Shareholder** doctype — every share agreement, movement, loan, and transfer points to one or more shareholders, and opening a Shareholder record shows you everything connected to them in one place (see Section 8).

---

## 2. Who can do this

Only two roles can create or edit anything in this area:

- **System Manager**
- **Accounts Manager**

If someone needs to *look* at holdings and reports without being able to edit anything — an investor-relations contact, for example — ask your System Administrator, since there isn't a lighter "view-only" role for this area today.

The **Share Transactions Report** (Section 9) is also visible to the **Accounts User** role.

---

## 3. Before you start — one-time setup

Do this once per company, before recording your first transaction. If someone has already set this up, skip to Section 4.

1. **Company** — make sure the Company record exists and its default currency is set correctly.
2. **Chart of Accounts** — make sure these accounts exist (create any that are missing):
   - A **Share Capital** account (Equity)
   - A **Share Premium** account (Equity)
   - A **Loan Liability** account (Liability) — for convertible loan notes
   - An **Interest Expense** account and an **Interest Payable** account — for loan interest
   - A **Bank Account**, linked to its GL account
3. **Share Type** — create one record per class of share you issue, for example "Ordinary Shares" or "Preference Shares." Go to **Share Type List → New**.
4. **Shareholder record for the company itself** — create a Shareholder record representing your own company. This is used automatically as the counterparty whenever shares are issued (it "gives" the shares that an investor "receives"). Make sure its name matches what the system expects — the Convertible Loan Note form, for instance, defaults this to "Sphynx"; check that matches your actual record.
5. **Shareholder record for every investor or lender** — create this before you create any agreement or loan note for them. Go to **Shareholder List → New**.

---

## 4. The records you'll work with

A quick map of what each record is for, before you dive into the step-by-step processes:

| Record | What it's for |
|---|---|
| **Shareholder** | One record per person, company, or fund that holds shares or has lent money. Everything else links back to this. |
| **Share Agreement** | The paperwork for a new share purchase — who's buying, how many shares, at what price, on what terms. Submitting it and clicking "Issue Shares" creates the Share Movement below. |
| **Share Movement** | The actual record of shares changing hands — created automatically from a Share Agreement or a converted loan, or created directly for a company buyback. This is what the system actually counts when it works out who owns how many shares. |
| **Convertible Loan Note** | A loan from an investor that's designed to convert into shares later, usually at a future funding round, instead of being repaid in cash. |
| **Share Transfer** | An existing shareholder selling or transferring shares to someone else (as opposed to the company issuing brand-new shares). |

---

## 5. Issuing new shares to an investor (Share Agreement)

Use this whenever a shareholder is buying shares directly from the company — a subscription, a fresh investment round, and so on.

### Step 1 — Create the Share Agreement
Go to **Share Agreement List → New** and fill in:

- **Agreement Date** — defaults to today.
- **Shareholder/Investor** — the Shareholder record for whoever is buying.
- **Agreement Type** — pick whichever describes this deal:
  - **Subscription Agreement** — an investor subscribing for newly issued shares.
  - **Share Purchase Agreement** — a straightforward purchase of shares for cash.
  - **Secondary Transfer Agreement** — one existing shareholder's shares being formally sold to a new party (note: the actual transfer itself should still go through Share Transfer, Section 7 — this agreement type is for documenting the deal terms).
  - **Shareholders Agreement** — a broader governance agreement between shareholders (voting rights, board seats, etc.), not necessarily tied to a single share purchase.
  - **Vesting Agreement** — shares that vest over time, typically for founders or employees.
- **Share Class/Type** — which class of share is being issued (Ordinary, Preference, etc.).
- **Number of Shares**, **Price per Share**, **Par Value per Share**.
- **Transaction Currency** — and **Exchange Rate**, which only appears if this currency is different from the company's default currency, and fills in automatically once you pick a currency.
- **Share Capital Account** and **Share Premium Account** — the accounting entries this agreement will eventually post to.
- **Terms** (optional, fill in whatever applies to this deal):
  - Vesting period, lock-in period.
  - Voting rights, dividend rights, pre-emptive rights (checkboxes).
  - **Liquidation Preference** — what this investor gets paid first if the company is sold or wound up, before other shareholders: **None**, **1x Non-Participating** (gets their investment back, then shares the rest normally), **1x Participating** (gets their investment back *and* still shares the rest), or **2x Non-Participating** (gets twice their investment back first).
  - **Anti-Dilution Protection** — protects this investor's ownership percentage if the company later issues shares at a lower price: **None**, **Full Ratchet** (their earlier price is fully adjusted down to match the new lower price), or **Weighted Average** (a milder adjustment that accounts for how many new shares were issued).
  - Board seats, drag-along rights, tag-along rights.
- **Payment** — payment method (**Bank Transfer**, **Cash**, **Cheque**, or **Other**), bank account, payment date.
- **Signed Agreement** — attach the signed document.
- **Opening Entry** — leave this as **No** for a normal, new investment. Only set it to **Yes** if you're entering a share position that existed *before* this system went live (a migrated/imported starting balance). See the callout below.

The **Total Consideration** and **Share Premium Amount** fields calculate themselves — you don't need to fill those in.

> **About Opening Entry:** if you're recording history from before go-live, the money for that investment was already accounted for in your books' opening balances — you don't want the system to post it *again* as a fresh Journal Entry. Setting Opening Entry to "Yes" tells the system to skip the accounting entry (Step 4 below) while still recording the shares themselves so they count correctly toward that shareholder's holdings.

### Step 2 — Submit the agreement
Use the standard **Submit** button. The Status field will still show "Draft" right after submitting — that's expected, it only updates once you complete Step 3.

### Step 3 — Issue the shares
On the submitted agreement, click **Actions → Issue Shares**. This:
- Creates a linked **Share Movement** record for this investor.
- Updates the agreement's status to "Shares Issued."
- Takes you straight to the new Share Movement — Step 4 continues there.

The Share Movement opens as a **Draft**. A banner on the form reminds you it doesn't affect your books yet — you still need to submit it, and this is the moment to check the details are correct before you do.

### Step 4 — Submit the Share Movement, then record the payment
**Submit** the Share Movement first. Once submitted, use the **Create Journal Entry** button — this posts the accounting entry (money coming into the bank account, and Share Capital, plus Share Premium if the shares were priced above par, increasing on the books) and links the entry back to the Share Movement. A banner reminds you this step is still outstanding until you do it.

**If this is an Opening Entry, you won't see the Create Journal Entry button** — that's correct, not a fault. No Journal Entry is needed since the balance is already in your books; submitting the Share Movement is still required so the shares count toward the shareholder's holdings.

### If you need to cancel
Use **Cancel Agreement** (found under Actions on a submitted agreement). This automatically cancels the linked Share Movement and Journal Entry for you — you don't need to cancel each one by hand. Once cancelled, a **Delete Agreement** button appears if you need to remove it completely.

---

## 6. Recording an investor loan that converts to shares (Convertible Loan Note)

Use this when an investor is lending the company money now, with the expectation that the loan converts into shares later — usually at the next funding round — rather than being repaid in cash.

### Step 1 — Create the Convertible Loan Note
Go to **Convertible Loan Note List → New** and fill in:

- **Issue Date**, **Lender** (the Shareholder record for whoever is lending), **Maturity Date**.
- **Lender Type** — **Individual**, **Company**, **Fund**, or **Other**.
- **Principal Amount** — how much is being lent.
- **Interest Rate** (annual %).
- **Interest Calculation Method** — **Simple** (interest calculated only on the original principal) or **Compound** (interest calculated on principal plus previously accrued interest, compounding over time).
- **Interest Payment Frequency** — how often interest is meant to be accrued: **Monthly**, **Quarterly**, **Annually**, **At Maturity** (all at once when the loan is due), or **Capitalized** (interest is added to the principal rather than paid out separately).
- **Loan Currency** — and **Exchange Rate**, which appears and fills in automatically only if this differs from the company's default currency.
- **Conversion Trigger** — what causes this loan to convert into shares:
  - **At Maturity** — converts automatically when the loan's maturity date is reached.
  - **Qualified Financing Round** — converts when the company raises a new round above a set threshold (see Qualified Financing Threshold).
  - **Optional** — conversion happens whenever the lender or company chooses to trigger it.
  - **Automatic on Event** — converts on some other defined triggering event (e.g. an acquisition).
- **Conversion Discount Rate** — a discount the lender gets on the share price at conversion, compared to what new investors pay in that round (rewards them for lending early).
- **Valuation Cap** — the maximum company valuation used to work out the lender's conversion price, protecting them from converting at too high a price if the company's value has grown a lot.
- **Conversion Share Type** and **Par Value per Share** — what type of share this converts into.
- **Accounting**: Loan Liability Account, Bank Account, Interest Expense/Payable Accounts, and the Share Capital/Premium Accounts that will be used later at conversion.
- **Signed Note Agreement** — attach the signed document.

### Step 2 — Submit the CLN

### Step 3 — Record the disbursement
Once the money has actually gone out to the investor, click **Actions → Record Loan Disbursement**. This posts the accounting entry (money out of the bank, loan liability recorded) and moves the loan's status to **Active**.

### Step 4 — Accrue interest periodically
Whenever it's time to book interest (matching the frequency you chose in Step 1), click **Actions → Accrue Interest**. You'll be asked for the accrual date, and, if the loan is in a foreign currency, an exchange rate (or leave it blank to use the rate already on the loan). This posts the interest accounting entry and adds a row to the loan's **Interest Accruals** table, so you can see the full history on the form.

### Step 5a — Convert to shares
When the conversion trigger is met, click **Actions → Convert to Shares**. You'll be asked for the next funding round's share price and/or the fully diluted share count, depending on which conversion terms apply to this loan. The system then:
- Works out the conversion price (using the discount rate and/or valuation cap, whichever gives the lender the better price).
- Posts the accounting entry that clears the loan liability (and any unpaid interest) into share capital.
- Creates and submits a Share Movement recording the new shares.
- Marks the loan's status as **Converted**.

### Step 5b — Or, repay the loan in cash instead
If the loan is being paid back in cash rather than converting into shares, click **Actions → Record Repayment** instead of converting. You'll be asked for:
- **Repayment Date**.
- **Early Repayment Penalty** — only shown if this loan has "Early Repayment Allowed" checked. Leave it blank if no penalty applies. If you do enter one, this CLN needs an Interest Expense Account set, since that's where the penalty is booked.

This posts the accounting entry clearing the loan liability and any accrued interest, plus the penalty if one applies, out of the bank account, and marks the loan's status as **Repaid**.

### If you need to cancel
Use the standard **Cancel** action. This automatically cancels everything linked to this loan — the resulting Share Movement (if converted), the conversion entry, the repayment entry (if repaid), every interest accrual entry, and the disbursement entry — and updates the lender's totals. You don't need to cancel each one individually. Once cancelled, use **Delete CLN & All Linked Docs** if you need to remove it completely.

---

## 7. Transferring shares between shareholders, or a buyback

Use **Share Transfer** — not Share Agreement — whenever shares are moving between *existing* parties rather than being freshly issued by the company, or when the company is buying its own shares back.

### Step 1 — Create the Share Transfer
Go to **Share Transfer List → New** and fill in:

- **Transfer Type** — **Issue** (brand-new shares, an alternative path to the Share Agreement flow), **Purchase**, or **Transfer** (moving existing shares from one shareholder to another).
- If Transfer Type is **Issue**, also choose **Issue Type**: **Standard** or **Convertible Loan** — this changes which account fields appear on the form, since a convertible-loan-linked issue books to different accounts.
- **From Shareholder** and **To Shareholder**.
- **Number of Shares** and the **rate per share** (in your chosen transaction currency).
- **Receiving Account (Asset)** — the account where the money comes in.
- **Share Capital / Loan Liability Account** — the equity or liability side of the entry.
- **Exchange Rate** — required only if your transaction currency differs from the company's default currency; the system will stop you from saving without one in that case.

The system checks your chosen accounts automatically — they must not be group accounts, must belong to the right company, must match your transaction currency, and must be the correct type (an Asset account for the receiving side, Equity or Liability for the other side). If saving gives you an error, it's almost always one of those four checks — start by checking the account's Company and Currency.

### Step 2 — Submit the Share Transfer

### Step 3 — Record the payment
Use **Create Journal Entry** on the submitted form. This posts the accounting entry for the transfer, with both parties recorded against it.

### If you need to reverse it
Use **Cancel Journal Entry** to cancel the linked entry before cancelling the Share Transfer itself.

### Company buybacks
A company buying back its own shares is recorded as a **Share Movement** (Section 8 explains this Movement Type) rather than a Share Transfer. Create it with Movement Type "Share Buyback," then post the Journal Entry from that Share Movement — it posts the reverse of a normal issuance.

---

## 8. Understanding Share Movement Types

Every Share Movement — whether created automatically from a Share Agreement, a converted loan, or entered directly for a buyback — has a **Movement Type**. Here's what each one means:

| Movement Type | What it means |
|---|---|
| **Equity Capital Injection** | A shareholder has paid the company for brand-new shares. This is what a Share Agreement creates automatically when you click "Issue Shares" (Section 5, Step 3) — the normal outcome of a new investment. |
| **Share Purchase** | A shareholder purchasing shares in a way that isn't tied to a formal Share Agreement — for example, a manually recorded purchase. |
| **Loan Equity Injection** | Shares created by converting a Convertible Loan Note (Section 6, Step 5). The system sets this automatically when you click "Convert to Shares" — you don't need to choose it yourself. |
| **Share Buyback** | The company repurchasing shares from a shareholder, reducing their holding rather than increasing it. The accounting entry runs in reverse compared to the other three types — money goes *out* of the bank, and Share Capital goes *down*. |

You'll only need to choose a Movement Type yourself when recording a buyback directly — the other three are set automatically by the process that creates them.

---

## 9. Checking who owns what — reports

Three places to look, depending on what you need:

### 9.1 Share Transactions Report — the cap table
Go to **Report → Share Transactions Report**. Filter by Company (required), Shareholder, Share Class, date range, and/or Movement Type. Shows a running, cumulative shares-held balance and ownership percentage for every shareholder and share class, combining Share Movements and loan activity — this is a live report, computed fresh every time you run it, so it's always current. This is your main "who owns what, and how has that changed over time" view.

From a Shareholder record, click **View → View Ledger** to jump straight here, pre-filtered to that shareholder.

### 9.2 Shareholder Balance — a snapshot as of a date
Go to **Report → Shareholder Balance**. Filter by Company (required), As On Date (required, defaults to today), Shareholder, and/or Share Class. Shows shares acquired, shares given up, current holding, ownership %, and total investment, as of the date you choose — useful when you need a clean point-in-time summary rather than a full transaction history.

### 9.3 Share Movement Report — tracing the accounting
Go to **Report → Share Movement Report**. Shows the underlying accounting activity (debit/credit accounts, amounts, linked Journal Entries) per shareholder. Use this when you need to trace exactly what accounting entries a transaction produced, rather than to answer "how many shares does someone hold."

### Shareholder totals
Every Shareholder record also shows **Total Shares Held** and **Total Investment** directly on the form, and these update automatically whenever a Share Movement or loan changes. If you ever need to force a recalculation — for example after a bulk data import — use the **Sync Totals** button on the Shareholder form (for one record), or **Sync All Shareholder Totals** at the top of this guide's page in the Desk (for every shareholder at once).

---

## 10. Everything connected to a Shareholder

Open any Shareholder record and look at the **Connections** section (usually shown in the sidebar, or under a "Links" tab depending on your screen size) to see every document tied to them, grouped by relationship:

- **Agreements** — every Share Agreement where they're the investor.
- **Shares Received** / **Shares Given Up** — every Share Movement where they gained or gave up shares (a buyback, for instance, would show under "Given Up").
- **Loans** — every Convertible Loan Note where they're the lender.
- **Transfers Received** / **Transfers Given** — every Share Transfer involving them, in either direction.

This is the fastest way to get a full picture of one shareholder's history without running a report.

---

## 11. Common situations

| What you're seeing | What's going on | What to do |
|---|---|---|
| A Status field (on a Share Agreement, Share Movement, or CLN) won't let you change it | This is intentional — status only changes automatically as a result of the Actions buttons (Issue Shares, Record Disbursement, Convert to Shares, etc.) | Don't try to edit it directly; use the relevant Action button instead |
| "Exchange Rate is required" when saving a Share Transfer | Your transaction currency is different from the company's default currency, and no rate has been entered | Enter an exchange rate before saving |
| An account validation error on Share Transfer | The account you picked is a group account, belongs to the wrong company, doesn't match your transaction currency, or is the wrong account type | Check the account's Company, Currency, and type fields |
| "Create Journal Entry" is missing on a Share Movement | It's an Opening Entry (Section 5) | Expected — no Journal Entry is needed for opening entries |
| One shareholder's Total Shares Held looks negative or clearly wrong | A data setup issue affecting a small number of historical transactions for that shareholder | The totals themselves are calculated correctly from what's recorded — ask whoever administers the system to look into the underlying transactions for that shareholder |
| Both "Convert to Shares" and "Record Repayment" show on a CLN | Expected — an active loan can go either way; use whichever applies and the other disappears once the loan's status changes | Pick the one that matches what's actually happening with this loan |
| The Actions buttons (Issue Shares, Record Disbursement, Convert to Shares, Record Repayment, etc.) don't appear at all | The site may need an update applied | Ask whoever administers the system to check and apply the latest update |
| Don't use **Share Register** or **Bulk Upload** | Both are unfinished placeholders with nothing working behind them | Use the processes and reports described in this guide instead |

---

## 12. Quick reference — where to go for what

| I want to... | Go to... |
|---|---|
| Issue new shares to an investor | Share Agreement List → New (Section 5) |
| Record an investor loan that will convert to shares | Convertible Loan Note List → New (Section 6) |
| Move shares between existing shareholders | Share Transfer List → New (Section 7) |
| Buy back the company's own shares | Share Movement, Movement Type "Share Buyback" (Section 8) |
| See a shareholder's current holdings and history | Report → Share Transactions Report, or View Ledger from their Shareholder record (Section 9.1) |
| See a shareholder's balance as of a specific date | Report → Shareholder Balance (Section 9.2) |
| Trace the accounting behind a transaction | Report → Share Movement Report (Section 9.3) |
| See everything tied to one shareholder | Open the Shareholder record → Connections (Section 10) |
| Force-refresh a shareholder's totals | Sync Totals button on the Shareholder form (Section 9) |
