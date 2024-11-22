dbus_dep = dependency('dbus-1', required: false)

dbus_service_dir = get_option('dbus-service-dir')
dbus_policy_dir = get_option('dbus-policy-dir')

if dbus_dep.found() or (get_option('dbus-service-dir') != '' and get_option('dbus-policy-dir') != '')
    if dbus_dep.found()
        dbus_service_dir = dbus_dep.get_variable(pkgconfig: 'system_bus_services_dir')
        dbus_policy_dir = dbus_dep.get_variable('datadir') / 'dbus-1' / 'system.d'
    endif

    install_data('id.waydro.Mount.conf',
        install_dir: dbus_policy_dir,
        install_mode: 'rw-r--r--'
    )

    install_data('id.waydro.Mount.service',
        install_dir: dbus_service_dir,
        install_mode: 'rw-r--r--'
    )
endif
