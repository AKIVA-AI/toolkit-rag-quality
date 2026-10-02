# Security policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 1.0.x   | Yes       |
| < 1.0   | No        |

Security fixes are released as patch versions of the latest minor release.

## Reporting a vulnerability

Please do not report security problems in a public issue, pull request or
discussion. Report them privately through GitHub: open this repository's
**Security** tab and choose **Report a vulnerability**
(<https://github.com/AKIVA-AI/toolkit-rag-quality/security/advisories/new>). Include:

- what the problem is and its impact;
- steps or input files to reproduce it;
- the affected version or commit.

We aim to acknowledge a report within 7 days and ask for up to 90 days to
release a fix before public disclosure. We credit reporters who want to be
credited.

## Guidance

- Treat corpora, queries, and retrieved results as untrusted inputs.
- Run in sandboxed CI when testing untrusted content.

## Known advisories

CI runs `pip-audit` over the package with every optional extra installed. Advisories it ignores are listed here; each is re-checked by the date shown and removed once a fix is available.

| Advisory | Package | Reaches you through | Status | Re-check by |
|---|---|---|---|---|
| CVE-2026-81726 (GHSA-8mgp-746c-j5xp, PYSEC-2026-3740) | `nltk` <= 3.10.3 | `llamaindex` extra: `llama-index-core` requires `nltk` | No fixed `nltk` release exists, and the latest `llama-index-core` (0.14.25) still requires it. Not exploitable through this package: `toolkit_rag_quality` never imports `nltk` or `llama_index`; the adapter only calls `retrieve()` on a retriever you construct. | 2026-11-01 |

CVE-2026-81726 is a path traversal in NLTK's model-artifact loading APIs. If your own code, or LlamaIndex code you call, loads NLTK resources from untrusted paths, follow the upstream advisory and upgrade `nltk` as soon as a fixed release ships. When one does, the `llamaindex` extra will gain a floor pin on it and the ignore will be removed.
