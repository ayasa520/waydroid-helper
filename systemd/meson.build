systemd = dependency('systemd')
systemd_system_unit_dir = systemd.get_variable(pkgconfig: 'systemdsystemunitdir')
systemd_user_unit_dir = systemd.get_variable(pkgconfig: 'systemduserunitdir')

install_data(
  'system/waydroid-mount.service',
  install_dir: systemd_system_unit_dir
)

install_data(
  'user/waydroid-monitor.service',
  install_dir: systemd_user_unit_dir
)

