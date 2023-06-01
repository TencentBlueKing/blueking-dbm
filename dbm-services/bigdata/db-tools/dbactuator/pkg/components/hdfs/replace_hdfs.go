package hdfs

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
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
	executeCmd := fmt.Sprintf("su - %s -c \"mkdir -p ~/.ssh/; echo '%s' >> ~/.ssh/authorized_keys\"",
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

// CheckActive TODO
func (i *CheckActiveService) CheckActive() (err error) {
	checkActiveResult := make(map[string]string, 2)
	checkNn1Cmd := fmt.Sprintf("su - %s -c \"hdfs haadmin -getServiceState nn1 | xargs echo -n\"", i.ExecuteUser)
	checkNn2Cmd := fmt.Sprintf("su - %s -c \"hdfs haadmin -getServiceState nn2 | xargs echo -n\"", i.ExecuteUser)

	maxRetryCount := 3
	// var interval int = 5
	for retryCount := 0; retryCount < maxRetryCount; retryCount++ {
		time.Sleep(5 * time.Second)
		if result, err := osutil.ExecShellCommand(false, checkNn1Cmd); err != nil {
			logger.Error("%s execute failed, %v", checkNn1Cmd, err)
			continue
		} else {
			checkActiveResult[result] = i.Params.Nn1Ip
		}
		if result, err := osutil.ExecShellCommand(false, checkNn2Cmd); err != nil {
			logger.Error("%s execute failed, %v", checkNn2Cmd, err)
			continue
		} else {
			checkActiveResult[result] = i.Params.Nn2Ip
			break
		}
	}

	jsonBytes, err := json.Marshal(checkActiveResult)
	if err != nil {
		logger.Error("transfer checkActiveResult to json failed", err.Error())
		return err
	}
	// 标准输出 json返回结果
	fmt.Printf("<ctx>%s</ctx>", string(jsonBytes))
	return nil
}
