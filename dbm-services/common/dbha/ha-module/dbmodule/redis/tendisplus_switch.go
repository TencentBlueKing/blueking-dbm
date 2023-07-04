package redis

import (
	"fmt"
	"strings"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
)

// TendisplusSwitch TODO
type TendisplusSwitch struct {
	RedisSwitchInfo
	slave2M *RedisSlaveInfo
}

// CheckSwitch TODO
func (ins *TendisplusSwitch) CheckSwitch() (bool, error) {
	return true, nil
}

// DoSwitch TODO
func (ins *TendisplusSwitch) DoSwitch() error {
	log.Logger.Infof("redis do switch. info:{%s}", ins.ShowSwitchInstanceInfo())
	slave2Master := false
	for _, slave := range ins.Slave {
		isMaster, err := ins.CheckSlaveMaster(&slave)
		if err != nil {
			log.Logger.Infof("Tendisplus Check slave is master err[%s]", err.Error())
			continue
		}

		if isMaster {
			slave2Master = true
			ins.slave2M = &slave
			log.Logger.Infof("Tendisplus find slave[%s:%d] is master",
				slave.Ip, slave.Port)
			break
		}
	}

	if slave2Master {
		log.Logger.Infof("Tendisplus have slave[%s:%d] switch to master",
			ins.slave2M.Ip, ins.slave2M.Port)
		return nil
	} else {
		switchInfoLog := fmt.Sprintf("no slave change to master, info:%s",
			ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.SwitchInfo, switchInfoLog)
		log.Logger.Infof(switchInfoLog)
		return nil
	}
}

// ShowSwitchInstanceInfo TODO
func (ins *TendisplusSwitch) ShowSwitchInstanceInfo() string {
	format := `<%s#%d IDC:%s Status:%s App:%s ClusterType:%s MachineType:%s Cluster:%s> switch`
	str := fmt.Sprintf(
		format, ins.Ip, ins.Port, ins.IDC, ins.Status, ins.App,
		ins.ClusterType, ins.MetaType, ins.Cluster,
	)
	return str
}

// RollBack TODO
func (ins *TendisplusSwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo TODO
func (ins *TendisplusSwitch) UpdateMetaInfo() error {
	return nil
}

// CheckConfig TODO
func (ins *TendisplusSwitch) CheckConfig() bool {
	return true
}

// CheckSlaveMaster check if the slave of this instance is change to master role
func (ins *TendisplusSwitch) CheckSlaveMaster(slave *RedisSlaveInfo) (bool, error) {
	r := &client.RedisClient{}
	addr := fmt.Sprintf("%s:%d", slave.Ip, slave.Port)
	r.Init(addr, ins.Pass, ins.Timeout, 0)
	defer r.Close()

	rsp, err := r.Info()
	if err != nil {
		log.Logger.Errorf("slave exec redis info failed,addr=%s,err=%s",
			addr, err.Error())
		return false, err
	}

	rspInfo, ok := rsp.(string)
	if !ok {
		redisErr := fmt.Errorf("slave exec redis info response type is not string")
		log.Logger.Errorf(redisErr.Error())
		return false, redisErr
	}

	if !strings.Contains(rspInfo, "cluster_enabled:1") {
		redisErr := fmt.Errorf("slave not support cluster,addr:%s,info:%s,rsp:%s",
			addr, ins.ShowSwitchInstanceInfo(), rspInfo)
		log.Logger.Errorf(redisErr.Error())
		return false, redisErr
	}

	log.Logger.Debugf("Tendisplus switch slaveCheckMaster slave[%s] rsp:%s",
		addr, rspInfo)
	if strings.Contains(rspInfo, "role:master") {
		log.Logger.Infof("Slave already begin master,info:{%s},slave:{%s:%d}",
			ins.ShowSwitchInstanceInfo(), slave.Ip, slave.Port)
		return true, nil
	}
	return false, nil
}

// ParseRole parse tendisplus role by the response of info command
func (ins *TendisplusSwitch) ParseRole(info string) (string, error) {
	beginPos := strings.Index(info, "role:")
	if beginPos < 0 {
		roleErr := fmt.Errorf("tendisplus rsp not contains role")
		log.Logger.Errorf(roleErr.Error())
		return "", roleErr
	}

	endPos := strings.Index(info[beginPos:], "\r\n")
	if endPos < 0 {
		roleErr := fmt.Errorf("tendisplus the substr is invalid,%s",
			info[beginPos:])
		log.Logger.Errorf(roleErr.Error())
		return "", roleErr
	}

	roleInfo := info[beginPos+len("role:") : beginPos+endPos]
	return roleInfo, nil
}
