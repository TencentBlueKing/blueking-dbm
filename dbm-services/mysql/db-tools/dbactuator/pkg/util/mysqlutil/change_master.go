package mysqlutil

import (
	"fmt"
	"regexp"
	"strconv"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/pkg/errors"
)

// ChangeMaster TODO
type ChangeMaster struct {
	MasterHost     string `json:"master_host"  validate:"required,ip" `               // 主库ip
	MasterPort     int    `json:"master_port"  validate:"required,lt=65536,gte=3306"` // 主库端口
	MasterUser     string `json:"master_user" validate:"required"`
	MasterPassword string `json:"master_password" validate:"required"`
	MasterLogFile  string `json:"master_log_file"` // binlog 文件名称
	MasterLogPos   int64  `json:"master_log_pos"`  // binlog 位点信息

	MasterAutoPosition int    `json:"master_auto_position"`
	Channel            string `json:"channel"`
	IsGtid             bool   `json:"is_gtid"` // 是否启动GID方式进行建立主从
	ExecutedGtidSet    string `json:"executed_gtid_set"`
	MaxTolerateDelay   int    `json:"max_tolerate_delay"` // 最大容忍延迟,即主从延迟小于该值,认为建立主从关系成功
	Force              bool   `json:"force"`              // 如果当前实例存在主从关系是否直接reset slave后,强制change master

	ChangeSQL string `json:"change_sql"`
}

// Validate TODO
func (c *ChangeMaster) Validate() error {
	return nil
}

// GetSQL 根据各个字段组合成 change master to
func (c *ChangeMaster) GetSQL() string {
	var sql string
	if c.IsGtid {
		sql = fmt.Sprintf(
			`CHANGE MASTER TO MASTER_HOST='%s',MASTER_PORT=%d, MASTER_USER = '%s', MASTER_PASSWORD = '%s'`,
			c.MasterHost, c.MasterPort, c.MasterUser, c.MasterPassword,
		)
	} else {
		sql = fmt.Sprintf(
			`CHANGE MASTER TO MASTER_HOST='%s', 
			 MASTER_PORT=%d, 
			 MASTER_USER ='%s', 
			 MASTER_PASSWORD='%s',
			 MASTER_LOG_FILE='%s', 
			 MASTER_LOG_POS=%d`,
			c.MasterHost,
			c.MasterPort,
			c.MasterUser,
			c.MasterPassword,
			c.MasterLogFile,
			c.MasterLogPos,
		)
	}
	c.ChangeSQL = sql
	return sql
}

// ParseChangeSQL 根据 change_sql 字段拆解成各个字段
func (c *ChangeMaster) ParseChangeSQL() error {
	// 移除 = 号前后的空格
	c.ChangeSQL = util.RegexReplaceSubString(c.ChangeSQL, `\s+=`, "=")
	c.ChangeSQL = util.RegexReplaceSubString(c.ChangeSQL, `=\s+`, "=")

	reHost := regexp.MustCompile(`(?iU)master_host=['"](.*)['"]`)
	rePort := regexp.MustCompile(`(?i)master_port=(\d+)`)
	reLogFile := regexp.MustCompile(`(?iU)master_log_file=['"](.*)['"]`)
	reLogPos := regexp.MustCompile(`(?i)master_log_pos=(\d+)`)
	if m := reLogFile.FindStringSubmatch(c.ChangeSQL); len(m) == 2 {
		c.MasterLogFile = m[1]
	}
	if m := reLogPos.FindStringSubmatch(c.ChangeSQL); len(m) == 2 {
		c.MasterLogPos, _ = strconv.ParseInt(m[1], 10, 64)
	}
	if m := reHost.FindStringSubmatch(c.ChangeSQL); len(m) == 2 {
		c.MasterHost = m[1]
	}
	if m := rePort.FindStringSubmatch(c.ChangeSQL); len(m) == 2 {
		c.MasterPort, _ = strconv.Atoi(m[1])
	}
	logger.Warn("parsed items %+v", c)
	return nil
}

// ParseXtraBinlogInfo 从 xtrabackup_binlog_info 中解析出 file,pos，无 host,port 信息
func ParseXtraBinlogInfo(binlogInfo string) (*ChangeMaster, error) {
	// binlog20000.005986      54045
	reg := regexp.MustCompile(`(.+\.\d+)\s+(\d+)`)
	if m := reg.FindStringSubmatch(binlogInfo); len(m) != 3 {
		return nil, errors.Errorf("fail to get binlog_info from %s", binlogInfo)
	} else {
		pos, _ := strconv.Atoi(m[2])
		cm := &ChangeMaster{
			MasterLogFile: m[1],
			MasterLogPos:  int64(pos),
		}
		return cm, nil
	}
}
