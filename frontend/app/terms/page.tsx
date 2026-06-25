import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="legal-page">
      <Link className="text-link" href="/">
        Back to Growly
      </Link>
      <h1>Terms of Service</h1>
      <p>Last updated: June 25, 2026.</p>
      <p>
        These terms describe the basic rules for using Growly as a marketing
        workspace for research, planning, drafts, publishing workflows, and
        reporting.
      </p>

      <h2>Accounts</h2>
      <p>
        You are responsible for access to your account and for the workspace
        content, source links, drafts, and connected services you add.
      </p>

      <h2>Subscriptions</h2>
      <p>
        Paid plans are handled through Polar checkout and the Polar customer
        portal. Plan access can change when a subscription is canceled, past due,
        or revoked.
      </p>

      <h2>Generated content</h2>
      <p>
        Growly helps prepare marketing material, but your team is responsible for
        reviewing content before it is approved, exported, scheduled, or
        published.
      </p>

      <h2>Service changes</h2>
      <p>
        Growly may update product features, pricing, plan limits, or integrations
        as the service develops.
      </p>
    </main>
  );
}
