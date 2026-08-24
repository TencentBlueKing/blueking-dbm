package base

import (
	"testing"
	"time"
)

func TestTopicMetrics(t *testing.T) {
	// 获取指标收集器
	metrics := GetTopicMetrics()
	if metrics == nil {
		t.Fatal("GetTopicMetrics returned nil")
	}

	// 测试记录消费尝试
	topic := "test_topic"
	modelTable := "test_table"
	writer := "mysql"
	groupID := "test_group"

	// 记录一次消费尝试
	metrics.RecordMessageTotal(topic, modelTable, writer, groupID, 10)

	// 记录消息成功
	metrics.RecordMessageSuccess(topic, modelTable, writer, groupID, 10)

	// 记录消息失败
	metrics.RecordMessageFailed(topic, modelTable, writer, groupID, "handle_failed", 2)

	// 记录 event 成功
	metrics.RecordEventSuccess(topic, modelTable, writer, groupID, 8)

	// 记录 event 失败
	metrics.RecordEventFailed(topic, modelTable, writer, groupID, "unmarshal", 2)

	// 记录致命错误
	metrics.RecordFatalError(topic, modelTable, writer, groupID, "setup_error")

	// 验证指标不为 nil
	if metrics.MessageTotal == nil {
		t.Error("MessageTotal is nil")
	}
	if metrics.MessageSuccess == nil {
		t.Error("MessageSuccess is nil")
	}
	if metrics.MessageFailed == nil {
		t.Error("MessageFailed is nil")
	}
	if metrics.EventTotal == nil {
		t.Error("EventTotal is nil")
	}
	if metrics.EventSuccess == nil {
		t.Error("EventSuccess is nil")
	}
	if metrics.EventFailed == nil {
		t.Error("EventFailed is nil")
	}
	if metrics.FatalErrors == nil {
		t.Error("FatalErrors is nil")
	}
}

func TestBKReportConfig(t *testing.T) {
	config := &BKReportConfig{
		ReportUrl: "http://test.com:10205/v2/push/",
	}
	config.Token = "test-token"
	config.DataID = 12345

	if config.ReportUrl == "" {
		t.Error("Proxy should not be empty")
	}
	if config.Token == "" {
		t.Error("Metric token should not be empty")
	}
	if config.DataID == 0 {
		t.Error("Metric DataID should not be 0")
	}
}

func TestMetricsReporter(t *testing.T) {
	config := &BKReportConfig{
		ReportUrl: "http://test.com:10205/v2/push/",
	}
	config.Token = "test-token"
	config.DataID = 12345

	reporter := NewMetricsReporter(config)
	if reporter == nil {
		t.Fatal("NewMetricsReporter returned nil")
	}

	if reporter.config == nil {
		t.Error("Reporter config is nil")
	}
	if reporter.httpClient == nil {
		t.Error("Reporter httpClient is nil")
	}
}

func TestGetTopicMetricsSingleton(t *testing.T) {
	// 测试单例模式
	metrics1 := GetTopicMetrics()
	metrics2 := GetTopicMetrics()

	if metrics1 != metrics2 {
		t.Error("GetTopicMetrics should return the same instance")
	}
}

func TestRecordMultipleMetrics(t *testing.T) {
	metrics := GetTopicMetrics()

	// 记录多个不同 topic 的指标
	topics := []string{"topic1", "topic2", "topic3"}
	for _, topic := range topics {
		metrics.RecordMessageTotal(topic, "table", "writer", "group", 5)
		metrics.RecordMessageSuccess(topic, "table", "writer", "group", 5)
		metrics.RecordEventSuccess(topic, "table", "writer", "group", 5)
	}

	// 验证不会 panic
	time.Sleep(100 * time.Millisecond)
}

func TestRecordFatalError(t *testing.T) {
	metrics := GetTopicMetrics()

	// 测试记录不同类型的致命错误
	errorTypes := []string{"setup_error", "migration_error", "connection_error"}
	for _, errorType := range errorTypes {
		metrics.RecordFatalError("test_topic", "test_table", "mysql", "test_group", errorType)
	}

	// 验证不会 panic
	if metrics.FatalErrors == nil {
		t.Error("FatalErrors should not be nil")
	}
}
