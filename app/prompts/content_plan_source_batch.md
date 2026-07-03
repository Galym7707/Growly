You are compressing public market evidence for a content plan.

Use only the supplied source items. Do not invent facts, metrics, quotes, or
platform analytics. Return valid JSON only with these keys:
summary, top_topics, top_pains, top_content_gaps, content_ideas, evidence_urls.

Keep each list concise. evidence_urls must contain only supplied URLs.
Write every user-facing value in the language named by the "language" context
field: "ru" means Russian, "en" means English, "kk" means Kazakh. This
overrides the language of the source snippets - translate findings instead of
copying their language. When the field is missing or empty, use Russian.

Context:
{context_json}
