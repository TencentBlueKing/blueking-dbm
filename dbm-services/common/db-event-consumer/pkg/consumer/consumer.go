// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package consumer

import (
	"errors"
	"log/slog"
	"reflect"
	"sync"
	"time"

	"github.com/IBM/sarama"
	json "github.com/goccy/go-json"

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

// recordMessageTotal 记录消费的 kafka message 总数
func (s *AnySinker) recordMessageTotal(topic string, count int) {
	s.metrics.RecordMessageTotal(topic, s.modelTable, s.writer, s.groupID, count)
}

// recordMessageSuccess 记录成功处理的 kafka message 数量
func (s *AnySinker) recordMessageSuccess(topic string, count int) {
	s.metrics.RecordMessageSuccess(topic, s.modelTable, s.writer, s.groupID, count)
}

// recordMessageFailed 记录处理失败的 kafka message 数量
func (s *AnySinker) recordMessageFailed(topic string, count int, errorType string) {
	s.metrics.RecordMessageFailed(topic, s.modelTable, s.writer, s.groupID, errorType, count)
}

// recordEventTotal 记录解包后的 event 总数
func (s *AnySinker) recordEventTotal(topic string, count int) {
	s.metrics.RecordEventTotal(topic, s.modelTable, s.writer, s.groupID, count)
}

// recordEventSuccess 记录成功写入 DB 的 event 数量
func (s *AnySinker) recordEventSuccess(topic string, count int) {
	s.metrics.RecordEventSuccess(topic, s.modelTable, s.writer, s.groupID, count)
}

// recordEventFailed 记录处理失败的 event 数量
func (s *AnySinker) recordEventFailed(topic string, count int, errorType string) {
	s.metrics.RecordEventFailed(topic, s.modelTable, s.writer, s.groupID, errorType, count)
}

// recordFatalError 记录致命错误指标
func (s *AnySinker) recordFatalError(topic string, errorType string) {
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
		s.recordFatalError(topic, "setup_error")
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

	batchSize := 1
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
			// 将 Value 复制一份独立的 []byte，断开与 sarama 内部 FetchResponse 大 buffer 的引用关系。
			// sarama 的 Record.Value/Key/Headers 都是原始 buf 的子切片（零拷贝），
			// 只要任何一个字段还在引用 buf，整个 FetchResponse buffer（最大 1MB）都无法被 GC。
			if message.Value != nil {
				valueCopy := make([]byte, len(message.Value))
				copy(valueCopy, message.Value)
				message.Value = valueCopy
			}
			// Key 和 Headers 同样引用原始 buf，必须断开引用
			message.Key = nil
			message.Headers = nil
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
			// 将 Value 复制一份独立的 []byte，断开与 sarama 内部 fetch response 大 buf 的引用关系。
			// sarama 的 ConsumerMessage.Value/Key/Headers 是对整个 FetchResponse 原始字节的子切片引用，
			// 如果不断开引用，只要有一条消息未处理完，整个 response buf（可能数 MB）都无法被 GC 回收。
			if message.Value != nil {
				valueCopy := make([]byte, len(message.Value))
				copy(valueCopy, message.Value)
				message.Value = valueCopy
			}
			message.Key = nil
			message.Headers = nil
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
	msgCount := len(msgs)

	// 记录 MessageTotal
	s.recordMessageTotal(topic, msgCount)

	var err error
	var eventCount int
	if s.Sinker.RuntimeConfig.BkDataId > 0 {
		eventCount, err = s.HandleMessagesBklogGorm(msgs, sk)
		// bklog 场景的 EventTotal 在 HandleMessagesBklogGorm 内部记录
	} else if !s.strictSchema {
		// 非 bklog 场景：1 message = 1 event
		s.recordEventTotal(topic, msgCount)
		eventCount, err = s.HandleMessagesMapper(msgs, sk)
	} else if s.dsWriter.Type() == "mysql_xorm" {
		s.recordEventTotal(topic, msgCount)
		eventCount, err = s.HandleMessagesXorm(msgs, sk)
	} else {
		s.recordEventTotal(topic, msgCount)
		eventCount, err = s.HandleMessages(msgs, sk)
		if err != nil {
			err = nil
			eventCount = 0
			for _, msg := range msgs {
				if cnt, err2 := s.HandleMessages([]*sarama.ConsumerMessage{msg}, sk); err2 != nil {
					slog.Error("handle message", err2)
					err = errors.Join(err, err2)
				} else {
					eventCount += cnt
				}
			}
		}
	}

	// 记录消费结果
	if err != nil {
		s.recordMessageFailed(topic, msgCount, "handle_failed")
		// failed event metrics is reported in Handler
	} else {
		s.recordMessageSuccess(topic, msgCount)
		s.recordEventSuccess(topic, eventCount)
	}

	return err
}

// HandleMessages for gorm, gorm 主要是 migrate 方便
func (s *AnySinker) HandleMessages(msgs []*sarama.ConsumerMessage, sk *Sinker) (int, error) {
	if len(msgs) == 0 {
		return 0, nil
	}
	var err error

	// 预分配精确容量，用 reflect.Index + Set 替代 reflect.Append 避免 growslice
	sliceType := reflect.SliceOf(s.modelType)
	result := reflect.MakeSlice(sliceType, len(msgs), len(msgs))
	idx := 0

	for _, message := range msgs {
		objValue := reflect.New(s.modelType)
		obj := objValue.Interface()

		err := json.Unmarshal(message.Value, obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			s.recordEventFailed(s.Sinker.RuntimeConfig.Topic, 1, "unmarshal")
			return 0, err
		}
		result.Index(idx).Set(objValue.Elem())
		idx++
	}
	result = result.Slice(0, idx)

	if creator, ok := s.modelObject.(base.CustomCreator); ok {
		err = creator.Create(result.Interface(), s.dsWriter)
	} else {
		err = s.dsWriter.WriteBatch(s.modelObject, result.Interface())
	}
	if err != nil {
		s.recordEventFailed(s.Sinker.RuntimeConfig.Topic, idx, "write")
		return 0, err
	}
	return idx, nil
}

// HandleMessagesXorm xorm 实现写入简单很多
func (s *AnySinker) HandleMessagesXorm(msgs []*sarama.ConsumerMessage, sk *Sinker) (int, error) {
	if len(msgs) == 0 {
		return 0, nil
	}
	var objs []base.ModelSinker
	for _, message := range msgs {
		// slog.Debug("process message", slog.String("Value", string(message.Value)))
		obj := reflect.New(s.modelType).Interface()

		err := json.Unmarshal(message.Value, &obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			s.recordEventFailed(s.Sinker.RuntimeConfig.Topic, 1, "unmarshal")
			return 0, err
		}
		objs = append(objs, obj.(base.ModelSinker))
	}

	if err := s.dsWriter.WriteBatch(s.modelObject, objs); err != nil {
		s.recordEventFailed(s.Sinker.RuntimeConfig.Topic, len(objs), "write")
		return 0, err
	}
	return len(objs), nil
}

// HandleMessagesMapper map 形式，根据 map key拼成 sql 写入。不关心表结构
// 如果表结构上字段不存在，会报错。要结合 AutoMigrate 使用
func (s *AnySinker) HandleMessagesMapper(msgs []*sarama.ConsumerMessage, sk *Sinker) (int, error) {
	if len(msgs) == 0 {
		return 0, nil
	}
	var objs []map[string]interface{}
	for _, message := range msgs {
		// slog.Debug("process message", slog.String("Value", string(message.Value)))
		var obj map[string]interface{}
		// map 形式，无法正确处理时区问题
		err := json.Unmarshal(message.Value, &obj)
		if err != nil {
			slog.Error("unmarshal task object", err, slog.Any("msg", message.Value))
			s.recordEventFailed(s.Sinker.RuntimeConfig.Topic, 1, "unmarshal")
			return 0, err
		}
		objs = append(objs, obj)
	}
	if err := s.dsWriter.WriteBatch(s.modelObject, objs); err != nil {
		s.recordEventFailed(s.Sinker.RuntimeConfig.Topic, len(objs), "write")
		return 0, err
	}
	return len(objs), nil
}

// HandleMessagesBklogGorm bklog 需要解包处理
func (s *AnySinker) HandleMessagesBklogGorm(msgs []*sarama.ConsumerMessage, sk *Sinker) (int, error) {
	if len(msgs) == 0 {
		return 0, nil
	}

	// 第一遍：预解析所有消息，收集 MessageWrapper 和总 items 数量
	type parsedMsg struct {
		msg   base.MessageWrapper
		items []struct {
			Data json.RawMessage `json:"data"`
		}
	}
	parsedMsgs := make([]parsedMsg, 0, len(msgs))
	totalItems := 0
	for _, message := range msgs {
		var msg base.MessageWrapper
		err := json.Unmarshal(message.Value, &msg)
		if err != nil {
			slog.Error("unmarshal message", err)
			s.recordMessageFailed(s.Sinker.RuntimeConfig.Topic, 1, "parse")
			continue
		}
		totalItems += len(msg.Items)
		parsedMsgs = append(parsedMsgs, parsedMsg{msg: msg, items: msg.Items})
	}
	if totalItems == 0 {
		return 0, nil
	}
	// 记录 EventTotal（bklog 解包后的 event 总数）
	s.recordEventTotal(s.Sinker.RuntimeConfig.Topic, totalItems)

	// 预分配精确容量的目标切片，用 reflect.Index + Set 替代 reflect.Append，
	// 避免 reflect.Append 的类型检查开销和 growslice 扩容
	sliceType := reflect.SliceOf(s.modelType)
	result := reflect.MakeSlice(sliceType, totalItems, totalItems)
	idx := 0

	for _, pm := range parsedMsgs {
		for _, item := range pm.items {
			objValue := reflect.New(s.modelType)
			obj := objValue.Interface()
			if bklogItem, ok := obj.(base.BklogUnmarshalItem); ok {
				err := bklogItem.UnmarshalItem(item.Data, pm.msg)
				if err != nil {
					s.recordEventFailed(s.Sinker.RuntimeConfig.Topic, 1, "unmarshal-1")
					continue
				}
				result.Index(idx).Set(objValue.Elem())
				idx++
			} else { // json
				// 用 json.Unmarshal 直接解引号，避免 string(data) + strconv.Unquote + []byte(unquoteData) 三次分配
				var unquoteData string
				if err := json.Unmarshal(item.Data, &unquoteData); err != nil {
					slog.Error("unmarshal item data as string", slog.Any("error", err))
					continue
				}

				if err := json.Unmarshal([]byte(unquoteData), &obj); err != nil {
					s.recordEventFailed(s.Sinker.RuntimeConfig.Topic, 1, "unmarshal-2")
					slog.Error("unmarshal task object", slog.Any("error", err), slog.Any("msg", unquoteData))
					return 0, err
				}
				result.Index(idx).Set(objValue.Elem())
				idx++
			}
		}
	}
	if idx == 0 {
		return 0, nil
	}
	// 截断到实际成功解析的数量
	result = result.Slice(0, idx)

	var err error
	if creator, ok := s.modelObject.(base.CustomCreator); ok {
		err = creator.Create(result.Interface(), s.dsWriter)
	} else {
		err = s.dsWriter.WriteBatch(s.modelObject, result.Interface())
	}
	if err != nil {
		s.recordEventFailed(s.Sinker.RuntimeConfig.Topic, idx, "write")
		return 0, err
	}
	return idx, nil
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

	// 记录 retry_event 维度的指标
	topic := s.Sinker.RuntimeConfig.BkCollectorName
	s.recordMessageTotal(topic, len(payloads))
	if err != nil {
		s.recordMessageFailed(topic, len(payloads), "handle_failed")
	} else {
		s.recordMessageSuccess(topic, len(payloads))
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
			var unquoteData string
			if err := json.Unmarshal(item.Data, &unquoteData); err != nil {
				slog.Error("unmarshal item data as string", slog.Any("error", err))
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
