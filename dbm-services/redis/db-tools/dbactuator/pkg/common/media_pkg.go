package common

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// MediaPkg 通用介质包处理
type MediaPkg struct {
	Pkg    string `json:"pkg" validate:"required"`          // 安装包名
	PkgMd5 string `json:"pkg_md5"  validate:"required,md5"` // 安装包MD5
}

// GetAbsolutePath 返回介质存放的绝对路径
func (m *MediaPkg) GetAbsolutePath() string {
	return filepath.Join(consts.PackageSavePath, m.Pkg)
}

// GePkgBaseName 例如将 mysql-5.7.20-linux-x86_64-tmysql-3.1.5-gcs.tar.gz
// 解析出 mysql-5.7.20-linux-x86_64-tmysql-3.1.5-gcs
// 用于做软连接使用
func (m *MediaPkg) GePkgBaseName() string {
	pkgFullName := filepath.Base(m.GetAbsolutePath())
	return regexp.MustCompile("(.tar.gz|.tgz)$").ReplaceAllString(pkgFullName, "")
}

// Check 检查介质包
func (m *MediaPkg) Check() (err error) {
	var fileMd5 string
	// 判断安装包是否存在
	pkgAbPath := m.GetAbsolutePath()
	if !util.FileExists(pkgAbPath) {
		return fmt.Errorf("%s不存在", pkgAbPath)
	}
	if fileMd5, err = util.GetFileMd5(pkgAbPath); err != nil {
		return fmt.Errorf("获取[%s]md5失败, %v", m.Pkg, err.Error())
	}
	// 校验md5
	if fileMd5 != m.PkgMd5 {
		return fmt.Errorf("安装包的md5不匹配,[%s]文件的md5[%s]不正确", fileMd5, m.PkgMd5)
	}
	return
}

// DbToolsMediaPkg db工具包
type DbToolsMediaPkg struct {
	MediaPkg
}

// Install 安装dbtools
// 1. 确保本地 /data/install/dbtool.tar.gz 存在,且md5校验ok;
// 2. 检查 {REDIS_BACKUP_DIR}/dbbak/dbatool.tar.gz 与 /data/install/dbtool.tar.gz 是否一致;
// - md5一致,则忽略更新;
// - /data/install/dbtool.tar.gz 不存在 or md5不一致 则用最新 /data/install/dbtool.tar.gz 工具覆盖 {REDIS_BACKUP_DIR}/dbbak/dbatool
// 3. 创建 /home/mysql/dbtools -> /data/dbbak/dbtools 软链接
// 4. cp  /data/install/dbtool.tar.gz {REDIS_BACKUP_DIR}/dbbak/dbatool.tar.gz
func (pkg *DbToolsMediaPkg) Install() (err error) {
	var fileMd5 string
	var overrideLocal bool = true
	var newMysqlHomeLink bool = true
	var realLink string
	err = pkg.Check()
	if err != nil {
		return
	}
	toolsName := filepath.Base(consts.DbToolsPath)
	backupDir := filepath.Join(consts.GetRedisBackupDir(), "dbbak") // 如 /data/dbbak
	bakdirToolsTar := filepath.Join(backupDir, toolsName+".tar.gz") // 如 /data/dbbak/dbtools.tar.gz
	installToolTar := pkg.GetAbsolutePath()
	if util.FileExists(bakdirToolsTar) {
		fileMd5, err = util.GetFileMd5(bakdirToolsTar)
		if err != nil {
			return
		}
		if fileMd5 == pkg.PkgMd5 {
			overrideLocal = false
		}
	}
	if overrideLocal {
		// 最新介质覆盖本地
		untarCmd := fmt.Sprintf("tar -zxf %s -C %s", installToolTar, backupDir)
		mylog.Logger.Info(untarCmd)
		_, err = util.RunBashCmd(untarCmd, "", nil, 10*time.Minute)
		if err != nil {
			return
		}
	}
	if !util.FileExists(filepath.Join(backupDir, toolsName)) { // 如 /data/dbbak/dbtools 目录不存在
		err = fmt.Errorf("dir:%s not exists", filepath.Join(backupDir, toolsName))
		mylog.Logger.Error(err.Error())
		return
	}
	if util.FileExists(consts.DbToolsPath) {
		realLink, err = filepath.EvalSymlinks(consts.DbToolsPath)
		if err != nil {
			err = fmt.Errorf("filepath.EvalSymlinks %s fail,err:%v", consts.DbToolsPath, err)
			mylog.Logger.Error(err.Error())
			return err
		}
		if realLink == filepath.Join(backupDir, toolsName) { // /home/mysql/dbtools 已经是指向 /data/dbbak/dbtools 的软连接
			newMysqlHomeLink = false
		}
	}
	if newMysqlHomeLink {
		// 需创建 /home/mysql/dbtools -> /data/dbbak/dbtools 软链接
		err = os.Symlink(filepath.Join(backupDir, toolsName), consts.DbToolsPath)
		if err != nil {
			err = fmt.Errorf("os.Symlink %s -> %s fail,err:%s", consts.DbToolsPath, filepath.Join(backupDir, toolsName), err)
			mylog.Logger.Error(err.Error())
			return
		}
		mylog.Logger.Info("create softLink success,%s -> %s", consts.DbToolsPath, filepath.Join(backupDir, toolsName))
	}
	cpCmd := fmt.Sprintf("cp %s %s", installToolTar, bakdirToolsTar)
	mylog.Logger.Info(cpCmd)
	_, err = util.RunBashCmd(cpCmd, "", nil, 10*time.Minute)
	if err != nil {
		return
	}
	util.LocalDirChownMysql(consts.DbToolsPath)
	util.LocalDirChownMysql(backupDir)
	return nil
}
