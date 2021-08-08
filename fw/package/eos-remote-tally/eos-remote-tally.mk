EOS_REMOTE_TALLY_VERSION = 89b869b2065fd47e0d7ceaa95bf7852fefe70596 # FIXME
EOS_REMOTE_TALLY_SITE = $(call github,jktjkt,eos-remote-midi-for-video,$(EOS_REMOTE_TALLY_VERSION))
EOS_REMOTE_TALLY_INSTALL_STAGING = NO

ifeq ($(call qstrip,$(EOS_REMOTE_TALLY_MQTT_SERVER)),)
$(error EOS_REMOTE_TALLY_MQTT_SERVER cannot be empty)
endif

define EOS_REMOTE_TALLY_INSTALL_INIT_SYSTEMD
	mkdir -p $(TARGET_DIR)/usr/lib/systemd/system/multi-user.target.wants/
	$(INSTALL) -D -m 0644 \
		$(BR2_EXTERNAL_HRZTV_PATH)/package/eos-remote-tally/eos-remote-tally.service \
		$(TARGET_DIR)/usr/lib/systemd/system/
	ln -sf ../eos-remote-tally.service $(TARGET_DIR)/usr/lib/systemd/system/multi-user.target.wants/
	echo 'TALLY_SERVER=$(EOS_REMOTE_TALLY_MQTT_SERVER)' > $(TARGET_DIR)/etc/tally.conf
endef

define EOS_REMOTE_TALLY_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/tally.py $(TARGET_DIR)/usr/bin/eos-remote-tally
endef

$(eval $(generic-package))
