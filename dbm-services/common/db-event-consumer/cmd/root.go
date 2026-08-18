// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmd

import (
	"context"
	"fmt"
	"net/http"
	"net/http/pprof"
	"os"
	"sync"
	"time"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/config"
	"dbm-services/common/db-event-consumer/pkg/consumer"
	sinkerPkg "dbm-services/common/db-event-consumer/pkg/sinker"

	"github.com/gin-gonic/gin"
	"github.com/spf13/cobra"
	"golang.org/x/exp/slog"
)

var rootCmd = &cobra.Command{
	Use:   "db-event-consumer",
	Short: "db-event-consumer",
	Long:  "db-event-consumer",
	RunE: func(cmd *cobra.Command, args []string) error {
		config.InitConfig()
		initLogger(config.MainConfig.Log)
		if err := sinkerPkg.InitDatasource(); err != nil {
			return err
		}

		base.GetTopicMetrics()
		initMetricsReporter()
		initHTTPServer()

		// 全局获取一次 collectors 列表，供 BkCollectorName 匹配使用
		var collectorsMap map[string]*config.BkDataConfig
		if config.MainConfig.BkmApiInfo != nil && config.MainConfig.BkmApiInfo.BklogApiUrl != "" {
			var err error
			collectorsMap, err = consumer.ListBkDataId(config.MainConfig.BkmApiInfo)
			if err != nil {
				slog.Warn("list bk_data_id from collectors failed", slog.Any("err", err))
			}
		}

		wg := &sync.WaitGroup{}
		for _, sink := range config.SinkerConfigs {
			if sink.Enable != nil && *sink.Enable == false {
				slog.Info("skip sink", slog.String("table", sink.ModelTable))
				continue
			}
			// 创建 DSWriter 是致命错误（配置问题），失败则退出程序
			dsWriter, err := sinkerPkg.GetDSWriter(sinkerPkg.DatasourceMap[sink.Datasource])
			if err != nil {
				return err
			}
			dsWriter.SetWriteMode(sink.WriteMode)
			startSinkerConsumer(sink, dsWriter, collectorsMap, wg)
		}
		wg.Wait()
		return nil
	},
}

// initMetricsReporter 启动指标上报器
func initMetricsReporter() {
	if config.MainConfig.BkmReport != nil && config.MainConfig.BkmReport.ReportUrl != "" {
		reporter := base.NewMetricsReporter(config.MainConfig.BkmReport)
		reporter.StartReporting(1 * time.Minute)
		slog.Info("metrics reporter started",
			slog.String("report_url", config.MainConfig.BkmReport.ReportUrl),
			slog.Int("data_id", config.MainConfig.BkmReport.DataID))
	} else {
		slog.Warn("metrics reporter not configured, skipping")
	}
}

// initHTTPServer 启动 HTTP 服务（健康检查 + pprof）
func initHTTPServer() {
	if config.MainConfig.OtelPort <= 0 {
		return
	}
	r := gin.Default()
	r.Handle("GET", "/ping", func(context *gin.Context) {
		context.String(http.StatusOK, "pong")
	})

	pprofGroup := r.Group("/debug/pprof")
	{
		pprofGroup.GET("/", gin.WrapF(pprof.Index))
		pprofGroup.GET("/cmdline", gin.WrapF(pprof.Cmdline))
		pprofGroup.GET("/profile", gin.WrapF(pprof.Profile))
		pprofGroup.GET("/symbol", gin.WrapF(pprof.Symbol))
		pprofGroup.GET("/trace", gin.WrapF(pprof.Trace))
		pprofGroup.GET("/allocs", gin.WrapH(pprof.Handler("allocs")))
		pprofGroup.GET("/block", gin.WrapH(pprof.Handler("block")))
		pprofGroup.GET("/goroutine", gin.WrapH(pprof.Handler("goroutine")))
		pprofGroup.GET("/heap", gin.WrapH(pprof.Handler("heap")))
		pprofGroup.GET("/mutex", gin.WrapH(pprof.Handler("mutex")))
		pprofGroup.GET("/threadcreate", gin.WrapH(pprof.Handler("threadcreate")))
	}
	go func() {
		_ = r.Run(fmt.Sprintf("127.0.0.1:%d", config.MainConfig.OtelPort))
	}()
}

// startSinkerConsumer 启动单个 sinker 的消费者，内部错误均为非致命（跳过该 sinker）
func startSinkerConsumer(sink *config.SinkerConfig, dsWriter base.DSWriter, collectorsMap map[string]*config.BkDataConfig, wg *sync.WaitGroup) {
	sinker := consumer.Sinker{
		RuntimeConfig: sink,
		DSWriter:      dsWriter,
	}

	// 解析 kafka 连接信息
	if err := resolveKafkaMeta(&sinker, sink, collectorsMap); err != nil {
		return // 非致命错误，跳过该 sinker
	}

	cg, err := sinker.NewConsumerGroup()
	if err != nil {
		slog.Error("new consumer group", err,
			slog.String("topic", sinker.RuntimeConfig.Topic),
			slog.String("groupId", sinker.RuntimeConfig.Topic+sinker.RuntimeConfig.GroupIdSuffix))
		return
	}
	consumerHandler, err := sinker.NewSinkHandler()
	if err != nil {
		slog.Error("new sink handler", slog.String("error", err.Error()),
			slog.String("topic", sinker.RuntimeConfig.Topic),
			slog.String("groupId", sinker.RuntimeConfig.Topic+sinker.RuntimeConfig.GroupIdSuffix))
		return
	}

	// 注册 topic 对应的完整消费处理器，供 retry_event 路由时通过 event_type(=topic) 直接复用
	if handler, ok := consumerHandler.(base.MessageHandler); ok {
		sinkerPkg.ModelDSWriterMap[sink.Topic] = sinkerPkg.ModelSinkEntry{
			Writer:  dsWriter,
			Model:   sinkerPkg.ModelSinkerRegistered[sink.ModelTable], // FakeModel 时为 nil
			Handler: handler,
		}
	}

	wg.Add(1)
	go func() {
		defer wg.Done()
		for {
			ctx := context.Background()
			err := cg.Consume(ctx, []string{sinker.RuntimeConfig.Topic}, consumerHandler)
			if err != nil {
				slog.Error("consume message", err)
				break
			}
			if err := ctx.Err(); err != nil {
				slog.Error("consume context", err)
				break
			}
		}
		_ = cg.Close()
	}()
}

// resolveKafkaMeta 根据配置解析 kafka 连接信息
func resolveKafkaMeta(sinker *consumer.Sinker, sink *config.SinkerConfig, collectorsMap map[string]*config.BkDataConfig) error {
	if sink.BkDataId > 0 {
		sinker.RuntimeConfig.Topic = ""
		if err := consumer.QueryKafkaMetaWithBkDataId(sinker, config.MainConfig.BkmApiInfo); err != nil {
			slog.Error("get kafka meta", err, slog.Int("bk_data_id", sink.BkDataId))
			return err
		}
		if sinker.RuntimeConfig.Topic == "" {
			slog.Error("topic is empty", slog.String("table", sink.ModelTable))
			return fmt.Errorf("topic is empty for table %s", sink.ModelTable)
		}
	} else if sink.BkCollectorName != "" {
		if collectorsMap == nil {
			slog.Error("collectors map is nil, cannot resolve bk_collector_name",
				slog.String("bk_collector_name", sink.BkCollectorName))
			return fmt.Errorf("collectors map is nil")
		}
		collectorCfg, ok := collectorsMap[sink.BkCollectorName]
		if !ok {
			slog.Error("collector not found in list",
				slog.String("bk_collector_name", sink.BkCollectorName))
			return fmt.Errorf("collector not found: %s", sink.BkCollectorName)
		}
		sink.BkDataId = collectorCfg.BkDataId
		slog.Info("resolved bk_data_id from collector",
			slog.String("bk_collector_name", sink.BkCollectorName),
			slog.Int("bk_data_id", sink.BkDataId))
		sinker.RuntimeConfig.Topic = ""
		if err := consumer.QueryKafkaMetaWithBkDataId(sinker, config.MainConfig.BkmApiInfo); err != nil {
			slog.Error("get kafka meta", err, slog.Int("bk_data_id", sink.BkDataId))
			return err
		}
		if sinker.RuntimeConfig.Topic == "" {
			slog.Error("topic is empty", slog.String("table", sink.ModelTable))
			return fmt.Errorf("topic is empty for table %s", sink.ModelTable)
		}
	} else {
		sinker.MetaInfo = config.MainConfig.KafkaInfo
	}
	return nil
}

func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		slog.Error("start", err)
		os.Exit(1)
	}
}
