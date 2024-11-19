import subprocess
import os
import re
import requests
import urllib.parse
import threading
import time
import shutil
import base64


class SignatureAuth(requests.auth.AuthBase):
    """Attaches HTTP Signature Authentication to the given Request object."""

    def __init__(self, user, ssh_key):
        self.ssh_key = ssh_key
        self.ssh_keygen_path = shutil.which("ssh-keygen")
        self.user = user
        # Keep state in per-thread local storage
        self._thread_local = threading.local()

    def decode_it(self, obj):
        """Decode the given object unless it is a str.

        If the given object is a str or has no decode method, the object itself is
        returned. Otherwise, try to decode the object using utf-8. If this
        fails due to a UnicodeDecodeError, try to decode the object using
        latin-1.
        """
        if isinstance(obj, str) or not hasattr(obj, 'decode'):
            return obj
        try:
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            return obj.decode('latin-1')
        
    def ssh_sign(self, data, namespace):
        keyfile = self.ssh_key
        keyfile = os.path.expanduser(keyfile)
        cmd = [self.ssh_keygen_path, '-Y', 'sign', '-f', keyfile, '-n', namespace, '-q']
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding="utf-8")
        signature, _ = proc.communicate(data)

        if proc.returncode:
            raise RuntimeError('ssh-keygen signature creation failed: %d' % proc.returncode)

        match = re.match(r"\A-----BEGIN SSH SIGNATURE-----\n(.*)\n-----END SSH SIGNATURE-----", signature, re.S)
        if not match:
            raise RuntimeError('could not extract ssh signature')
        return base64.b64decode(match.group(1))

    def init_per_thread_state(self):
        # Ensure state is initialized just once per-thread
        if not hasattr(self._thread_local, "init"):
            self._thread_local.init = True
            self._thread_local.last_nonce = ""
            self._thread_local.nonce_count = 0
            self._thread_local.chal = {}
            self._thread_local.pos = None
            self._thread_local.num_401_calls = None

    def build_signature_header(self, method, url):
        """
        :rtype: str
        """

        realm = self._thread_local.chal["realm"]

        now = int(time.time())
        sigdata = "(created): %d" % now
        signature = self.ssh_sign(sigdata, realm)
        signature = self.decode_it(base64.b64encode(signature))
        return 'keyId="%s",algorithm="ssh",headers="(created)",created=%d,signature="%s"' \
            % (self.user, now, signature)

    def handle_redirect(self, r, **kwargs):
        """Reset num_401_calls counter on redirects."""
        if r.is_redirect:
            self._thread_local.num_401_calls = 1

    def handle_401(self, r, **kwargs):
        """
        Takes the given response and tries digest-auth, if needed.

        :rtype: requests.Response
        """

        # If response is not 4xx, do not auth
        # See https://github.com/psf/requests/issues/3772
        if not 400 <= r.status_code < 500:
            self._thread_local.num_401_calls = 1
            return r

        if self._thread_local.pos is not None:
            # Rewind the file position indicator of the body to where
            # it was to resend the request.
            r.request.body.seek(self._thread_local.pos)
        s_auth = r.headers.get("www-authenticate", "")

        if "signature" in s_auth.lower() and self._thread_local.num_401_calls < 2:
            self._thread_local.num_401_calls += 1
            pat = re.compile(r"signature ", flags=re.IGNORECASE)
            self._thread_local.chal = requests.utils.parse_dict_header(pat.sub("", s_auth, count=1))

            # Consume content and release the original connection
            # to allow our new request to reuse the same one.
            r.content
            r.close()
            prep = r.request.copy()
            requests.cookies.extract_cookies_to_jar(prep._cookies, r.request, r.raw)
            prep.prepare_cookies(prep._cookies)

            auth = self.build_signature_header(prep.method, prep.url)
            auth_val = f'Signature {auth}'
            prep.headers["Authorization"] = auth_val
            _r = r.connection.send(prep, **kwargs)
            _r.history.append(r)
            _r.request = prep

            return _r

        self._thread_local.num_401_calls = 1
        return r

    def __call__(self, r):
        # Initialize per-thread state, if needed
        self.init_per_thread_state()
        # If we have a saved nonce, skip the 401
        if self._thread_local.last_nonce:
            auth = self.build_signature_header(r.method, r.url)
            auth_val = f'Signature {auth}'
            r.headers["Authorization"] = auth_val
        try:
            self._thread_local.pos = r.body.tell()
        except AttributeError:
            # In the case of HTTPDigestAuth being reused and the body of
            # the previous request was a file-like object, pos has the
            # file position of the previous body. Ensure it's set to
            # None.
            self._thread_local.pos = None
        r.register_hook("response", self.handle_401)
        r.register_hook("response", self.handle_redirect)
        self._thread_local.num_401_calls = 1

        return r

    def __eq__(self, other):
        return all(
            [
                self.user == getattr(other, "user", None),
                self.ssh_key == getattr(other, "ssh_key", None),
            ]
        )

    def __ne__(self, other):
        return not self == other
