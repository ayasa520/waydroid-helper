moduledir = pkgdatadir / 'waydroid_helper'
utildir = moduledir / 'util'
compatwidgetdir = moduledir / 'compat_widget'
toolsdir = moduledir / 'tools'
gnome = import('gnome')

python = import('python')

conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)
conf.set('datadir', get_option('prefix') / get_option('datadir'))
conf.set('bindir', get_option('prefix') / get_option('bindir'))
conf.set('project_name',  meson.project_name())
build_appimage = get_option('build_appimage')

if build_appimage 
    conf.set('build_appimage', 'True')
else
    conf.set('build_appimage', 'False')
    conf.set('PYTHON', python.find_installation('python3').path())
endif

configure_file(
    input: 'waydroid-helper.in',
    output: 'waydroid-helper',
    configuration: conf,
    install: true,
    install_dir: get_option('bindir'),
    install_mode: 'rwxr-xr-x',
)

configure_file(
    input: 'waydroid-cli.in',
    output: 'waydroid-cli',
    configuration: conf,
    install: true,
    install_dir: get_option('bindir'),
    install_mode: 'rwxr-xr-x',
)

waydroid_helper_sources = [
    '__init__.py',
    'main.py',
    'window.py',
    'waydroid.py',
    'general_page.py',
    'props_page.py',
    'extensions_page.py',
    'infobar.py',
    'extension_row.py',
    'available_version_page.py',
    'shared_folder.py'
]
util_sources = [
    'util/__init__.py',
    'util/subprocess_manager.py',
    'util/task.py',
    'util/extensions_manager.py',
    'util/arch.py',
    'util/log.py',
]

tools_sources = [
    'tools/__init__.py',
    'tools/monitor_service.py',
    'tools/mount_service.py',
]

compat_widget_sources = [
    'compat_widget/__init__.py',
    'compat_widget/navigation_view.py',
    'compat_widget/navigation_page.py',
    'compat_widget/toolbar_view.py',
    'compat_widget/spinner.py',
    'compat_widget/dialog.py',
    'compat_widget/header_bar.py',
    'compat_widget/file_dialog.py',
]
install_data(waydroid_helper_sources, install_dir: moduledir)
install_data(util_sources, install_dir: utildir)
install_data(compat_widget_sources, install_dir: compatwidgetdir)
install_data(tools_sources, install_dir: toolsdir)