systemd = dependency('systemd', required: false)
systemd_system_unit_dir = get_option('systemd-system-unit-dir')
systemd_user_unit_dir = get_option('systemd-user-unit-dir')

if systemd.found() or (systemd_system_unit_dir != '' and systemd_user_unit_dir != '')
    if systemd.found()
        systemd_system_unit_dir = systemd.get_variable(pkgconfig: 'systemdsystemunitdir')
        systemd_user_unit_dir = systemd.get_variable(pkgconfig: 'systemduserunitdir')
    endif

    install_data(
        'system/waydroid-mount.service',
        install_dir: systemd_system_unit_dir
    )

    install_data(
        'user/waydroid-monitor.service',
        install_dir: systemd_user_unit_dir
    )
endif
