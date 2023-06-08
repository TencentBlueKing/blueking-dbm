package spider

import (
	"fmt"
	"strings"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
)

const (
	// StatusInit TODO
	StatusInit = "init"
	// StatusSuccess TODO
	StatusSuccess = "success"
	// StatusRunning TODO
	StatusRunning = "running"
	// StatusFailed TODO
	StatusFailed = "failed"
	// StatusQuit 手动设置为 quit 状态的任务，会自动kill掉
	StatusQuit = "quit"
	// StatusUnknown TODO
	StatusUnknown = "unknown"
)

// GlobalBackupModel TODO
type GlobalBackupModel struct {
	ServerName   string `json:"Server_name" db:"Server_name"`
	Host         string `json:"Host" db:"Host"`
	Port         int    `json:"Port" db:"Port"`
	Wrapper      string `json:"Wrapper" db:"Wrapper"`
	ShardValue   int    `json:"ShardValue" db:"ShardValue"`
	BackupId     string `json:"BackupId" db:"BackupId"`
	BillId       string `json:"BillId" db:"BillId"`
	BackupStatus string `json:"BackupStatus" db:"BackupStatus"`
	TaskPid      int    `json:"TaskPid" db:"TaskPid"`
	CreatedAt    string `json:"CreatedAt" db:"CreatedAt"`
	UpdatedAt    string `json:"UpdatedAt" db:"UpdatedAt"`
}

// GlobalBackup TODO
type GlobalBackup struct {
	*GlobalBackupModel

	retries    int
	localLog   *logrus.Entry
	instObj    *mysqlconn.InsObject
	cnfFile    string
	cnfObj     parsecnf.CnfShared
	shardValue int
}

// TableName TODO
func (b GlobalBackupModel) TableName() string {
	return fmt.Sprintf("%s.global_backup", cst.INFODBA_SCHEMA)
}

// String 用于打印
func (b GlobalBackupModel) String() string {
	return fmt.Sprintf(
		"GlobalBackup{ServerName:%s Host:%s Port:%d Wrapper:%s ShardValue:%d BackupId:%s BackupStatus:%s TaskPid:%d, CreatedAt:%s}",
		b.ServerName, b.Host, b.Port, b.Wrapper, b.ShardValue, b.BackupId, b.BackupStatus, b.TaskPid, b.CreatedAt)
}

// GlobalBackupList 用于自定义排序
type GlobalBackupList []*GlobalBackupModel

// Len 用于排序
func (e GlobalBackupList) Len() int {
	return len(e)
}

// Less 用于排序
func (e GlobalBackupList) Less(i, j int) bool {
	if e[i].CreatedAt > e[j].CreatedAt {
		return true
	}
	return false
}

// Swap 用于排序
func (e GlobalBackupList) Swap(i, j int) {
	e[i], e[j] = e[j], e[i]
}

func buildSchema(db *sqlx.DB) string {
	isSpider, err := mysqlconn.IsSpiderNode(db)
	if err != nil {
		logger.Log.Error("buildSchema IsSpiderNode", err)
		return ""
	}
	if isSpider {
		s := MysqlServer{}
		parts, err := s.GetMysqlServers(db)
		if err != nil {
			logger.Log.Errorf("buildSchema GetMysqlServers: %v", err)
			return ""
		}

		partValues, err := getSpiderPartitions(parts)
		if err != nil {
			logger.Log.Errorf("buildSchema getSpiderPartitions: %v", err)
			return ""
		}
		return globalBackup("SPIDER", partValues)
	} else {
		return globalBackup("InnoDB", nil)
	}
}

func globalBackup(tableEngine string, partValues []int) string {
	// 真正的唯一性是：BackupId,Host,Port
	// ShardValue 是为了路由到对应的分片
	createTable := fmt.Sprintf(`
CREATE TABLE IF NOT EXISTS %s.global_backup (
  Server_name varchar(10) NOT NULL DEFAULT '',
  Wrapper varchar(20) NOT NULL DEFAULT '',
  Host varchar(60) NOT NULL DEFAULT '',
  Port int(4) NOT NULL DEFAULT 0,
  ShardValue int(11) NOT NULL,
  BackupId varchar(40) NOT NULL DEFAULT '',
  BackupStatus varchar(30) NOT NULL DEFAULT '',
  TaskPid int NOT NULL DEFAULT -1,
  CreatedAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UpdatedAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (BackupId,Host,Port,ShardValue)
) ENGINE=%s DEFAULT CHARSET=utf8mb4 COMMENT='shard_key "ShardValue"'
`, cst.INFODBA_SCHEMA, tableEngine)

	if tableEngine != "SPIDER" {
		return createTable
	}
	var partitions []string
	partitionInfo := fmt.Sprintf(`PARTITION BY LIST (ShardValue MOD %d)`, len(partValues))
	for _, i := range partValues {
		p := fmt.Sprintf(
			`PARTITION pt%d VALUES IN (%d) COMMENT = 'database "infodba_schema", table "global_backup", server "SPT%d"' ENGINE = SPIDER`, i, i, i)
		partitions = append(partitions, p)
	}
	createSQL := fmt.Sprintf("%s \n%s \n(%s)", createTable, partitionInfo, strings.Join(partitions, ",\n"))
	return createSQL
}

func migrateBackupSchema(err error, db *sqlx.DB) error {
	backupSchema := buildSchema(db)
	if backupSchema == "" {
		return errors.New("wrong backupSchema")
	}
	var sqlList []string
	if strings.Contains(backupSchema, "PARTITION pt") { // spider node
		sqlList = append(sqlList, "set session ddl_execute_by_ctl=OFF;")
	}
	if cmutil.NewMySQLError(err).Code == 1146 {
		sqlList = append(sqlList, backupSchema)

	} else if cmutil.NewMySQLError(err).Code == 1054 {
		dropSchema := fmt.Sprintf(`DROP TABLE IF EXISTS %s.global_backup;`, cst.INFODBA_SCHEMA)
		sqlList = append(sqlList, dropSchema)
		sqlList = append(sqlList, backupSchema)
	}
	logger.Log.Infof("init global_backup: %v", sqlList)
	for _, sqlStr := range sqlList {
		if _, err = db.Exec(sqlStr); err != nil {
			return errors.WithMessage(err, "recreate backupSchema failed")
		}
	}
	logger.Log.Info("migrate table success: global_backup")
	return nil
}
