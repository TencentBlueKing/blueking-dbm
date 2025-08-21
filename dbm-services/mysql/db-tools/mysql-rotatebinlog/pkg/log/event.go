package log

import (
	"encoding/json"
	"time"

	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/models"
)

type MysqlBinlogResultEvent models.BinlogFileModel

func (e *MysqlBinlogResultEvent) ClusterType() string {
	return "tendbha"
}

func (e *MysqlBinlogResultEvent) EventType() string {
	return "mysql_binlog_result"
}

func (e *MysqlBinlogResultEvent) EventCreateTimeStamp() int64 {
	return time.Now().UnixMicro()
}

func (e *MysqlBinlogResultEvent) EventBkBizId() int64 {
	return int64(e.BkBizId)
}

// 不强求实现 String, 这里是给下面的错误处理写例子用的
func (e *MysqlBinlogResultEvent) String() string {
	b, _ := json.Marshal(e)
	return string(b)
}
