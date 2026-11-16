# Source only in interactive shells. Every check is detached and bounded.
case $- in *i*) ;; *) return 0;; esac
if [ -n "${DISPLAY:-}" ]; then
 ( timeout 8 "${CLIPBOARD_HISTORY_DIR:-$HOME/.install/clipboard}/bin/clipboard-history" --ensure-running >/dev/null 2>&1 < /dev/null & )
fi
