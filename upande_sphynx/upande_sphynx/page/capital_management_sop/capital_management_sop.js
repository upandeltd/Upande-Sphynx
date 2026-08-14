frappe.pages["capital-management-sop"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Capital Management SOP",
		single_column: true,
	});

	page.add_inner_button(__("Sync All Shareholder Totals"), function () {
		frappe.confirm(
			__("Recalculate Total Shares Held and Total Investment for every Shareholder from submitted Share Movements and active loans?"),
			function () {
				frappe.call({
					method: "upande_sphynx.api.capital_management.recompute_shareholder_totals",
					freeze: true,
					freeze_message: __("Syncing Shareholder totals..."),
					callback: function (r) {
						if (!r.exc && r.message) {
							frappe.show_alert({
								message: __("Recalculated totals for {0} Shareholder(s).", [r.message.recalculated]),
								indicator: "green",
							});
						}
					},
				});
			}
		);
	});

	$(page.body).html(upande_sphynx.capital_management_sop.get_html());
};

upande_sphynx.capital_management_sop = {
	get_html: function () {
		return `
<style>
.cms-sop {
	--cms-bg: #eef0ea;
	--cms-surface: #ffffff;
	--cms-surface-sunk: #e4e7de;
	--cms-ink: #1e2b22;
	--cms-ink-muted: #51604f;
	--cms-ink-faint: #7c8a78;
	--cms-accent: #2e6f5e;
	--cms-accent-strong: #1f5245;
	--cms-accent-tint: #dfeae5;
	--cms-warn: #a9741f;
	--cms-warn-tint: #f5ead2;
	--cms-rule: #d3d6c9;
	--cms-shadow: 0 1px 2px rgba(30,43,34,0.06), 0 4px 16px rgba(30,43,34,0.05);
	max-width: 880px;
	margin: 0 auto;
	padding: 0.5rem 0 4rem;
	color: var(--cms-ink);
	line-height: 1.6;
}
html[data-theme="dark"] .cms-sop {
	--cms-bg: #12160f;
	--cms-surface: #1b2118;
	--cms-surface-sunk: #232b1f;
	--cms-ink: #e7ece3;
	--cms-ink-muted: #a8b3a2;
	--cms-ink-faint: #798378;
	--cms-accent: #5fc9a8;
	--cms-accent-strong: #8adcbf;
	--cms-accent-tint: #1f342d;
	--cms-warn: #e0ab45;
	--cms-warn-tint: #362b16;
	--cms-rule: #2c342a;
	--cms-shadow: 0 1px 2px rgba(0,0,0,0.3), 0 4px 20px rgba(0,0,0,0.25);
}
.cms-sop * { box-sizing: border-box; }
.cms-sop h1, .cms-sop h2, .cms-sop h3, .cms-sop h4 {
	font-family: Georgia, "Iowan Old Style", "Palatino Linotype", "Times New Roman", serif;
	color: var(--cms-ink);
	font-weight: 700;
	letter-spacing: -0.01em;
}
.cms-sop code { font-family: ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace; background: var(--cms-surface-sunk); padding: 0.1rem 0.35rem; border-radius: 4px; }
.cms-sop a { color: var(--cms-accent-strong); }
.cms-sop .cms-header { border-bottom: 3px solid var(--cms-ink); padding-bottom: 1.5rem; margin-bottom: 2rem; }
.cms-sop .cms-eyebrow { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--cms-accent-strong); font-weight: 700; margin-bottom: 0.5rem; }
.cms-sop h1.cms-title { font-size: 2rem; margin: 0 0 0.4rem; }
.cms-sop .cms-meta { display: flex; flex-wrap: wrap; gap: 0.3rem 1.2rem; font-size: 0.83rem; color: var(--cms-ink-muted); margin-top: 0.9rem; }
.cms-sop .cms-meta strong { color: var(--cms-ink); }
.cms-sop .cms-nav { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 2.4rem; }
.cms-sop .cms-nav a {
	font-size: 0.8rem; font-weight: 600; text-decoration: none;
	background: var(--cms-surface); border: 1px solid var(--cms-rule); border-radius: 999px;
	padding: 0.4rem 0.9rem; color: var(--cms-ink-muted); box-shadow: var(--cms-shadow);
}
.cms-sop .cms-nav a:hover { color: var(--cms-accent-strong); border-color: var(--cms-accent); }
.cms-sop section { margin-bottom: 2.8rem; scroll-margin-top: 1rem; }
.cms-sop h2 { font-size: 1.4rem; border-bottom: 1px solid var(--cms-rule); padding-bottom: 0.55rem; margin: 0 0 1.1rem; }
.cms-sop h3 { font-size: 1.08rem; margin: 1.6rem 0 0.6rem; color: var(--cms-accent-strong); }
.cms-sop p { max-width: 68ch; }
.cms-sop p.cms-lede { color: var(--cms-ink-muted); max-width: 68ch; }
.cms-sop ul, .cms-sop ol.cms-steps { max-width: 68ch; padding-left: 1.2rem; }
.cms-sop li { margin-bottom: 0.35rem; }
.cms-sop .cms-banner { background: var(--cms-accent-tint); border: 1px solid var(--cms-accent); border-radius: 10px; padding: 1.2rem 1.4rem; margin-bottom: 1.4rem; }
.cms-sop .cms-banner .cms-banner-head { display: flex; align-items: center; gap: 0.55rem; font-weight: 700; color: var(--cms-accent-strong); font-size: 0.88rem; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.4rem; }
.cms-sop .cms-banner .cms-dot { width: 0.5rem; height: 0.5rem; border-radius: 50%; background: var(--cms-accent); flex-shrink: 0; }
.cms-sop .cms-banner p { margin: 0; max-width: none; }
.cms-sop .cms-table-wrap { overflow-x: auto; border: 1px solid var(--cms-rule); border-radius: 10px; background: var(--cms-surface); box-shadow: var(--cms-shadow); }
.cms-sop table { border-collapse: collapse; width: 100%; font-size: 0.86rem; }
.cms-sop th, .cms-sop td { text-align: left; padding: 0.6rem 0.85rem; vertical-align: top; border-bottom: 1px solid var(--cms-rule); }
.cms-sop thead th { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--cms-ink-faint); background: var(--cms-surface-sunk); font-weight: 700; white-space: nowrap; }
.cms-sop tbody tr:last-child td { border-bottom: none; }
.cms-sop tbody tr:hover { background: var(--cms-surface-sunk); }
.cms-sop .cms-issue-id { display: inline-flex; align-items: center; justify-content: center; min-width: 1.5rem; height: 1.5rem; background: var(--cms-warn-tint); color: var(--cms-warn); border-radius: 5px; font-weight: 700; font-size: 0.76rem; }
.cms-sop .cms-callout { border-left: 4px solid var(--cms-accent); background: var(--cms-accent-tint); border-radius: 0 8px 8px 0; padding: 0.85rem 1.05rem; margin: 1rem 0 1.2rem; max-width: 68ch; }
.cms-sop .cms-callout p { margin: 0; max-width: none; }
.cms-sop .cms-callout.cms-warn { border-color: var(--cms-warn); background: var(--cms-warn-tint); }
.cms-sop .cms-callout-label { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem; color: var(--cms-accent-strong); }
.cms-sop .cms-callout.cms-warn .cms-callout-label { color: var(--cms-warn); }
.cms-sop ol.cms-steps { list-style: none; padding-left: 0; counter-reset: cmsstep; }
.cms-sop ol.cms-steps > li { counter-increment: cmsstep; position: relative; padding-left: 2.7rem; padding-bottom: 1.3rem; border-left: 2px solid var(--cms-rule); margin-left: 0.8rem; }
.cms-sop ol.cms-steps > li:last-child { border-left-color: transparent; padding-bottom: 0.1rem; }
.cms-sop ol.cms-steps > li::before {
	content: counter(cmsstep); position: absolute; left: -0.8rem; top: 0;
	width: 1.6rem; height: 1.6rem; background: var(--cms-surface); border: 2px solid var(--cms-accent);
	color: var(--cms-accent-strong); border-radius: 50%; display: flex; align-items: center; justify-content: center;
	font-family: ui-monospace, monospace; font-weight: 700; font-size: 0.8rem;
}
.cms-sop ol.cms-steps h4 { margin: 0 0 0.3rem; font-size: 0.98rem; font-family: inherit; color: var(--cms-ink); }
.cms-sop .cms-setup-card { background: var(--cms-surface); border: 1px solid var(--cms-rule); border-radius: 10px; padding: 1.3rem 1.5rem; box-shadow: var(--cms-shadow); max-width: 68ch; }
.cms-sop .cms-setup-card ol { counter-reset: cmssetup; list-style: none; padding-left: 0; margin: 0; }
.cms-sop .cms-setup-card li { counter-increment: cmssetup; padding-left: 2.1rem; position: relative; margin-bottom: 0.9rem; }
.cms-sop .cms-setup-card li:last-child { margin-bottom: 0; }
.cms-sop .cms-setup-card li::before {
	content: counter(cmssetup); position: absolute; left: 0; top: 0.05rem; font-family: ui-monospace, monospace;
	font-weight: 700; color: var(--cms-accent); font-size: 0.82rem; background: var(--cms-accent-tint);
	width: 1.4rem; height: 1.4rem; border-radius: 5px; display: flex; align-items: center; justify-content: center;
}
.cms-sop .cms-role-row { display: flex; gap: 0.6rem; flex-wrap: wrap; margin: 0.9rem 0 1.3rem; }
.cms-sop .cms-role-badge { background: var(--cms-surface); border: 1px solid var(--cms-rule); border-radius: 999px; padding: 0.4rem 0.9rem; font-size: 0.82rem; font-weight: 600; box-shadow: var(--cms-shadow); display: flex; align-items: center; gap: 0.45rem; }
.cms-sop .cms-swatch { width: 0.55rem; height: 0.55rem; border-radius: 50%; background: var(--cms-accent); }
.cms-sop .cms-report-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; }
.cms-sop .cms-report-card { background: var(--cms-surface); border: 1px solid var(--cms-rule); border-radius: 10px; padding: 1.2rem 1.3rem; box-shadow: var(--cms-shadow); }
.cms-sop .cms-report-card h4 { margin: 0 0 0.25rem; font-size: 0.96rem; }
.cms-sop .cms-report-card .cms-tag { display: inline-block; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.04em; font-weight: 700; color: var(--cms-accent-strong); background: var(--cms-accent-tint); padding: 0.12rem 0.45rem; border-radius: 4px; margin-bottom: 0.5rem; }
.cms-sop .cms-report-card p { font-size: 0.85rem; color: var(--cms-ink-muted); margin: 0.35rem 0 0; max-width: none; }
.cms-sop footer { border-top: 1px solid var(--cms-rule); margin-top: 1.5rem; padding-top: 1.2rem; font-size: 0.8rem; color: var(--cms-ink-faint); }
</style>

<div class="cms-sop">
	<header class="cms-header">
		<p class="cms-eyebrow">Upande Sphynx &middot; User Guide</p>
		<h1 class="cms-title">Capital Management</h1>
		<p class="cms-lede" style="margin-top:0.4rem;">How to issue shares, record investor loans, transfer shares, and check who owns what.</p>
		<div class="cms-meta">
			<span><strong>Who this is for:</strong> Anyone in Accounts who works with shares, loans, or transfers</span>
			<span><strong>Reviewed:</strong> 14 Aug 2026</span>
		</div>
	</header>

	<nav class="cms-nav">
		<a href="#cms-overview">Overview</a>
		<a href="#cms-roles">Who can do this</a>
		<a href="#cms-setup">One-time setup</a>
		<a href="#cms-records">The records you'll use</a>
		<a href="#cms-process-a">Issuing shares</a>
		<a href="#cms-process-b">Convertible Loan Notes</a>
		<a href="#cms-process-c">Transfers &amp; buybacks</a>
		<a href="#cms-movement-types">Movement types</a>
		<a href="#cms-reporting">Reports</a>
		<a href="#cms-connections">Shareholder connections</a>
		<a href="#cms-troubleshooting">Common situations</a>
		<a href="#cms-quickref">Quick reference</a>
	</nav>

	<section id="cms-overview">
		<h2>1 &middot; What Capital Management does</h2>
		<p class="cms-lede">This part of the system keeps track of your company's shares and the money raised for them. It covers four everyday situations:</p>
		<ul>
			<li><strong>A new investor buys shares</strong> &rarr; recorded as a <strong>Share Agreement</strong>, which produces a <strong>Share Movement</strong>.</li>
			<li><strong>An investor lends money that will turn into shares later</strong> &rarr; recorded as a <strong>Convertible Loan Note</strong>.</li>
			<li><strong>Shares move from one existing shareholder to another, or the company buys shares back</strong> &rarr; recorded as a <strong>Share Transfer</strong> (or, for a buyback, a <strong>Share Movement</strong>).</li>
			<li><strong>You need to know who owns what, and how much they've invested</strong> &rarr; answered by the <strong>Shareholder</strong> record and two reports.</li>
		</ul>
		<p>Everything ties back to the <strong>Shareholder</strong> doctype &mdash; opening a Shareholder record shows everything connected to them in one place (Section 10).</p>
	</section>

	<section id="cms-roles">
		<h2>2 &middot; Who can do this</h2>
		<p class="cms-lede">Only two roles can create or edit anything in this area:</p>
		<div class="cms-role-row">
			<span class="cms-role-badge"><span class="cms-swatch"></span>System Manager</span>
			<span class="cms-role-badge"><span class="cms-swatch"></span>Accounts Manager</span>
		</div>
		<p>If someone needs to <em>look</em> at holdings and reports without editing anything &mdash; an investor-relations contact, for example &mdash; ask your System Administrator, since there isn't a lighter "view-only" role for this area today.</p>
		<p>The <a href="#cms-reporting">Share Transactions Report</a> is additionally visible to <strong>Accounts User</strong>.</p>
	</section>

	<section id="cms-setup">
		<h2>3 &middot; Before you start &mdash; one-time setup</h2>
		<p class="cms-lede">Do this once per company, before recording your first transaction. If someone has already set this up, skip to Section 5.</p>
		<div class="cms-setup-card">
			<ol>
				<li><strong>Company</strong> &mdash; make sure the record exists and its default currency is set correctly.</li>
				<li><strong>Chart of Accounts</strong> &mdash; make sure these exist, creating any that are missing: a <strong>Share Capital</strong> account (Equity), a <strong>Share Premium</strong> account (Equity), a <strong>Loan Liability</strong> account (Liability) for convertible notes, <strong>Interest Expense</strong> and <strong>Interest Payable</strong> accounts, and a <strong>Bank Account</strong> with its linked GL account.</li>
				<li><strong>Share Type</strong> &mdash; one record per class of share you issue (e.g. Ordinary Shares, Preference Shares). Share Type List &rarr; New.</li>
				<li><strong>Shareholder record for the company itself.</strong> Used automatically as the counterparty whenever shares are issued. Confirm its name matches what the system expects &mdash; the Convertible Loan Note form, for instance, defaults this to "Sphynx."</li>
				<li><strong>Shareholder record for every investor or lender</strong> &mdash; create this before creating any agreement or loan note for them.</li>
			</ol>
		</div>
	</section>

	<section id="cms-records">
		<h2>4 &middot; The records you'll use</h2>
		<p class="cms-lede">A quick map of what each record is for, before the step-by-step processes below.</p>
		<div class="cms-table-wrap">
			<table>
				<thead><tr><th>Record</th><th>What it's for</th></tr></thead>
				<tbody>
					<tr><td><strong>Shareholder</strong></td><td>One record per person, company, or fund that holds shares or has lent money. Everything else links back to this.</td></tr>
					<tr><td><strong>Share Agreement</strong></td><td>The paperwork for a new share purchase &mdash; who's buying, how many shares, at what price, on what terms. Submitting it and clicking "Issue Shares" creates the Share Movement below.</td></tr>
					<tr><td><strong>Share Movement</strong></td><td>The actual record of shares changing hands. This is what the system counts when working out who owns how many shares.</td></tr>
					<tr><td><strong>Convertible Loan Note</strong></td><td>A loan from an investor designed to convert into shares later, instead of being repaid in cash.</td></tr>
					<tr><td><strong>Share Transfer</strong></td><td>An existing shareholder selling or transferring shares to someone else, rather than the company issuing brand-new shares.</td></tr>
				</tbody>
			</table>
		</div>
	</section>

	<section id="cms-process-a">
		<h2>5 &middot; Issuing new shares to an investor (Share Agreement)</h2>
		<p class="cms-lede">Use this whenever a shareholder is buying shares directly from the company.</p>
		<ol class="cms-steps">
			<li>
				<h4>Create the Share Agreement</h4>
				<p>Share Agreement List &rarr; New. Fill in:</p>
				<ul>
					<li><strong>Agreement Date</strong> (defaults to today), <strong>Shareholder/Investor</strong></li>
					<li><strong>Agreement Type</strong> &mdash; <strong>Subscription Agreement</strong> (investor subscribing for newly issued shares); <strong>Share Purchase Agreement</strong> (a straightforward purchase for cash); <strong>Secondary Transfer Agreement</strong> (documents an existing shareholder's shares being sold on &mdash; the actual transfer still goes through Share Transfer, Section 7); <strong>Shareholders Agreement</strong> (broader governance terms, not tied to one purchase); <strong>Vesting Agreement</strong> (shares vesting over time, typically for founders/employees).</li>
					<li>Share Class/Type, Number of Shares, Price per Share, Par Value per Share</li>
					<li>Transaction Currency, and Exchange Rate (only appears, and fills in automatically, if this currency differs from the company default)</li>
					<li>Share Capital Account and Share Premium Account</li>
					<li>Terms (optional): vesting, lock-in, voting/dividend rights, board seats, drag/tag-along, plus two worth knowing in detail:
						<ul>
							<li><strong>Liquidation Preference</strong> &mdash; who gets paid first if the company is sold or wound up: <strong>None</strong>; <strong>1x Non-Participating</strong> (investment back, then shares the rest normally); <strong>1x Participating</strong> (investment back <em>and</em> still shares the rest); <strong>2x Non-Participating</strong> (twice their investment back first).</li>
							<li><strong>Anti-Dilution Protection</strong> &mdash; protects this investor if shares are later issued at a lower price: <strong>None</strong>; <strong>Full Ratchet</strong> (fully adjusts their price down to the new lower price); <strong>Weighted Average</strong> (a milder, proportional adjustment).</li>
						</ul>
					</li>
					<li>Payment method (Bank Transfer / Cash / Cheque / Other), bank account, payment date, and the signed agreement attachment</li>
					<li><strong>Opening Entry</strong> &mdash; leave "No" for a normal transaction. Set "Yes" only for a share position migrated from before go-live.</li>
				</ul>
				<p><em>Total Consideration</em> and <em>Share Premium Amount</em> calculate automatically.</p>
			</li>
			<li>
				<h4>Submit the agreement</h4>
				<p>Standard Submit action. Status will still read "Draft" until the next step runs &mdash; that's expected.</p>
			</li>
			<li>
				<h4>Issue the shares</h4>
				<p>Click <strong>Actions &rarr; Issue Shares</strong>. This creates a linked <strong>Share Movement</strong>, sets the agreement's status to "Shares Issued," and takes you straight to the new Share Movement. It opens as a <strong>Draft</strong> &mdash; a banner on the form reminds you it doesn't affect your books yet.</p>
			</li>
			<li>
				<h4>Submit the Share Movement, then record the payment</h4>
				<p>Submit the Share Movement first, then use <strong>Create Journal Entry</strong> to post the accounting entry. A banner reminds you this step is outstanding until you do it. <strong>Unavailable for Opening Entries</strong> &mdash; no Journal Entry is needed, but submitting the Share Movement is still required so the shares count toward the shareholder's holdings.</p>
			</li>
		</ol>
		<div class="cms-callout">
			<div class="cms-callout-label">If you need to cancel</div>
			<p>Use <strong>Cancel Agreement</strong> (Actions menu) on a submitted agreement &mdash; it cascades automatically, cancelling the linked Share Movement and Journal Entry. Once cancelled, a <strong>Delete Agreement</strong> button appears if you need to remove it entirely.</p>
		</div>
	</section>

	<section id="cms-process-b">
		<h2>6 &middot; Recording an investor loan that converts to shares (CLN)</h2>
		<p class="cms-lede">Use this when an investor lends money now, expecting it to convert into shares later &mdash; usually at the next funding round &mdash; rather than being repaid in cash.</p>
		<ol class="cms-steps">
			<li>
				<h4>Create the Convertible Loan Note</h4>
				<p>Convertible Loan Note List &rarr; New. Fill in:</p>
				<ul>
					<li>Issue Date, Lender, Maturity Date</li>
					<li><strong>Lender Type</strong> &mdash; Individual, Company, Fund, or Other</li>
					<li>Principal Amount, Interest Rate</li>
					<li><strong>Interest Calculation Method</strong> &mdash; <strong>Simple</strong> (interest only on the original principal) or <strong>Compound</strong> (interest on principal plus previously accrued interest)</li>
					<li><strong>Interest Payment Frequency</strong> &mdash; Monthly, Quarterly, Annually, <strong>At Maturity</strong> (all at once when due), or <strong>Capitalized</strong> (added to principal rather than paid separately)</li>
					<li>Loan Currency, and Exchange Rate (only appears, and fills in automatically, if different from the company default)</li>
					<li><strong>Conversion Trigger</strong> &mdash; <strong>At Maturity</strong> (converts automatically at the maturity date); <strong>Qualified Financing Round</strong> (converts when a new funding round above a set threshold happens); <strong>Optional</strong> (triggered whenever the lender or company chooses); <strong>Automatic on Event</strong> (some other defined event, e.g. an acquisition)</li>
					<li>Conversion Discount Rate (a price discount rewarding the lender for lending early), Valuation Cap (a maximum company valuation used for the conversion price, protecting the lender if the company's value has grown a lot), Conversion Share Type, Par Value per Share</li>
					<li>Loan Liability Account, Bank Account, Interest Expense/Payable Accounts, Share Capital/Premium Accounts (needed later at conversion), signed note attachment</li>
				</ul>
			</li>
			<li><h4>Submit the CLN</h4></li>
			<li>
				<h4>Record the disbursement</h4>
				<p>Once the money has gone out, click <strong>Actions &rarr; Record Loan Disbursement</strong>. Posts the accounting entry and moves the loan to "Active."</p>
			</li>
			<li>
				<h4>Accrue interest periodically</h4>
				<p>Click <strong>Actions &rarr; Accrue Interest</strong> (matching the frequency you chose), entering the accrual date and, for a foreign-currency loan, an exchange rate if you want to override the one already on the loan. Adds a row to the loan's Interest Accruals table.</p>
			</li>
			<li>
				<h4>Convert to shares &mdash; or, repay in cash instead</h4>
				<p><strong>To convert:</strong> when the trigger is met, click <strong>Actions &rarr; Convert to Shares</strong> with the next round's price and/or fully diluted share count. This works out the conversion price (whichever gives the lender the better deal between the discount and the valuation cap), clears the loan into share capital, creates a Share Movement, and marks the loan "Converted."</p>
				<p><strong>To repay in cash instead:</strong> click <strong>Actions &rarr; Record Repayment</strong>, giving a repayment date and, only if this loan has "Early Repayment Allowed" checked, an optional penalty amount (needs an Interest Expense Account set on the loan). This clears the loan liability and any accrued interest, plus the penalty if one applies, out of the bank account, and marks the loan "Repaid."</p>
			</li>
		</ol>
		<div class="cms-callout">
			<div class="cms-callout-label">If you need to cancel</div>
			<p>Standard Cancel action &mdash; cascades automatically, cancelling the resulting Share Movement, the conversion entry, the repayment entry, every interest accrual entry, and the disbursement entry, and updating the lender's totals. Once cancelled, use <strong>Delete CLN &amp; All Linked Docs</strong> to remove it entirely.</p>
		</div>
	</section>

	<section id="cms-process-c">
		<h2>7 &middot; Transferring shares between shareholders, or a buyback</h2>
		<p class="cms-lede">Use <strong>Share Transfer</strong> &mdash; not Share Agreement &mdash; whenever shares are moving between existing parties, or when the company is buying its own shares back.</p>
		<ol class="cms-steps">
			<li>
				<h4>Create the Share Transfer</h4>
				<p>Share Transfer List &rarr; New. <strong>Transfer Type</strong>: <strong>Issue</strong> (new shares, an alternative to the Share Agreement flow), <strong>Purchase</strong>, or <strong>Transfer</strong> (moving existing shares between shareholders). If Issue, also choose <strong>Issue Type</strong> &mdash; Standard or Convertible Loan &mdash; which changes the account fields shown.</p>
				<p>Enter From/To Shareholder, Number of Shares, rate per share, the <strong>Receiving Account (Asset)</strong> for incoming funds, and the <strong>Share Capital / Loan Liability Account</strong> for the equity/liability side. An exchange rate is required if your transaction currency differs from the company currency.</p>
				<p>The system checks your accounts automatically &mdash; not a group account, right company, matching currency, correct account type. A validation error is almost always one of those four.</p>
			</li>
			<li><h4>Submit the Share Transfer</h4></li>
			<li>
				<h4>Record the payment</h4>
				<p>Use <strong>Create Journal Entry</strong> on the submitted form.</p>
			</li>
		</ol>
		<div class="cms-callout">
			<div class="cms-callout-label">If you need to reverse it</div>
			<p>Use <strong>Cancel Journal Entry</strong> to cancel the linked entry before cancelling the Share Transfer itself.</p>
		</div>
		<div class="cms-callout">
			<div class="cms-callout-label">Company buybacks</div>
			<p>Recorded as a <strong>Share Movement</strong> (Section 8) with Movement Type "Share Buyback," rather than a Share Transfer. Post the Journal Entry from that Share Movement &mdash; it posts the reverse of a normal issuance.</p>
		</div>
	</section>

	<section id="cms-movement-types">
		<h2>8 &middot; Understanding Share Movement types</h2>
		<p class="cms-lede">Every Share Movement has a Movement Type. Here's what each one means &mdash; you'll only need to choose one yourself when recording a buyback directly; the other three are set automatically by whatever process creates them.</p>
		<div class="cms-table-wrap">
			<table>
				<thead><tr><th>Movement Type</th><th>What it means</th></tr></thead>
				<tbody>
					<tr><td><strong>Equity Capital Injection</strong></td><td>A shareholder has paid the company for brand-new shares. Created automatically when you click "Issue Shares" on a Share Agreement (Section 5) &mdash; the normal outcome of a new investment.</td></tr>
					<tr><td><strong>Share Purchase</strong></td><td>A shareholder purchasing shares in a way that isn't tied to a formal Share Agreement &mdash; for example, a manually recorded purchase.</td></tr>
					<tr><td><strong>Loan Equity Injection</strong></td><td>Shares created by converting a Convertible Loan Note (Section 6). Set automatically when you click "Convert to Shares."</td></tr>
					<tr><td><strong>Share Buyback</strong></td><td>The company repurchasing shares from a shareholder, reducing their holding. The accounting runs in reverse compared to the other three &mdash; money goes <em>out</em> of the bank, and Share Capital goes <em>down</em>.</td></tr>
				</tbody>
			</table>
		</div>
	</section>

	<section id="cms-reporting">
		<h2>9 &middot; Checking who owns what &mdash; reports</h2>
		<p class="cms-lede">Three places to look, depending on what you need.</p>
		<div class="cms-report-grid">
			<div class="cms-report-card">
				<span class="cms-tag">The cap table</span>
				<h4>Share Transactions Report</h4>
				<p>Filter by Company (required), Shareholder, Share Class, date range, Movement Type. Shows a running, cumulative shares-held balance and ownership percentage &mdash; computed fresh every time you run it, always current.</p>
				<p>From a Shareholder record, click <strong>View &rarr; View Ledger</strong> to jump here pre-filtered.</p>
			</div>
			<div class="cms-report-card">
				<span class="cms-tag">Snapshot as of a date</span>
				<h4>Shareholder Balance</h4>
				<p>Filter by Company (required), As On Date (required, defaults today), Shareholder, Share Class. Shows shares acquired, shares given up, current holding, ownership %, and total investment as of the date you choose.</p>
			</div>
			<div class="cms-report-card">
				<span class="cms-tag">Trace the accounting</span>
				<h4>Share Movement Report</h4>
				<p>Shows the underlying accounting activity per shareholder &mdash; debit/credit accounts, amounts, linked Journal Entries. Use this to trace what accounting entries a transaction produced, not to answer "how many shares does someone hold."</p>
			</div>
		</div>
		<p style="margin-top:1.1rem;">Every Shareholder record also shows <strong>Total Shares Held</strong> and <strong>Total Investment</strong> directly on the form, updated automatically. Force a recalculation with the <strong>Sync Totals</strong> button on a Shareholder form, or <strong>Sync All Shareholder Totals</strong> at the top of this page &mdash; useful after a bulk import.</p>
	</section>

	<section id="cms-connections">
		<h2>10 &middot; Everything connected to a Shareholder</h2>
		<p class="cms-lede">Open any Shareholder record and look at the <strong>Connections</strong> section (sidebar, or a "Links" tab depending on your screen) to see every document tied to them, grouped by relationship:</p>
		<ul>
			<li><strong>Agreements</strong> &mdash; every Share Agreement where they're the investor.</li>
			<li><strong>Shares Received</strong> / <strong>Shares Given Up</strong> &mdash; every Share Movement where they gained or gave up shares (a buyback would show under "Given Up").</li>
			<li><strong>Loans</strong> &mdash; every Convertible Loan Note where they're the lender.</li>
			<li><strong>Transfers Received</strong> / <strong>Transfers Given</strong> &mdash; every Share Transfer involving them, either direction.</li>
		</ul>
		<p>This is the fastest way to get a full picture of one shareholder's history without running a report.</p>
	</section>

	<section id="cms-troubleshooting">
		<h2>11 &middot; Common situations</h2>
		<div class="cms-table-wrap">
			<table>
				<thead><tr><th>What you're seeing</th><th>What's going on</th><th>What to do</th></tr></thead>
				<tbody>
					<tr><td>A Status field won't let you change it</td><td>Intentional &mdash; status only changes as a result of the Actions buttons</td><td>Don't edit it directly; use the relevant Action button instead</td></tr>
					<tr><td>"Exchange Rate is required" on Share Transfer</td><td>Transaction currency differs from company default, no rate entered</td><td>Enter an exchange rate before saving</td></tr>
					<tr><td>Account validation error on Share Transfer</td><td>Account is a group, wrong company, wrong currency, or wrong type</td><td>Check the account's Company, Currency, and type</td></tr>
					<tr><td>"Create Journal Entry" is missing on a Share Movement</td><td>It's an Opening Entry (Section 5)</td><td>Expected &mdash; no Journal Entry needed for opening entries</td></tr>
					<tr><td>One shareholder's Total Shares Held looks negative or clearly wrong</td><td>A data setup issue affecting a small number of historical transactions</td><td>The totals are calculated correctly from what's recorded; ask whoever administers the system to look into that shareholder's transactions</td></tr>
					<tr><td>Both "Convert to Shares" and "Record Repayment" show on a CLN</td><td>Expected &mdash; an active loan can go either way; use whichever applies and the other disappears once status changes</td><td>Pick the one that matches what's actually happening with this loan</td></tr>
					<tr><td>The Actions buttons don't appear at all</td><td>The site may need an update applied</td><td>Ask whoever administers the system to check and apply the latest update</td></tr>
					<tr><td>Don't use Share Register or Bulk Upload</td><td>Both are unfinished placeholders</td><td>Use the processes and reports in this guide instead</td></tr>
				</tbody>
			</table>
		</div>
	</section>

	<section id="cms-quickref">
		<h2>12 &middot; Quick reference</h2>
		<div class="cms-table-wrap">
			<table>
				<thead><tr><th>I want to&hellip;</th><th>Go to&hellip;</th></tr></thead>
				<tbody>
					<tr><td>Issue new shares to an investor</td><td>Share Agreement List &rarr; New (Section 5)</td></tr>
					<tr><td>Record an investor loan that will convert to shares</td><td>Convertible Loan Note List &rarr; New (Section 6)</td></tr>
					<tr><td>Move shares between existing shareholders</td><td>Share Transfer List &rarr; New (Section 7)</td></tr>
					<tr><td>Buy back the company's own shares</td><td>Share Movement, Movement Type "Share Buyback" (Section 8)</td></tr>
					<tr><td>See a shareholder's current holdings and history</td><td>Share Transactions Report, or View Ledger from their Shareholder record (Section 9)</td></tr>
					<tr><td>See a shareholder's balance as of a specific date</td><td>Shareholder Balance report (Section 9)</td></tr>
					<tr><td>Trace the accounting behind a transaction</td><td>Share Movement Report (Section 9)</td></tr>
					<tr><td>See everything tied to one shareholder</td><td>Open the Shareholder record &rarr; Connections (Section 10)</td></tr>
					<tr><td>Force-refresh a shareholder's totals</td><td>Sync Totals button on the Shareholder form (Section 9)</td></tr>
				</tbody>
			</table>
		</div>
	</section>

	<footer>
		Source of truth: <code>docs/CAPITAL_MANAGEMENT_SOP.md</code> in the upande_sphynx repository. Update that file first when the process changes, then refresh this page.
	</footer>
</div>
`;
	},
};
