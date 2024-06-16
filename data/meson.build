desktop_file = i18n.merge_file(
    input: 'com.jaoushingan.WaydroidHelper.desktop.in',
    output: 'com.jaoushingan.WaydroidHelper.desktop',
    type: 'desktop',
    po_dir: '../po',
    install: true,
    install_dir: get_option('datadir') / 'applications',
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
    test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

appstream_file = i18n.merge_file(
    input: 'com.jaoushingan.WaydroidHelper.metainfo.xml.in',
    output: 'com.jaoushingan.WaydroidHelper.metainfo.xml',
    po_dir: '../po',
    install: true,
    install_dir: get_option('datadir') / 'metainfo',
)

appstreamcli = find_program('appstreamcli', required: false, disabler: true)
test(
    'Validate appstream file',
    appstreamcli,
    args: ['validate', '--no-net', '--explain', appstream_file],
)

install_data(
    'com.jaoushingan.WaydroidHelper.gschema.xml',
    install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)

install_data(
    'devices.json',
    install_dir: get_option('datadir') / meson.project_name() / 'data',
)

compile_schemas = find_program('glib-compile-schemas', required: false, disabler: true)
test(
    'Validate schema file',
    compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()],
)

subdir('icons')