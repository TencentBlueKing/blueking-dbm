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
type TopicMetrics struct {
	// 消费次数
	ConsumeTotal *prometheus.CounterVec
	// 消费成功次数
	ConsumeSuccess *prometheus.CounterVec
	// 消费失败次数
	ConsumeFailed *prometheus.CounterVec
	// 消费消息数量
	ConsumeMessages *prometheus.CounterVec
	// 致命错误次数（如 Setup 失败）
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
		topicMetrics = &TopicMetrics{
			ConsumeTotal: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_consume_total",
					Help: "Total number of kafka consume attempts",
				},
				[]string{"topic", "model_table", "writer", "group_id"},
			),
			ConsumeSuccess: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_consume_success_total",
					Help: "Total number of successful kafka consume",
				},
				[]string{"topic", "model_table", "writer", "group_id"},
			),
			ConsumeFailed: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_consume_failed_total",
					Help: "Total number of failed kafka consume",
				},
				[]string{"topic", "model_table", "writer", "group_id", "error_type"},
			),
			ConsumeMessages: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_consume_messages_total",
					Help: "Total number of kafka messages consumed",
				},
				[]string{"topic", "model_table", "writer", "group_id"},
			),
			FatalErrors: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "kafka_fatal_errors_total",
					Help: "Total number of fatal errors (e.g., Setup failures)",
				},
				[]string{"topic", "model_table", "writer", "group_id", "error_type"},
			),
		}

		// 注册指标
		prometheus.MustRegister(topicMetrics.ConsumeTotal)
		prometheus.MustRegister(topicMetrics.ConsumeSuccess)
		prometheus.MustRegister(topicMetrics.ConsumeFailed)
		prometheus.MustRegister(topicMetrics.ConsumeMessages)
		prometheus.MustRegister(topicMetrics.FatalErrors)
	})
	return topicMetrics
}

// RecordConsumeAttempt 记录消费尝试
func (tm *TopicMetrics) RecordConsumeAttempt(topic, modelTable, writer, groupID string, msgCount int) {
	tm.ConsumeTotal.WithLabelValues(topic, modelTable, writer, groupID).Inc()
	tm.ConsumeMessages.WithLabelValues(topic, modelTable, writer, groupID).Add(float64(msgCount))
}

// RecordConsumeSuccess 记录消费成功
func (tm *TopicMetrics) RecordConsumeSuccess(topic, modelTable, writer, groupID string) {
	tm.ConsumeSuccess.WithLabelValues(topic, modelTable, writer, groupID).Inc()
}

// RecordConsumeFailed 记录消费失败
func (tm *TopicMetrics) RecordConsumeFailed(topic, modelTable, writer, groupID, errorType string) {
	tm.ConsumeFailed.WithLabelValues(topic, modelTable, writer, groupID, errorType).Inc()
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
		if metricName != "kafka_consume_total" &&
			metricName != "kafka_consume_success_total" &&
			metricName != "kafka_consume_failed_total" &&
			metricName != "kafka_consume_messages_total" &&
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
