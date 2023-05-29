#/bin/bash 

FOUND=$(grep nofile /etc/security/limits.conf |grep -v "#")
if [ ! -z "$FOUND" ]; then
       sed -i '/ nofile /s/^/#/' /etc/security/limits.conf 
fi
PKGS=("perl" "perl-Digest-MD5" "perl-Test-Simple" "perl-DBI" "perl-DBD-MySQL" "perl-Data-Dumper" "perl-Encode" "perl-Time-HiRes" "perl-JSON")
for pkg in  ${PKGS[@]}
do
    if rpm -q ${pkg} &> /dev/null;then
        echo "$pkg already install"
        continue
    fi
    yum install -y ${pkg}   
done
