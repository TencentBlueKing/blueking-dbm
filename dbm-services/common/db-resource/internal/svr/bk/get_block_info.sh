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
    #echo  -n "${dname}: "
    diskType=`getDiskType ${dname}`
    #echo "${diskType}"
    rotational=`cat ${SYSBLOCK_DIR}/${dname}/queue/rotational`
    #echo ${rotational}
    if [ ! $rotational == 1 ]
    then
        diskType="SSD"
    fi

    if [[ ${dname} =~ nvme && ${dname} != nvme ]]  || [[ ${dname} =~  ^md[0-9] ]] || [[ ${dname} == "fioa" ]] 
    then
        mp=`getMountPoint ${dname}`
        sz=`cat ${SYSBLOCK_DIR}/${dname}/size`
        sz=$((sz+0)) 
        totalSize=`expr $sz \* 512 / 1024 / 1024 / 1024`   
        sft=`getSysFileType ${dname}`
        #echo -n "{\"MountPoint\":\"${mp}\",\"Size\":${totalSize},\"FileType\":\"${sft}\",\"DiskType\":\"${diskType}\"}"
        if [ -f ${SYSBLOCK_DIR}/${dname}/serial ]
        then
            diskId=`cat  ${SYSBLOCK_DIR}/${dname}/serial`
        fi
        tmp_arr[${#tmp_arr[*]}]="{\"mount_point\":\"${mp}\",\"size\":${totalSize},\"file_type\":\"${sft}\",\"disk_type\":\"${diskType}\",\"disk_id\":\"${diskId}\"}"
        continue
   fi

    pt=0
    for pname in `ls  ${SYSBLOCK_DIR}/${dname}`
    do
        if [[  ! ${pname} =~ ^${dname} ]]
        then
            continue   
        fi
        pt=$((pt+1))
        mp=`getMountPoint ${pname}`
        sft=`getSysFileType ${pname}` 
        sz=`cat ${SYSBLOCK_DIR}/${dname}/${pname}/size`     
        sz=$((sz+0)) 
        totalSize=`expr $sz \* 512 / 1024 / 1024 / 1024  `   
        if [[ ! ${mp} =~ data ]]
        then
            continue
        fi
        if [ -f ${SYSBLOCK_DIR}/${dname}/serial ]
        then
            diskId=`cat  ${SYSBLOCK_DIR}/${dname}/serial`
        fi
        tmp_arr[${#tmp_arr[*]}]="{\"mount_point\":\"${mp}\",\"size\":${totalSize},\"file_type\":\"${sft}\",\"disk_type\":\"${diskType}\",\"disk_id\":\"${diskId}\"}"
    done
    if [[ $pt == 0 ]];
    then
        mp=`getMountPoint ${dname}`
        sz=`cat ${SYSBLOCK_DIR}/${dname}/size`
        sz=$((sz+0)) 
        totalSize=`expr $sz \* 512 / 1024 / 1024 / 1024`   
        sft=`getSysFileType ${dname}`
        #echo -n "{\"MountPoint\":\"${mp}\",\"Size\":${totalSize},\"FileType\":\"${sft}\",\"DiskType\":\"${diskType}\"}"
        if [ -f ${SYSBLOCK_DIR}/${dname}/serial ]
        then
            diskId=`cat  ${SYSBLOCK_DIR}/${dname}/serial`
        fi
        tmp_arr[${#tmp_arr[*]}]="{\"mount_point\":\"${mp}\",\"size\":${totalSize},\"file_type\":\"${sft}\",\"disk_type\":\"${diskType}\",\"disk_id\":\"${diskId}\"}"
    fi
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