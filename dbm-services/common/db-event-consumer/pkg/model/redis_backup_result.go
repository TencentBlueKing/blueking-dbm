// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

import (
	"database/sql/driver"
	"log/slog"
	"strconv"
	"time"

	"github.com/go-playground/validator/v10"
	json "github.com/goccy/go-json"
	sb "github.com/huandu/go-sqlbuilder"
	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"gorm.io/gorm"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/sinker"
)

type stringOrInt64 int64

func (n *stringOrInt64) UnmarshalJSON(data []byte) error {
	if string(data) == "null" || len(data) == 0 {
		return nil
	}
	if data[0] == '"' {
		var s string
		if err := json.Unmarshal(data, &s); err != nil {
			return err
		}
		if s == "" {
			*n = 0
			return nil
		}
		v, err := strconv.ParseInt(s, 10, 64)
		if err != nil {
			return err
		}
		*n = stringOrInt64(v)
		return nil
	}
	v, err := strconv.ParseInt(string(data), 10, 64)
	if err != nil {
		return err
	}
	*n = stringOrInt64(v)
	return nil
}

func (n stringOrInt64) Value() (driver.Value, error) {
	return int64(n), nil
}

/*
{"report_type":"redis_fullbackup","bk_biz_id":"00001","bk_cloud_id":0,
"server_ip":"1.1.1.81","server_port":30000,"domain":"x.x.x.x",
"db_type":"TendisplusInstance","role":"slave",
"backup_dir":"/data/dbbak","backup_file":"/data/dbbak/00001-TENDISPLUS-FULL-slave-1.1.1.1-30000-20251215-050000.tar",
"backup_file_size":48912568320,"backup_taskid":"26192158766","backup_md5":"",
"backup_identify":"SCHEDULED-2025121505","backup_tag":"REDIS_FULL","shard_value":"0-2730",
"time_zone":"CST","status":"to_backup_system_start","message":"上传备份系统中",
"start_time":"2025-12-15T05:00:00+08:00","end_time":"2025-12-15T05:01:35+08:00"}

{"report_type":"redis_fullbackup","bk_biz_id":"00002","bk_cloud_id":0,
"server_ip":"1.1.1.6","server_port":30002,"domain":"cache.1-b-exp.x.db",
"db_type":"RedisInstance","role":"slave",
"backup_dir":"/data/dbbak","backup_file":"/data/dbbak/00002-redis-slave-1.1.1.6-30002-20251216-130011.aof.zst",
"backup_file_size":1425,"backup_taskid":"26206360774","backup_md5":"",
"backup_file_tag":"SCHEDULED-2025121601","backup_tag":"REDIS_FULL","shard_value":"210000-314999",
"time_zone":"CST","status":"to_backup_system_start","message":"上传备份系统中",
"start_time":"2025-12-16T13:00:11+08:00","end_time":"2025-12-16T13:00:16+08:00"}
*/
type RedisBackupResultModel struct {
	base.BaseModel `json:",inline" gorm:"embedded" xorm:"extends"`

	BackupType   string `json:"report_type" db:"backup_type" gorm:"column:backup_type;type:varchar(32);NOT NULL"`
	ImmuteDomain string `json:"domain" db:"immute_domain" gorm:"column:immute_domain;type:varchar(255);NOT NULL"`
	BackupHost   string `json:"server_ip" db:"backup_host" gorm:"column:backup_host;type:varchar(32);NOT NULL;index:uk_cluster,unique,priority:1"`
	BackupPort   int    `json:"server_port" db:"backup_port" gorm:"column:backup_port;type:int;NOT NULL;index:uk_cluster,unique,priority:2"`
	InstRole     string `json:"role" db:"redis_role" gorm:"column:redis_role;type:varchar(32);NOT NULL"`
	DbType       string `json:"db_type" db:"redis_type" gorm:"column:redis_type;type:varchar(32);NOT NULL"`
	// BillId          string `json:"bill_id" db:"bill_id" gorm:"column:bill_id;type:varchar(32);NOT NULL"`
	BkBizId stringOrInt64 `json:"bk_biz_id" db:"bk_biz_id" gorm:"column:bk_biz_id;type:int;NOT NULL"`
	// MysqlVersion    string `json:"mysql_version" db:"mysql_version" gorm:"column:mysql_version;type:varchar(120);NOT NULL"`

	BackupTaskID   string `json:"backup_taskid" db:"backup_taskid" gorm:"column:backup_taskid;type:varchar(128);NOT NULL"`
	BackupFilesize uint64 `json:"backup_file_size" db:"backup_file_size" gorm:"column:backup_file_size;type:bigint;NOT NULL"`
	BackupFileName string `json:"backup_file" db:"backup_file" gorm:"column:backup_file;type:varchar(255);NOT NULL;index:uk_cluster,unique,priority:3"`

	ShardValue     string `json:"shard_value" db:"shard_value" gorm:"column:shard_value;type:varchar(255)"`
	BackupTag      string `json:"backup_tag" db:"backup_tag" gorm:"column:backup_tag;type:varchar(255);NOT NULL"`
	BackupIdentify string `json:"backup_identify" db:"backup_identify" gorm:"column:backup_identify;type:varchar(255);NOT NULL"`

	// IsStandby 是否是 standby, yes/no, empty means unknown - keep it.
	IsStandby       string    `json:"is_standby" db:"is_standby" gorm:"column:is_standby;type:varchar(10)"`
	BackupBeginTime time.Time `json:"start_time" db:"backup_begin_time" gorm:"column:backup_begin_time;type:TIMESTAMP NULL;default:null"`
	BackupEndTime   time.Time `json:"end_time" db:"backup_end_time" gorm:"column:backup_end_time;type:TIMESTAMP NULL;default:null"`

	ExtraFields  json.RawMessage `json:"extra_fields" db:"extra_fields" gorm:"column:extra_fields;type:longtext;NOT NULL"`
	BackupStatus string          `json:"status" db:"backup_status" gorm:"column:backup_status;type:varchar(32);NOT NULL"`
}

func (m *RedisBackupResultModel) TableName() string {
	return "tb_redis_backup_result"
}

// UniqueKey is used to handle duplicate record
func (m *RedisBackupResultModel) UniqueKey() []string {
	return []string{"backup_host", "backup_port", "backup_file"}
}

func (m *RedisBackupResultModel) MigrateSchema(w base.DSWriter) error {
	slog.Info("run migrate for RedisBackupResultModel", slog.String("table", m.TableName()))
	if w.Type() == "mysql" || w.Type() == "mysql_raw" {
		dbWriter, ok := w.(base.GormMigrator)
		if !ok {
			return errors.Errorf("writer_type=%s has no gorm db for custom migrate: %s", w.Type(), m.TableName())
		}
		db := dbWriter.GormDB()
		// 调用通用 migrate
		if err := db.Migrator().AutoMigrate(&m); err != nil {
			return err
		}
		// 处理索引与其他约束
		// uk_cluster: 同一实例的同一个备份文件仅入一条记录, 避免 REPLACE 覆盖不同文件.
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "uk_cluster",
			[]string{"backup_host", "backup_port", "backup_file"}, true, true); err != nil {
			return err
		}
		// 老版本可能残留 uk_hostport, 迁移到 uk_cluster 后清理掉
		if err := dropIndexIfExists(db, m.TableName(), "uk_hostport"); err != nil {
			return err
		}
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_domain_identify",
			[]string{"immute_domain", "backup_identify"}, false, true); err != nil {
			return err
		}
		// 老版本同字段索引名为 idx_clustertime, 已由 idx_domain_identify 取代, 清理掉
		if err := dropIndexIfExists(db, m.TableName(), "idx_clustertime"); err != nil {
			return err
		}
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_backupid",
			[]string{"backup_taskid"}, false, true); err != nil {
			return err
		}
		return nil
	} else {
		return w.AutoMigrate(m)
	}
}

func (m *RedisBackupResultModel) Create(objs interface{}, w base.DSWriter) error {
	if w.Type() == "mysql" {
		if writer, ok := w.(*sinker.MysqlWriter); ok {
			return m.mysqlCreate(objs, writer.GormDB())
		} else if writer, ok := w.(*sinker.XormWriter); ok {
			return errors.Errorf("not implement custom writer: %s", writer.Type())
		} else {
			return errors.Errorf("not implement custom writer: %s", w.Type())
		}
	} else {
		newObj := objs.([]RedisBackupResultModel)
		return w.WriteBatch(m, newObj)
	}
}

func (m *RedisBackupResultModel) mysqlCreate(i interface{}, db *gorm.DB) error {
	kafkaObjs, ok := i.([]RedisBackupResultModel)
	if !ok {
		kafkaObjs = []RedisBackupResultModel{i.(RedisBackupResultModel)}
	}

	builder := sb.NewInsertBuilder()
	builder.ReplaceInto(m.TableName())
	builder.Cols("immute_domain",
		"backup_host",
		"backup_port",
		"redis_role",
		"redis_type",
		"shard_value",
		"backup_type",
		"is_standby",
		"backup_file",
		"backup_taskid",
		"backup_file_size",
		"backup_tag",
		"backup_identify",
		"backup_begin_time",
		"backup_end_time",
		"backup_status",
		"bk_biz_id",
		"extra_fields",
		"event_create_timestamp",
		"event_report_timestamp",
		"event_uuid",
	)

	for _, kafkaObj := range kafkaObjs {
		var modelObj = &RedisBackupResultModel{}
		if err := copier.Copy(modelObj, kafkaObj); err != nil {
			return err
		}
		modelObj.ExtraFields, _ = json.Marshal(kafkaObj.ExtraFields)
		modelObj.BkBizId = kafkaObj.BkBizId
		builder.Values(
			modelObj.ImmuteDomain,
			modelObj.BackupHost,
			modelObj.BackupPort,
			modelObj.InstRole,
			modelObj.DbType,
			modelObj.ShardValue,
			modelObj.BackupType,
			modelObj.IsStandby,
			modelObj.BackupFileName,
			modelObj.BackupTaskID,
			modelObj.BackupFilesize,
			modelObj.BackupTag,
			modelObj.BackupIdentify,
			modelObj.BackupBeginTime.UTC(),
			modelObj.BackupEndTime.UTC(),
			modelObj.BackupStatus,
			int64(modelObj.BkBizId),
			modelObj.ExtraFields,
			modelObj.EventCreateTimestamp,
			modelObj.EventReportTimestamp,
			modelObj.EventUuid,
		)
	}

	sqlStr, sqlArgs := builder.Build()
	sqlFull, err := sb.MySQL.Interpolate(sqlStr, sqlArgs)
	if err != nil {
		return err
	}
	err = db.Model(m).Exec(sqlFull).Error
	if err != nil {
		slog.Error("replace message",
			slog.Any("msg", err), slog.String("sql", sqlStr), slog.Any("args", sqlArgs))
		//return err
	}
	return nil
}

func (m *RedisBackupResultModel) Validate() error {
	validate := validator.New()
	return validate.Struct(m)
	//validationErrors := err.(validator.ValidationErrors)
}

func (m *RedisBackupResultModel) UnmarshalJSON(data []byte) error {
	type redisBackupResultModel RedisBackupResultModel
	msg := struct {
		*redisBackupResultModel
		BackupFileTag string `json:"backup_file_tag"`
	}{
		redisBackupResultModel: (*redisBackupResultModel)(m),
	}
	if err := json.Unmarshal(data, &msg); err != nil {
		return err
	}
	if m.BackupIdentify == "" {
		m.BackupIdentify = msg.BackupFileTag
	}
	return nil
}

// type RedisBackupResultMsg struct {
// 	base.BaseModel `json:",inline"`
// 	//dbareport.IndexContent `json:",inline"`
// 	dbareport.BackupMetaFileBase `json:",inline"`
// 	dbareport.ExtraFields        `json:",inline"`
// 	FileList                     []*dbareport.TarFileItem `json:"file_list" db:"file_list"`
// }
