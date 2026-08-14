# Security

The supplied Compose profile and README command bind the API to `127.0.0.1`.
Put an authenticated gateway in front of it if remote clients need access. Do
not publish port 8000 directly to an untrusted network. Set `API_KEY` to enable
vLLM's built-in bearer-token authentication.

## CVE-2026-48746 backport

The pinned Intel base contains a vLLM revision older than 0.22.0 and is
therefore version-matched by scanners to CVE-2026-48746, an API-key
authentication bypass. This image backports the complete two-line upstream fix
from vLLM pull request 43426: authentication reads the ASGI scope path directly
instead of reconstructing it through a caller-controlled `Host` header.

`test_auth_backport.py` verifies that the vulnerable reconstruction is absent,
then exercises ordinary and malicious-Host unauthenticated requests. Both must
return HTTP 401 when vLLM's built-in API key is configured. Version-only
scanners may continue to report the CVE because the package version is
unchanged.

## Scan scope

The public source and release image contain no model checkpoint, credentials,
private endpoints, personal paths, prompts, request logs, or private deployment
identifiers. Release 0.1.4 pins Ubuntu's fixed `linux-libc-dev`
6.8.0-137.137 package on top of the Intel base. A Trivy 0.73.0 scan of the clean
release candidate on 2026-08-13 found zero secrets, two critical matches, and
68 high matches. Both critical matches are duplicate version-based detections
of CVE-2026-48746; the backport and exploit regression test are documented
above. The image still contains inherited packages with published high-severity
advisories. Keep the endpoint private, review current scan output, and rebase
onto a newer Intel image after the Glimmer/XPU patch set has been revalidated.

Report a suspected vulnerability through GitHub private vulnerability
reporting. Do not include real API keys, prompts, model data, or private network
details in a public issue.
