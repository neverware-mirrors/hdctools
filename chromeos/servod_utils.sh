# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

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
    sed -i "/$key/c$key=$value" $config_file
  else
    echo "$key=$value" >> $config_file
  fi
}

cache_servov4_hub() {
  local config_file=$1
  local serial=$2

  if [ -z "${serial}" ]; then
    return
  fi

  # Find this servo if it is a servo_v4, check its serialno
  SERVOPATH=$(grep -l "^${serial}\$" /sys/bus/usb/devices/*/serial)

  if [ -n "${SERVOPATH}" ]; then
    SERVOV4=$(dirname "${SERVOPATH}")

    logger -t "$UPSTART_JOB" "Servo: ${serial} found at: ${SERVOV4}"

    # The hub is one level up.
    SERVOV4_HUB=$(echo "${SERVOV4}" | sed 's/..$//')

    logger -t "$UPSTART_JOB" "Servo Hub is: ${SERVOV4_HUB}"

    if [ -n "${SERVOV4_HUB}" ]; then
      if [ -f "${SERVOV4_HUB}"/authorized ]; then
        # If this hub actually exists, let's save the path for later.
        update_config "${config_file}" HUB "${SERVOV4_HUB}"
      else
        logger -t "$UPSTART_JOB" "File not found: ${SERVOV4_HUB}/authorized"
      fi
    else
      logger -t "$UPSTART_JOB" "No hub detected for ${serial}"
    fi
  else
    logger -t "$UPSTART_JOB" "No servo detected for ${serial}"
  fi
}

slam_servov4_hub() {
  local hub=$1

  if [ -n "${hub}" ]; then
    if [ -f "${hub}"/authorized ]; then
      logger -t "$UPSTART_JOB" "Restarting USB interface on ${hub}"
      echo 0 > "${hub}"/authorized
      sleep 1
      echo 1 > "${hub}"/authorized
      sleep 3
    else
      logger -t "$UPSTART_JOB" "Hub control ${hub}/authorized doesn't exist"
    fi
  fi
}

# For testing:
test_servo_utils () {
  logger() {
    echo $@
  }
  cache_servov4_hub "test.config"
  cache_servov4_hub "test.config" "Uninitialized"
  . ./test.config
  slam_servov4_hub $HUB
}
