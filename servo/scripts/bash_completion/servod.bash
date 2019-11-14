#!/bin/bash
# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

_all_servod_xmls=$(python2 -c "
from servo import system_config
print(' '.join(system_config.SystemConfig().get_all_cfg_names()))
")

_all_servod_boards=()
for board in /mnt/host/source/src/overlays/overlay-*; do
  board=${board##*/}
  if [[ "${board}" != *-variant-* ]]; then
    _all_servod_boards+=("${board#overlay-}")
  fi
done

# suggests bash auto completions according to current character
_servod_completion() {
  local cur="${COMP_WORDS[${COMP_CWORD}]}"
  local pre=
  if [[ ${#COMP_WORDS[@]} -gt 1 ]]; then
    pre="${COMP_WORDS[$((COMP_CWORD - 1))]}"
  fi

  if [[ "${cur}" == "-c" ]]; then
    COMPREPLY=("-c")
  elif [[ "${pre}" == "-c" ]]; then
    # shellcheck disable=SC2207
    COMPREPLY=($(compgen -W "${_all_servod_xmls}" -- "${cur}"))
  elif [[ "${cur}" == "-b" ]]; then
    COMPREPLY=("-b")
  elif [[ "${pre}" == "-b" ]]; then
    # shellcheck disable=SC2207
    COMPREPLY=($(compgen -W "${_all_servod_boards[*]}" -- "${cur}"))
  elif [[ "${cur}" == "-s" ]]; then
    COMPREPLY=("-s")
  elif [[ "${pre}" == "-s" ]]; then
    local _all_serial

    _all_serial=$(lsusb -d 18d1: -v 2>/dev/null |
                  awk '$0 ~ /iSerial/ {print $3}')
    # shellcheck disable=SC2207
    COMPREPLY=($(compgen -W "${_all_serial}" -- "${cur}"))
  fi
}

complete -F _servod_completion servod
