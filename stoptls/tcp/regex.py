import re

IMAP_COMMAND = re.compile('^(?P<tag>\S*) (?P<cmd>[A-Za-z]*)\r?\n$')
IMAP_RESPONSE = re.compile('^(?P<tag>\S*) (?:(?P<ok>[Oo][Kk])|(?P<bad>[Bb][Aa][Dd])|(?P<no>[Nn][Oo]) )?(?P<response>.*)\r\n$')
IMAP_STARTTLS = re.compile('( ?)STARTTLS( ?)', flags=re.IGNORECASE)

SMTP_COMMAND = re.compile('^(?P<cmd>\S*)(?P<args> .*)\r?\n$')
SMTP_RESPONSE = re.compile('^(?P<status_code>[0-9]{3})(?:(?P<line_cont>-)| )(?P<message>.*)?\r\n$')
