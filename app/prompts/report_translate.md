Translate the report payload to the target language.

Context JSON:
{context_json}

Rules:
- Return JSON only. Do not wrap it in Markdown.
- Keep the exact top-level shape:
  {
    "title": string | null,
    "body": string | null,
    "summary": string | null,
    "query": string | null,
    "structure": object,
    "recommendations": array
  }
- Translate user-facing prose in title, body, summary, query, structure, and recommendations.
- Preserve URLs, source names, IDs, usernames, emails, dates, prices, numeric metrics, percentages, and platform names exactly.
- Preserve object keys exactly. Translate values only.
- Preserve array lengths and item order.
- If a value is null, empty, a URL, or a non-text scalar, return it unchanged.
- Do not add claims, sources, metrics, competitors, or recommendations.
