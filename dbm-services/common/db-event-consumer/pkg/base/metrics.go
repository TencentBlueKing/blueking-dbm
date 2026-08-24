package base

import (
	"bytes"
	"fmt"
	"log/slog"
	"net/http"
	"sync"
	"time"

	json "github.com/goccy/go-json"
	"github.com/prometheus/client_golang/prometheus"
)

// TopicMetrics 每个 topic 的消费指标
// 概念区分：
//   - message: 一条 kafka 消息（ConsumerMessage），即从 kafka broker 拉取的原始消息
//   - event: 一条业务事件（item/obj），一条 message 可能包含多个 event（如 bklog 解包场景）
type TopicMetrics struct {
	// --- Message 维度指标 ---
	// MessageTotal 消费的 kafka message 总数
	MessageTotal *prometheus.CounterVec
	// MessageSuccess 成功处理的 kafka message 数量
	MessageSuccess *prometheus.CounterVec
	// MessageFailed 处理失败的 kafka message 数量
	MessageFailed *prometheus.CounterVec

	// --- Event 维度指标 ---
	// EventTotal 解包后的 event 总数（尝试处理的 items/obj 条数）
	EventTotal *prometheus.CounterVec
	// EventSuccess 成功写入 DB 的 event 数量
	EventSuccess *prometheus.CounterVec
	// EventFailed 处理失败的 event 数量
	EventFailed *prometheus.CounterVec

	// --- 其他指标 ---
	// FatalErrors 致命错误次数（如 Setup 失败）
	FatalErrors *prometheus.CounterVec
}

var (
	topicMetrics *TopicMetrics
	once         sync.Once
)

// BKReportConfig 蓝鲸上报配置
type BKReportConfig struct {
	Token  string `json:"token" yaml:"token"`
	DataID int    `json:"data_id" yaml:"data_id"`
	// ReportUrl report proxy url
	ReportUrl string `json:"report_url" yaml:"report_url"`
}

// GetTopicMetrics 获取全局的 TopicMetrics 实例
func GetTopicMetrics() *TopicMetrics {
	once.Do(func() {
		labels := []string{"topic", "model_table", "writer", "group_id"}
		topicMetrics = &TopicMetrics{
			// Message 维度
			MessageTotal: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_message_total",
					Help: "Total number of kafka messages consumed (raw ConsumerMessage from broker)",
				},
				labels,
			),
			MessageSuccess: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_message_success_total",
					Help: "Total number of kafka messages successfully processed",
				},
				labels,
			),
			MessageFailed: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_message_failed_total",
					Help: "Total number of kafka messages failed to process",
				},
				[]string{"topic", "model_table", "writer", "group_id", "error_type"},
			),
			// Event 维度
			EventTotal: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_event_total",
					Help: "Total number of events (items/objects) unpacked from messages",
				},
				labels,
			),
			EventSuccess: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_event_success_total",
					Help: "Total number of events successfully written to DB",
				},
				labels,
			),
			EventFailed: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_event_failed_total",
					Help: "Total number of events failed to process",
				},
				[]string{"topic", "model_table", "writer", "group_id", "error_type"},
			),
			// 其他
			FatalErrors: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_fatal_errors_total",
					Help: "Total number of fatal errors (e.g., Setup failures)",
				},
				[]string{"topic", "model_table", "writer", "group_id", "error_type"},
			),
		}

		// 注册指标
		prometheus.MustRegister(topicMetrics.MessageTotal)
		prometheus.MustRegister(topicMetrics.MessageSuccess)
		prometheus.MustRegister(topicMetrics.MessageFailed)
		prometheus.MustRegister(topicMetrics.EventTotal)
		prometheus.MustRegister(topicMetrics.EventSuccess)
		prometheus.MustRegister(topicMetrics.EventFailed)
		prometheus.MustRegister(topicMetrics.FatalErrors)
	})
	return topicMetrics
}

// RecordMessageTotal 记录消费的 kafka message 总数
func (tm *TopicMetrics) RecordMessageTotal(topic, modelTable, writer, groupID string, count int) {
	tm.MessageTotal.WithLabelValues(topic, modelTable, writer, groupID).Add(float64(count))
}

// RecordMessageSuccess 记录成功处理的 kafka message 数量
func (tm *TopicMetrics) RecordMessageSuccess(topic, modelTable, writer, groupID string, count int) {
	tm.MessageSuccess.WithLabelValues(topic, modelTable, writer, groupID).Add(float64(count))
}

// RecordMessageFailed 记录处理失败的 kafka message 数量
func (tm *TopicMetrics) RecordMessageFailed(topic, modelTable, writer, groupID, errorType string, count int) {
	tm.MessageFailed.WithLabelValues(topic, modelTable, writer, groupID, errorType).Add(float64(count))
}

// RecordEventTotal 记录解包后的 event 总数（尝试处理的 items/obj）
func (tm *TopicMetrics) RecordEventTotal(topic, modelTable, writer, groupID string, count int) {
	tm.EventTotal.WithLabelValues(topic, modelTable, writer, groupID).Add(float64(count))
}

// RecordEventSuccess 记录成功写入 DB 的 event 数量
func (tm *TopicMetrics) RecordEventSuccess(topic, modelTable, writer, groupID string, count int) {
	tm.EventSuccess.WithLabelValues(topic, modelTable, writer, groupID).Add(float64(count))
}

// RecordEventFailed 记录处理失败的 event 数量
func (tm *TopicMetrics) RecordEventFailed(topic, modelTable, writer, groupID, errorType string, count int) {
	tm.EventFailed.WithLabelValues(topic, modelTable, writer, groupID, errorType).Add(float64(count))
}

// RecordFatalError 记录致命错误
func (tm *TopicMetrics) RecordFatalError(topic, modelTable, writer, groupID, errorType string) {
	tm.FatalErrors.WithLabelValues(topic, modelTable, writer, groupID, errorType).Inc()
}

// BKReportData 蓝鲸上报数据格式
type BKReportData struct {
	DataID      int                `json:"data_id"`
	AccessToken string             `json:"access_token"`
	Data        []BKReportDataItem `json:"data"`
}

// BKReportDataItem 上报数据项
type BKReportDataItem struct {
	Metrics   map[string]float64 `json:"metrics"`
	Target    string             `json:"target"`
	Dimension map[string]string  `json:"dimension"`
	// Timestamp 数据时间，精确到毫秒，非必需项
	Timestamp int64 `json:"timestamp"`
}

// MetricsReporter 指标上报器
type MetricsReporter struct {
	config     *BKReportConfig
	httpClient *http.Client
}

// NewMetricsReporter 创建指标上报器
func NewMetricsReporter(config *BKReportConfig) *MetricsReporter {
	return &MetricsReporter{
		config: config,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// StartReporting 启动定时上报
func (mr *MetricsReporter) StartReporting(interval time.Duration) {
	ticker := time.NewTicker(interval)
	go func() {
		for range ticker.C {
			if err := mr.Report(); err != nil {
				slog.Error("failed to report metrics", slog.Any("error", err))
			}
		}
	}()
}

// Report 执行一次上报
func (mr *MetricsReporter) Report() error {
	// 收集指标
	metricFamilies, err := prometheus.DefaultGatherer.Gather()
	if err != nil {
		return fmt.Errorf("gather metrics failed: %w", err)
	}

	var reportItems []BKReportDataItem
	timestamp := time.Now().UnixMilli()

	// 遍历所有指标
	for _, mf := range metricFamilies {
		metricName := mf.GetName()
		// 只上报我们定义的 kafka 消费指标，忽略 golang 内置的指标
		if metricName != "kafka_message_total" &&
			metricName != "kafka_message_success_total" &&
			metricName != "kafka_message_failed_total" &&
			metricName != "kafka_event_total" &&
			metricName != "kafka_event_success_total" &&
			metricName != "kafka_event_failed_total" &&
			metricName != "kafka_fatal_errors_total" {
			continue
		}

		for _, m := range mf.GetMetric() {
			labels := make(map[string]string)
			for _, label := range m.GetLabel() {
				labels[label.GetName()] = label.GetValue()
			}

			var value float64
			if m.Counter != nil {
				value = m.Counter.GetValue()
			}

			dimension := map[string]string{
				"model_table": labels["model_table"],
				"writer":      labels["writer"],
				"group_id":    labels["group_id"],
			}
			// 如果有 error_type 标签，也添加到维度中
			if errorType, ok := labels["error_type"]; ok {
				dimension["error_type"] = errorType
			}

			item := BKReportDataItem{
				Metrics: map[string]float64{
					metricName: value,
				},
				Target:    labels["topic"],
				Dimension: dimension,
				Timestamp: timestamp,
			}
			reportItems = append(reportItems, item)
		}
	}

	if len(reportItems) == 0 {
		slog.Debug("no metrics to report")
		return nil
	}

	// 构造上报数据
	reportData := BKReportData{
		DataID:      mr.config.DataID,
		AccessToken: mr.config.Token,
		Data:        reportItems,
	}

	// 发送 HTTP 请求
	jsonData, err := json.Marshal(reportData)
	if err != nil {
		return fmt.Errorf("marshal report data failed: %w", err)
	}

	resp, err := mr.httpClient.Post(mr.config.ReportUrl, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("post report data failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("report failed with status code: %d", resp.StatusCode)
	}

	slog.Info("metrics reported successfully", slog.Int("items", len(reportItems)))
	return nil
}
