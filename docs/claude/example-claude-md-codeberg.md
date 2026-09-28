# Example: Codeberg-auth section of `~/.claude/CLAUDE.md`

> ⚠️ **Not needed for ConductionNL work.** ConductionNL lives on GitHub, so this section does not belong in your `~/.claude/CLAUDE.md` unless you work on a non-Conduction repo hosted on Forgejo. If it is still there from the 2026 Codeberg period, shrink it to one line. For example: "Codeberg is not used; `keychain` autoload is commented out in `~/.bashrc`, re-enable only for a Forgejo-hosted repo." A stale section makes Claude source a dead keychain agent before every `git` call. See the [Codeberg guide's banner](./codeberg-auth-setup.md).

A ready-to-copy template for the per-user Codeberg-auth facts that belong in your **global** Claude memory (`~/.claude/CLAUDE.md`), as described in the [routing rule](./codeberg-auth-setup.md#save-your-codeberg-setup-facts-to-claude-memory) of the canonical setup guide.

Copy the block below into your `~/.claude/CLAUDE.md`. Adjust the username and email placeholders. The canonical doc reference at the top of the snippet tells future Claude sessions where the long-form troubleshooting lives, so memory entries stay short.

````markdown
## Codeberg authentication

Canonical doc: `~/.github/docs/claude/codeberg-auth-setup.md` (also at
<https://github.com/ConductionNL/.github/blob/main/docs/claude/codeberg-auth-setup.md>).
Read it before guessing — do not investigate auth state from scratch.

- **SSH key:** `~/.ssh/id_ed25519_codeberg` (ED25519, passphrase-protected). Not `id_rsa` / `id_ed25519`.
- **`tea` CLI** login name: `codeberg`. Token in `~/.config/tea/config.yml`.

Unlock the key for the WSL session (run in a fresh terminal):

```bash
keychain ~/.ssh/id_ed25519_codeberg
```

In-session recovery when Claude's `SSH_AUTH_SOCK` points at a dead agent
(see Edge case 1 in the canonical doc). Source the keychain env into each
Bash call instead of restarting Claude:

```bash
. ~/.keychain/$(hostname)-sh && git <command>
```

Verify:

```bash
ssh-add -l                  # expect: 256 SHA256:... <your-email> (ED25519)
ssh -T git@codeberg.org     # expect: "Hi there, <YourCodebergUsername>!"
```
````

## See also

- [Codeberg Authentication Setup](./codeberg-auth-setup.md) — full setup walkthrough, edge cases, and troubleshooting table.
