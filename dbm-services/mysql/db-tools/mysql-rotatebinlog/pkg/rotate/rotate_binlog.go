package rotate

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/timeutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/backup"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/models"

	"github.com/pkg/errors"
	"github.com/spf13/cast"
)

// ServerObj rotate_binlog.yaml servers 配置
type ServerObj struct {
	Host     string       `json:"host" mapstructure:"host" validate:"required"` // 当前实例的主机地址
	Port     int          `json:"port" mapstructure:"port" validate:"required"` // 当前实例的端口
	Username string       `json:"username,omitempty" mapstructure:"username"`   // 连接当前实例的User
	Password string       `json:"password,omitempty" mapstructure:"password"`   // 连接当前实例的User Pwd
	Socket   string       `json:"socket,omitempty" mapstructure:"socket"`       // 连接socket
	Tags     InstanceMeta `json:"tags" mapstructure:"tags" validate:"required"`

	dbWorker  *native.DbWorker
	binlogDir string
	// 已按文件名升序排序，本地存在的binlog文件列表
	binlogFiles  []*BinlogFile
	backupClient backup.BackupClient
	instance     *native.InsObject
	rotate       *BinlogRotate
}

// InstanceMeta servers.tags
type InstanceMeta struct {
	BkBizId       int    `json:"bk_biz_id" mapstructure:"bk_biz_id"`
	ClusterDomain string `json:"cluster_domain" mapstructure:"cluster_domain"`
	ClusterId     int    `json:"cluster_id" mapstructure:"cluster_id"`
	DBRole        string `json:"db_role" mapstructure:"db_role" validate:"required" enums:"master,slave"`
}

// String 用于打印
func (i *ServerObj) String() string {
	return fmt.Sprintf(
		"{Host:%s, Port:%d, Username:%s Tags.ClusterDomain:%s Tags.DBRole:%s}",
		i.Host, i.Port, i.Username, i.Tags.ClusterDomain, i.Tags.DBRole,
	)
}

// Rotate 实例 rotate 主逻辑
// 如果返回有错误，该实例不参与后续binlog处理。不返回错误 nil 时，ServerObj.rotate 对象有效
func (i *ServerObj) Rotate() (err error) {
	maxKeepDuration := timeutil.ViperGetDuration("public.max_keep_duration")
	if maxKeepDuration < cst.MaxKeepDurationMin {
		logger.Warn("max_keep_duration=%s is too small, set to %s", maxKeepDuration, cst.MaxKeepDurationMin)
		maxKeepDuration = cst.MaxKeepDurationMin
	}

	if i.dbWorker, err = i.instance.Conn(); err != nil {
		return err
	}
	if i.binlogDir, _, err = i.dbWorker.GetBinlogDir(i.Port); err != nil {
		return err
	}
	rotate := &BinlogRotate{
		backupClient: i.backupClient,
		binlogInst: models.BinlogFileModel{
			BkBizId:   i.Tags.BkBizId,
			ClusterId: i.Tags.ClusterId,
			Host:      i.Host,
			Port:      i.Port,
		},
		purgeInterval:   timeutil.ViperGetDuration("public.purge_interval"),
		rotateInterval:  timeutil.ViperGetDuration("public.rotate_interval"),
		maxKeepDuration: maxKeepDuration,
		binlogDir:       i.binlogDir,
	}
	i.rotate = rotate
	logger.Info("rotate obj: %+v", rotate)
	if err := os.Chmod(i.binlogDir, 0755); err != nil {
		return errors.Wrap(err, "chmod 655")
	}

	if err = i.FlushLogs(); err != nil {
		logger.Error(err.Error())
		logger.Error("%+v", err)
	}
	return nil
}

// FreeSpace 实例 rotate 主逻辑
// Remove, Backup, Purge
func (i *ServerObj) FreeSpace() (err error) {
	sizeToFreeBytes := i.rotate.sizeToFreeMB * 1024 * 1024 // MB to bytes
	logger.Info("plan to free port %d binlog bytes %d", i.Port, sizeToFreeBytes)
	if err = i.rotate.Remove(sizeToFreeBytes, true); err != nil {
		logger.Error("Remove %+v", err)
	}
	if err = i.PurgeIndex(); err != nil {
		logger.Error("PurgeIndex %+v", err)
	}
	defer i.dbWorker.Stop()
	return nil
}

// GetEarliestAliveBinlog TODO
func (i *ServerObj) GetEarliestAliveBinlog() (string, error) {
	if len(i.binlogFiles) == 0 {
		return "", errors.Errorf("no binlog files found from binlog_dir=%s", i.binlogDir)
	}
	for _, f := range i.binlogFiles {
		filePath := filepath.Join(i.binlogDir, f.Filename)
		if cmutil.FileExists(filePath) {
			return f.Filename, nil
		}
	}
	return "", errors.Errorf("cannot get earliest binlog file from %s", i.binlogDir)
}

// BinlogFile TODO
type BinlogFile struct {
	Filename string
	Mtime    string
	Size     int64
}

// String 用于打印
func (f *BinlogFile) String() string {
	return fmt.Sprintf("{Filename:%s Mtime:%s Size:%d}", f.Filename, f.Mtime, f.Size)
}

// getBinlogFilesLocal 获取实例的 本地 binlog 列表，会按文件名排序
func (i *ServerObj) getBinlogFilesLocal() (string, []*BinlogFile, error) {
	// 临时关闭 binlog 删除
	files, err := os.ReadDir(i.binlogDir) // 已经按文件名排序
	if err != nil {
		return "", nil, errors.Wrap(err, "read binlog dir")
	}
	reFilename := regexp.MustCompile(cst.ReBinlogFilename)
	for _, fi := range files {
		if !reFilename.MatchString(fi.Name()) {
			if !strings.HasSuffix(fi.Name(), ".index") {
				logger.Warn("illegal binlog file name %s", fi.Name())
			}
			continue
		} else {
			fii, _ := fi.Info()
			i.binlogFiles = append(
				i.binlogFiles, &BinlogFile{
					Filename: fi.Name(),
					Mtime:    fii.ModTime().Format(cst.DBTimeLayout),
					Size:     fii.Size(),
				},
			)
		}
	}
	// 确认排序
	sort.Slice(
		i.binlogFiles,
		func(m, n int) bool { return i.binlogFiles[m].Filename < i.binlogFiles[n].Filename },
	) // 升序
	logger.Info("getBinlogFilesLocal: %+v", i.binlogFiles)
	return i.binlogDir, i.binlogFiles, nil
}

// PurgeIndex purge binlog files that has been removed
func (i *ServerObj) PurgeIndex() error {
	timeIntvl := models.TimeInterval{TaskName: "purge_index", Tag: cast.ToString(i.Port)}
	if !timeIntvl.IntervalOut(models.DB.Conn, i.rotate.purgeInterval) {
		return nil
	}
	fileName, err := i.GetEarliestAliveBinlog()
	if err != nil {
		return err
	}
	if err := i.PurgeLogs(fileName, ""); err != nil {
		return err
	}
	if err = timeIntvl.Update(models.DB.Conn); err != nil {
		logger.Error(err.Error())
	}
	return nil
}

// PurgeLogs godoc
func (i *ServerObj) PurgeLogs(toFile, beforeTime string) error {
	if toFile != "" {
		purgeCmd := fmt.Sprintf("PURGE BINARY LOGS TO '%s'", toFile)
		logger.Info("purgeCmd: %s", purgeCmd)
		if _, err := i.dbWorker.ExecWithTimeout(60*time.Second, purgeCmd); err != nil {
			return err
		}
	}
	if beforeTime != "" {
		purgeCmd := fmt.Sprintf("PURGE BINARY LOGS BEFORE '%s'", beforeTime)
		logger.Info("purgeCmd: %s", purgeCmd)
		if _, err := i.dbWorker.ExecWithTimeout(60*time.Second, purgeCmd); err != nil {
			return err
		}
	}
	return nil
}
