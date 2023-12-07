package dbareport

import (
	"encoding/json"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
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
	// ReTar tar file with suffix .tar
	ReTar = `(.+)(\.tar)`
)

// BackupMetaFileBase index meta info 基础内容
type BackupMetaFileBase struct {
	// BackupId backup uuid 代表一次备份
	BackupId       string `json:"backup_id" db:"backup_id"`
	BackupType     string `json:"backup_type" db:"backup_type"`
	ClusterId      int    `json:"cluster_id" db:"cluster_id"`
	ClusterAddress string `json:"cluster_address" db:"cluster_address"`
	BackupHost     string `json:"backup_host" db:"backup_host"`
	BackupPort     int    `json:"backup_port" db:"backup_port"`
	MysqlRole      string `json:"mysql_role" db:"mysql_role"`
	// ShardValue 分片 id，仅 spider 有用
	ShardValue      int    `json:"shard_value" db:"shard_value"`
	BillId          string `json:"bill_id" db:"bill_id"`
	BkBizId         int    `json:"bk_biz_id" db:"bk_biz_id"`
	MysqlVersion    string `json:"mysql_version" db:"mysql_version"`
	DataSchemaGrant string `json:"data_schema_grant" db:"data_schema_grant"`
	// IsFullBackup 是否包含数据的全备
	IsFullBackup bool `json:"is_full_backup" db:"is_full_backup"`

	BackupConsistentTime time.Time `json:"backup_consistent_time" db:"backup_consistent_time"`
	BackupBeginTime      time.Time `json:"backup_begin_time" db:"backup_begin_time"`
	BackupEndTime        time.Time `json:"backup_end_time" db:"backup_end_time"`

	// ConsistentBackupTime todo 为了字段兼容性，可以删掉
	ConsistentBackupTime time.Time `json:"consistent_backup_time" db:"consistent_backup_time"`
}

// IndexContent the content of the index file
// 不包含秘钥
type IndexContent struct {
	BackupMetaFileBase
	// ExtraFields 这里不能展开
	ExtraFields

	// BinlogInfo show slave status / show master status
	BinlogInfo BinlogStatusInfo `json:"binlog_info" db:"binlog_info"`

	FileList []*TarFileItem `json:"file_list" db:"file_list"`

	reData       *regexp.Regexp
	reSchema     *regexp.Regexp
	reSchemaDb   *regexp.Regexp
	reMetadata   *regexp.Regexp
	reSchemaView *regexp.Regexp
	reSplitPart  *regexp.Regexp
	reTar        *regexp.Regexp
}

// TarFileItem 备份打包文件信息
type TarFileItem struct {
	FileName      string   `json:"file_name"`
	FileSize      int64    `json:"file_size"`
	FileType      string   `json:"file_type" enums:"schema,data,metadata,priv"`
	ContainFiles  []string `json:"contain_files"`
	ContainTables []string `json:"contain_tables"`
}

func (f *TarFileItem) GetDBTables() {

}

// IndexFileItem the associated info of the backup file
// 记录每个表在哪个 tar 文件
type IndexFileItem struct {
	BackupFileName string `json:"backup_file_name"`
	BackupFileSize int64  `json:"backup_file_size"`
	// 备份真实打包后的文件名。扩展：可能是 .priv
	TarFileName string `json:"tar_file_name"`
	// TarFileSize    int64  `json:"tar_file_size"`
	DBTable  string `json:"db_table"`
	FileType string `json:"file_type" enums:"schema,data,metadata,priv"`
}

// ExtraFields 写入 db 的更多信息，json存储
type ExtraFields struct {
	BkCloudId     int    `json:"bk_cloud_id" db:"bk_cloud_id"`
	TotalFilesize uint64 `json:"total_filesize" db:"total_filesize"`
	// TotalSizeKBUncompress 压缩前大小，如果是zstd压缩会提供压缩前大小，-1,0 都是无效值。这不是精确大小，可能存在四舍五入
	TotalSizeKBUncompress int64 `json:"total_size_kb_uncompress" db:"total_size_kb_uncompress"`
	EncryptEnable         bool  `json:"encrypt_enable" db:"encrypt_enable"`
	// StorageEngine 物理备份使用
	StorageEngine string `json:"storage_engine" db:"storage_engine"`
	// BackupCharset 逻辑备份使用
	BackupCharset string `json:"backup_charset" db:"backup_charset"`
	TimeZone      string `json:"time_zone" db:"time_zone"`
}

// JudgeIsFullBackup 是否是带所有数据的全备
// 这里比较难判断逻辑备份 Regex 正则是否只包含系统库，所以优先判断如果是库表备份，认为false
func (i *IndexContent) JudgeIsFullBackup(cnf *config.Public) bool {
	if i.DataSchemaGrant == cst.BackupSchema || strings.Contains(cnf.BackupDir, "backupDatabaseTable_") {
		i.IsFullBackup = false
		return i.IsFullBackup
	}
	if i.BackupType == cst.BackupPhysical {
		i.IsFullBackup = true
	}
	i.IsFullBackup = true
	return true
}

func (r *BackupLogReport) BuildMetaInfo(cnf *config.Public, metaInfo *IndexContent) error {
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
	metaInfo.MysqlVersion = versionStr
	storageEngineStr, err := mysqlconn.GetStorageEngine(db)
	if err != nil {
		return err
	}
	metaInfo.BackupType = cnf.BackupType
	metaInfo.BackupHost = cnf.MysqlHost
	metaInfo.BackupPort = cnf.MysqlPort
	metaInfo.MysqlRole = cnf.MysqlRole
	metaInfo.DataSchemaGrant = cnf.DataSchemaGrant
	metaInfo.BillId = cnf.BillId
	metaInfo.ClusterId = cnf.ClusterId
	metaInfo.ClusterAddress = cnf.ClusterAddress
	metaInfo.ShardValue = cnf.ShardValue
	metaInfo.BkBizId = cnf.BkBizId
	metaInfo.BkCloudId = cnf.BkCloudId
	metaInfo.BackupCharset = cnf.MysqlCharset
	metaInfo.StorageEngine = storageEngineStr
	metaInfo.TimeZone, _ = time.Now().Zone()
	metaInfo.ConsistentBackupTime = metaInfo.BackupConsistentTime
	// BeginTime, EndTime, ConsistentTime, BinlogInfo,storageEngineStr build in PrepareBackupMetaInfo

	metaInfo.BackupId = r.BackupId
	if r.EncryptedKey != "" {
		metaInfo.EncryptEnable = true
	}
	metaInfo.JudgeIsFullBackup(cnf)

	metaInfo.reData = regexp.MustCompile(ReData)
	metaInfo.reSchema = regexp.MustCompile(ReSchema)
	metaInfo.reSchemaDb = regexp.MustCompile(ReSchemaDb)
	metaInfo.reMetadata = regexp.MustCompile(ReMetadata)
	metaInfo.reSchemaView = regexp.MustCompile(ReSchemaView)
	metaInfo.reSplitPart = regexp.MustCompile(ReSplitPart)
	return nil
}

// AppendFileList append a IndexFileItem into IndexFileItem[]
func (i *IndexContent) AppendFileList(f TarFileItem) {
	i.FileList = append(i.FileList, &f)
}

// parseTableSchema 从 mydumper 文件名里解析出库表和文件类型
func (i *IndexContent) parseTableSchema(f *IndexFileItem) {
	var matches []string
	if matches = i.reData.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = cst.FileData
		f.DBTable = matches[1]
	} else if matches = i.reSchema.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = cst.FileSchema
		f.DBTable = matches[1]
	} else if matches = i.reSchemaDb.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = cst.FileSchema
		f.DBTable = matches[1]
	} else if matches = i.reMetadata.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = cst.FileMetadata
	} else if matches = i.reSchemaView.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = cst.FileSchema
	} else if strings.HasSuffix(f.BackupFileName, ".priv") {
		f.FileType = cst.FilePriv
	} else if matches = i.reSplitPart.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = cst.FilePart
	} else if matches = i.reTar.FindStringSubmatch(f.BackupFileName); len(matches) == 3 {
		f.FileType = cst.FileTar
	} else {
		f.FileType = cst.FileOther
	}
}

// SaveIndexContent record some server info and fileIndex info,
// and then write these content to [targetName].index
func (i *IndexContent) SaveIndexContent(cnf *config.Public) (string, error) {
	contentJson, err := json.Marshal(i)
	if err != nil {
		logger.Log.Error("Failed to marshal json encoding data from IndexContent, err: ", err)
		return "", err
	}
	indexFilePath := path.Join(cnf.BackupDir, cnf.TargetName()+".index")
	indexFile, err := os.OpenFile(indexFilePath, os.O_RDWR|os.O_CREATE, 0666)
	if err != nil {
		logger.Log.Error("failed to create index file: ", indexFilePath)
		return "", err
	}
	defer func() {
		_ = indexFile.Close()
	}()

	_, err = indexFile.Write(contentJson)
	if err != nil {
		logger.Log.Error("Failed to write json encoding data into Index file :", indexFilePath, ", err: ", err)
		return "", err
	}
	return indexFilePath, nil
}

// AddPrivFileItem add .priv to index file
func (i *IndexContent) AddPrivFileItem(targetFilePath string) {
	privFile := targetFilePath + ".priv"
	if exists, fSize, _ := util.FileExistReturnSize(privFile); exists {
		privFilename := filepath.Base(privFile)
		tarFileItem := TarFileItem{FileName: privFilename, FileSize: fSize, FileType: cst.FilePriv}
		i.AppendFileList(tarFileItem)
	} else {
		logger.Log.Warnf("collect info failed to find priv file: %s", privFile)
	}
}
