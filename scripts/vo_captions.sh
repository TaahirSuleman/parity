#!/bin/zsh
# VoiceOver captions by script (docs/voice-recording.md, docs/25 §3): poll what VoiceOver last spoke and write one line per change.
#   scripts/vo_captions.sh <seconds> [out.tsv]        lines: <epoch ms><TAB><phrase>
# Needs VoiceOver on and "Allow VoiceOver to be controlled with AppleScript" (VoiceOver Utility → General). The phrase current at the
# first poll was spoken before the poll started, so it is the baseline, not a caption. VO_POLL_MS (default 120) sets the poll interval.
set -u
zmodload zsh/datetime
seconds=${1:?usage: vo_captions.sh <seconds> [out.tsv]}
out=${2:-/dev/stdout}
poll_ms=${VO_POLL_MS:-120}
phrase() { osascript -e 'tell application "VoiceOver" to return content of last phrase' 2>/dev/null; }
last=$(phrase) || { print -u2 "vo_captions: VoiceOver is not running, or 'Allow VoiceOver to be controlled with AppleScript' is off (VoiceOver Utility → General)"; exit 3; }
[[ "$out" != /dev/stdout ]] && : > "$out"
end=$(( EPOCHREALTIME + seconds ))
while (( EPOCHREALTIME < end )); do
  now=$(phrase) || { print -u2 "vo_captions: lost VoiceOver"; exit 3; }
  if [[ "$now" != "$last" ]]; then
    ms=$(( EPOCHREALTIME * 1000 )); ms=${ms%.*}
    printf '%s\t%s\n' "$ms" "${now//[$'\t\n\r']/ }" >> "$out"
    last=$now
  fi
  sleep $(( poll_ms / 1000.0 ))
done
