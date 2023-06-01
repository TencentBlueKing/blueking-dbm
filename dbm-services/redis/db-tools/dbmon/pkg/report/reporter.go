package report // 主动上报(备份等)记录

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/util"
)

// Reporter 上报接口
type Reporter interface {
	AddRecord(item string, flush bool) error
	Close() error
}

// CreateReportDir 创建上报目录 /home/mysql/dbareport -> {REDIS_BACKUP_DIR}/dbbak/dbareport
func CreateReportDir() (err error) {
	var realLink string
	realReportDir := filepath.Join(consts.GetRedisBackupDir(), "dbbak", "dbareport") // 如 /data/dbbak/dbareport
	if !util.FileExists(realReportDir) {
		err = util.MkDirsIfNotExists([]string{realReportDir})
		if err != nil {
			mylog.Logger.Error(err.Error())
			return
		}
	}
	util.LocalDirChownMysql(realReportDir)
	if util.FileExists(consts.DbaReportSaveDir) {
		realLink, err = filepath.EvalSymlinks(consts.DbaReportSaveDir)
		if err != nil {
			err = fmt.Errorf("filepath.EvalSymlinks %s fail,err:%v", consts.DbaReportSaveDir, err)
			mylog.Logger.Error(err.Error())
			return err
		}
		// /home/mysql/dbareport -> /data/dbbak/dbareport ok,直接返回
		if realLink == realReportDir {
			return nil
		}
		// 如果 /home/mysql/dbareport 不是指向 /data/dbbak/dbareport,先删除
		rmCmd := "rm -rf " + consts.DbaReportSaveDir
		util.RunBashCmd(rmCmd, "", nil, 1*time.Minute)
	}
	err = os.Symlink(realReportDir, consts.DbaReportSaveDir)
	if err != nil {
		err = fmt.Errorf("os.Symlink %s -> %s fail,err:%s", consts.DbaReportSaveDir, realReportDir, err)
		mylog.Logger.Error(err.Error())
		return
	}
	mylog.Logger.Info(fmt.Sprintf("create softLink success,%s -> %s", consts.DbaReportSaveDir, realReportDir))
	util.MkDirsIfNotExists([]string{consts.RedisReportSaveDir})
	util.LocalDirChownMysql(consts.DbaReportSaveDir)
	return
}
