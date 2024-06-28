package atommongodb

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"time"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
)

// ReplacePackageConfParams 配置文件参数
type ReplacePackageConfParams struct {
	common.MediaPkg `json:"mediapkg"`
	IP              string `json:"ip" validate:"required"`
	Port            int    `json:"port" validate:"required"`
	DbVersion       string `json:"dbVersion" validate:"required"`
	InstanceType    string `json:"instanceType" validate:"required"` // mongos mongod
}

// ReplacePackage 安装包替换
type ReplacePackage struct {
	BaseJob
	runtime            *jobruntime.JobGenericRuntime
	BinDir             string
	DataDir            string
	OsUser             string // MongoDB安装在哪个用户下
	OsGroup            string
	ConfParams         *MongoDBConfParams
	InstallPackagePath string
	UnTarPath          string
	InstallPath        string // soft link目录
	LockFilePath       string // 锁文件路径
}

// NewReplacePackage 实例化结构体
func NewReplacePackage() jobruntime.JobRunner {
	return &ReplacePackage{}
}

// Name 获取原子任务的名字
func (r *ReplacePackage) Name() string {
	return "replace_package"
}

// Run 运行原子任务
func (r *ReplacePackage) Run() error {
	// 解压安装包并修改属主，重建软链接
	if err := r.unTarAndRecreateSoftLink(); err != nil {
		return err
	}
	return nil
}

// Retry 重试
func (r *ReplacePackage) Retry() uint {
	return 2
}

// Rollback 回滚
func (r *ReplacePackage) Rollback() error {
	return nil
}

// Init 初始化
func (r *ReplacePackage) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	r.runtime = runtime
	r.runtime.Logger.Info("start to init")
	r.BinDir = consts.UsrLocal
	r.DataDir = consts.GetMongoDataDir()
	r.OsUser = consts.GetProcessUser()
	r.OsGroup = consts.GetProcessUserGroup()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(r.runtime.PayloadDecoded), &r.ConfParams); err != nil {
		r.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of replace package fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of replace package fail by json.Unmarshal, error:%s", err)
	}

	// 获取信息
	r.InstallPackagePath = r.ConfParams.MediaPkg.GetAbsolutePath()

	// 设置各种路径
	r.LockFilePath = filepath.Join(r.DataDir, "mongoinstall.lock")
	r.UnTarPath = filepath.Join(r.BinDir, r.ConfParams.MediaPkg.GePkgBaseName())
	r.InstallPath = filepath.Join(r.BinDir, "mongodb")
	r.runtime.Logger.Info("init successfully")
	return nil
}

// checkDbVersion 检查db版本
func (r *ReplacePackage) checkDbVersion() (error, bool) {
	// 检查db版本
	r.runtime.Logger.Info("start to check db version")
	dbVersion, err := common.CheckMongoVersion(r.BinDir, r.ConfParams.InstanceType)
	if err != nil {
		r.runtime.Logger.Error("check db version fail, error:%s", err)
		return err, false
	}
	r.runtime.Logger.Info("current db version is %s", dbVersion)
	if dbVersion != r.ConfParams.DbVersion {
		return nil, false
	}
	r.runtime.Logger.Info("check db version successfully")
	return nil, true
}

// unTarAndRecreateSoftLink 解压安装包，重建软链接并给目录授权
func (r *ReplacePackage) unTarAndRecreateSoftLink() error {
	r.runtime.Logger.Info("start to replace package")
	// 检查db版本
	err, versionStatus := r.checkDbVersion()
	if err != nil {
		return err
	}
	if versionStatus {
		return nil
	}

	// 删除软链接
	if util.FileExists(r.InstallPath) {
		r.runtime.Logger.Info("start to delete soft link")
		softLink := fmt.Sprintf("rm -rf %s", r.InstallPath)
		if _, err := util.RunBashCmd(softLink, "", nil, 60*time.Second); err != nil {
			r.runtime.Logger.Error(
				fmt.Sprintf("delete soft link fail, error:%s", err))
			return fmt.Errorf("delete soft link, error:%s", err)
		}
		r.runtime.Logger.Info("delete soft link successfully")
	}

	// 解压安装包并授权
	// 安装多实例并发执行添加文件锁
	r.runtime.Logger.Info("start to get file lock")
	fileLock := common.NewFileLock(r.LockFilePath)
	// 获取锁
	err = fileLock.Lock()
	if err != nil {
		for {
			err = fileLock.Lock()
			if err != nil {
				time.Sleep(1 * time.Second)
				continue
			}
			r.runtime.Logger.Info("get file lock successfully")
			break
		}
	} else {
		r.runtime.Logger.Info("get file lock successfully")
	}
	if err = common.UnTarAndCreateSoftLinkAndChown(r.runtime, r.BinDir,
		r.InstallPackagePath, r.UnTarPath, r.InstallPath, r.OsUser, r.OsGroup); err != nil {
		return err
	}
	// 释放锁
	_ = fileLock.UnLock()
	r.runtime.Logger.Info("release file lock successfully")

	// 检查db版本
	err, versionStatus = r.checkDbVersion()
	if err != nil {
		return err
	}
	if !versionStatus {
		r.runtime.Logger.Error("replace package fail, current db version is not %s", r.ConfParams.DbVersion)
		return fmt.Errorf("replace package fail, current db version is not %s", r.ConfParams.DbVersion)
	}
	r.runtime.Logger.Info("replace package successfully")
	return nil
}
