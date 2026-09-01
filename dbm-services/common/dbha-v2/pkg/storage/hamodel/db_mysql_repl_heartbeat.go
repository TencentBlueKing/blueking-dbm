/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package hamodel

const (
	// DbhaReplHeartbeatTableName is the probe-maintained replication-delay heartbeat
	// table on the probed instance.
	DbhaReplHeartbeatTableName = "dbha_repl_heartbeat"

	DbhaReplHeartbeatFieldHost       = "host"
	DbhaReplHeartbeatFieldPort       = "port"
	DbhaReplHeartbeatFieldServerID   = "server_id"
	DbhaReplHeartbeatFieldUpdateTime = "update_time"

	// CreateDbhaReplHeartbeatTableSQL creates the probe-owned repl heartbeat table.
	// Keep in sync with DbhaReplHeartbeat field tags below.
	CreateDbhaReplHeartbeatTableSQL = "CREATE TABLE IF NOT EXISTS `" +
		ProbeMysqlDbName + "`.`" + DbhaReplHeartbeatTableName + "` (" +
		"`host` varchar(64) NOT NULL," +
		"`port` int NOT NULL," +
		"`server_id` bigint unsigned NOT NULL DEFAULT 0," +
		"`update_time` varchar(32) NOT NULL," +
		"PRIMARY KEY (`host`, `port`)" +
		") ENGINE=InnoDB DEFAULT CHARSET=utf8"
)

// DbhaReplHeartbeat defines the schema of ProbeMysqlDbName.dbha_repl_heartbeat.
// The MySQL probe creates this table (IF NOT EXISTS) and upserts one row per target host:port.
type DbhaReplHeartbeat struct {
	Host       string `gorm:"column:host;primaryKey;type:varchar(64);not null"`
	Port       int    `gorm:"column:port;primaryKey;not null"`
	ServerID   uint64 `gorm:"column:server_id;not null"`
	UpdateTime string `gorm:"column:update_time;type:varchar(32);not null"`
}

// TableName returns the unqualified repl heartbeat table name.
func (DbhaReplHeartbeat) TableName() string {
	return DbhaReplHeartbeatTableName
}
