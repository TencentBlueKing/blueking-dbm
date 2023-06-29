// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/components"
	"dbm-services/riak/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/riak/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"path"
	"strings"
	"time"

	"gopkg.in/ini.v1"
)

// InstallRiakComp TODO
type InstallRiakComp struct {
	Params                *InstallRaikParam `json:"extend"`
	InstallRiakRunTimeCtx `json:"-"`
}

// InstallRaikParam TODO
type InstallRaikParam struct {
	Pkg                            components.Medium `json:"pkg" validate:"required"`
	DistributedCookie              *string           `json:"distributed_cookie" validate:"required"`
	RingSize                       *string           `json:"ring_size" validate:"required"`
	LeveldbExpiration              *string           `json:"leveldb.expiration"  validate:"required"`
	LeveldbExpirationMode          *string           `json:"leveldb.expiration.mode"  validate:"required"`
	LeveldbExpirationRetentionTime *string           `json:"leveldb.expiration.retention_time"  validate:"required"`
}

// InstallRiakRunTimeCtx 运行时上下文
type InstallRiakRunTimeCtx struct {
	DataDir string
	Config  map[string]string
	LocalIp string
}

// Init TODO
func (i *InstallRiakComp) Init() error {
	mountpoint, err := osutil.FindFirstMountPoint(
		cst.DefaultDataRootPath,
		cst.AlterNativeDataRootPath,
	)
	if err != nil {
		logger.Error("not found mount point: %s", err.Error())
		return err
	}
	if osutil.IsDataDirOk(mountpoint) {
		i.DataDir = mountpoint
	} else {
		logger.Error("%s could not be data dir", mountpoint)
		return fmt.Errorf("%s could not be data dir", mountpoint)
	}
	platformDataDir := path.Join(mountpoint, cst.DataDir)
	cmd := fmt.Sprintf("mkdir -p %s; chown -R riak:root %s", platformDataDir, platformDataDir)
	_, err = osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
		return err
	}
	return nil
}

// PreCheck 预检查
func (i *InstallRiakComp) PreCheck() error {
	// 空闲检查
	err := i.OsClearCheck()
	if err != nil {
		logger.Error("OsClearCheck failed: %s", err.Error())
		return err
	}
	// 校验介质
	err = i.Params.Pkg.Check()
	if err != nil {
		logger.Error("riak rpm package check failed: %s", err.Error())
		return err
	}
	return nil
}

// OsClearCheck 空闲检查
func (i *InstallRiakComp) OsClearCheck() error {
	cmd := fmt.Sprintf(`%s | grep 'RESULT:' | cut -d':' -f2`, cst.OsClearScriptPath)
	result, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("[%s] error occurs while checking os clear %s", cmd, err.Error())
		return fmt.Errorf("[%s] error occurs while checking os clear %s", cmd, err.Error())
	}
	ignoreDirtyFile := fmt.Sprintf("%s%s", result[0:3], result[4:5])
	if strings.Contains(ignoreDirtyFile, "1") {
		cmd = fmt.Sprintf(`%s | grep 'dirty' | grep -v 'dirty FILE'`, cst.OsClearScriptPath)
		dirty, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			logger.Error("[%s] error occurs while checking os clear %s", cmd, err.Error())
			return fmt.Errorf("[%s] error occurs while checking os clear %s", cmd, err.Error())
		}
		logger.Error("os not clear:\n %s", dirty)
		return fmt.Errorf("os not clear:\n %s", dirty)
	}
	return nil
}

// CreateConfigFile 创建riak配置文件
func (i *InstallRiakComp) CreateConfigFile() error {
	bytes, err := staticembed.RiakConfigTemplate.ReadFile(staticembed.RiakConfigTemplateFileName)
	if err != nil {
		logger.Error("read riak config template failed %s", err.Error())
		return err
	}
	file, err := ini.Load(bytes)
	if err != nil {
		logger.Error("riak config template to ini file error: %s", err.Error())
		return err
	}
	i.LocalIp, err = osutil.GetLocalIP()
	if err != nil {
		logger.Error("get local ip error: %s", err.Error())
		return err
	}
	i.Config = map[string]string{
		"nodename":                          fmt.Sprintf("riak@%s", i.LocalIp),
		"platform_data_dir":                 path.Join(i.DataDir, cst.DataDir),
		"platform_log_dir":                  cst.LogPath,
		"listener.http.internal":            fmt.Sprintf("%s:%d", i.LocalIp, cst.DefaultHttpPort),
		"listener.protobuf.internal":        fmt.Sprintf("%s:%d", i.LocalIp, cst.DefaultProtobufPort),
		"ring_size":                         *i.Params.RingSize,
		"distributed_cookie":                *i.Params.DistributedCookie,
		"leveldb.expiration":                *i.Params.LeveldbExpiration,
		"leveldb.expiration.mode":           *i.Params.LeveldbExpirationMode,
		"leveldb.expiration.retention_time": *i.Params.LeveldbExpirationRetentionTime,
	}
	for k, v := range i.Config {
		file.Section(file.SectionStrings()[0]).DeleteKey(k)
		_, err = file.Section(file.SectionStrings()[0]).NewKey(k, v)
		if err != nil {
			logger.Error("modify config file error: %s", err.Error())
			return err
		}
	}
	err = file.SaveTo(cst.ConfigPath)
	if err != nil {
		logger.Error("config file save failed:%s", err.Error())
		return err
	}
	logger.Info("create config file success")
	return nil
}

// Start 启动riak
func (i *InstallRiakComp) Start() error {
	cmd := "riak start"
	_, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
		return err
	}
	time.Sleep(time.Minute)
	logger.Info("start riak success")
	return nil
}

// CheckRiakStatus 检查riak状态
func (i *InstallRiakComp) CheckRiakStatus() error {
	err := CheckStatus(i.Config, i.LocalIp)
	if err != nil {
		logger.Info("CheckRiakStatus error: %s", err.Error())
		return err
	}
	logger.Info("riak node status check success")
	return nil
}

// CheckStatus 检查riak状态
func CheckStatus(items map[string]string, localIp string) error {
	checkStatus := fmt.Sprintf(` %s | grep "(C) riak@%s " | grep 'valid'`, cst.ClusterStatusCmd, localIp)
	_, err := osutil.ExecShellCommand(false, checkStatus)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", checkStatus, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", checkStatus, err.Error())
		return err
	}
	cmd := "riak config effective"
	config, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
		return err
	}
	file, err := ini.Load([]byte(config))
	if err != nil {
		logger.Error("riak config template to ini file error: %s", err.Error())
		return err
	}
	for k, v := range items {
		key, err := file.Section(file.SectionStrings()[0]).GetKey(k)
		if err != nil {
			logger.Error("riak get config %s error: %s", k, err.Error())
			return err
		}
		if v != key.Value() {
			logger.Error("riak %s value: %s not consistent with expected value %s", k, key.Value(), v)
			return fmt.Errorf("riak %s value: %s not consistent with expected value %s", k, key.Value(), v)
		}
		logger.Info("key:%s values:%s", k, v)
	}
	return nil
}

// InstallRiakPackage 安装riak包
func (i *InstallRiakComp) InstallRiakPackage() error {
	pkg := path.Join(cst.BK_PKG_INSTALL_PATH, cst.RiakPkgVersion)
	res, err := osutil.ExecShellCommand(false, "rpm -q riak")
	if err == nil {
		if strings.Contains(res, cst.RiakPkgVersion) {
			logger.Warn("riak already install")
			return nil
		} else {
			logger.Error("riak already install, expected version: %s but get %s", cst.RiakPkgVersion, res)
			return fmt.Errorf("riak already install, expected version: %s but get %s", cst.RiakPkgVersion, res)
		}
	}
	cmd := fmt.Sprintf("rpm -Uvh %s.rpm", pkg)
	_, err = osutil.ExecShellCommand(false, cmd)
	if err != nil && !strings.Contains(err.Error(), "usermod: no changes") {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
		return err
	}
	logger.Info("install riak package success")
	return nil
}
