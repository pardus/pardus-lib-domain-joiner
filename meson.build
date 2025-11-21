project(
  'pardus-lib-domain-joiner',
  version: '0.1.0',
  license: 'GPL-3.0+',
)

py = import('python').find_installation()

# Install Python source files
py.install_sources(
  [
    'src/__init__.py',
    'src/config_manager.py',
    'src/domain_joiner_ldap.py',
    'src/domain_joiner_realmd.py',
    'src/domain_joiner_winbind.py',
    'src/domain_operations.py',
    'src/update_krb5_config.py',
  ],
  subdir: 'pardus_domain_joiner',
)

langs = ['tr', 'pt']

foreach lang : langs
    install_data(
        'po/' + lang + '/LC_MESSAGES/pardus-lib-domain-joiner.mo',
        install_dir: '/usr/share/locale/' + lang + '/LC_MESSAGES'
    )
endforeach

install_data(
    'po/tr/LC_MESSAGES/pardus-lib-domain-joiner.mo',
    install_dir: join_paths(get_option('prefix'), 'share/locale/tr/LC_MESSAGES')
)

install_data(
  'data/pardus-pam-config', install_dir:'/usr/share/pam-configs', rename:'pardus-domain-joiner'
)
