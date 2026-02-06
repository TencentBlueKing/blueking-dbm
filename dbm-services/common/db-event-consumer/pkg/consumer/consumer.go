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
	"strconv"
	"time"

	"github.com/Shopify/sarama"

	"dbm-services/common/db-event-consumer/pkg/base"
)

type AnySinker struct {
	dsWriter    base.DSWriter
	Ready       chan bool
	Sinker      *Sinker
	modelType   reflect.Type
	modelObject interface{}
	modelValue  reflect.Value
	// write mode: insert_ignore,upsert,insert
	writeMode string

	strictSchema bool
}

func (s *AnySinker) Setup(sarama.ConsumerGroupSession) error {
	var err error
	if s.Sinker.RuntimeConfig.SkipMigrateSchema || !s.strictSchema {
		return nil
	}
	if migrator, ok := s.modelObject.(base.CustomMigrator); ok {
		err = migrator.MigrateSchema(s.dsWriter)
	} else {
		err = s.dsWriter.AutoMigrate(s.modelObject)
	}

	// 如果遇到错误，上报 fatal_errors 指标
	if err != nil {
		metrics := base.GetTopicMetrics()
		topic := s.Sinker.RuntimeConfig.Topic
		modelTable := s.Sinker.RuntimeConfig.ModelTable
		writer := s.Sinker.RuntimeConfig.Datasource
		groupID := s.Sinker.RuntimeConfig.Topic + s.Sinker.RuntimeConfig.GroupIdSuffix
		metrics.RecordFatalError(topic, modelTable, writer, groupID, "setup_error")
		slog.Error("setup failed", slog.Any("error", err),
			slog.String("topic", topic),
			slog.String("model_table", modelTable))
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
	// 写入失败分类 TODO
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
			if message == nil {
				// channel 已关闭，应该退出或跳过
				continue
			}
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
func (s *AnySinker) HandleMessageTryBatch(msgs []*sarama.ConsumerMessage, sk *Sinker) error {
	// 获取指标收集器
	metrics := base.GetTopicMetrics()

	// 获取标签信息
	topic := sk.RuntimeConfig.Topic
	modelTable := sk.RuntimeConfig.ModelTable
	writer := sk.RuntimeConfig.Datasource
	groupID := sk.RuntimeConfig.Topic + sk.RuntimeConfig.GroupIdSuffix

	// 记录消费尝试和消息数量
	metrics.RecordConsumeAttempt(topic, modelTable, writer, groupID, len(msgs))

	var err error
	if s.Sinker.RuntimeConfig.BkDataId > 0 {
		err = s.HandleMessagesBklogGorm(msgs, sk)
	} else if !s.strictSchema {
		err = s.HandleMessagesMapper(msgs, sk)
	} else if s.dsWriter.Type() == "mysql_xorm" {
		err = s.HandleMessagesXorm(msgs, sk)
	} else {
		err = s.HandleMessages(msgs, sk)
		if err != nil {
			err = nil
			for _, msg := range msgs {
				if err2 := s.HandleMessages([]*sarama.ConsumerMessage{msg}, sk); err2 != nil {
					slog.Error("handle message", err2)
					err = errors.Join(err, err2)
				}
			}
		}
	}

	// 记录消费结果
	if err != nil {
		metrics.RecordConsumeFailed(topic, modelTable, writer, groupID)
	} else {
		metrics.RecordConsumeSuccess(topic, modelTable, writer, groupID)
	}

	return err
}

// HandleMessages for gorm, gorm 主要是 migrate 方便
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

		err := json.Unmarshal(message.Value, obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			return err
		}
		result = reflect.Append(result, objValue.Elem())
	}
	if creator, ok := s.modelObject.(base.CustomCreator); ok {
		err = creator.Create(result.Interface(), s.dsWriter)
	} else {
		err = s.dsWriter.WriteBatch(s.modelObject, result.Interface())
	}
	return err
}

// HandleMessagesXorm xorm 实现写入简单很多
func (s *AnySinker) HandleMessagesXorm(msgs []*sarama.ConsumerMessage, sk *Sinker) error {
	if len(msgs) == 0 {
		return nil
	}
	var objs []base.ModelSinker
	for _, message := range msgs {
		slog.Debug("process message", slog.String("Value", string(message.Value)))
		obj := reflect.New(s.modelType).Interface()

		err := json.Unmarshal(message.Value, &obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			return err
		}
		objs = append(objs, obj.(base.ModelSinker))
	}

	if err := s.dsWriter.WriteBatch(s.modelObject, objs); err != nil {
		return err
	}
	return nil
}

// HandleMessagesMapper map 形式，根据 map key拼成 sql 写入。不关心表结构
// 如果表结构上字段不存在，会报错。要结合 AutoMigrate 使用
func (s *AnySinker) HandleMessagesMapper(msgs []*sarama.ConsumerMessage, sk *Sinker) error {
	if len(msgs) == 0 {
		return nil
	}
	var objs []map[string]interface{}
	for _, message := range msgs {
		slog.Debug("process message", slog.String("Value", string(message.Value)))
		var obj map[string]interface{}
		// map 形式，无法正确处理时区问题
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

// HandleMessagesBklog bklog 需要解包处理
func (s *AnySinker) HandleMessagesBklog(msgs []*sarama.ConsumerMessage, sk *Sinker) error {
	if len(msgs) == 0 {
		return nil
	}
	var objs []base.ModelSinker
	for _, message := range msgs {
		// slog.Debug("process message", slog.String("Value", string(message.Value)))
		var msg messageWrapper
		err := json.Unmarshal(message.Value, &msg)
		if err != nil {
			slog.Error("unmarshal message", err)
			continue
		}
		for _, item := range msg.Items {
			unquoteData, err := strconv.Unquote(string(item.Data))
			if err != nil {
				slog.Error("unquote message payload", err)
				continue
			}
			obj := reflect.New(s.modelType).Interface()

			err = json.Unmarshal([]byte(unquoteData), &obj)
			if err != nil {
				slog.Error("unmarshal task object", err, slog.Any("msg", unquoteData))
				return err
			}

			objs = append(objs, obj.(base.ModelSinker))
		}
	}
	var err error
	if creator, ok := s.modelObject.(base.CustomCreator); ok {
		err = creator.Create(objs, s.dsWriter)
	} else {
		err = s.dsWriter.WriteBatch(s.modelObject, objs)
	}
	return err
}

// HandleMessagesBklogGorm bklog 需要解包处理
func (s *AnySinker) HandleMessagesBklogGorm(msgs []*sarama.ConsumerMessage, sk *Sinker) error {
	if len(msgs) == 0 {
		return nil
	}
	// 创建目标切片
	sliceType := reflect.SliceOf(s.modelType)
	result := reflect.MakeSlice(sliceType, 0, 0)
	for _, message := range msgs {
		slog.Debug("process message", slog.String("Value", string(message.Value)))
		var msg messageWrapper
		err := json.Unmarshal(message.Value, &msg)
		if err != nil {
			slog.Error("unmarshal message", err)
			continue
		}
		for _, item := range msg.Items {
			unquoteData, err := strconv.Unquote(string(item.Data))
			if err != nil {
				slog.Error("unquote message payload", err)
				continue
			}
			objValue := reflect.New(s.modelType)
			obj := objValue.Interface()

			err = json.Unmarshal([]byte(unquoteData), &obj)
			if err != nil {
				slog.Error("unmarshal task object", err, slog.Any("msg", unquoteData))
				return err
			}

			result = reflect.Append(result, objValue.Elem())
		}
	}
	var err error
	if creator, ok := s.modelObject.(base.CustomCreator); ok {
		err = creator.Create(result.Interface(), s.dsWriter)
	} else {
		err = s.dsWriter.WriteBatch(s.modelObject, result.Interface())
	}
	return err
}

// HandleMessagesBklogMapper bklog 需要解包处理
func (s *AnySinker) HandleMessagesBklogMapper(msgs []*sarama.ConsumerMessage, sk *Sinker) error {
	if len(msgs) == 0 {
		return nil
	}
	var objs []map[string]interface{}
	for _, message := range msgs {
		slog.Debug("process message", slog.String("Value", string(message.Value)))
		var msg messageWrapper
		err := json.Unmarshal(message.Value, &msg)
		if err != nil {
			slog.Error("unmarshal message", err)
			continue
		}
		for _, item := range msg.Items {
			unquoteData, err := strconv.Unquote(string(item.Data))
			if err != nil {
				slog.Error("unquote message payload", err)
				continue
			}
			var obj map[string]interface{}
			// map 形式，无法正确处理时区问题
			err = json.Unmarshal([]byte(unquoteData), &obj)
			if err != nil {
				slog.Error("unmarshal task object", err, slog.Any("msg", unquoteData))
				return err
			}
			objs = append(objs, obj)
		}
	}
	err := s.dsWriter.WriteBatch(s.modelObject, objs)
	return err
}
