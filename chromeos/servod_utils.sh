# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SERVO_MICRO_PID='501a'

log_output() {
  logger -t "${UPSTART_JOB}" $@
  echo $@
}

update_config() {
  local config_file=$1
  local key=$2
  local value=$3

  if [ -z "$value" ]; then
    return
  fi

  # If file exists and key is in the config file, replace it in the file.
  # Otherwise append it to the config file.
  if [ -f $config_file ] && grep -q "^${key}=" "$config_file"; then
    sed -i "/^${key}=/c${key}=${value}" $config_file
  else
    echo "${key}=${value}" >> $config_file
  fi
}

clean_config_key() {
  local config_file=$1
  local key=$2

  if [ -f ${config_file} ]; then
    sed -i "/^${key}=/d" $config_file
  fi
}

cache_servov4_hub_and_servo_micro() {
  local config_file=$1
  local servov4_serial=$2

  if [ -z "${servov4_serial}" ]; then
    return
  fi

  log_output "Probe for servo: ${servov4_serial}"

  # Find this servo if it is a servo_v4, check its serialno
  SERVOPATH=$(grep -l "^${servov4_serial}\$" /sys/bus/usb/devices/*/serial ||
      true)

  if [ -z "${SERVOPATH}" ]; then
    log_output "No servo detected for ${servov4_serial}"
    return
  fi
  SERVOV4=$(dirname "${SERVOPATH}")

  log_output "Servo: ${servov4_serial} found at: ${SERVOV4}"

  # The hub is one level up.
  SERVOV4_HUB=$(echo "${SERVOV4}" | sed 's/\.[0-9]\+$//')
  if [ "${SERVO4_HUB}" == "${SERVOV4}" ]; then
    log_output "Can't get servo hub by ${SERVOV4}"
    clean_config_key "${config_file}" HUB
    return
  fi

  log_output "Servo Hub is: ${SERVOV4_HUB}"

  if [ -z "${SERVOV4_HUB}" ]; then
    log_output "No hub detected for ${servov4_serial}"
    clean_config_key "${config_file}" HUB
    return
  fi

  if [ ! -f "${SERVOV4_HUB}"/authorized ]; then
    log_output "File not found: ${SERVOV4_HUB}/authorized"
    return
  fi

  # If this hub actually exists, let's save the path for later.
  log_output "Servo hub cached!"
  update_config "${config_file}" HUB "${SERVOV4_HUB}"

  # Try to cache servo micro serial if present.
  SERVO_MICRO_PATH=$(grep -l "^${SERVO_MICRO_PID}\$" \
      "${SERVOV4_HUB}"/*/idProduct || true)
  if [ -z "${SERVO_MICRO_PATH}" ]; then
    log_output "No Servo Micro detected."
    clean_config_key "${config_file}" SERVO_MICRO_SERIAL
    return
  fi
  SERVO_MICRO=$(dirname "${SERVO_MICRO_PATH}")
  if [ ! -f "${SERVO_MICRO}"/serial ]; then
    log_output "Servo Micro detected, but no serial found!"
    return
  fi
  SERVO_MICRO_SERIAL=$(cat "${SERVO_MICRO}"/serial)
  log_output "Servo Micro serial is ${SERVO_MICRO_SERIAL}. Cached!"
  update_config "${config_file}" SERVO_MICRO_SERIAL "${SERVO_MICRO_SERIAL}"
}

slam_servov4_hub() {
  local hub=$1

  if [ -n "${hub}" ]; then
    if [ -f "${hub}/authorized" ]; then
      log_output "Restarting USB interface on ${hub}"
      echo 0 > "${hub}/authorized"
      sleep 1
      echo 1 > "${hub}/authorized"
      sleep 3
    else
      log_output "Hub control ${hub}/authorized doesn't exist"
    fi
  else
    log_output "Hub not specified"
  fi
}

update_firmware() {
  local board=$1
  local serial=$2
  local vidpid=$3

  # Check for the presence of a board with this serialno.
  lsusb -d "${vidpid}" -v | grep -q "${serial}" || return

  log_output "Check for ${board} update"
  servo_updater -b ${board} -s "${serial}" --reboot || return
  log_output "Completed ${board} update without reported errors."
}

# For testing:
test_servo_utils () {
  logger() {
    echo $@
  }
  cache_servov4_hub_and_servo_micro "test.config"
  cache_servov4_hub_and_servo_micro "test.config" "Uninitialized"
  . ./test.config
  slam_servov4_hub $HUB
}
