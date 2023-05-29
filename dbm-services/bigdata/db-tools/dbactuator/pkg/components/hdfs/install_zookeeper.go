package hdfs

import (
	"fmt"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

// InstallZookeeperService TODO
type InstallZookeeperService struct {
	GeneralParam *components.GeneralParam
	Params       *InstallHdfsParams
	ZookeeperConfig
	InstallParams
	RollBackContext rollback.RollBackObjects
}

// ZookeeperConfig TODO
type ZookeeperConfig struct {
	TickTime   int
	InitLimit  int
	SyncLimit  int
	DataDir    string
	DataLogDir string
	ClientPort int
	MyId       int
}

// RenderZookeeperConfig TODO
func (i *InstallZookeeperService) RenderZookeeperConfig() (err error) {

	extraCmd := fmt.Sprintf("mkdir -p %s %s; chown -R hadoop:root %s",
		i.InstallDir+"/zookeeper/data", i.InstallDir+"/zookeeper/logs", i.InstallDir+"/zookeeper/")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	nodeIp := i.Params.Host
	zookeeperIpList := strings.Split(i.Params.ZkIps, ",")

	logger.Info("zoo.cfg")
	extraCmd = fmt.Sprintf(`echo "tickTime=2000
initLimit=10
syncLimit=5
dataDir=/data/hadoopenv/zookeeper/data
dataLogDir=/data/hadoopenv/zookeeper/logs
clientPort=2181
autopurge.snapRetainCount=3
autopurge.purgeInterval=1
server.0=%s:2888:3888
server.1=%s:2888:3888
server.2=%s:2888:3888" > %s`, zookeeperIpList[0], zookeeperIpList[1], zookeeperIpList[2], "/data/hadoopenv/zookeeper/conf/zoo.cfg")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("myid")
	myidNum := 0
	for i := 0; i < len(zookeeperIpList); i++ {
		if nodeIp == zookeeperIpList[i] {
			myidNum = i
			break
		}
	}
	extraCmd = fmt.Sprintf(`echo %d > %s`, myidNum, i.InstallDir+"/zookeeper/data/myid")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	return nil
}

// InstallZookeeper TODO
func (i *InstallZookeeperService) InstallZookeeper() (err error) {

	if err := i.RenderZookeeperConfig(); err != nil {
		logger.Error("RenderZookeeperConfig failed, %v", err)
		return err
	}
	return SupervisorUpdateZooKeeperConfig(i.SupervisorConfDir)
}

// UpdateZooKeeperConfigParams TODO
type UpdateZooKeeperConfigParams struct {
	Host   string `json:"host" validate:"required,ip"`
	OldIps string `json:"old_zk_ips" validate:"required"`
	NewIps string `json:"new_zk_ips" validate:"required"`
}

// UpdateZooKeeperConfigService TODO
type UpdateZooKeeperConfigService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *UpdateZooKeeperConfigParams
	RollBackContext rollback.RollBackObjects
}

// UpdateZooKeeperConfig TODO
func (i *UpdateZooKeeperConfigService) UpdateZooKeeperConfig() (err error) {

	configName := "/data/hadoopenv/zookeeper/conf/zoo.cfg"
	oldZkList := strings.Split(i.Params.OldIps, ",")
	newZkList := strings.Split(i.Params.NewIps, ",")
	if len(oldZkList) != len(newZkList) {
		return errors.New("替换ZK IP数量不一致")
	}
	for i, _ := range oldZkList {
		replaceCommand := fmt.Sprintf("sed -i 's/\\<%s\\>/%s/g' %s",
			oldZkList[i], newZkList[i], configName)
		if _, err = osutil.ExecShellCommand(false, replaceCommand); err != nil {
			logger.Error("%s execute failed, %v", replaceCommand, err)
		}
	}
	return nil
}
