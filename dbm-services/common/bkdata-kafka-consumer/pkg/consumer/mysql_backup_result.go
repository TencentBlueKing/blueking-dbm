// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package consumer

import (
	"encoding/json"
	"errors"
	"log/slog"
	"strconv"
	"time"

	sq "github.com/Masterminds/squirrel"
	"github.com/Shopify/sarama"
	"github.com/jinzhu/copier"
	"gorm.io/gorm"

	"dbm-services/common/bkdata-kafka-consumer/pkg/model/mysql_backup_result"
)

type MysqlBackupResult struct {
	Ready  chan bool
	Db     *gorm.DB
	Sinker *Sinker
}

func (c *MysqlBackupResult) Setup(sarama.ConsumerGroupSession) error {
	createTableSql := mysql_backup_result.CREATE_TABLE_SQL
	if err := c.Db.Exec(createTableSql).Error; err != nil {
		slog.Error("create table failed: %v, sql:%s", err, createTableSql)
		return err
	}
	return nil
}

func (c *MysqlBackupResult) Cleanup(sarama.ConsumerGroupSession) error {
	return nil
}

func (c *MysqlBackupResult) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	BatchSize := 10
	msgs := make([]*sarama.ConsumerMessage, 0, BatchSize)
	for {
		select {
		case <-time.After(time.Second * 1):
			if len(msgs) > 0 {
				if err := c.HandleMessageTryBatch(msgs, c.Sinker, c.Db); err != nil {
					slog.Error("handle message batch", err)
				} else {
					session.MarkMessage(msgs[len(msgs)-1], "")
				}
				msgs = msgs[:0]
			}
		case message := <-claim.Messages():
			msgs = append(msgs, message)
			if len(msgs) >= BatchSize {
				if err := c.HandleMessageTryBatch(msgs, c.Sinker, c.Db); err != nil {
					slog.Error("handle message batch", err)
					time.Sleep(200 * time.Millisecond)
				} else {
					session.MarkMessage(message, "")
				}
				msgs = msgs[:0]
			}
		case <-session.Context().Done():
			return nil
		}
	}
}

// HandleMessageTryBatch 先尝试批量写入到 db，如果失败，再尝试单条写入
func (c *MysqlBackupResult) HandleMessageTryBatch(msgs []*sarama.ConsumerMessage, s *Sinker, db *gorm.DB) error {
	err := c.HandleMessages(msgs, s, db)
	if err != nil {
		err = nil
		for _, msg := range msgs {
			if err2 := c.HandleMessages([]*sarama.ConsumerMessage{msg}, s, db); err2 != nil {
				slog.Error("handle message", err2)
				err = errors.Join(err, err2)
			}
		}
		return err
	}
	return nil
}

func (c *MysqlBackupResult) HandleMessages(msgs []*sarama.ConsumerMessage, s *Sinker, db *gorm.DB) error {
	if len(msgs) == 0 {
		return nil
	}
	sqlBuilder := sq.Replace(*s.RuntimeConfig.Dsn.Table).Columns("cluster_address",
		"backup_host",
		"backup_port",
		"mysql_role",
		"shard_value",
		"backup_id",
		"backup_type",
		"data_schema_grant",
		"is_full_backup",
		"backup_consistent_time",
		"backup_begin_time",
		"backup_end_time",
		"backup_status",
		"mysql_version",
		"file_retention_tag",
		"total_filesize",
		"cluster_id",
		"bk_biz_id",
		"bill_id",
		"binlog_info",
		"extra_fields",
		"file_list",
	)
	for _, message := range msgs {
		slog.Debug("process message", slog.String("Value", string(message.Value)))
		var msg messageWrapper
		err := json.Unmarshal(message.Value, &msg)
		if err != nil {
			slog.Error("unmarshal message", err)
			return err
		}

		for _, item := range msg.Items {
			var kafkaObj mysql_backup_result.IndexContent
			slog.Debug("unmarshal task object", slog.String("data", string(item.Data)))
			unquoteData, err := strconv.Unquote(string(item.Data))
			if err != nil {
				slog.Error("unquote message payload", err)
				return err
			}

			err = json.Unmarshal([]byte(unquoteData), &kafkaObj)
			if err != nil {
				slog.Error("unmarshal task object", err, slog.Any("msg", unquoteData))
				return err
			}

			var modelObj = &mysql_backup_result.ModelBackupReport{}
			if err = copier.Copy(modelObj, kafkaObj); err != nil {
				return err
			}
			modelObj.FileList, _ = json.Marshal(kafkaObj.FileList)
			modelObj.BinlogInfo, _ = json.Marshal(kafkaObj.BinlogInfo)
			modelObj.ExtraFields, _ = json.Marshal(kafkaObj.ExtraFields)
			modelObj.BkBizId = kafkaObj.BkBizId

			slog.Debug("unmarshal task obj", slog.Any("obj", kafkaObj))
			//err = c.Db.Table(*c.Sinker.RuntimeConfig.Dsn.Table).FirstOrCreate(&modelObj).Error
			sqlBuilder = sqlBuilder.Values(
				modelObj.ClusterAddress,
				modelObj.BackupHost,
				modelObj.BackupPort,
				modelObj.MysqlRole,
				modelObj.ShardValue,
				modelObj.BackupId,
				modelObj.BackupType,
				modelObj.DataSchemaGrant,
				modelObj.IsFullBackup,
				modelObj.BackupConsistentTime,
				modelObj.BackupBeginTime,
				modelObj.BackupEndTime,
				modelObj.BackupStatus,
				modelObj.MysqlVersion,
				modelObj.FileRetentionTag,
				modelObj.TotalFilesize,
				modelObj.ClusterId,
				modelObj.BkBizId,
				modelObj.BillId,
				modelObj.BinlogInfo,
				modelObj.ExtraFields,
				modelObj.FileList,
			)
		}
	}
	sqlStr, sqlArgs, err := sqlBuilder.ToSql()
	if err != nil {
		return err
	}
	err = db.Exec(sqlStr, sqlArgs...).Error
	if err != nil {
		slog.Error("replace message",
			slog.Any("msg", err), slog.String("sql", sqlStr), slog.Any("args", sqlArgs))
		//return err
	}
	return nil
}
