package redis

import (
	"fmt"
	"strings"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// RedisClusterSwitch tendisplus switch instance
type RedisClusterSwitch struct {
	RedisSwitchInfo
	// the slave already switched to master
	slave2M *dbutil.SlaveInfo
}

// CheckSwitch nothing to check
func (ins *RedisClusterSwitch) CheckSwitch() (bool, error) {
	return true, nil
}

// DoSwitch only check the status of tendisplus instance
func (ins *RedisClusterSwitch) DoSwitch() error {
	log.Logger.Infof("redis do switch. info:{%s}", ins.ShowSwitchInstanceInfo())
	slave2Master := false
	for _, slave := range ins.Slave {
		isMaster, err := ins.CheckSlaveMaster(&slave)
		if err != nil {
			log.Logger.Infof("redisC Check slave is master err[%s]", err.Error())
			continue
		}

		if isMaster {
			slave2Master = true
			ins.slave2M = &slave
			log.Logger.Infof("redisC find slave[%s:%d] is master", slave.Ip, slave.Port)
			break
		}
	}

	if slave2Master {
		log.Logger.Infof("redisC have slave[%s:%d] switch to master",
			ins.slave2M.Ip, ins.slave2M.Port)
		return nil
	}
	switchInfoLog := fmt.Sprintf("no slave changed to master, maybe auto switch failed. info:%s",
		ins.ShowSwitchInstanceInfo())
	ins.ReportLogs(constvar.InfoResult, switchInfoLog)
	log.Logger.Infof(switchInfoLog)
	return nil
}

// ShowSwitchInstanceInfo show switch instance
func (ins *RedisClusterSwitch) ShowSwitchInstanceInfo() string {
	format := `<%s#%d IDC:%d Status:%s App:%s ClusterType:%s MachineType:%s Cluster:%s> switch`
	str := fmt.Sprintf(
		format, ins.Ip, ins.Port, ins.IdcID, ins.Status, ins.App,
		ins.ClusterType, ins.MetaType, ins.Cluster,
	)
	return str
}

// RollBack TODO
func (ins *RedisClusterSwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo TODO
func (ins *RedisClusterSwitch) UpdateMetaInfo() error {
	return nil
}

// CheckConfig TODO
func (ins *RedisClusterSwitch) CheckConfig() bool {
	return true
}

// CheckSlaveMaster check if the slave of this instance is change to master role
func (ins *RedisClusterSwitch) CheckSlaveMaster(slave *dbutil.SlaveInfo) (bool, error) {
	r := &client.RedisClient{}
	addr := fmt.Sprintf("%s:%d", slave.Ip, slave.Port)
	if ins.Pass == "" {
		ins.Pass = GetPassByClusterID(ins.GetClusterId(), ins.GetMetaType())
	}
	r.Init(addr, ins.Pass, ins.Timeout, 0)
	defer r.Close()

	rsp, err := r.Info()
	if err != nil {
		log.Logger.Errorf("slave exec redis info failed,addr=%s,err=%s",
			addr, err.Error())
		return false, err
	}

	rspInfo, _ := rsp.(string)
	if !strings.Contains(rspInfo, "cluster_enabled:1") {
		redisErr := fmt.Errorf("slave not support cluster,addr:%s,info:%s,rsp:%s",
			addr, ins.ShowSwitchInstanceInfo(), rspInfo)
		log.Logger.Errorf(redisErr.Error())
	}

	log.Logger.Debugf("redisC switch slaveCheckMaster slave[%s] rsp:%s", addr, rspInfo)
	if strings.Contains(rspInfo, "role:master") {
		log.Logger.Infof("Slave already begin master,info:{%s},slave:{%s:%d}",
			ins.ShowSwitchInstanceInfo(), slave.Ip, slave.Port)
		return true, nil
	}
	return false, nil
}
