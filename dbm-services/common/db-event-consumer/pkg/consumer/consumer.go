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
	"sync"
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

	// metrics 相关
	metrics    *base.TopicMetrics
	modelTable string
	writer     string
	groupID    string
}

// recordMetricsAttempt 记录消费尝试指标
func (s *AnySinker) recordMetricsAttempt(topic string, msgCount int) {
	s.metrics.RecordConsumeAttempt(topic, s.modelTable, s.writer, s.groupID, msgCount)
}

// recordMetricsSuccess 记录消费成功指标
func (s *AnySinker) recordMetricsSuccess(topic string) {
	s.metrics.RecordConsumeSuccess(topic, s.modelTable, s.writer, s.groupID)
}

// recordMetricsFailed 记录消费失败指标
func (s *AnySinker) recordMetricsFailed(topic string, errorType string) {
	s.metrics.RecordConsumeFailed(topic, s.modelTable, s.writer, s.groupID, errorType)
}

// recordMetricsFatalError 记录致命错误指标
func (s *AnySinker) recordMetricsFatalError(topic string, errorType string) {
	s.metrics.RecordFatalError(topic, s.modelTable, s.writer, s.groupID, errorType)
}

// Setup run default migrate or custom migrate
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
		topic := s.Sinker.RuntimeConfig.Topic
		s.recordMetricsFatalError(topic, "setup_error")
		slog.Error("setup failed", slog.Any("error", err),
			slog.String("topic", topic),
			slog.String("model_table", s.modelTable))
	}

	return err
}

func (s *AnySinker) Cleanup(sarama.ConsumerGroupSession) error {
	return nil
}

func (s *AnySinker) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	ingestThreads := s.Sinker.RuntimeConfig.IngestThreads
	slog.Info("consumer claim started",
		slog.String("topic", claim.Topic()),
		slog.Any("partition", claim.Partition()),
		slog.String("groupId", s.groupID),
		slog.String("model", s.Sinker.RuntimeConfig.ModelTable),
		slog.Any("offset", claim.InitialOffset()),
		slog.Int("ingest_threads", ingestThreads),
		slog.Bool("from_beginning", s.Sinker.RuntimeConfig.FromBeginning))

	batchSize := 10
	if s.Sinker.RuntimeConfig.SinkBatchSize > 0 {
		batchSize = s.Sinker.RuntimeConfig.SinkBatchSize
	}
	const FlushInterval = 500 * time.Millisecond

	// 当 ingest_threads > 1 时，启用并发写入模式
	if ingestThreads > 1 {
		return s.consumeClaimConcurrent(session, claim, batchSize, FlushInterval, ingestThreads)
	}

	msgs := make([]*sarama.ConsumerMessage, 0, batchSize)
	ticker := time.NewTicker(FlushInterval)
	defer ticker.Stop()

	// flushBatch 将当前攒的消息批量写入，成功则 MarkMessage 并清空
	flushBatch := func() {
		if len(msgs) == 0 {
			return
		}
		if err := s.HandleMessageTryBatch(msgs, s.Sinker); err != nil {
			slog.Error("handle message batch",
				slog.Any("error", err), slog.String("table", s.Sinker.RuntimeConfig.ModelTable),
				slog.Int("msg_count", len(msgs)))
			// 写入失败 sleep 防止日志刷屏，然后跳过这批消息继续消费
			time.Sleep(200 * time.Millisecond)
		} else {
			session.MarkMessage(msgs[len(msgs)-1], "")
		}
		msgs = msgs[:0]
	}

	for {
		select {
		case message, ok := <-claim.Messages():
			if !ok {
				// channel 已关闭（partition 被撤回或 rebalance），退出消费循环
				slog.Warn("claim.Messages() channel closed, session ending",
					slog.String("topic", claim.Topic()),
					slog.Any("partition", claim.Partition()),
					slog.String("model", s.Sinker.RuntimeConfig.ModelTable))
				flushBatch()
				return nil
			}
			if message == nil {
				continue
			}
			msgs = append(msgs, message)
			if len(msgs) >= batchSize {
				flushBatch()
			}
		case <-ticker.C:
			flushBatch()
		case <-session.Context().Done():
			// 退出前尝试刷新剩余消息
			slog.Warn("session context done, flushing remaining messages",
				slog.String("topic", claim.Topic()),
				slog.Any("partition", claim.Partition()),
				slog.String("model", s.Sinker.RuntimeConfig.ModelTable))
			flushBatch()
			return nil
		}
	}
}

// consumeClaimConcurrent 并发写入模式：启动固定数量的 goroutine 来并发处理消息批次
// 主 goroutine 负责从 kafka 攒批并 MarkMessage（offset 始终向前推进），然后将批次分发给 worker 写入
func (s *AnySinker) consumeClaimConcurrent(
	session sarama.ConsumerGroupSession,
	claim sarama.ConsumerGroupClaim,
	batchSize int,
	flushInterval time.Duration,
	workers int,
) error {
	jobCh := make(chan []*sarama.ConsumerMessage, workers)

	// 启动 worker goroutine
	var wg sync.WaitGroup
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			for msgs := range jobCh {
				if err := s.HandleMessageTryBatch(msgs, s.Sinker); err != nil {
					slog.Error("handle message batch (concurrent)",
						slog.Any("error", err),
						slog.String("table", s.Sinker.RuntimeConfig.ModelTable),
						slog.Int("msg_count", len(msgs)),
						slog.Int("worker_id", workerID))
					time.Sleep(200 * time.Millisecond)
				}
			}
		}(i)
	}

	msgs := make([]*sarama.ConsumerMessage, 0, batchSize)
	ticker := time.NewTicker(flushInterval)
	defer ticker.Stop()

	// dispatchBatch 主线程 MarkMessage 后将批次分发给 worker 写入
	dispatchBatch := func() {
		if len(msgs) == 0 {
			return
		}
		session.MarkMessage(msgs[len(msgs)-1], "")
		batch := make([]*sarama.ConsumerMessage, len(msgs))
		copy(batch, msgs)
		jobCh <- batch
		msgs = msgs[:0]
	}

	defer func() {
		close(jobCh)
		wg.Wait()
	}()

	for {
		select {
		case message, ok := <-claim.Messages():
			if !ok {
				slog.Warn("claim.Messages() channel closed, session ending (concurrent)",
					slog.String("topic", claim.Topic()),
					slog.Any("partition", claim.Partition()),
					slog.String("model", s.Sinker.RuntimeConfig.ModelTable))
				dispatchBatch()
				return nil
			}
			if message == nil {
				continue
			}
			msgs = append(msgs, message)
			if len(msgs) >= batchSize {
				dispatchBatch()
			}
		case <-ticker.C:
			dispatchBatch()
		case <-session.Context().Done():
			slog.Warn("session context done, flushing remaining messages (concurrent)",
				slog.String("topic", claim.Topic()),
				slog.Any("partition", claim.Partition()),
				slog.String("model", s.Sinker.RuntimeConfig.ModelTable))
			dispatchBatch()
			return nil
		}
	}
}

// HandleMessageTryBatch 先尝试批量写入到 db，如果失败，再尝试单条写入
func (s *AnySinker) HandleMessageTryBatch(msgs []*sarama.ConsumerMessage, sk *Sinker) error {
	topic := sk.RuntimeConfig.Topic

	// 记录消费尝试和消息数量
	s.recordMetricsAttempt(topic, len(msgs))

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
		s.recordMetricsFailed(topic, "handle_failed")
	} else {
		s.recordMetricsSuccess(topic)
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
		// slog.Debug("process message", slog.String("Value", string(message.Value)))
		objValue := reflect.New(s.modelType)
		obj := objValue.Interface()

		err := json.Unmarshal(message.Value, obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			s.recordMetricsFailed(s.Sinker.RuntimeConfig.Topic, "unmarshal")
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
		// slog.Debug("process message", slog.String("Value", string(message.Value)))
		obj := reflect.New(s.modelType).Interface()

		err := json.Unmarshal(message.Value, &obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			s.recordMetricsFailed(s.Sinker.RuntimeConfig.Topic, "unmarshal")
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
		// slog.Debug("process message", slog.String("Value", string(message.Value)))
		var obj map[string]interface{}
		// map 形式，无法正确处理时区问题
		err := json.Unmarshal(message.Value, &obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			s.recordMetricsFailed(s.Sinker.RuntimeConfig.Topic, "unmarshal")
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
		var msg base.MessageWrapper
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
		// slog.Debug("process message", slog.String("Value", string(message.Value)))
		var msg base.MessageWrapper
		err := json.Unmarshal(message.Value, &msg)
		if err != nil {
			slog.Error("unmarshal message", err)
			s.recordMetricsFailed(s.Sinker.RuntimeConfig.Topic, "parse")
			continue
		}

		for _, item := range msg.Items {
			objValue := reflect.New(s.modelType)
			obj := objValue.Interface()
			if bklogItem, ok := obj.(base.BklogUnmarshalItem); ok {
				err = bklogItem.UnmarshalItem(item.Data, msg)
				if err != nil {
					// slog.Error("unmarshal bklog item", err, slog.Any("msg", string(item.Data)))
					s.recordMetricsFailed(s.Sinker.RuntimeConfig.Topic, "unmarshal-1")
					continue
				}
				result = reflect.Append(result, objValue.Elem())
			} else { // json
				unquoteData, err := strconv.Unquote(string(item.Data))
				if err != nil {
					slog.Error("unquote message payload", err)
					continue
				}

				err = json.Unmarshal([]byte(unquoteData), &obj)
				if err != nil {
					s.recordMetricsFailed(s.Sinker.RuntimeConfig.Topic, "unmarshal-2")
					slog.Error("unmarshal task object", err, slog.Any("msg", unquoteData))
					return err
				}
				result = reflect.Append(result, objValue.Elem())
			}
		}
	}
	if result.Len() == 0 {
		return nil
	}
	var err error
	if creator, ok := s.modelObject.(base.CustomCreator); ok {
		err = creator.Create(result.Interface(), s.dsWriter)
	} else {
		err = s.dsWriter.WriteBatch(s.modelObject, result.Interface())
	}
	return err
}

// HandleRawMessages 将原始消息体（[][]byte）包装后复用完整的消费入库逻辑
// 供 retry_event 路由时调用，避免重复实现反序列化、write_mode、omit_fields 等边界逻辑
func (s *AnySinker) HandleRawMessages(payloads [][]byte) error {
	if len(payloads) == 0 {
		return nil
	}
	msgs := make([]*sarama.ConsumerMessage, 0, len(payloads))
	for _, p := range payloads {
		msgs = append(msgs, &sarama.ConsumerMessage{Value: p})
	}
	err := s.HandleMessageTryBatch(msgs, s.Sinker)

	// 记录 retry_event 维度的指标（success/failed）
	topic := s.Sinker.RuntimeConfig.BkCollectorName
	s.recordMetricsAttempt(topic, len(payloads))
	if err != nil {
		s.recordMetricsFailed(topic, "handle_failed")
	} else {
		s.recordMetricsSuccess(topic)
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
		// slog.Debug("process message", slog.String("Value", string(message.Value)))
		var msg base.MessageWrapper
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
