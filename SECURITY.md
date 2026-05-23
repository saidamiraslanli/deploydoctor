# Security Policy

## Reporting a Vulnerability

If you find a security issue in DeployDoctor, please do not open a public issue.

Use GitHub's private vulnerability reporting feature if available.

Please include:

- affected version
- operating system
- command used
- expected behavior
- actual behavior
- relevant logs or output

## Scope

DeployDoctor is a local and remote diagnostic CLI. Security-sensitive areas include:

- subprocess handling
- command execution
- log reading
- network requests
- SSL/TLS inspection
- handling of user-provided domains

DeployDoctor does not intentionally collect telemetry or send diagnostic results to third-party services.
