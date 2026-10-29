// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package configreport

import (
	"bytes"
	"context"
	"database/sql"
	"database/sql/driver"
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"
)

// discardConn 通过 Raw+ErrBadConn 让 database/sql 真正关闭底层 TCP 连接，而不是归还到连接池
// 用于修改了 session 变量（如 sql_log_bin=0）的连接，避免脏状态泄漏给其他调用方
// 连接池在后续请求时会自动创建新连接
func discardConn(conn *sqlx.Conn) {
	_ = conn.Raw(func(any) error { return driver.ErrBadConn })
	_ = conn.Close()
}

// resetConnOrClose 恢复 sql_log_bin=1 并归还连接到池
// 如果恢复失败，通过 Raw+ErrBadConn 丢弃连接，避免脏 session 状态泄漏到连接池
func resetConnOrClose(conn *sqlx.Conn) {
	if _, err := conn.ExecContext(context.Background(), "SET SESSION sql_log_bin=1"); err != nil {
		slog.Warn("failed to restore sql_log_bin, discarding connection", slog.String("error", err.Error()))
		_ = conn.Raw(func(any) error { return driver.ErrBadConn })
		// Raw 已经 close(ErrBadConn)，后续 Close() 只会返回 ErrConnDone
	}
	_ = conn.Close()
}

const maskedValue = "******"

// sensitiveKeys 需要脱敏的 JSON 字段名（转小写、去掉下划线后比较）
// dbbackup: MysqlPasswd, ssh_pass; rotatebinlog: password; checksum: Password
var sensitiveKeys = map[string]struct{}{
	"password":    {},
	"passwd":      {},
	"mysqlpasswd": {},
	"sshpass":     {},
}

func isSensitiveKey(k string) bool {
	_, ok := sensitiveKeys[strings.ReplaceAll(strings.ToLower(k), "_", "")]
	return ok
}

// MaskedJSONPayload 将配置对象序列化为 JSON，并把非空的密码字段值替换为 ******
// 返回脱敏后的对象（用于事件上报）和对应的 JSON 文本（用于写入 local_config），两者内容一致，便于与服务端记录做比对
func MaskedJSONPayload(v interface{}) (interface{}, string, error) {
	raw, err := json.Marshal(v)
	if err != nil {
		return nil, "", errors.WithMessage(err, "marshal config")
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber() // 避免大整数转 float64 丢精度
	var obj interface{}
	if err = dec.Decode(&obj); err != nil {
		return nil, "", errors.WithMessage(err, "decode config json")
	}
	obj = maskSensitive(obj)
	out, err := json.Marshal(obj)
	if err != nil {
		return nil, "", errors.WithMessage(err, "marshal masked config")
	}
	return obj, string(out), nil
}

// maskSensitive 递归处理 map / slice，敏感字段非空字符串值替换为 ******
func maskSensitive(v interface{}) interface{} {
	switch t := v.(type) {
	case map[string]interface{}:
		for k, val := range t {
			if s, ok := val.(string); ok && isSensitiveKey(k) {
				if s != "" {
					t[k] = maskedValue
				}
				continue
			}
			t[k] = maskSensitive(val)
		}
		return t
	case []interface{}:
		for i := range t {
			t[i] = maskSensitive(t[i])
		}
		return t
	default:
		return v
	}
}

// FlattenOneLevel 将嵌套 JSON 对象收一级
// 顶层 key 的值如果是 map，其子项提升为 "parent.child": childValue（childValue 保持原样不再递归）
// 顶层 key 的值如果不是 map（string/number/bool/null/array），保持不变
//
//	{"a":{"x":1,"y":2},"b":3} → {"a.x":1,"a.y":2,"b":3}
func FlattenOneLevel(v interface{}) interface{} {
	m, ok := v.(map[string]interface{})
	if !ok {
		return v
	}
	result := make(map[string]interface{}, len(m))
	for k, val := range m {
		sub, ok := val.(map[string]interface{})
		if !ok {
			result[k] = val
			continue
		}
		for ck, cv := range sub {
			result[k+"."+ck] = cv
		}
	}
	return result
}

// ModelLocalConfig infodba_schema.local_config
type ModelLocalConfig struct {
	Host          string `db:"host"`
	Port          int    `db:"port"`
	ConfType      string `db:"conf_type"`
	ConfFile      string `db:"conf_file"`
	ConfigKey     string `db:"config_key"`
	ConfigValue   string `db:"config_value"`
	ConfMtime     int64  `db:"conf_mtime"`
	ClusterDomain string `db:"cluster_domain"`
}

// TableName local_config 表名
func (m ModelLocalConfig) TableName() string {
	return fmt.Sprintf("%s.%s", cst.DBASchema, "local_config")
}

// migrateLocalConfigSchema 创建 local_config 表
// 如果 errs 能够处理（表不存在/字段不存在），自动修复表结构
func migrateLocalConfigSchema(errs error, conn *sqlx.Conn) error {
	if errs != nil {
		mysqlErr := cmutil.NewMySQLError(errs)
		if !(mysqlErr.Code == 1054 || mysqlErr.Code == 1146) {
			return errors.WithMessage(errs, "error unhandled")
		}
	}
	createTable := fmt.Sprintf(`
CREATE TABLE IF NOT EXISTS %s (
	host varchar(60) NOT NULL,
	port int(11) NOT NULL DEFAULT 0,
	conf_type varchar(60) NOT NULL,
	conf_file varchar(60) NOT NULL,
	config_key varchar(60) NOT NULL DEFAULT '',
	config_value mediumtext NOT NULL,
	conf_mtime bigint NOT NULL DEFAULT 0,
	updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	cluster_domain varchar(255) DEFAULT NULL,
	PRIMARY KEY (host, port, conf_file, config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
`, ModelLocalConfig{}.TableName())

	dropTable := fmt.Sprintf(`DROP TABLE IF EXISTS %s;`, ModelLocalConfig{}.TableName())
	sqlList := []string{dropTable, createTable}
	slog.Info("init local_config", slog.Any("sql", sqlList))
	for _, sqlStr := range sqlList {
		if _, err := conn.ExecContext(context.Background(), sqlStr); err != nil {
			return errors.WithMessage(err, "create local_config failed")
		}
	}
	slog.Info("migrate table success: local_config")
	return nil
}

// NeedWriteLocalConfig 判断是否需要写入 local_config
// 满足以下任一条件即返回 true：
//  1. 本机（host, port, conf_file, config_key）没有这一行
//  2. 文件 mtime 和上次写入时记录的 conf_mtime 不同
//  3. updated_at 已超过 24 小时
//
// 表不存在（1146）或字段不存在（1054）也视为需要写入
func NeedWriteLocalConfig(db *pkg.MySQLMonitorDBH, cfg *ModelLocalConfig) (bool, error) {
	if db == nil || db.DB == nil {
		return true, nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// 查询：同时满足 conf_mtime 相同 且 updated_at 在 24 小时内 → 不需要写
	sqlStr := fmt.Sprintf(
		"SELECT 1 FROM %s WHERE host=? AND port=? AND conf_file=? AND config_key=? AND conf_mtime=? AND updated_at > NOW() - INTERVAL 24 HOUR",
		cfg.TableName(),
	)
	var exists int
	err := db.QueryRowxContext(ctx, sqlStr, cfg.Host, cfg.Port, cfg.ConfFile, cfg.ConfigKey, cfg.ConfMtime).Scan(&exists)
	if err != nil {
		if err == sql.ErrNoRows {
			return true, nil
		}
		mysqlErr := cmutil.NewMySQLError(err)
		if mysqlErr.Code == 1146 || mysqlErr.Code == 1054 {
			return true, nil
		}
		return false, errors.WithMessage(err, "check local_config")
	}
	return false, nil
}

// DeleteLocalConfig 删除本机 local_config 中的一行（配置文件不存在时使用）
func DeleteLocalConfig(db *pkg.MySQLMonitorDBH, cfg *ModelLocalConfig) error {
	if db == nil || db.DB == nil {
		return nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	conn, err := db.Connx(ctx)
	if err != nil {
		return errors.WithMessage(err, "delete local_config get conn")
	}
	defer discardConn(conn)

	if _, err = conn.ExecContext(ctx, "SET SESSION sql_log_bin=0"); err != nil {
		return errors.WithMessage(err, "delete local_config set sql_log_bin=0")
	}

	sqlStr := fmt.Sprintf(
		"DELETE FROM %s WHERE host=? AND port=? AND conf_file=? AND config_key=?",
		cfg.TableName(),
	)
	if _, err = conn.ExecContext(ctx, sqlStr, cfg.Host, cfg.Port, cfg.ConfFile, cfg.ConfigKey); err != nil {
		mysqlErr := cmutil.NewMySQLError(err)
		if mysqlErr.Code == 1146 || mysqlErr.Code == 1054 {
			return nil // 表都没有，不需要删
		}
		return errors.WithMessage(err, "delete local_config")
	}
	return nil
}

// ReplaceLocalConfig 覆盖式写入本机实例 infodba_schema.local_config，不记录 binlog
func ReplaceLocalConfig(db *pkg.MySQLMonitorDBH, cfg *ModelLocalConfig) error {
	if db == nil || db.DB == nil {
		return errors.New("write local_config: db connection is nil")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	conn, err := db.Connx(ctx)
	if err != nil {
		return errors.WithMessage(err, "write local_config get conn")
	}
	defer discardConn(conn)

	if _, err = conn.ExecContext(ctx, "SET SESSION sql_log_bin=0"); err != nil {
		return errors.WithMessage(err, "write local_config set sql_log_bin=0")
	}

	sqlStr := fmt.Sprintf(
		"REPLACE INTO %s (host, port, conf_type, conf_file, config_key, config_value, conf_mtime, updated_at, cluster_domain) "+
			"VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?)",
		cfg.TableName(),
	)
	args := []interface{}{
		cfg.Host, cfg.Port, cfg.ConfType, cfg.ConfFile, cfg.ConfigKey, cfg.ConfigValue, cfg.ConfMtime, cfg.ClusterDomain,
	}
	if _, err = conn.ExecContext(ctx, sqlStr, args...); err != nil {
		slog.Warn("write local_config failed, try to fix", slog.String("error", err.Error()))
		if err = migrateLocalConfigSchema(err, conn); err != nil {
			return err
		}
		if _, err = conn.ExecContext(ctx, sqlStr, args...); err != nil {
			return errors.WithMessage(err, "write local_config again")
		}
	}
	return nil
}
