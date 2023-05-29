// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/components"
	"dbm-services/riak/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
	"fmt"

	"gopkg.in/ini.v1"
)

// GetConfigComp TODO
type GetConfigComp struct {
	Params              *GetConfigParam `json:"extend"`
	GetConfigRunTimeCtx `json:"-"`
}

// GetConfigParam TODO
type GetConfigParam struct {
}

// GetConfigRunTimeCtx 运行时上下文
type GetConfigRunTimeCtx struct {
	Configs map[string]string
}

// Config Config
type Config struct {
	DistributedCookie string `json:"distributed_cookie"`
	RingSize          string `json:"ring_size"`

	// riak legs战绩模块历史数据过期删除
	LeveldbExpiration              string `json:"leveldb.expiration"`
	LeveldbExpirationMode          string `json:"leveldb.expiration.mode"`
	LeveldbExpirationRetentionTime string `json:"leveldb.expiration.retention_time"`
}

// GetConfig 获取配置
func (i *GetConfigComp) GetConfig() error {
	localIp, err := osutil.GetLocalIP()
	if err != nil {
		logger.Error("get local ip error: %s", err.Error())
		return err
	}
	checkStatus := fmt.Sprintf(`%s | grep " riak@%s " | grep 'valid'`, cst.ClusterStatusCmd, localIp)
	_, err = osutil.ExecShellCommand(false, checkStatus)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", checkStatus, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", checkStatus, err.Error())
		return err
	}
	// riak实例的参数
	cmd := "riak config effective"
	config, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
		return err
	}
	// 生成ini文件
	file, err := ini.Load([]byte(config))
	if err != nil {
		logger.Error("riak config template to ini file error: %s", err.Error())
		return err
	}
	// 配置项
	i.Configs = map[string]string{
		"ring_size":                         "",
		"distributed_cookie":                "",
		"leveldb.expiration":                "",
		"leveldb.expiration.mode":           "",
		"leveldb.expiration.retention_time": "",
	}
	// 获取ini文件中的配置值
	for k, _ := range i.Configs {
		key, err := file.Section(file.SectionStrings()[0]).GetKey(k)
		if err != nil {
			logger.Error("riak get config [%s] error: %s", k, err.Error())
			return err
		}
		if key.Value() == "" {
			logger.Error("riak get config [%s] error: value is null", k)
			return fmt.Errorf("riak get config [%s] error: value is null", k)
		}
		i.Configs[k] = key.Value()
	}
	return nil
}

// OutputConfigInfo 输出config信息
func (i *GetConfigComp) OutputConfigInfo() error {
	err := components.PrintOutputCtx(&i.Configs)
	if err != nil {
		logger.Error("print config failed: %s.", err.Error())
		return err
	}
	return nil
}
