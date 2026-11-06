package hdfs

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

// GenerateKeyParams TODO
type GenerateKeyParams struct {
	Host string `json:"host" validate:"required,ip"`
}

// GenerateKeyService TODO
type GenerateKeyService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params *GenerateKeyParams

	RollBackContext rollback.RollBackObjects
}

// GenerateKeyResult TODO
type GenerateKeyResult struct {
	Key string `json:"key"`
}

// GenerateKey TODO
func (i *GenerateKeyService) GenerateKey() (err error) {

	executeCmd := "if [ ! -f ~/.ssh/id_rsa.pub ]; then ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa -q; fi;"
	if _, err := osutil.ExecShellCommand(false, executeCmd); err != nil {
		logger.Error("%s execute failed, %v", executeCmd, err)
	}
	catKeyCmd := " cat ~/.ssh/id_rsa.pub | xargs echo -n"
	if result, err := osutil.ExecShellCommand(false, catKeyCmd); err != nil {
		logger.Error("%s execute failed, %v", catKeyCmd, err)
		return err
	} else {
		resultStruct := GenerateKeyResult{
			Key: result,
		}
		jsonBytes, err := json.Marshal(resultStruct)
		if err != nil {
			logger.Error("transfer resultStruct to json failed", err.Error())
			return err
		}
		// 标准输出 json返回结果
		fmt.Printf("<ctx>%s</ctx>", string(jsonBytes))
		return nil
	}
}

// WriteKeyParams TODO
type WriteKeyParams struct {
	Host string `json:"host" validate:"required,ip"`
	Key  string `json:"key" validate:"required"`
}

// WriteKeyService TODO
type WriteKeyService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *WriteKeyParams
	RollBackContext rollback.RollBackObjects
}

// WriteKey TODO
func (i *WriteKeyService) WriteKey() (err error) {
	// mkdir/echo 不依赖组件环境变量，无需加载 profile
	executeCmd := fmt.Sprintf(
		"su - %s -c \"mkdir -p ~/.ssh/; echo '%s' >> ~/.ssh/authorized_keys\"",
		i.ExecuteUser, i.Params.Key)
	if _, err := osutil.ExecShellCommand(false, executeCmd); err != nil {
		logger.Error("%s execute failed, %v", executeCmd, err)
	}
	return nil
}

// ScpDirParams TODO
type ScpDirParams struct {
	Host      string `json:"host" validate:"required,ip"`
	Dest      string `json:"dest" validate:"required,ip"`
	Component string `json:"component"`
	// Dir 		   string `json:"dir" validate:"required"`
	// DestDir        string `json:"dest_dir"`
}

// ScpDirService TODO
type ScpDirService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *ScpDirParams
	RollBackContext rollback.RollBackObjects
}

// ScpDir TODO
func (i *ScpDirService) ScpDir() (err error) {

	metaDataDirs := GetMetaDataDirByRole(i.Params.Component)
	for _, metaDataDir := range metaDataDirs {
		executeCmd := fmt.Sprintf("scp -o \"StrictHostKeyChecking no\" -r %s %s@%s:%s 2>&1",
			metaDataDir, i.ExecuteUser, i.Params.Dest, metaDataDir)
		if _, err := osutil.ExecShellCommand(false, executeCmd); err != nil {
			logger.Error("%s execute failed, %v", executeCmd, err)
			return err
		}
	}
	return nil
}

// GetMetaDataDirByRole TODO
func GetMetaDataDirByRole(component string) []string {
	metaDataDirs := make([]string, 0)
	switch component {
	case NameNode:
		metaDataDirs = []string{"/data/hadoopdata/name"}
	case JournalNode:
		metaDataDirs = []string{"/data/hadoopdata/jn"}
	case ZooKeeper:
		metaDataDirs = []string{"/data/hadoopenv/zookeeper/conf/zoo.cfg",
			"/data/hadoopenv/zookeeper/data", "/data/hadoopenv/zookeeper/logs"}
	}
	return metaDataDirs
}

// CheckActiveParams TODO
type CheckActiveParams struct {
	Host  string `json:"host" validate:"required,ip"`
	Nn1Ip string `json:"nn1_ip" validate:"required"`
	Nn2Ip string `json:"nn2_ip" validate:"required"`
}

// CheckActiveService TODO
type CheckActiveService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *CheckActiveParams
	RollBackContext rollback.RollBackObjects
}

// NameNode HA 服务状态，hdfs haadmin -getServiceState 的合法输出。
// 上游 dbm-ui 的 update_hdfs_resource.py 按 cluster_active_info["active"] / ["standby"]
// 取值，因此这两个状态必须同时拿到，且不能出现其它 key。
const (
	nnStateActive  = "active"
	nnStateStandby = "standby"
)

// getNameNodeServiceState 查询单个 NameNode 的 HA 状态。
// 使用 ExecShellCommandJ（仅 exit code 非 0 才算失败）：hdfs 脚本会把 log4j 告警写到 stderr，
// 用 ExecShellCommand 会因「stderr 非空即失败」把正常查询判为失败。
func (i *CheckActiveService) getNameNodeServiceState(nnName string) (string, error) {
	cmd := fmt.Sprintf("su - %s -c \"%s hdfs haadmin -getServiceState %s\"",
		i.ExecuteUser, LoadProfileCmd, nnName)
	output, err := osutil.ExecShellCommandJ(false, cmd)
	if err != nil {
		return "", errors.WithMessagef(err, "execute [%s] failed", cmd)
	}
	state := strings.ToLower(strings.TrimSpace(output))
	if state != nnStateActive && state != nnStateStandby {
		return "", errors.Errorf("unexpected service state of %s: %q", nnName, state)
	}
	return state, nil
}

// CheckActive 查询 nn1/nn2 的主备状态，以 {"active": ip, "standby": ip} 的形式输出。
func (i *CheckActiveService) CheckActive() (err error) {
	maxRetryCount := 3
	checkActiveResult := make(map[string]string, 2)

	for retryCount := 0; retryCount < maxRetryCount; retryCount++ {
		time.Sleep(5 * time.Second)

		nn1State, nn1Err := i.getNameNodeServiceState("nn1")
		if nn1Err != nil {
			logger.Error("get nn1 service state failed, %v", nn1Err)
			continue
		}
		nn2State, nn2Err := i.getNameNodeServiceState("nn2")
		if nn2Err != nil {
			logger.Error("get nn2 service state failed, %v", nn2Err)
			continue
		}
		// 必须是一主一备，同为 active（脑裂）或同为 standby（无主）都要重试
		if nn1State == nn2State {
			logger.Error("nn1 and nn2 are both %s, retrying", nn1State)
			continue
		}

		checkActiveResult[nn1State] = i.Params.Nn1Ip
		checkActiveResult[nn2State] = i.Params.Nn2Ip
		break
	}

	// 重试耗尽仍未拿到完整主备信息时必须报错：
	// 若返回空 map 且不报错，上游会把「没查到主备」当成功结果继续执行后续替换动作
	if len(checkActiveResult) != 2 {
		return errors.Errorf("failed to get active/standby namenode after %d retries", maxRetryCount)
	}

	jsonBytes, err := json.Marshal(checkActiveResult)
	if err != nil {
		logger.Error("transfer checkActiveResult to json failed, %v", err)
		return err
	}
	// 标准输出 json返回结果
	fmt.Printf("<ctx>%s</ctx>", string(jsonBytes))
	return nil
}
