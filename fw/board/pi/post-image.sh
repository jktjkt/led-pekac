#!/bin/bash

set -e

cp package/rpi-firmware/config.txt "${BINARIES_DIR}/rpi-firmware/config.txt"

echo "Adding 'dtoverlay=miniuart-bt' to config.txt (fixes ttyAMA0 serial console)."
cat << __EOF__ >> "${BINARIES_DIR}/rpi-firmware/config.txt"

# fixes rpi (3B, 3B+, 3A+, 4B and Zero W) ttyAMA0 serial console
dtoverlay=miniuart-bt
__EOF__

echo "Enabling I2C in config.txt"
cat << __EOF__ >> "${BINARIES_DIR}/rpi-firmware/config.txt"

# Enable I2C
dtparam=i2c_arm=on,i2c_arm_baudrate=400000
__EOF__

echo "Enabling the LED driver in config.txt"
cat << __EOF__ >> "${BINARIES_DIR}/rpi-firmware/config.txt"

# Tally light
dtoverlay=tally
__EOF__

# Pass an empty rootpath. genimage makes a full copy of the given rootpath to
# ${GENIMAGE_TMP}/root so passing TARGET_DIR would be a waste of time and disk
# space. We don't rely on genimage to build the rootfs image, just to insert a
# pre-built one in the disk image.

GENIMAGE_TMP="${BUILD_DIR}/genimage.tmp"
trap 'rm -rf "${ROOTPATH_TMP}"' EXIT
ROOTPATH_TMP="$(mktemp -d)"

rm -rf "${GENIMAGE_TMP}"

genimage \
	--rootpath "${ROOTPATH_TMP}"   \
	--tmppath "${GENIMAGE_TMP}"    \
	--inputpath "${BINARIES_DIR}"  \
	--outputpath "${BINARIES_DIR}" \
	--config "${BR2_EXTERNAL_HRZTV_PATH}/board/pi/genimage.cfg"

exit $?
