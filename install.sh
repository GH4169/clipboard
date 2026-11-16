#!/usr/bin/env bash
set -euo pipefail
root_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"
if [[ -e "$HOME/.local/bin/clipboard-history" && "$(readlink -f "$HOME/.local/bin/clipboard-history")" != "$root_dir/bin/clipboard-history" ]];then
 printf 'An unrelated clipboard-history launcher already exists; preserve it and choose a different name.\n' >&2;exit 1
fi
ln -sfn "$root_dir/bin/clipboard-history" "$HOME/.local/bin/clipboard-history"
install -m 0644 "$root_dir/clipboard-history.service" "$HOME/.config/systemd/user/clipboard-history.service"
systemctl --user daemon-reload
systemctl --user enable clipboard-history.service
# An existing owner and its in-memory history are preserved until the next
# desktop/session start; running a second owner exits without taking over.
"$HOME/.local/bin/codex-desktop" run "$root_dir/bin/clipboard-history" --ensure-running
