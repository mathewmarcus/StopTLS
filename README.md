# StopTLS

## iptables Rules
### Required
* iptables -t PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
* iptables -A INPUT -p tcp --dport 8080 -j ACCEPT

### Testing (in a VM)
* iptables -P FORWARD ACCEPT
* iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
