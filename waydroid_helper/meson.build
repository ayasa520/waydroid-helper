pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'waydroid_helper'
utildir = moduledir / 'util'
gnome = import('gnome')

gnome.compile_resources(
    'waydroid-helper',
    'waydroid-helper.gresource.xml',
    gresource_bundle: true,
    install: true,
    install_dir: pkgdatadir,
)

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
    'generalpage.py',
    'propspage.py',
    'extensionspage.py',
    'infobar.py',
    'extensionrow.py',
    'extensionwindow.py',
]
util_sources = [
    'util/SubprocessManager.py',
    'util/Task.py',
    'util/ExtentionsManager.py',
    'util/arch.py',
]

install_data(waydroid_helper_sources, install_dir: moduledir)
install_data(util_sources, install_dir: utildir)