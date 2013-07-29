__title__ = 'tld.utils'
__version__ = '0.3'
__build__ = 0x000003
__author__ = 'Artur Barseghyan'
__all__ = ('update_tld_names', 'get_tld')

from urlparse import urlparse
import urllib2
import os

from tld.settings import NAMES_SOURCE_URL as TLD_NAMES_SOURCE_URL, NAMES_LOCAL_PATH as TLD_NAMES_LOCAL_PATH, DEBUG
from tld.exceptions import TldIOError, TldDomainNotFound, TldBadUrl

PROJECT_DIR = lambda base : os.path.abspath(os.path.join(os.path.dirname(__file__), base).replace('\\','/'))

_ = lambda x: x

tld_names = []

def update_tld_names():
    """
    Updates the local copy of TLDs file.
    """
    try:
        remote_file = urllib2.urlopen(TLD_NAMES_SOURCE_URL)
        local_file = open(PROJECT_DIR(TLD_NAMES_LOCAL_PATH), 'w')
        local_file.write(remote_file.read())
        local_file.close()
        remote_file.close()
    except Exception, e:
        raise TldIOError(e)

    return True

def get_tld(url, active_only=False, fail_silently=False):
    """
    Extracts the top level domain based on the mozilla's effective TLD names dat file. Returns a string. May throw
    ``TldBadUrl`` or ``TldDomainNotFound`` exceptions if there's bad URL provided or no TLD match found respectively.

    :param url: URL to get top level domain from.
    :param active_only: If set to True, only active patterns are matched.
    :param fail_silently: If set to True, no exceptions are raised and None is returned on failure.
    :return: String with top level domain or None on failure.
    """
    def init(retry_count=0):
        """
        Build the ``tlds`` list if empty. Recursive.

        :param retry_count: If greater than 1, we raise an exception in order to avoid infinite loops.
        :return: Returns interable
        """
        if retry_count > 1:
            if fail_silently:
                return None
            else:
                raise TldIOError

        global tld_names

        # If already loaded, return
        if len(tld_names):
            return tld_names

        local_file = None
        try:
            # Load the TLD names file
            local_file = open(PROJECT_DIR(TLD_NAMES_LOCAL_PATH))
            # Make a list of it all, strip all garbage
            tld_names = list(set([line.strip() for line in local_file if line[0] not in '/\n']))
            local_file.close()
        except IOError, e:
            update_tld_names() # Grab the file
            retry_count += 1 # Increment ``retry_count`` in order to avoid infinite loops
            return init(retry_count) # Run again
        except Exception, e:
            try:
                local_file.close()
            except:
                pass

            if fail_silently:
                return None
            else:
                raise e

        return tld_names

    init() # Init

    # Get (sub) domain name
    domain_name = urlparse(url).netloc

    if not domain_name:
        raise TldBadUrl(url=url)

    domain_parts = domain_name.split('.')

    # Looping from much to less (for example if we have a domain named "v3.api.google.co.uk" we'll try
    # "v3.api.google.co.uk", then "api.google.co.uk", then "api.google.co.uk", then "google.co.uk", then
    # "co.uk" and finally "uk". If the last one does not match any TLDs, we throw a <TldDomainNotFound>
    # exception.
    for i in range(0, len(domain_parts)):
        sliced_domain_parts = domain_parts[i:]

        match = '.'.join(sliced_domain_parts)
        wildcard_match = '.'.join(['*'] + sliced_domain_parts[1:])
        inactive_match = "!%s" % match

        # Match tlds
        if (match in tld_names or wildcard_match in tld_names or (active_only is False and inactive_match in tld_names)):
            return ".".join(domain_parts[i-1:])

    if fail_silently:
        return None
    else:
        raise TldDomainNotFound(domain_name=domain_name)
