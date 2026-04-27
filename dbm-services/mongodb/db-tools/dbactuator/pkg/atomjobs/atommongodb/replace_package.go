package atommongodb

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
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
	CurrentVersion  string `json:"currentVersion" validate:"required"` // 当前版本
	DestVersion     string `json:"destVersion" validate:"required"`    // 目标版本
	InstanceType    string `json:"instanceType" validate:"required"`   // mongos mongod
}

// ReplacePackage 安装包替换
type ReplacePackage struct {
	BaseJob
	runtime            *jobruntime.JobGenericRuntime
	BinDir             string
	DataDir            string
	OsUser             string // MongoDB安装在哪个用户下
	OsGroup            string
	ConfParams         *ReplacePackageConfParams
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
// 1. 检测当前db版本，如果当前版本已经是目标版本，则直接返回
// 2. 解压安装包并修改属主，重建软链接
// 3. 检测当前db版本，如果当前版本不是目标版本，则返回错误
func (r *ReplacePackage) Run() error {
	// fetch File Lock
	fileLock, err := common.NewFileLock(r.LockFilePath)
	if err != nil {
		return fmt.Errorf("create file lock fail, lock file: %s, err:%v", r.LockFilePath, err)
	}
	lockDeadline := time.Now().Add(20 * time.Minute)
	waitLockCount := 0
	for {
		if err := fileLock.Lock(); err == nil {
			break
		} else if time.Now().After(lockDeadline) {
			return fmt.Errorf("get file lock timeout(20 minutes), lock file: %s", r.LockFilePath)
		}
		// print log every 300 seconds
		if waitLockCount%300 == 0 {
			r.runtime.Logger.Info("waiting for file lock, waitLockCount: %d, lock file: %s", waitLockCount, r.LockFilePath)
		}
		time.Sleep(1 * time.Second)
		waitLockCount++
	}
	defer func() {
		if err := fileLock.UnLock(); err != nil {
			r.runtime.Logger.Error("release file lock fail, error:%s", err)
		}
	}()
	// 前端传入的版本号可能包含mongodb-前缀，需要去掉
	r.ConfParams.CurrentVersion = strings.ReplaceAll(r.ConfParams.CurrentVersion, "mongodb-", "")
	r.ConfParams.DestVersion = strings.ReplaceAll(r.ConfParams.DestVersion, "mongodb-", "")

	// 检查当前版本（与 Flow 一致：主次版本 M.m 对齐，忽略 patch；CheckMongoVersion 常为 3.4.20 等形式）
	dbVersion, err := common.CheckMongoVersion(r.BinDir, r.ConfParams.InstanceType)
	if err != nil {
		return fmt.Errorf("check db version fail, error:%s", err)
	}
	dbMM := versionMajorMinor(dbVersion)
	destMM := versionMajorMinor(r.ConfParams.DestVersion)
	curMM := versionMajorMinor(r.ConfParams.CurrentVersion)

	switch {
	case dbMM == destMM:
		r.runtime.Logger.Info("current db version is %s (mm=%s), already matches dest line %s", dbVersion, dbMM, destMM)
		return nil
	case dbMM == curMM:
		// dbVersion is the current release line, need to replace the package
		r.runtime.Logger.Info("current db version is %s (mm=%s), need to replace the package to %s", dbVersion, dbMM, destMM)
		if err := r.unTarAndRecreateSoftLink(); err != nil {
			return fmt.Errorf("unTar and create soft link fail, error:%s", err)
		}
		dbVersionAfter, err := common.CheckMongoVersion(r.BinDir, r.ConfParams.InstanceType)
		if err != nil {
			return fmt.Errorf("check db version fail, error:%s", err)
		}
		if versionMajorMinor(dbVersionAfter) != destMM {
			return fmt.Errorf(
				"db version mismatch after replace: current=%s (line=%s), expected target line=%s (destVersion=%s)",
				dbVersionAfter, versionMajorMinor(dbVersionAfter), destMM, r.ConfParams.DestVersion,
			)
		}
		return nil
	default:
		return fmt.Errorf(
			"unexpected current db version before replace: current=%s (line=%s), expected current line=%s or target line=%s (destVersion=%s)",
			dbVersion, dbMM, curMM, destMM, r.ConfParams.DestVersion,
		)
	}
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
	r.BinDir = consts.GetMongoBinDir()
	r.DataDir = consts.GetMongoDataDir()
	r.OsUser = consts.GetProcessUser()
	r.OsGroup = consts.GetProcessUserGroup()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(r.runtime.PayloadDecoded), &r.ConfParams); err != nil {
		r.runtime.Logger.Error("get parameters of replace package fail by json.Unmarshal, error:%s", err)
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

// unTarAndRecreateSoftLink 解压安装包，重建软链接并给目录授权
func (r *ReplacePackage) unTarAndRecreateSoftLink() error {

	// 删除软链接（放在锁内，避免并发竞态）
	if util.FileExists(r.InstallPath) {
		r.runtime.Logger.Info("start to delete soft link")
		if err := os.RemoveAll(r.InstallPath); err != nil {
			r.runtime.Logger.Error("delete soft link fail, error:%s", err)
			return fmt.Errorf("delete soft link, error:%s", err)
		}
		r.runtime.Logger.Info("delete soft link successfully")
	}

	if err := common.UnTarAndCreateSoftLinkAndChown(r.runtime, r.BinDir,
		r.InstallPackagePath, r.UnTarPath, r.InstallPath, r.OsUser, r.OsGroup); err != nil {
		return fmt.Errorf("unTar and create soft link fail, error:%s", err)
	}
	r.runtime.Logger.Info("unTar and create soft link successfully")
	return nil
}
