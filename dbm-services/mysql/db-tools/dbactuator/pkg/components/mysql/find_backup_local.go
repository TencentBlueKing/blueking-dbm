package mysql

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/dbbackup"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"strings"

	"github.com/pkg/errors"
)

// FindLocalBackupComp 有 resp 返回
type FindLocalBackupComp struct {
	Params FindLocalBackupParam `json:"extend"`
}

// FindLocalBackupParam 参数
type FindLocalBackupParam struct {
	BackupDirs []string `json:"backup_dirs" validate:"required"`
	// 查找哪个实例的备份
	TgtInstance *native.Instance `json:"tgt_instance" validate:"required"`
	// 指定查询哪个 cluster_id 的备份，如果不指定可能查询到其它非法的备份
	ClusterId  int  `json:"cluster_id"`
	FileServer bool `json:"file_server"`

	resp FindLocalBackupResp
}

// LocalBackupObj TODO
type LocalBackupObj struct {
	BKBizID string `json:"bk_biz_id"`
	// 备份所属 host
	InstHost string `json:"inst_host"`
	// 备份所属 port
	InstPort int `json:"inst_port"`

	DBRole          string `json:"db_role"`
	DataSchemaGrant string `json:"data_schema_grant"`
	BackupId        string `json:"backup_id"`
	BillId          string `json:"bill_id"`
	ClusterId       int    `json:"cluster_id"`

	// 备份时间，目前是备份开始时间
	BackupTime string `json:"backup_time"`
	// InfoFile   common.InfoFileDetail `json:"info_file"`
	// 备份文件列表
	FileList []string `json:"file_list"`
	// 备份所在目录
	BackupDir  string `json:"backup_dir"`
	BackupType string `json:"backup_type"`
	IndexFile  string `json:"index_file"`
}

// FindLocalBackupResp TODO
type FindLocalBackupResp struct {
	// backups key 是 .info 文件
	Backups map[string]*LocalBackupObj `json:"backups"` // info_file: detail
	// 记录上面 backups 最近的一次备份
	Latest string `json:"latest"`
}

// Example TODO
func (f *FindLocalBackupComp) Example() interface{} {
	comp := FindLocalBackupComp{
		Params: FindLocalBackupParam{
			BackupDirs:  []string{"/data/dbbak", "/data1/dbbak"},
			TgtInstance: &common.InstanceExample,
			FileServer:  false,
		},
	}
	return comp
}

// Init TODO
func (f *FindLocalBackupParam) Init() error {
	var err error
	if f.TgtInstance.Host == "" {
		f.TgtInstance.Host, err = osutil.GetLocalIP()
		if err != nil {
			return err
		}
	}
	return nil
}

// PreCheck TODO
func (f *FindLocalBackupParam) PreCheck() error {
	if f.TgtInstance.Port == 0 {
		return errors.New("target instance port is needed")
	}
	return nil
}

// StartOld TODO
func (f *FindLocalBackupParam) StartOld() error {
	backups := make(map[string]*LocalBackupObj)
	infoLatest := ""
	for _, dir := range f.BackupDirs {
		if !cmutil.IsDirectory(dir) {
			continue
		}
		script := fmt.Sprintf("ls %s/*_%s_%d_*.info", dir, f.TgtInstance.Host, f.TgtInstance.Port)
		logger.Info("find cmd: %s", script)
		out, err := osutil.ExecShellCommand(false, script)
		if err != nil {
			logger.Warn("find error %w", err)
			if strings.Contains(out, "No such file or directory") { // 如果是 No such file or directory, 则忽略
				continue
			}
			return err
		}
		logger.Info("find cmd output: %s", out)
		infoList := util.SplitAnyRune(strings.TrimSpace(out), " \n")
		for _, info := range infoList {
			file := dbbackup.InfoFileDetail{}
			if err = dbbackup.ParseBackupInfoFile(info, &file); err != nil {
				logger.Warn("file %s parse error: %s", info, err.Error())
				// return err
			} else {
				if info > infoLatest {
					infoLatest = info
				}
				fileList := []string{}
				for f := range file.FileInfo {
					fileList = append(fileList, f)
				}
				localBackup := &LocalBackupObj{
					BackupDir:  dir,
					FileList:   fileList,
					BackupType: file.BackupType,
					// InfoFile:   file,
					BKBizID:    file.App,
					BackupTime: file.StartTime,
					InstHost:   file.BackupHost,
					InstPort:   file.BackupPort,
				}
				backups[info] = localBackup
			}
		}
	}
	resp := FindLocalBackupResp{
		Backups: backups,
		Latest:  infoLatest,
	}
	f.resp = resp
	// fmt.Println(resp)
	return nil
}

// Start TODO
func (f *FindLocalBackupParam) Start() error {
	backups := make(map[string]*LocalBackupObj)
	indexLatest := dbbackup.BackupIndexFile{}
	for _, dir := range f.BackupDirs {
		if !cmutil.IsDirectory(dir) {
			continue
		}
		script := fmt.Sprintf("ls %s/*_%s_%d_*.index", dir, f.TgtInstance.Host, f.TgtInstance.Port)
		logger.Info("find cmd: %s", script)
		out, err := osutil.ExecShellCommand(false, script)
		if err != nil {
			logger.Warn("find error %w", err)
			if strings.Contains(out, "No such file or directory") { // 如果是 No such file or directory, 则忽略
				continue
			}
			return err
		}
		logger.Info("find cmd output: %s", out)
		indexList := util.SplitAnyRune(strings.TrimSpace(out), " \n")
		for _, info := range indexList {
			file := dbbackup.BackupIndexFile{}
			/*
				contentBytes, err := os.ReadFile(info)
				if err != nil {
					return err
				}
				if err := json.Unmarshal(contentBytes, &file); err != nil {
					logger.Error("fail to read index file to struct: %s", info)
					continue
					// return err
				}
			*/
			if err := dbbackup.ParseBackupIndexFile(info, &file); err != nil {
				logger.Warn("file %s parse error: %s", info, err.Error())
				continue
			}

			if f.ClusterId != 0 && f.ClusterId != file.ClusterId {
				logger.Warn("backup index %s does not belong to cluster_id=%s", info, f.ClusterId)
				continue
			}
			if file.ConsistentBackupTime > indexLatest.ConsistentBackupTime {
				indexLatest = file
			}
			fileList := file.GetTarFileList("")
			localBackup := &LocalBackupObj{
				BackupDir:       dir,
				FileList:        fileList,
				BackupType:      file.BackupType,
				BKBizID:         file.BkBizId,
				ClusterId:       file.ClusterId,
				BackupTime:      file.ConsistentBackupTime,
				InstHost:        file.BackupHost,
				InstPort:        file.BackupPort,
				DBRole:          file.MysqlRole,
				BackupId:        file.BackupId,
				BillId:          file.BillId,
				DataSchemaGrant: file.DataSchemaGrant,
				IndexFile:       info,
			}
			if file.BackupId == "" {
				logger.Warn("backup_id should not be empty: %+v", localBackup)
			}
			backups[file.BackupId] = localBackup
		}
	}
	resp := FindLocalBackupResp{
		Backups: backups,
		Latest:  indexLatest.BackupId,
	}
	f.resp = resp
	// fmt.Println(resp)
	return nil
}

// PostCheck TODO
func (f *FindLocalBackupParam) PostCheck() error {
	if f.FileServer {
		logger.Info("start file httpserver")
	}
	return nil
}

// OutputCtx TODO
func (f *FindLocalBackupParam) OutputCtx() error {
	ss, err := components.WrapperOutput(f.resp)
	if err != nil {
		return err
	}
	fmt.Println(ss)
	return nil
}
