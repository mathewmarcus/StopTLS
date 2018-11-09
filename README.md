# StopTLS

StopTLS is a Man-in-the-Middle tool which performs opportunistic SSL/TLS stripping.

It requires Python >= 3.5 (i.e. Python with support for async/await syntax), the [aiohttp](https://aiohttp.readthedocs.io/en/stable/) library, and the [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) library for HTML parsing.

## iptables Rules
### Required
* iptables -t PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
* iptables -A INPUT -p tcp --dport 8080 -m conntrack --ctorigdstport 80 -j ACCEPT
