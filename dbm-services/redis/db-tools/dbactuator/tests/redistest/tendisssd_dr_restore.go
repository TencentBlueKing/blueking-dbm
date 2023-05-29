package redistest

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"path/filepath"
	"time"
)

// TendisSsdDrRestoreTest tendis-ssd 重建dr测试
type TendisSsdDrRestoreTest struct {
	atomredis.TendisssdDrRestoreParams
	Err error `json:"-"`
}

// SetMasterIP set master ip,传入为空则自动获取本地ip
func (test *TendisSsdDrRestoreTest) SetMasterIP(ip string) *TendisSsdDrRestoreTest {
	if test.Err != nil {
		return test
	}
	if ip == "" || ip == "127.0.0.1" {
		ip, test.Err = util.GetLocalIP()
		if test.Err != nil {
			return test
		}
	}
	test.MasterIP = ip
	return test
}

// SetMasterPorts set ports
// 如果ports=[],startPort=0,instNum=0,则默认startPort=40000,instNum=4
func (test *TendisSsdDrRestoreTest) SetMasterPorts(ports []int, startPort, instNum int) *TendisSsdDrRestoreTest {
	if test.Err != nil {
		return test
	}
	if len(ports) == 0 {
		if startPort == 0 {
			startPort = consts.TestTendisSSDMasterStartPort
		}
		if instNum == 0 {
			instNum = 4
		}
		for i := 0; i < instNum; i++ {
			ports = append(ports, startPort+i)
		}
	}
	test.MasterPorts = ports
	test.MasterStartPort = startPort
	test.MasterInstNum = instNum
	return test
}

// SetMasterAuth set master auth,传入为空则password=xxxxx
func (test *TendisSsdDrRestoreTest) SetMasterAuth(password string) *TendisSsdDrRestoreTest {
	if test.Err != nil {
		return test
	}
	if password == "" {
		password = "xxxx"
	}
	test.MasterAuth = password
	return test
}

// SetSlaveIP set slave ip,传入为空则自动获取本地ip
func (test *TendisSsdDrRestoreTest) SetSlaveIP(ip string) *TendisSsdDrRestoreTest {
	if test.Err != nil {
		return test
	}
	if ip == "" || ip == "127.0.0.1" {
		ip, test.Err = util.GetLocalIP()
		if test.Err != nil {
			return test
		}
	}
	test.SlaveIP = ip
	return test
}

// SetSlavePorts set ports
// 如果ports=[],startPort=0,instNum=0,则默认startPort=40000,instNum=4
func (test *TendisSsdDrRestoreTest) SetSlavePorts(ports []int, startPort, instNum int) *TendisSsdDrRestoreTest {
	if test.Err != nil {
		return test
	}
	if len(ports) == 0 {
		if startPort == 0 {
			startPort = consts.TestTendisSSDSlaveStartPort
		}
		if instNum == 0 {
			instNum = 4
		}
		for i := 0; i < instNum; i++ {
			ports = append(ports, startPort+i)
		}
	}
	test.SlavePorts = ports
	test.SlaveStartPort = startPort
	test.SlaveInstNum = instNum
	return test
}

// SetSlavePasswd set slave password,传入为空则password=xxxxx
func (test *TendisSsdDrRestoreTest) SetSlavePasswd(password string) *TendisSsdDrRestoreTest {
	if test.Err != nil {
		return test
	}
	if password == "" {
		password = "xxxx"
	}
	test.SlavePassword = password
	return test
}

// SetBackupDir set backup dir 设置backup dir
func (test *TendisSsdDrRestoreTest) SetBackupDir(dir string) *TendisSsdDrRestoreTest {
	if test.Err != nil {
		return test
	}
	if dir == "" {
		dir = filepath.Join(consts.GetRedisBackupDir(), "dbbak")
	}
	test.BackupDir = dir
	return test
}

// SetBackupTasks 设置备份信息
func (test *TendisSsdDrRestoreTest) SetBackupTasks(bakTasks []atomredis.BackupTask) *TendisSsdDrRestoreTest {
	if test.Err != nil {
		return test
	}
	test.BackupTasks = bakTasks
	return test
}

// RunRestore 执行ssd restore
func (test *TendisSsdDrRestoreTest) RunRestore() {
	msg := fmt.Sprintf("=========TendisSSDDrRestore test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========TendisSSDDrRestore test fail============")
		} else {
			msg = fmt.Sprintf("=========TendisSSDDrRestore test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewTendisssdDrRestore().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// SsdRestore ssd恢复slave
func SsdRestore(masterIP string, masterPorts []int, masterStartPort, masterInstNum int, masterAuth string,
	slaveIP string, slavePorts []int, slaveStartPort, slaveInstNum int, slavePasswd string,
	backupDir string, bakTasks []atomredis.BackupTask) (err error) {
	restoreTask := TendisSsdDrRestoreTest{}
	restoreTask.SetMasterIP(masterIP).
		SetMasterPorts(masterPorts, masterStartPort, masterInstNum).
		SetMasterAuth(masterAuth).
		SetSlaveIP(slaveIP).
		SetSlavePorts(slavePorts, slaveStartPort, slaveInstNum).
		SetSlavePasswd(slavePasswd).
		SetBackupDir(backupDir).
		SetBackupTasks(bakTasks)
	if restoreTask.Err != nil {
		return restoreTask.Err
	}
	restoreTask.RunRestore()
	if restoreTask.Err != nil {
		return
	}
	return nil
}
