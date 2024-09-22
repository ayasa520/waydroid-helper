project('pointer-lock', 'c')
wayland_scanner = find_program('wayland-scanner')

# 获取 Wayland 协议目录
wayland_protocols = dependency('wayland-protocols')
protocols_dir = wayland_protocols.get_pkgconfig_variable('pkgdatadir')

# 定义协议文件路径
pointer_constraints_xml = protocols_dir / 'unstable/pointer-constraints/pointer-constraints-unstable-v1.xml'
relative_pointer_xml = protocols_dir / 'unstable/relative-pointer/relative-pointer-unstable-v1.xml'

# 生成 Wayland 协议文件
pointer_constraints_h = custom_target('pointer-constraints-client-header',
  input: pointer_constraints_xml,
  output: 'pointer-constraints-unstable-v1.h',
  command: [wayland_scanner, 'client-header', '@INPUT@', '@OUTPUT@']
)

pointer_constraints_c = custom_target('pointer-constraints-private-code',
  input: pointer_constraints_xml,
  output: 'pointer-constraints-unstable-v1.c',
  command: [wayland_scanner, 'private-code', '@INPUT@', '@OUTPUT@'],
  depends: pointer_constraints_h
)

relative_pointer_h = custom_target('relative-pointer-client-header',
  input: relative_pointer_xml,
  output: 'relative-pointer-unstable-v1.h',
  command: [wayland_scanner, 'client-header', '@INPUT@', '@OUTPUT@']
)

relative_pointer_c = custom_target('relative-pointer-private-code',
  input: relative_pointer_xml,
  output: 'relative-pointer-unstable-v1.c',
  command: [wayland_scanner, 'private-code', '@INPUT@', '@OUTPUT@'],
  depends: relative_pointer_h
)
include_directories = include_directories('.')

# 编译动态链接库
wayland_client_dep = dependency('wayland-client')
wayland_server_dep = dependency('wayland-server')

libpointer_lock = shared_library('pointer-lock',
  [pointer_constraints_c, relative_pointer_c, 'wayland_pointer_lock.c'],
  dependencies: [wayland_client_dep, wayland_server_dep],
  include_directories: include_directories,
  install: true
)