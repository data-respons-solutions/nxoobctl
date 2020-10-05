openssl req -x509 -newkey rsa:2048 -sha256 -nodes -keyout cert.key -out cert.pub -days 7300 -config ssl.conf
