application_id = 'com.jaoushingan.WaydroidHelper'

scalable_dir = 'hicolor' / 'scalable' / 'apps'
install_data(
  scalable_dir / ('@0@.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / scalable_dir,
)

symbolic_dir = 'hicolor' / 'symbolic' / 'apps'
install_data(
  [
    symbolic_dir / ('@0@-symbolic.svg').format(application_id),
    symbolic_dir / 'application-x-addon-symbolic.svg',
    symbolic_dir / 'vcs-conflicting.svg',
    symbolic_dir / 'com.jaoushingan.WaydroidHelper-symbolic.svg',
    symbolic_dir / 'vcs-normal.svg',
    symbolic_dir / 'emblem-system-symbolic.svg',
    symbolic_dir / 'view-grid-symbolic.svg',
    symbolic_dir / 'user-home-symbolic.svg',
  ],
  install_dir: get_option('datadir') / 'icons' / symbolic_dir,
)
