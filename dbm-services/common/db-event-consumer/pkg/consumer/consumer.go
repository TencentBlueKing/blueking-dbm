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
	"reflect"
	"time"

	"github.com/Shopify/sarama"

	"dbm-services/common/db-event-consumer/pkg/model"
	"dbm-services/common/db-event-consumer/pkg/sinker"
)

type AnySinker struct {
	dsWriter    sinker.DSWriter
	Ready       chan bool
	Sinker      *Sinker
	modelType   reflect.Type
	modelObject interface{}
	modelValue  reflect.Value

	NoManageSchema bool
}

func (s *AnySinker) Setup(sarama.ConsumerGroupSession) error {
	var err error
	if s.Sinker.RuntimeConfig.SkipMigrateSchema {
		return nil
	}
	if migrator, ok := s.modelObject.(model.CustomMigrator); ok {
		err = migrator.MigrateSchema(s.dsWriter)
	} else {
		err = s.dsWriter.AutoMigrate(s.modelObject)
	}
	return err
}

func (s *AnySinker) Cleanup(sarama.ConsumerGroupSession) error {
	return nil
}

func (s *AnySinker) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	if s.Sinker.RuntimeConfig.FromBeginning {
		slog.Info("consumer from beginning",
			slog.Any("topic", claim.Topic()),
			slog.Any("partition", claim.Partition()),
			slog.Any("groupId", s.Sinker.RuntimeConfig.Topic+s.Sinker.RuntimeConfig.GroupIdSuffix))
		session.ResetOffset(claim.Topic(), claim.Partition(), 0, "")
	} else {
		slog.Info("consumer from offset",
			slog.Any("topic", claim.Topic()),
			slog.Any("partition", claim.Partition()),
			slog.Any("groupId", s.Sinker.RuntimeConfig.Topic+s.Sinker.RuntimeConfig.GroupIdSuffix),
			slog.Any("offset", claim.InitialOffset()))
	}
	BatchSize := 10
	msgs := make([]*sarama.ConsumerMessage, 0, BatchSize)
	for {
		select {
		case <-time.After(time.Second * 1):
			if len(msgs) > 0 {
				if err := s.HandleMessageTryBatch(msgs, s.Sinker); err != nil {
					slog.Error("handle message batch",
						slog.Any("error", err), slog.String("model", s.modelType.Name()))
				} else {
					session.MarkMessage(msgs[len(msgs)-1], "")
				}
				msgs = msgs[:0]
			}
		case message := <-claim.Messages():
			msgs = append(msgs, message)
			if len(msgs) >= BatchSize {
				if err := s.HandleMessageTryBatch(msgs, s.Sinker); err != nil {
					slog.Error("handle message batch",
						slog.Any("error", err), slog.String("model", s.modelType.Name()))
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
func (c *AnySinker) HandleMessageTryBatch(msgs []*sarama.ConsumerMessage, s *Sinker) error {
	if c.NoManageSchema {
		return c.HandleMessages3(msgs, s)
	}
	if c.dsWriter.Type() == "mysql_xorm" {
		return c.HandleMessages2(msgs, s)
	}
	err := c.HandleMessages(msgs, s)
	if err != nil {
		err = nil
		for _, msg := range msgs {
			if err2 := c.HandleMessages([]*sarama.ConsumerMessage{msg}, s); err2 != nil {
				slog.Error("handle message", err2)
				err = errors.Join(err, err2)
			}
		}
		return err
	}
	return nil
}

func (s *AnySinker) HandleMessages(msgs []*sarama.ConsumerMessage, sk *Sinker) error {
	if len(msgs) == 0 {
		return nil
	}
	var err error

	// 创建目标切片
	sliceType := reflect.SliceOf(s.modelType)
	result := reflect.MakeSlice(sliceType, 0, 0)

	for _, message := range msgs {
		slog.Debug("process message", slog.String("Value", string(message.Value)))
		objValue := reflect.New(s.modelType)
		obj := objValue.Interface()

		err := json.Unmarshal(message.Value, &obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			return err
		}
		result = reflect.Append(result, objValue.Elem())
	}
	//return nil
	if creator, ok := s.modelObject.(model.CustomCreator); ok {
		err = creator.Create(result.Interface(), s.dsWriter)
	} else {
		err = s.dsWriter.WriteBatch(s.modelObject, result.Interface())
	}
	return err
}

func (s *AnySinker) HandleMessages2(msgs []*sarama.ConsumerMessage, sk *Sinker) error {
	if len(msgs) == 0 {
		return nil
	}
	var objs []sinker.ModelSinker
	for _, message := range msgs {
		slog.Debug("process message", slog.String("Value", string(message.Value)))
		obj := reflect.New(s.modelType).Interface()

		err := json.Unmarshal(message.Value, &obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			return err
		}
		objs = append(objs, obj.(sinker.ModelSinker))
	}

	if err := s.dsWriter.WriteBatch(s.modelObject, objs); err != nil {
		return err
	}
	return nil
}

func (s *AnySinker) HandleMessages3(msgs []*sarama.ConsumerMessage, sk *Sinker) error {
	if len(msgs) == 0 {
		return nil
	}
	var objs []map[string]interface{}
	for _, message := range msgs {
		slog.Debug("process message", slog.String("Value", string(message.Value)))
		var obj map[string]interface{}

		err := json.Unmarshal(message.Value, &obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			return err
		}
		objs = append(objs, obj)
	}
	if err := s.dsWriter.WriteBatch(s.modelObject, objs); err != nil {
		return err
	}
	return nil
}
