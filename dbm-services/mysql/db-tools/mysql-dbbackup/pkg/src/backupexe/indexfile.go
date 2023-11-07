package backupexe

import (
	"encoding/json"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"strings"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"github.com/spf13/cast"
)

// FileIndex the associated info of the backup file
type FileIndex struct {
	BackupFileName string `json:"backup_file_name"`
	BackupFileSize int64  `json:"backup_file_size"`
	// 备份真实打包后的文件名。扩展：可能是 .priv
	TarFileName string `json:"tar_file_name"`
	DBTable     string `json:"db_table"`
	FileType    string `json:"file_type" enums:"schema,data,metadata"`
}

const (
	// FileSchema TODO
	FileSchema = "schema"
	// FileData TODO
	FileData = "data"
	// FileMetadata TODO
	FileMetadata = "metadata"
	// FileOther TODO
	FileOther = "other"
	// FilePriv TODO
	FilePriv = "priv"
	// FileTarPart TODO
	FileTarPart = "tarpart"
)

const (
	// ReMetadata TODO
	ReMetadata = `(.+)(\-metadata)`
	// ReSchema TODO
	ReSchema = `(.+)(\-schema\.sql)`
	// ReSchemaDb TODO
	ReSchemaDb = `(.+)(\-schema\-create\.sql)`
	// ReData TODO
	ReData = `(.+)(\.\d+\.sql)`
	// ReSchemaView TODO
	ReSchemaView = `(.+)(\-schema\-view\.sql)`
	// ReSplitPart TODO
	ReSplitPart = `(.+)(\.part_\d+)`
)

// IndexContent the content of the index file
type IndexContent struct {
	BackupType              string                     `json:"backup_type"`
	StorageEngine           string                     `json:"storage_engine"`
	MysqlVersion            string                     `json:"mysql_version"`
	BkBizId                 int                        `json:"bk_biz_id"`
	BackupId                string                     `json:"backup_id"`
	BillId                  string                     `json:"bill_id"`
	ClusterId               int                        `json:"cluster_id"`
	ClusterAddress          string                     `json:"cluster_address"`
	ShardValue              int                        `json:"shard_value"`
	BackupHost              string                     `json:"backup_host"`
	BackupPort              int                        `json:"backup_port"`
	BackupCharset           string                     `json:"backup_charset"`
	MysqlRole               string                     `json:"mysql_role"`
	DataSchemaGrant         string                     `json:"data_schema_grant"`
	ConsistentBackupTime    string                     `json:"consistent_backup_time"`
	BackupBeginTime         string                     `json:"backup_begin_time"`
	BackupEndTime           string                     `json:"backup_end_time"`
	TotalFilesize           uint64                     `json:"total_filesize"`
	TotalFilesizeUncompress uint64                     `json:"total_filesize_uncompress"`
	BinlogInfo              dbareport.BinlogStatusInfo `json:"binlog_info"`

	FileList []FileIndex `json:"file_list"`

	reData       *regexp.Regexp
	reSchema     *regexp.Regexp
	reSchemaDb   *regexp.Regexp
	reMetadata   *regexp.Regexp
	reSchemaView *regexp.Regexp
	reSplitPart  *regexp.Regexp
}

// Init the initialization of IndexContent
func (i *IndexContent) Init(cnf *config.Public, resultInfo *dbareport.BackupResult) error {
	i.BackupType = cnf.BackupType
	db, err := mysqlconn.InitConn(cnf)
	if err != nil {
		return err
	}
	defer func() {
		_ = db.Close()
	}()

	versionStr, err := mysqlconn.GetMysqlVersion(db)
	if err != nil {
		return err
	}
	i.MysqlVersion = versionStr
	storageEngineStr, err := mysqlconn.GetStorageEngine(db)
	if err != nil {
		return err
	}
	i.StorageEngine = storageEngineStr

	i.BkBizId = cnf.BkBizId
	i.BackupHost = cnf.MysqlHost
	i.BackupPort = cast.ToInt(cnf.MysqlPort)
	i.BackupCharset = cnf.MysqlCharset
	i.MysqlRole = cnf.MysqlRole
	i.DataSchemaGrant = cnf.DataSchemaGrant
	i.BillId = cnf.BillId
	i.ClusterId = cnf.ClusterId
	i.ClusterAddress = cnf.ClusterAddress

	i.ShardValue = resultInfo.ShardValue
	i.ConsistentBackupTime = resultInfo.ConsistentBackupTime
	i.BackupBeginTime = resultInfo.BackupBeginTime
	i.BackupEndTime = resultInfo.BackupEndTime
	i.BackupId = resultInfo.BackupId
	i.BinlogInfo = resultInfo.BinlogInfo

	i.reData = regexp.MustCompile(ReData)
	i.reSchema = regexp.MustCompile(ReSchema)
	i.reSchemaDb = regexp.MustCompile(ReSchemaDb)
	i.reMetadata = regexp.MustCompile(ReMetadata)
	i.reSchemaView = regexp.MustCompile(ReSchemaView)
	i.reSplitPart = regexp.MustCompile(ReSplitPart)
	return nil
}

// AppendFileList append a FileIndex into FileIndex[]
func (i *IndexContent) AppendFileList(f FileIndex) {
	i.FileList = append(i.FileList, f)
}

// parseFileTypeFromName 从 mydumper 文件名里解析出库表和文件类型
func (i *IndexContent) parseFileTypeFromName(f *FileIndex) {
	if matches := i.reData.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = FileData
		f.DBTable = matches[1]
	} else if matches := i.reSchema.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = FileSchema
		f.DBTable = matches[1]
	} else if matches := i.reSchemaDb.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = FileSchema
		f.DBTable = matches[1]
	} else if matches := i.reMetadata.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = FileMetadata
	} else if matches := i.reSchemaView.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = FileSchema
	} else if strings.HasSuffix(f.BackupFileName, ".priv") {
		f.FileType = FilePriv
	} else if matches := i.reSplitPart.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = FileTarPart
	} else {
		f.FileType = FileOther
	}
}

// RecordIndexContent record some server info and fileIndex info,
// and then write these content to [targetName].index
func (i *IndexContent) RecordIndexContent(cnf *config.Public) error {
	contentJson, err := json.Marshal(i)
	if err != nil {
		logger.Log.Error("Failed to marshal json encoding data from IndexContent, err: ", err)
		return err
	}
	indexFilePath := path.Join(cnf.BackupDir, cnf.TargetName()+".index")
	indexFile, err := os.OpenFile(indexFilePath, os.O_RDWR|os.O_CREATE, 0666)
	if err != nil {
		logger.Log.Error("failed to create index file: ", indexFilePath)
		return err
	}
	defer func() {
		_ = indexFile.Close()
	}()

	_, err = indexFile.Write(contentJson)
	if err != nil {
		logger.Log.Error("Failed to write json encoding data into Index file :", indexFilePath, ", err: ", err)
		return err
	}

	return nil
}

func (i *IndexContent) addFileContent(targetFile, originFile string, originFilesize int64) {
	_, nfilename := filepath.Split(originFile)
	_, ntarname := filepath.Split(targetFile)
	fileMapping := FileIndex{
		BackupFileName: nfilename,
		TarFileName:    ntarname,
		BackupFileSize: originFilesize,
	}
	i.parseFileTypeFromName(&fileMapping)
	i.AppendFileList(fileMapping)
}

// addPrivFile add .priv to index file
func (i *IndexContent) addPrivFile(targetFilePath string) {
	privFile := targetFilePath + ".priv"
	if exists, fSize, _ := util.FileExistReturnSize(privFile); exists {
		privFilename := filepath.Base(privFile)
		fileMapping := FileIndex{BackupFileName: privFilename, TarFileName: privFilename, BackupFileSize: fSize}
		i.parseFileTypeFromName(&fileMapping)
		i.AppendFileList(fileMapping)
	} else {
		logger.Log.Warnf("collect info failed to find priv file: %s", privFile)
	}
}
