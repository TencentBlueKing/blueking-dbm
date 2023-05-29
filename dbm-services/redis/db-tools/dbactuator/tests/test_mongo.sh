#!/usr/bin/env bash
source /etc/profile
repoUser=""
repoPassword=""

mongodbPkgName="mongodb-linux-x86_64-3.4.20.tar.gz"
mongodbPkgMd5="e68d998d75df81b219e99795dec43ffb"

localMongodbPkgName="/data/install/$mongodbPkgName"
localMongodbPkgMd5=""

repoUrl=""

usage() {
    echo -e "Usage: $0 [OPTIONS]"
    echo -e ""
    echo -e "-H --help -h required,display help info"
    echo -e "--repo-user required,bk repo user name,"
    echo -e "--repo-password required,bk repo user password"
    echo -e "--repo-url required,bk repo https url"
    echo -e ""
    exit 1
}

if [[ $# -lt 2 ]]; then
    usage
fi

for i in "$@"; do
    case $i in
    --repo-user=*)
        repoUser="${i#*=}"
        shift
        ;;
    --repo-password=*)
        repoPassword="${i#*=}"
        shift
        ;;
    --repo-url=*)
        repoUrl="${i#*=}"
        shift
        ;;
    *)
        echo -e "unknown option:$i"
        usage
        ;;
    esac
done

if [[ -z $repoUser ]]; then
    echo -e "error: --repo-user must be passed,repoUser=$repoUser"
    usage
fi

if [[ -z $repoPassword ]]; then
    echo -e "error: --repo-password must be passed,repoPassword=$repoPassword"
    usage
fi

if [[ -z $repoUrl ]]; then
    echo -e "error: --repo-url must be passed,repoUrl=$repoUrl"
    usage
fi

if [[ -e $localMongodbPkgName ]]; then
    localMongodbPkgMd5=$(md5sum $localMongodbPkgName | awk '{print $1}')
fi


wgetCmd="wget --user=$repoUser --password=$repoPassword $repoUrl/install_package/$mongodbPkgName -O $localMongodbPkgName"
if [[ ! -e $localMongodbPkgName ]]; then
    echo $wgetCmd
    $wgetCmd
elif [[ -n $localMongodbPkgMd5 && $localMongodbPkgMd5 != $mongodbPkgMd5 ]]; then
    echo "rm -f $localMongodbPkgName"
    rm -f $localMongodbPkgName
    echo $wgetCmd
    $wgetCmd
fi

cd $(dirname $0)/../pkg/atomjobs/atommongodb/
go test -v
rm -rf logs

