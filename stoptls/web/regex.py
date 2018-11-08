import re

SCHEME_DELIMITER = re.compile(':\/\/|:(?:\\\\x2[Ff]){2}|%3[Aa](?:%2[Ff]){2}')
SCHEME = re.compile('(?:https)({})'.format(SCHEME_DELIMITER.pattern))
SECURE_URL = re.compile('(?:https)((?:{})[a-zA-z0-9.\/?\-#=&;%:~_$@+,\\\\]+)'
                        .format(SCHEME_DELIMITER.pattern),
                        flags=re.IGNORECASE)
UNSECURE_URL = re.compile('(?:http)((?:{})[a-zA-z0-9.\/?\-#=&;%:~_$@+,\\\\]+)'
                          .format(SCHEME_DELIMITER.pattern),
                          flags=re.IGNORECASE)
RELATIVE_URL = re.compile('(^\/(?!\/)[a-zA-z0-9.\/?\-#=&;%:~_$@+,\\\\]+)')
COOKIE_SECURE_FLAG = re.compile('Secure;?',
                                flags=re.IGNORECASE)
CSS_OR_SCRIPT = re.compile('^script$|^style$')
