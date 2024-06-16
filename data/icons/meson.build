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
    symbolic_dir / ('@0@-addon-symbolic.svg').format(application_id),
    symbolic_dir / ('@0@-conflicting.svg').format(application_id),
    symbolic_dir / ('@0@-symbolic.svg').format(application_id),
    symbolic_dir / ('@0@-normal.svg').format(application_id),
    symbolic_dir / ('@0@-system-symbolic.svg').format(application_id),
    symbolic_dir / ('@0@-grid-symbolic.svg').format(application_id),
    symbolic_dir / ('@0@-home-symbolic.svg').format(application_id),
    symbolic_dir / ('@0@-system-shutdown-symbolic.svg').format(application_id),
  ],
  install_dir: get_option('datadir') / 'icons' / symbolic_dir,
)
