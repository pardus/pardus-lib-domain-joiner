project('pardus-domain-core', version: '1.0.0')

# Python modül desteğini al
python = import('python').find_installation()

# Python modülünü site-packages'e kur
python.install_sources(
  'pardus-domain-core',
  subdir: 'pardus_domain_core'  # Bu, import pardus_domain_core demek olur
)

# Pam config dosyasını kur
install_data(
  'data/pardus-pam-config',
  install_dir: '/usr/share/pam-configs'
)

# core dosyalarını /usr/share/... altına da kopyala
core_files = files(
  'pardus-domain-core/__init__.py',
  'pardus-domain-core/config_manager.py',
  'pardus-domain-core/domain_joiner_ldap.py',
  'pardus-domain-core/domain_joiner_realmd.py',
  'pardus-domain-core/domain_joiner_winbind.py',
  'pardus-domain-core/domain_operations.py',
  'pardus-domain-core/__version__',
)

install_data(core_files,
  install_dir: '/usr/share/pardus/pardus-domain-settings/pardus-domain-core/pardus-domain-core'
)

