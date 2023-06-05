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
	"strconv"
	"strings"

	"golang.org/x/exp/maps"
	"gopkg.in/ini.v1"
)

const ConfigPath = "/etc/riak/riak.conf"
const RiakPkgVersion = "riak-2.2.1-1.el6.x86_64.rpm"
const MhsModuleId = 0
const LegsModuleId = 1
const PpModuleId = 2
const TestModuleId = 3
const MixedModuleId = 4

// InstallRiakComp TODO
type InstallRiakComp struct {
	Params                *InstallRaikParam `json:"extend"`
	InstallRiakRunTimeCtx `json:"-"`
}

// InstallRaikParam TODO
type InstallRaikParam struct {
	Pkg               components.Medium `json:"pkg" validate:"required"`
	DistributedCookie *string           `json:"distributed_cookie" validate:"required"`
	RingSize          *int              `json:"ring_size" validate:"required"`
	DbModuleId        *int              `json:"db_module_id" validate:"required"`
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
	platformDataDir := path.Join(mountpoint, "/riak/data")
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
		logger.Info("riak rpm package check failed: %s", err.Error())
		return err
	}
	return nil
}

// OsClearCheck 空闲检查
func (i *InstallRiakComp) OsClearCheck() error {
	result, err := osutil.ExecShellCommand(false,
		"/usr/src/sojob/subjob/isclear/os_is_clear.pl | grep 'RESULT:' | cut -d':' -f2")
	if err != nil {
		return fmt.Errorf("error occurs while checking os clear %s", err.Error())
	}
	ignoreDirtyFile := fmt.Sprintf("%s%s", result[0:3], result[4:5])
	if strings.Contains(ignoreDirtyFile, "1") {
		dirty, err := osutil.ExecShellCommand(false,
			"/usr/src/sojob/subjob/isclear/os_is_clear.pl | grep 'dirty' | grep -v 'dirty FILE'")
		if err != nil {
			return fmt.Errorf("error occurs while checking os clear %s", err.Error())
		}
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
	legsExpiration := map[string]string{
		"leveldb.expiration":                "on",
		"leveldb.expiration.mode":           "whole_file",
		"leveldb.expiration.retention_time": "365d",
	}
	i.Config = map[string]string{
		"nodename":                   fmt.Sprintf("riak@%s", i.LocalIp),
		"platform_data_dir":          path.Join(i.DataDir, "/riak/data"),
		"platform_log_dir":           "/data/riak/log",
		"listener.http.internal":     fmt.Sprintf("%s:8098", i.LocalIp),
		"listener.protobuf.internal": fmt.Sprintf("%s:8087", i.LocalIp),
		"ring_size":                  strconv.Itoa(*i.Params.RingSize),
		"distributed_cookie":         *i.Params.DistributedCookie,
	}
	if *i.Params.DbModuleId == LegsModuleId {
		maps.Copy(i.Config, legsExpiration)
	}
	for k, v := range i.Config {
		file.Section(file.SectionStrings()[0]).DeleteKey(k)
		_, err = file.Section(file.SectionStrings()[0]).NewKey(k, v)
		if err != nil {
			logger.Error("modify config file error: %s", err.Error())
			return err
		}
	}
	err = file.SaveTo(ConfigPath)
	if err != nil {
		logger.Error("config file save failed:%s", err.Error())
		return err
	}
	logger.Info("create config file success")
	return nil
}

// Start 启动riak
func (i *InstallRiakComp) Start() error {
	cmd := "/usr/sbin/riak start"
	_, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
		return err
	}
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
	checkStatus := fmt.Sprintf(`riak-admin cluster status | grep "(C) riak@%s " | grep 'valid'`, localIp)
	_, err := osutil.ExecShellCommand(false, checkStatus)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", checkStatus, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", checkStatus, err.Error())
		return err
	}
	cmd := "/usr/sbin/riak config effective"
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
	pkg := path.Join(cst.BK_PKG_INSTALL_PATH, RiakPkgVersion)
	cmd := fmt.Sprintf("rpm -Uvh %s", pkg)
	_, err := osutil.ExecShellCommand(false, cmd)
	if err != nil && !strings.Contains(err.Error(), "usermod: no changes") {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
		return err
	}
	logger.Info("install riak package success")
	return nil
}
