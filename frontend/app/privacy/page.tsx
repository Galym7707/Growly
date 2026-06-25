import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="legal-page">
      <Link className="text-link" href="/">
        Back to Growly
      </Link>
      <h1>Privacy Policy</h1>
      <p>Last updated: June 25, 2026.</p>
      <p>
        This page describes how Growly handles account, workspace, billing, and
        content data used by the service.
      </p>

      <h2>Data we process</h2>
      <ul>
        <li>Account details such as email address and authentication metadata.</li>
        <li>Workspace settings, connected source links, drafts, tasks, and reports.</li>
        <li>Billing identifiers and payment event metadata received from Polar.</li>
      </ul>

      <h2>How we use data</h2>
      <p>
        We use data to run the product, prepare marketing workflows, maintain
        subscription access, diagnose errors, and protect the service.
      </p>

      <h2>Billing</h2>
      <p>
        Payments are processed by Polar. Growly stores subscription and order
        identifiers so the app can show plan status and unlock paid features.
      </p>

      <h2>Contact</h2>
      <p>
        For privacy questions, contact the Growly team through the support
        channel listed in your workspace.
      </p>
    </main>
  );
}
