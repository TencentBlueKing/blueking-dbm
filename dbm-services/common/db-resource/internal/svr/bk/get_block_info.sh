#!/bin/bash 

SYSBLOCK_DIR=${SYSBLOCK_DIR:-"/sys/block"}
# 从环境变量中获取META_DOMAIN的值，如果不存在则使用默认值
META_DOMAIN=${META_DOMAIN:-'127.0.0.1'}

getDiskType(){
    dname=$1    
    if [[ $dname =~ ^fd ]]
    then
        echo "FDD"
    elif [[ $dname =~ ^sd ]]
    then
        echo "HDD"
    elif [[ $dname =~ ^hd ]]
    then
        echo "HDD"
    elif [[ $dname =~ ^vd ]]
    then
        echo "HDD"
    elif [[ $dname =~ ^nvme ]]
    then
        echo "SSD"
    elif [[ $dname =~ ^sr ]]
    then
        echo "ODD"
    elif [[ $dname =~ ^xvd ]]
    then
        echo "HDD"
    elif [[ $dname =~ ^mmc ]]
    then
        echo "SSD"
    fi
}

getMountPoint(){
    pname="/dev/$1"
    mp=`df -hT|egrep "${pname} "|awk '{print $NF}'`
    echo ${mp}
}

# 文件系统类型
getSysFileType(){
    pname="/dev/$1"
    sz=`df -hT|grep ${pname}|awk '{print $2}'`
    echo ${sz}
}

## get all  block
tmp_arr=()
for dname in `ls ${SYSBLOCK_DIR}/`
do
    if [[  ${dname} =~ ^loop ||  ${dname} =~ ^nb ||   ${dname} =~ ^ram  ||  ${dname} =~ ^sr  ]]
    then
        continue
    fi

    raiddev=false
        ## 是否存在磁盘做了软raid
    if [ -e /proc/mdstat ];then
        IFS=' ' read -ra array <<< `cat  /proc/mdstat |grep md|awk -F: '{print $2}'| sed 's/\[[0-9]\]//g'`
        for raidname in "${array[@]}"
        do
            if [ ${dname} == ${raidname} ];then
                raiddev=true
                break
            fi
        done
    fi
    if [ "$raiddev" = true ];then
        continue
    fi
    # echo  -n "${dname}: "
    diskType=`getDiskType ${dname}`
    # echo "${diskType}"
    rotational=`cat ${SYSBLOCK_DIR}/${dname}/queue/rotational`
    # echo ${rotational}
    if [ ! $rotational == 1 ]
    then
        diskType="SSD"
    fi
    partitioned=false
    parttions=($(lsblk |grep $dname|grep  part|awk -F"└─|-" '{print $2}'|awk '{print $1}'))
    if [ ${#parttions[*]} -ge 1 ];then
        partitioned=true
    else
        parttions=(${dname})
    fi
    for part in ${parttions[*]}
    do
                    # 不采集根目录磁盘的大小
                    mp=`getMountPoint ${part}`
                    if [ -z "$mp" ];then
                        mp=`getMountPoint ${dname}`
                    fi 
                    if [ -z "$mp" ];then
                        continue
                    fi 
                    if [ ${mp} == "/" ];then
                        continue
                    fi
                    if [ "$partitioned" = true ];then
                        sz=`cat ${SYSBLOCK_DIR}/${dname}/${part}/size`
                    else
                        sz=`cat ${SYSBLOCK_DIR}/${part}/size`
                    fi
                    sz=$((sz+0)) 
                    totalSize=`expr $sz \* 512 / 1024 / 1024 / 1024`   
                    sft=`getSysFileType ${part}`
                    if [ -f ${SYSBLOCK_DIR}/${dname}/serial ]
                    then
                        diskId=`cat  ${SYSBLOCK_DIR}/${dname}/serial`
                    fi
                    tmp_arr[${#tmp_arr[*]}]="{\"mount_point\":\"${mp}\",\"size\":${totalSize},\"file_type\":\"${sft}\",\"disk_type\":\"${diskType}\",\"disk_id\":\"${diskId}\"}"
                    continue
    done
done


cpunum=`cat /proc/cpuinfo| grep "processor"| wc -l`
memsize=`free -m | awk '/Mem/ {print $2}'`
curl http://${META_DOMAIN}/latest/meta-data/placement/region -s -o /dev/null
if [ $? -eq 0 ]
then
    region=`curl http://${META_DOMAIN}/latest/meta-data/placement/region -s -o /dev/null`
fi
curl http://$META_DOMAIN/latest/meta-data/placement/zone -s -o /dev/null
if [ $? -eq 0 ]
then
    zone=`curl http://${META_DOMAIN}/latest/meta-data/placement/zone -s -o /dev/null`
fi
echo -n "{\"cpu\":${cpunum},\"mem\":${memsize},\"region\":\"${region}\",\"zone\":\"${zone}\","
length=${#tmp_arr[@]}
stop=$(($length-1))
echo -n "\"disk\":["
for ((i=0; i<$length; i++))
do
    echo -n ${tmp_arr[$i]}
    if [[ ! $i == $stop ]];
    then
        echo -n ","
    fi
done
echo -n "]}"