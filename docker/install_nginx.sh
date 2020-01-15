# -------------------------------------------
# Vars
# -------------------------------------------
OS_VERSION=${UBUNTU_NAME:-bionic}

# -------------------------------------------
# NGINX
# -------------------------------------------
cat > /etc/apt/sources.list.d/nginx.list <<EOF
deb http://nginx.org/packages/mainline/ubuntu/ ${OS_VERSION} nginx
deb-src http://nginx.org/packages/mainline/ubuntu/ ${OS_VERSION} nginx
EOF
wget -O - http://nginx.org/packages/keys/nginx_signing.key | apt-key add -

apt-get update
apt-get install --no-install-recommends -y nginx

# -------------------------------------------
# Create self-signed certificate for NGINX, 
# this is only for testing use, the folder should be mounted with the real certs on container startup in a productive environment
# -------------------------------------------
mkdir -p /etc/letsencrypt/live/localcosmos.org

openssl genrsa -out /etc/letsencrypt/live/localcosmos.org/privkey.pem 4096

cat > /etc/letsencrypt/live/localcosmos.org/localcosmos.cnf << EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_ca
prompt = no

[req_distinguished_name]
countryName = DE
stateOrProvinceName = Bayern
localityName = Nuernberg
organizationName = SiSolSystems
organizationalUnitName = LocalCosmos
emailAddress = postmaster@$(hostname -d)
# Must be last for client to validate...
commonName = $(hostname -f)

[v3_ca]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
basicConstraints = CA:TRUE
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = $(hostname -f)
DNS.3 = $(hostname -s)
IP.1 = 127.0.0.1
IP.2 = $(hostname -i)
EOF

openssl req -new -x509 -key /etc/letsencrypt/live/localcosmos.org/privkey.pem -out /etc/letsencrypt/live/localcosmos.org/fullchain.pem -days 365 -config /etc/letsencrypt/live/localcosmos.org/localcosmos.cnf -sha256
