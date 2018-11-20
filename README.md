# StopTLS

StopTLS is a Man-in-the-Middle tool which performs opportunistic SSL/TLS stripping.

Currently it supports the following protocols: HTTP(S), SMTP, and IMAP

It requires Python >= 3.5 (i.e. Python with support for async/await syntax), the [aiohttp](https://aiohttp.readthedocs.io/en/stable/) library, and the [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) library for HTML parsing.

## Usage
```
usage: main.py [--help] [-h [HTTP_PORT]] [-t [TCP_PORT]]
               [-p {SMTP,IMAP} [{SMTP,IMAP} ...]]

MitM proxy which performs opportunistic SSL/TLS stripping

optional arguments:
  --help                show this help message and exit
  -h [HTTP_PORT], --http [HTTP_PORT]
                        HTTP listen port [default: 10000]
  -t [TCP_PORT], --tcp [TCP_PORT]
                        TCP listen port [default: 49151]
  -p {SMTP,IMAP} [{SMTP,IMAP} ...], --tcp-protocols {SMTP,IMAP} [{SMTP,IMAP} ...]
                        supported TCP protocols
```

## Setup
### 1. Download
```bash
$ git clone https://github.com/mathewmarcus/bruteforce-gpg.git
```

### 2. Install Dependencies
``` bash
$ pip install -r requirements.txt
```

### 3. Add `iptables` rules
Add rules to redirect and allow traffic to the ports specified by the `-h [HTTP_PORT], --http [HTTP_PORT]` and `-t [TCP_PORT], --tcp [TCP_PORT]` options. 

`stoptls` is setup to handle HTTP traffic on one port, and all other TCP traffic on another, as indicated by the CLI options.

So, assuming the following `stoptls` invocation:
```bash
$ python main.py --http 8080 --tcp 8081 --tcp-protocols SMTP IMAP
```

`iptables` rules would then need to be added to the `PREROUTING` chain in the `nat` table and the `INPUT` chain in the `filter` table, as shown below:

#### `nat` table, `PREROUTING` chain
##### HTTP
```bash
$ sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
```

##### SMTP
```bash
$ sudo iptables -t nat -A PREROUTING -p tcp --dport 25 -j REDIRECT --to-port 8081
$ sudo iptables -t nat -A PREROUTING -p tcp --dport 587 -j REDIRECT --to-port 8081
```

##### IMAP
```bash
$ sudo iptables -t nat -A PREROUTING -p tcp --dport 143 -j REDIRECT --to-port 8081
```

#### `filter` table, `INPUT` chain
Assuming a default `DROP` policy on this chain, add rules for the `HTTP_PORT` and/or `TCP_PORT`s specified earlier. So, for the above example:

##### HTTP
```bash
sudo iptables -A INPUT -p tcp --dport 8080 -m conntrack --ctorigdstport 80 -j ACCEPT
```

##### SMTP
```bash
sudo iptables -A INPUT -p tcp --dport 8081 -m conntrack --ctorigdstport 25 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8081 -m conntrack --ctorigdstport 587 -j ACCEPT
```

##### IMAP
```bash
sudo iptables -A INPUT -p tcp --dport 8081 -m conntrack --ctorigdstport 143 -j ACCEPT
```

Why the `--ctorigdstport` option? This prevents the `stoptls` ports from being directly accessible (i.e. they will not appear in `nmap` scans).

## TODO
It should be noted that `StopTLS` is very much a work in progress, and is essentially a POC at this point. In fact, currently, it doesn't log anything, but simply strips and proxies the connections. Below is a non-exhaustive list of features to be added. 

1. Logging
2. Advanced configuration via an INI file
3. Custom log traffic filters for all protocols via config file directives and/or user-supplied callables (functions, methods, etc)
4. Support for additional, user-supplied protocols, by subclassing `stoptls.base.Proxy` and/or `stoptls.tcp.base.TCPProxyConn` abstract classes
5. Support for more complex, non-standard HTTP login mechanisms
6. Packaging and distribution via `pip` and `PyPi` repository
7. Integration testing with Docker

## Why?
Why create yet another SSLstripping tool when...
1. tools such as `sslstrip` and `sslsplit` already exist
2. HTTP Strict Transport Security (HSTS) has significantly limited the effectiveness of sslstripping attacks.

There are several answers:
1. I wanted to better understand the sslstripping attack vector.
2. I wanted to implement an sslstripping proxy using Python3 native asychronous support via `asyncio`, as opposed to an external library such as `twisted`.
3. I wanted a tool which supported/could support any TCP protocol which uses opportunistic SSL/TLS, in addition to HTTP.
4. I wanted a tool which was highly extensible and customizable.
