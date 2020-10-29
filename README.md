# Readme
Example client application for interfacing oob module.

# Important
* set_certificate (Installation of public key to module)

  oob module RTC is reset on each boot.
  
  To verify certificate validity in tls handshake during websocket connect the RTC needs to be valid.
  
  Module syncs time from NTP server whic is configurable by commmand set_config.
  
  NTP server address is resolved by DNS server which is configurable by command set_config.
  
  After certificate has been installed, it will not be possible connecting to oob module without it having access to NTP and DNS server, either from internet or local, whichever was configured.

# Default values
IPMode: STATIC

IPAddress: 192.168.0.130

netmask: 255.255.255.0

defaultGw: 192.168.0.254

DNS: 8.8.8.8

NTP: 0.europe.pool.ntp.org

NTP2: 0.pool.ntp.org

# Usage
See nxoobctl.py -h
