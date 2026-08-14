// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

import (
	"log/slog"
	"time"

	"github.com/pkg/errors"
	"gorm.io/gorm"

	"dbm-services/common/db-event-consumer/pkg/base"
)

/*
{"report_type":"redis_binlogbackup","bk_biz_id":"00002","bk_cloud_id":0,
"server_ip":"1.2.3.79","server_port":30009,"domain":"2.a.1.db",
"db_type":"TendisSSDInstance","role":"slave",
"backup_dir":"/data/dbbak/binlog/30009","backup_file":"/data/dbbak/binlog/30009/binlog-1.3.3.79-30009-0014018-20251216171048.log.zst",
"kvstoreidx":0,"backup_file_size":3649228,"time_zone":"CST","backup_taskid":"26208491383",
"backup_md5":"","backup_tag":"REDIS_BINLOG","shard_value":"7875-8749",
"status":"to_backup_system_start","message":"上传备份系统中","start_time":"2025-12-16T17:10:48+08:00","end_time":"2025-12-16T17:31:20+08:00"}

{"report_type":"redis_binlogbackup","bk_biz_id":"00002","bk_cloud_id":0,
"server_ip":"1.1.2.214","server_port":30000,"domain":"z.x.b.db",
"db_type":"TendisplusInstance","role":"slave",
"backup_dir":"/data/dbbak/binlog/30000","backup_file":"/data/dbbak/binlog/30000/binlog-1.2.1.214-30000-5-0022670-20251216171459.log.zst",
"kvstoreidx":5,"backup_file_size":2712382,"time_zone":"CST","backup_taskid":"26208498264",
"backup_md5":"","backup_tag":"REDIS_BINLOG","shard_value":"15236-15528",
"status":"to_backup_system_start","message":"上传备份系统中","start_time":"2025-12-16T17:14:59+08:00","end_time":"2025-12-16T17:34:59+08:00"}

*/

type RedisBinlogFileModel struct {
	base.BaseModel `json:",inline" gorm:"embedded" xorm:"extends"`

	BackupType   string `json:"report_type" db:"backup_type" gorm:"column:backup_type;type:varchar(32);NOT NULL"`
	ImmuteDomain string `json:"domain" db:"immute_domain" gorm:"column:immute_domain;type:varchar(255);NOT NULL"`
	BackupHost   string `json:"server_ip" db:"backup_host" gorm:"column:backup_host;type:varchar(32);NOT NULL;index:uk_cluster,unique,priority:1"`
	BackupPort   int    `json:"server_port" db:"backup_port" gorm:"column:backup_port;type:int;NOT NULL;index:uk_cluster,unique,priority:2"`
	KvStoreIdx   int    `json:"kvstoreidx" db:"kvstoreidx" gorm:"column:kvstoreidx;type:int;NOT NULL;index:uk_cluster,unique,priority:3"`
	InstRole     string `json:"role" db:"redis_role" gorm:"column:redis_role;type:varchar(32);NOT NULL"`
	DbType       string `json:"db_type" db:"redis_type" gorm:"column:redis_type;type:varchar(32);NOT NULL"`
	// BillId          string `json:"bill_id" db:"bill_id" gorm:"column:bill_id;type:varchar(32);NOT NULL"`
	BkBizId stringOrInt64 `json:"bk_biz_id" db:"bk_biz_id" gorm:"column:bk_biz_id;type:int;NOT NULL"`
	// MysqlVersion    string `json:"mysql_version" db:"mysql_version" gorm:"column:mysql_version;type:varchar(120);NOT NULL"`

	BackupTaskID   string `json:"backup_taskid" db:"backup_taskid" gorm:"column:backup_taskid;type:varchar(128);NOT NULL"`
	BackupFilesize uint64 `json:"backup_file_size" db:"backup_file_size" gorm:"column:backup_file_size;type:bigint;NOT NULL"`
	BackupFileName string `json:"backup_file" db:"backup_file" gorm:"column:backup_file;type:varchar(255);NOT NULL;index:uk_cluster,unique,priority:4"`

	ShardValue string `json:"shard_value" db:"shard_value" gorm:"column:shard_value;type:varchar(255)"`
	BackupTag  string `json:"backup_tag" db:"backup_tag" gorm:"column:backup_tag;type:varchar(255);NOT NULL"`

	BackupBeginTime time.Time `json:"start_time" db:"backup_begin_time" gorm:"column:backup_begin_time;type:TIMESTAMP NULL;default:null"`
	BackupEndTime   time.Time `json:"end_time" db:"backup_end_time" gorm:"column:backup_end_time;type:TIMESTAMP NULL;default:null"`
	BackupStatus    string    `json:"status,omitempty" db:"backup_status" gorm:"column:backup_status;type:varchar(32);NOT NULL"`
}

func (m RedisBinlogFileModel) TableName() string {
	return "tb_redis_binlog_result"
}

// UniqueKey is used to handle duplicate record
func (m RedisBinlogFileModel) UniqueKey() []string {
	return []string{"backup_host", "backup_port", "kvstoreidx", "backup_file"}
}

// MigrateSchema 自定义迁移: 处理列名 backup_ip -> backup_host 的历史数据.
// 老版本 (v<=?) 该列叫 backup_ip, 与 tb_redis_backup_result / tb_mysql_binlog_result
// 的 backup_host 不一致, 这里统一为 backup_host, 老列存在时通过 CHANGE COLUMN 保留存量数据.
func (m RedisBinlogFileModel) MigrateSchema(w base.DSWriter) error {
	slog.Info("run migrate for RedisBinlogFileModel", slog.String("table", m.TableName()))
	if w.Type() != "mysql" && w.Type() != "mysql_raw" {
		return w.AutoMigrate(m)
	}
	dbWriter, ok := w.(base.GormMigrator)
	if !ok {
		return errors.Errorf("writer_type=%s has no gorm db for custom migrate: %s", w.Type(), m.TableName())
	}
	db := dbWriter.GormDB()

	// 若历史表存在 backup_ip 列, 先把它重命名为 backup_host, 保留存量数据
	if db.Migrator().HasTable(m.TableName()) &&
		db.Migrator().HasColumn(&m, "backup_ip") &&
		!db.Migrator().HasColumn(&m, "backup_host") {
		slog.Info("rename column backup_ip -> backup_host",
			slog.String("table", m.TableName()))
		if err := db.Exec(
			"ALTER TABLE `" + m.TableName() + "` " +
				"CHANGE COLUMN `backup_ip` `backup_host` varchar(32) NOT NULL",
		).Error; err != nil {
			return errors.WithMessage(err, "rename backup_ip -> backup_host")
		}
		// 老唯一索引里带的是 backup_ip, 需要重建
		if err := dropIndexIfExists(db, m.TableName(), "uk_cluster"); err != nil {
			return err
		}
	}

	// 历史列 backup_status 曾为 tinyint (数值枚举), 现已改为 varchar(32) (与 dbmon 生产端
	// models/binlog.go 里 Status string 对齐). AutoMigrate 不会自动改变列类型, 这里显式
	// MODIFY COLUMN 以确保存量表也升级到 varchar(32); 已经是 varchar 的表执行也是幂等的.
	if db.Migrator().HasTable(m.TableName()) && db.Migrator().HasColumn(&m, "backup_status") {
		if err := db.Exec(
			"ALTER TABLE `" + m.TableName() + "` " +
				"MODIFY COLUMN `backup_status` varchar(32) NOT NULL",
		).Error; err != nil {
			return errors.WithMessage(err, "modify backup_status to varchar(32)")
		}
	}

	if err := db.Migrator().AutoMigrate(&m); err != nil {
		return err
	}

	if err := base.CreateOrUpdateIndex(db, m.TableName(), "uk_cluster",
		[]string{"backup_host", "backup_port", "kvstoreidx", "backup_file"}, true, true); err != nil {
		return err
	}
	return nil
}

func dropIndexIfExists(db *gorm.DB, tableName, indexName string) error {
	indexes, err := db.Migrator().GetIndexes(tableName)
	if err != nil {
		return errors.WithMessagef(err, "get indexes of %s", tableName)
	}
	for _, i := range indexes {
		if i.Name() == indexName {
			if err := db.Migrator().DropIndex(tableName, indexName); err != nil {
				return errors.WithMessagef(err, "drop old index %s on %s", indexName, tableName)
			}
			return nil
		}
	}
	return nil
}
