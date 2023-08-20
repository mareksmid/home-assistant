import requests
requests.packages.urllib3.util.connection.HAS_IPV6 = False
log.info("IPv6 was disabled")
