"""

"""
import ldap
import locale
from locale import gettext as _

locale.bindtextdomain('pardus_domain_core', '/usr/share/locale')
locale.textdomain('pardus_domain_core')

class LDAP:
    def __init__(self, address, username, password):
        self.address = address
        self.username = username
        self.password = password
        self.conn = None

    def _connect(self):
        """Private method to establish the LDAP connection."""
        try:
            self.conn = ldap.initialize(f"ldap://{self.address}")
            self.conn.protocol_version = 3
            self.conn.set_option(ldap.OPT_REFERRALS, 0)
        except ldap.LDAPError as e:
            print(_(f"Failed to initialize LDAP connection: {e}"))
            self.conn = None

    def authenticate(self):
        """Authenticate the user with the provided credentials."""
        if self.conn is None:
            self._connect()

        try:
            self.conn.simple_bind_s(self.username, self.password)
            print(_("LDAP authentication successful!"))
            return True
        except ldap.LDAPError as e:
            print(_(f"LDAP error: {e}"))
            return False
        except Exception as e:
            print(_(f"An error occurred: {e}"))
            return False

    def check_computer_exists_in_ad(self, hostname):
        """Check if the given hostname already exists in Active Directory."""
        if not self.authenticate():
            return False

        try:
            domain_controller = self._build_domain_controller()
            search_base = domain_controller
            search_filter = f"(cn={hostname})"

            result = self.conn.search_s(search_base, ldap.SCOPE_SUBTREE, search_filter)

            if result:
                for dn, entry in result:
                    if dn and entry:
                        print(_(f"Hostname {hostname} already exists in Active Directory!"))
                        # print(_(f"Found dn: {dn}"))
                        # print(_(f"Found entry: {entry}"))
                        return entry
                    else:
                        print(_(f"Hostname {hostname} is available to use."))
                        return None
        except ldap.LDAPError as e:
            print(_(f"LDAP search failed: {e}"))
            return None
        finally:
            self._unbind_connection()

    def _build_domain_controller(self):
        """Build the domain controller string from the LDAP address."""
        domain_parts = self.address.split(".")
        return ",".join([f"dc={part}" for part in domain_parts])

    def _unbind_connection(self):
        """Close the LDAP connection."""
        if self.conn:
            self.conn.unbind_s()
            print(_("Connection closed."))