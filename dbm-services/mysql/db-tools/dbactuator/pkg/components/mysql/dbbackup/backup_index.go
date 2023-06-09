package dbbackup

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
)

// BackupIndexFile godoc
type BackupIndexFile struct {
	BackupType    string `json:"backup_type"`
	StorageEngine string `json:"storage_engine"`
	MysqlVersion  string `json:"mysql_version"`

	BackupCharset string `json:"backup_charset"`
	BkBizId       string `json:"bk_biz_id"`
	// unique uuid
	BackupId        string `json:"backup_id"`
	BillId          string `json:"bill_id"`
	ClusterId       int    `json:"cluster_id"`
	BackupHost      string `json:"backup_host"`
	BackupPort      int    `json:"backup_port"`
	MysqlRole       string `json:"mysql_role"`
	DataSchemaGrant string `json:"data_schema_grant"`
	// 备份一致性时间点，物理备份可能为空
	ConsistentBackupTime string `json:"consistent_backup_time"`
	BackupBeginTime      string `json:"backup_begin_time"`
	BackupEndTime        string `json:"backup_end_time"`
	TotalFilesize        uint64 `json:"total_filesize"`

	FileList   []IndexFileItem  `json:"file_list"`
	BinlogInfo BinlogStatusInfo `json:"binlog_info"`

	indexFilePath string
	// backupFiles {data: {file1: obj, file2: obj}, priv: {}}
	backupFiles map[string][]IndexFileItem
	// 备份文件解压后的目录名，相对目录
	backupBasename string
	// 备份文件的所在根目录，比如 /data/dbbak
	backupDir  string
	targetDir  string
	splitParts []string
	tarParts   []string
}

// IndexFileItem godoc
type IndexFileItem struct {
	BackupFileName string `json:"backup_file_name"`
	BackupFileSize int64  `json:"backup_file_size"`
	TarFileName    string `json:"tar_file_name"`
	// TarFileSize    int64  `json:"tar_file_size"`
	DBTable  string `json:"db_table"`
	FileType string `json:"file_type" enums:"schema,data,metadata,priv"`
}

// BinlogStatusInfo master status and slave status
type BinlogStatusInfo struct {
	ShowMasterStatus *StatusInfo `json:"show_master_status"`
	ShowSlaveStatus  *StatusInfo `json:"show_slave_status"`
}

// StatusInfo detailed binlog information
type StatusInfo struct {
	BinlogFile string `json:"binlog_file"`
	BinlogPos  string `json:"binlog_pos"`
	Gtid       string `json:"gtid"`
	MasterHost string `json:"master_host"`
	MasterPort int    `json:"master_port"`
}

// String 用于打印
func (s *BinlogStatusInfo) String() string {
	return fmt.Sprintf("BinlogStatusInfo{MasterStatus:%+v, SlaveStatus:%+v}", s.ShowMasterStatus, s.ShowSlaveStatus)
}

// ParseBackupIndexFile read index file: fileDir/fileName
func ParseBackupIndexFile(indexFilePath string, indexObj *BackupIndexFile) error {
	fileDir, fileName := filepath.Split(indexFilePath)
	bodyBytes, err := os.ReadFile(indexFilePath)
	if err != nil {
		return err
	}
	if err := json.Unmarshal(bodyBytes, indexObj); err != nil {
		logger.Error("fail to read index file to struct: %s", fileName)
		// return err
	}

	indexObj.indexFilePath = indexFilePath
	indexObj.backupBasename = strings.TrimSuffix(fileName, ".index")
	indexObj.backupDir = fileDir
	// indexObj.targetDir = filepath.Join(fileDir, indexObj.backupBasename)

	indexObj.backupFiles = make(map[string][]IndexFileItem)
	for _, fileItem := range indexObj.FileList {
		indexObj.backupFiles[fileItem.FileType] = append(indexObj.backupFiles[fileItem.FileType], fileItem)
	}
	logger.Info("backupBasename=%s, backupType=%s, charset=%s",
		indexObj.backupBasename, indexObj.BackupType, indexObj.BackupCharset)
	return indexObj.ValidateFiles()
}

// GetTarFileList 从 index 中返回文件名列表
// fileType="" 时返回所有
func (f *BackupIndexFile) GetTarFileList(fileType string) []string {
	fileNamelist := []string{}
	if fileType == "" {
		for _, fileItem := range f.FileList {
			fileNamelist = append(fileNamelist, fileItem.TarFileName)
		}
		return util.UniqueStrings(fileNamelist)
	} else {
		fileList := f.backupFiles[fileType]
		for _, f := range fileList {
			fileNamelist = append(fileNamelist, f.TarFileName)
		}
		return util.UniqueStrings(fileNamelist)
	}
}

// ValidateFiles 校验文件是否连续，文件是否存在，文件大小是否正确
// splitParts example:  [a.part_1, a.part_2]
// tarParts example:  [a.0.tar  a.1.tar]
func (f *BackupIndexFile) ValidateFiles() error {
	var errFiles []string
	reSplitPart := regexp.MustCompile(ReSplitPart)
	reTarPart := regexp.MustCompile(ReTarPart) // 如果只有一个tar，也会存到这里
	// allFileList := f.GetTarFileList("")
	tarPartsWithoutSuffix := []string{} // remove .tar suffix from tar to get no. sequence
	for _, tarFile := range f.FileList {
		if fSize := cmutil.GetFileSize(filepath.Join(f.backupDir, tarFile.TarFileName)); fSize < 0 {
			errFiles = append(errFiles, tarFile.TarFileName)
			continue
		} // else if fSize != tarFile.TarFileSize {}
		if reSplitPart.MatchString(tarFile.TarFileName) {
			f.splitParts = append(f.splitParts, tarFile.TarFileName)
		} else if reTarPart.MatchString(tarFile.TarFileName) {
			tarPartsWithoutSuffix = append(tarPartsWithoutSuffix, strings.TrimSuffix(tarFile.TarFileName, ".tar"))
			f.tarParts = append(f.tarParts, tarFile.TarFileName)
		}
	}
	if len(errFiles) != 0 {
		return errors.Errorf("files not found in %s: %v", f.backupDir, errFiles)
	}
	sort.Strings(f.splitParts)
	sort.Strings(f.tarParts)

	if len(f.splitParts) >= 2 { // 校验文件是否连续
		fileSeqList := util.GetSuffixWithLenAndSep(f.splitParts, "_", 0)
		if err := util.IsConsecutiveStrings(fileSeqList, true); err != nil {
			return err
		}
	}
	if len(tarPartsWithoutSuffix) >= 2 {
		fileSeqList := util.GetSuffixWithLenAndSep(tarPartsWithoutSuffix, "_", 0)
		if err := util.IsConsecutiveStrings(fileSeqList, true); err != nil {
			return err
		}
	}
	return nil
}

// UntarFiles merge and untar
// set targetDir
func (f *BackupIndexFile) UntarFiles(untarDir string) error {
	if untarDir == "" {
		return errors.Errorf("untar target dir should not be emtpy")
	}
	f.targetDir = filepath.Join(untarDir, f.backupBasename)
	if cmutil.FileExists(f.targetDir) {
		return errors.Errorf("target untar path already exists %s", f.targetDir)
	}
	// 物理备份, merge parts
	if len(f.splitParts) > 0 {
		// TODO 考虑使用 pv 限速
		cmd := fmt.Sprintf(`cd %s && cat %s | tar -xf -C %s/ -`, f.backupDir, strings.Join(f.splitParts, " "), untarDir)
		if _, err := osutil.ExecShellCommand(false, cmd); err != nil {
			return errors.Wrap(err, cmd)
		}
	}
	if len(f.tarParts) > 0 {
		for _, p := range f.tarParts {
			cmd := fmt.Sprintf(`cd %s && tar -xf %s -C %s/`, f.backupDir, p, untarDir)
			if _, err := osutil.ExecShellCommand(false, cmd); err != nil {
				return errors.Wrap(err, cmd)
			}
		}
	}

	if !cmutil.FileExists(f.targetDir) {
		return errors.Errorf("targetDir %s is not ready", f.targetDir)
	}
	return nil
}
