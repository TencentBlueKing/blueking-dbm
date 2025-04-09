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
	"sync"
	"time"

	"dbm-services/common/bkdata-kafka-consumer/pkg/model/mysql_table_size"

	"github.com/Shopify/sarama"
	sb "github.com/huandu/go-sqlbuilder"
	"gorm.io/gorm"
)

type MysqlTableSizeDoris struct {
	Ready  chan bool
	Db     *gorm.DB
	Sinker *Sinker
	mu     sync.Mutex
}

func (c *MysqlTableSizeDoris) Setup(sarama.ConsumerGroupSession) error {
	// Mark the consumer as ready
	//close(c.Ready)
	return nil
}

func (c *MysqlTableSizeDoris) Cleanup(sarama.ConsumerGroupSession) error {
	return nil
}

func (c *MysqlTableSizeDoris) ConsumeClaim2(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	batchSize := 2000
	if c.Sinker.RuntimeConfig.Dsn.BatchInserts > 0 {
		batchSize = c.Sinker.RuntimeConfig.Dsn.BatchInserts
	}
	// prepared statement sql: expected 48016 arguments, got 179088
	msgs := make([]*sarama.ConsumerMessage, 0, batchSize)
	for {
		select {
		case <-time.After(time.Second * 1):
			if len(msgs) > 0 {
				if err := c.HandleMessageTryBatch2(msgs, c.Sinker, c.Db); err != nil {
					slog.Error("handle message batch", err)
				} else {
					for _, msg := range msgs {
						session.MarkMessage(msg, "")
					}
				}
				msgs = msgs[:0]
			}
		case message := <-claim.Messages():
			msgs = append(msgs, message)
			if len(msgs) >= batchSize {
				if err := c.HandleMessageTryBatch2(msgs, c.Sinker, c.Db); err != nil {
					slog.Error("handle message batch", err)
				} else {
					for _, msg := range msgs {
						session.MarkMessage(msg, "")
					}
				}
				msgs = msgs[:0]
			}
		case <-session.Context().Done():
			return nil
		}
	}
}

// HandleMessageTryBatch 先尝试批量写入到 db，如果失败，再尝试单条写入
func (c *MysqlTableSizeDoris) HandleMessageTryBatch2(msgs []*sarama.ConsumerMessage, s *Sinker, db *gorm.DB) error {
	err := c.HandleMessageBatch2(msgs, s, db)
	if err != nil {
		err = nil
		for _, msg := range msgs {
			if err2 := c.HandleMessageBatch2([]*sarama.ConsumerMessage{msg}, s, db); err2 != nil {
				slog.Error("handle message", err2)
				err = errors.Join(err, err2)
			}
		}
		return err
	}
	return nil
}

func (c *MysqlTableSizeDoris) HandleMessageBatch2(msgs []*sarama.ConsumerMessage, s *Sinker, db *gorm.DB) error {
	if len(msgs) == 0 {
		return nil
	}

	builder := sb.NewInsertBuilder()
	builder.InsertInto(*s.RuntimeConfig.Dsn.Table)
	builder.Cols(
		"thedate", "dteventtimestamp", "dteventtimehour",
		"report_time",
		"bk_biz_id",
		"cluster_domain",
		"instance_host",
		"instance_port",
		"original_database_name",
		"database_name",
		"table_name",
		"table_size",
		"database_size",
		"machine_type",
		"instance_role",
		"bk_cloud_id",
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
			var kafkaObj mysql_table_size.MysqlTableSize
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

			kafkaObj.TheDate, _ = strconv.Atoi(kafkaObj.ReportTime.Format("20060102"))
			kafkaObj.DtEventTimeStamp = kafkaObj.ReportTime.UnixMilli()
			kafkaObj.DtEventTimeHour = kafkaObj.ReportTime.Format("2006-01-02 15")
			slog.Debug("unmarshal task obj", slog.Any("obj", kafkaObj))
			builder.Values(
				kafkaObj.TheDate, kafkaObj.DtEventTimeStamp, kafkaObj.DtEventTimeHour,
				kafkaObj.ReportTime,
				kafkaObj.BkBizId,
				kafkaObj.ClusterDomain,
				kafkaObj.InstanceHost,
				kafkaObj.InstancePort,
				kafkaObj.OriginalDatabase,
				kafkaObj.Database,
				kafkaObj.Table,
				kafkaObj.TableSize,
				kafkaObj.DatabaseSize,
				kafkaObj.MachineType,
				kafkaObj.InstanceRole,
				kafkaObj.BkCloudId,
			)
		}
	}

	sqlStr, sqlArgs := builder.Build()
	//sqlFull, err := sb.Doris.Interpolate(sqlStr, sqlArgs)

	sqlFull, err := sb.MySQL.Interpolate(sqlStr, sqlArgs)
	if err != nil {
		return err
	}
	err = db.Exec(sqlFull).Error
	if err != nil {
		slog.Error("replace message",
			slog.Any("msg", err), slog.String("sql", sqlStr), slog.Any("args", sqlArgs))
		//return err
	}
	return nil
}
