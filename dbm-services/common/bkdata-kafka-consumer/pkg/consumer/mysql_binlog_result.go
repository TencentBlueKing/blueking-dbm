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

	"dbm-services/common/bkdata-kafka-consumer/pkg/model/mysql_binlog_result"

	sq "github.com/Masterminds/squirrel"
	"github.com/Shopify/sarama"
	"github.com/jinzhu/copier"
	"gorm.io/gorm"
)

type MysqlBinlogResult struct {
	Ready  chan bool
	Db     *gorm.DB
	Sinker *Sinker
}

func (c *MysqlBinlogResult) Setup(sarama.ConsumerGroupSession) error {
	createTableSql := mysql_binlog_result.CREATE_TABLE_SQL
	if err := c.Db.Exec(createTableSql).Error; err != nil {
		slog.Error("create table failed: %v, sql:%s", err, createTableSql)
		return err
	}
	return nil
}

func (c *MysqlBinlogResult) Cleanup(sarama.ConsumerGroupSession) error {
	return nil
}

func (c *MysqlBinlogResult) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
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
func (c *MysqlBinlogResult) HandleMessageTryBatch(msgs []*sarama.ConsumerMessage, s *Sinker, db *gorm.DB) error {
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

func (c *MysqlBinlogResult) HandleMessages(msgs []*sarama.ConsumerMessage, s *Sinker, db *gorm.DB) error {
	if len(msgs) == 0 {
		return nil
	}
	sqlBuilder := sq.Replace(*s.RuntimeConfig.Dsn.Table).Columns("bk_biz_id",
		"cluster_id",
		"cluster_domain",
		"db_role",
		"host",
		"port",
		"filename",
		"filesize",
		"file_mtime",
		"start_time",
		"stop_time",
		"backup_status",
		"backup_status_info",
		"task_id",
		"file_retention_tag",
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
			var kafkaObj mysql_binlog_result.BinlogFileModel
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

			var modelObj = &mysql_binlog_result.BinlogFileModel{}
			if err = copier.Copy(modelObj, kafkaObj); err != nil {
				return err
			}

			slog.Debug("unmarshal task obj", slog.Any("obj", kafkaObj))
			sqlBuilder = sqlBuilder.Values(
				modelObj.BkBizId,
				modelObj.ClusterId,
				modelObj.ClusterDomain,
				modelObj.DBRole,
				modelObj.Host,
				modelObj.Port,
				modelObj.Filename,
				modelObj.Filesize,
				modelObj.FileMtime,
				modelObj.StartTime,
				modelObj.StopTime,
				modelObj.BackupStatus,
				modelObj.BackupStatusInfo,
				modelObj.TaskId,
				modelObj.FileRetentionTag,
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
