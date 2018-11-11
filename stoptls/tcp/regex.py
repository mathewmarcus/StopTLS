import re

IMAP_COMMAND = re.compile('^(?P<tag>\S*) (?P<cmd>[A-Za-z]*)\r?\n$')
IMAP_RESPONSE = re.compile('^(?P<tag>\S*) (?:(?P<ok>[Oo][Kk])|(?P<bad>[Bb][Aa][Dd])|(?P<no>[Nn][Oo]) )?(?P<response>.*)\r\n$')
IMAP_STARTTLS = re.compile('( ?)STARTTLS( ?)', flags=re.IGNORECASE)
