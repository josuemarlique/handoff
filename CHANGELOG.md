# Changelog

## 1.0.0 — 2026-03-16

### Added
- Initial release
- **Generate mode**: creates structured handoff documents with YAML frontmatter
- **Resume mode**: loads and verifies previous handoffs with drift detection
- **Flags**: `--compact`, `--reason`, `--interactive`, `--note`, `--no-prompt`, `--no-memory`, `--no-priority`
- **Freshness check**: POSIX-compatible shell script with GNU/BSD cross-platform support
- **Sentiment detection**: scans conversation history for friction signals, repeated errors, abandoned approaches
- **Memory integration**: updates Claude's project memory system for ambient cross-session awareness
- **Dual formatting**: full mode (default, no token restrictions) and compact mode (token-conscious)
- **Example outputs**: full and compact format samples in `skills/handoff/examples/`
