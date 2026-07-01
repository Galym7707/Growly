# Polar billing

Growly uses Polar for SaaS checkout, webhook processing, subscription status, and the customer portal.

## Environment variables

Set these in local development and in Vercel project environment variables. Do not commit real values.

```env
NEXT_PUBLIC_APP_URL=
POLAR_ACCESS_TOKEN=
POLAR_WEBHOOK_SECRET=
POLAR_SERVER=sandbox
POLAR_SUCCESS_URL=
POLAR_CANCEL_URL=
POLAR_STARTER_PRODUCT_ID=
POLAR_PRO_PRODUCT_ID=
POLAR_AGENCY_PRODUCT_ID=
POLAR_VIDEO_CREDITS_10_PRODUCT_ID=
POLAR_VIDEO_CREDITS_30_PRODUCT_ID=
POLAR_VIDEO_CREDITS_100_PRODUCT_ID=
```

`POLAR_SERVER` should be `sandbox` for test checkout and `production` for live checkout.

## Video credits (pay-per-video AI generation)

Growly offers two AI-video providers in the draft media generator: **Blotato**
(template-based, no per-video charge) and **Replicate** (pay-per-video). To use
Replicate, a user spends **video credits** bought through Polar.

Flow:

1. The user buys a credit pack on `/settings/billing#credits`. Each pack is a
   one-time Polar product mapped by `POLAR_VIDEO_CREDITS_*_PRODUCT_ID`.
2. On `order.paid`, `/api/webhooks/polar` grants the credits to the buyer's
   balance in the `video_credits` table (keyed on the workspace id, which equals
   the Supabase user id). Credits are granted once — only on `order.paid`.
3. When the user generates a Replicate video, the backend reserves one credit
   (atomically) before starting the job, so a user with no credits cannot
   generate. The credit is kept when the video is delivered and **refunded once**
   if Replicate ultimately fails (tracked in `video_generations`).

The Replicate provider itself is configured on the backend with
`REPLICATE_ENABLED`, `REPLICATE_API_TOKEN`, and `REPLICATE_VIDEO_MODEL`
(swap the model without code changes). See `.env.example`.

## Manual setup in Polar

1. Create three recurring products in Polar sandbox: Starter, Pro, and Agency.
2. Copy the product IDs into `POLAR_STARTER_PRODUCT_ID`, `POLAR_PRO_PRODUCT_ID`, and `POLAR_AGENCY_PRODUCT_ID`.
3. Create an organization access token and set `POLAR_ACCESS_TOKEN`.
4. Add the webhook endpoint:

```text
https://YOUR_APP_DOMAIN/api/webhooks/polar
```

5. Subscribe the webhook to checkout, order, and subscription events.
6. Copy the webhook signing secret into `POLAR_WEBHOOK_SECRET`.

## Manual checkout test

1. Run database migrations so `subscriptions`, `payments`, `billing_events`, `video_credits`, and `video_generations` exist.
2. Start the app in local development.
3. Sign in to Growly.
4. Open `/settings/billing` or the public landing pricing section.
5. Click Starter, Pro, or Agency.
6. Confirm the app redirects to Polar checkout.
7. Complete the sandbox checkout.
8. Return to `/settings/billing`.
9. Check that the plan and subscription status are shown.

If a product ID is missing, paid checkout buttons should show `Payment is not configured yet.` instead of opening checkout.

## Manual webhook test

1. Complete a sandbox checkout or replay a Polar webhook event from the Polar dashboard.
2. Confirm `/api/webhooks/polar` returns a successful response.
3. Check `billing_events` for the raw event and processed status.
4. Check `subscriptions` for the user plan, status, Polar customer ID, and Polar subscription ID.
5. Check `payments` for Polar order events.
6. Replay the same event and confirm duplicate processing does not create duplicate rows.

## Useful Polar docs

- Next.js integration: https://polar.sh/docs/guides/nextjs
- Checkout sessions: https://polar.sh/docs/features/checkout/session
- Customer portal: https://polar.sh/docs/features/customer-portal/introduction
- API overview: https://polar.sh/docs/api-reference/introduction
