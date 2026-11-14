# Security and privacy

Rozgaar is intended for a single user on localhost. Do not expose the API or Chrome's remote-debugging port to a public interface, shared network or untrusted proxy. It is not designed as a multi-user hosted service.

`runtime/` can contain resumes, job exports, account-linked browser state and local history. `.archive/` may contain private backups and old checkouts. Both are excluded from source control. Keep backups private, and remove personal data from issue attachments and screenshots.

A browser profile or debug endpoint can grant access to signed-in sessions. Sign-in, verification and application submission remain manual. Site restrictions should stop collection rather than trigger an access bypass.

For a suspected vulnerability, use GitHub private vulnerability reporting if the repository owner has enabled it. Otherwise request a private reporting channel without posting exploit details or sensitive files publicly. No dedicated security response time is promised.
