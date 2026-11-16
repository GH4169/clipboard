if ($?prompt && $?DISPLAY) then
 if (! $?CLIPBOARD_HISTORY_DIR) setenv CLIPBOARD_HISTORY_DIR "$HOME/.install/clipboard"
 (timeout 8 python3 "$CLIPBOARD_HISTORY_DIR/clipboard_history.py" --ensure-running >& /dev/null < /dev/null &)
endif
