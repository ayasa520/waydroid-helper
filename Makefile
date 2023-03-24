PREFIX := /usr
BIN_DIR := $(PREFIX)/bin
DBUS_DIR := $(PREFIX)/share/dbus-1
POLKIT_DIR := $(PREFIX)/share/polkit-1
HELPER_DIR := $(PREFIX)/lib/waydroid-helper

INSTALL_BIN_DIR := $(DESTDIR)$(BIN_DIR)
INSTALL_DBUS_DIR := $(DESTDIR)$(DBUS_DIR)
INSTALL_POLKIT_DIR := $(DESTDIR)$(POLKIT_DIR)
INSTALL_HELPER_DIR := $(DESTDIR)$(PREFIX)/lib/waydroid-helper
install:
	chmod +x service.py waydroid-helper.py
	install -d $(INSTALL_BIN_DIR) $(INSTALL_DBUS_DIR)/system.d $(INSTALL_POLKIT_DIR)/actions $(INSTALL_DBUS_DIR)/system-services $(INSTALL_HELPER_DIR)
	cp -a waydroid-helper.py service.py tools service qml model bin $(INSTALL_HELPER_DIR)
	ln -sf $(INSTALL_HELPER_DIR)/waydroid-helper.py $(INSTALL_BIN_DIR)/waydroid-helper
	cp dbus/com.waydroid.Helper.conf $(INSTALL_DBUS_DIR)/system.d/
	cp dbus/com.waydroid.Helper.policy $(INSTALL_POLKIT_DIR)/actions/
	cp dbus/com.waydroid.Helper.service $(INSTALL_DBUS_DIR)/system-services/

uninstall:
	rm -rf $(INSTALL_HELPER_DIR) $(INSTALL_BIN_DIR)/waydroid-helper $(INSTALL_DBUS_DIR)/system.d/com.waydroid.Helper.conf  $(INSTALL_POLKIT_DIR)/actions/com.waydroid.Helper.policy $(INSTALL_DBUS_DIR)/system-services/com.waydroid.Helper.service