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
identifiers. The pinned Intel base contains operating-system and language
packages with published advisories. The 2026-08-13 Trivy scan reported 18
critical and 228 high matches: 16 critical matches were in the
`linux-libc-dev` header package, and two were the version-matched vLLM
authentication CVE whose backport is documented and regression-tested above.
Containers use the host kernel rather than running a kernel from that header
package, but this does not make every inherited finding irrelevant. Keep the
endpoint private, review current scan output, and rebase onto a newer Intel
image after the Glimmer/XPU patch set has been revalidated there.

Report a suspected vulnerability through GitHub private vulnerability
reporting. Do not include real API keys, prompts, model data, or private network
details in a public issue.
