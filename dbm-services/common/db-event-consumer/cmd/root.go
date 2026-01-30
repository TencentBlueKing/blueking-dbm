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
	"net/http"
	"os"
	"sync"
	"time"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/config"
	"dbm-services/common/db-event-consumer/pkg/consumer"
	"dbm-services/common/db-event-consumer/pkg/sinker"

	"github.com/gin-gonic/gin"
	"github.com/spf13/cobra"
	"golang.org/x/exp/slog"
)

var rootCmd = &cobra.Command{
	Use:   "kafka-consumer",
	Short: "kafka-consumer",
	Long:  "kafka-consumer",
	RunE: func(cmd *cobra.Command, args []string) error {
		config.InitConfig()
		initLogger(config.MainConfig.Log)
		if err := sinker.InitDatasource(); err != nil {
			return err
		}

		// 初始化指标收集器
		base.GetTopicMetrics()

		// 启动指标上报器（如果配置了）
		if config.MainConfig.BkmReport != nil && config.MainConfig.BkmReport.ReportUrl != "" {
			reporter := base.NewMetricsReporter(config.MainConfig.BkmReport)
			// 每分钟上报一次
			reporter.StartReporting(1 * time.Minute)
			slog.Info("metrics reporter started",
				slog.String("report_url", config.MainConfig.BkmReport.ReportUrl),
				slog.Int("data_id", config.MainConfig.BkmReport.DataID))
		} else {
			slog.Warn("metrics reporter not configured, skipping")
		}

		r := gin.Default()
		r.Handle("GET", "/ping", func(context *gin.Context) {
			context.String(http.StatusOK, "pong")
		})
		go func() {
			_ = r.Run("127.0.0.1:8002")
		}()

		wg := &sync.WaitGroup{}

		for _, sink := range config.SinkerConfigs {
			// 每一个 sinker 都有自己的 writer 实体
			dsWriter, err := sinker.GetDSWriter(sinker.DatasourceMap[sink.Datasource])
			if err != nil {
				return err
			}
			sinker := consumer.Sinker{
				RuntimeConfig: sink,
				DSWriter:      dsWriter,
			}
			if sink.BkDataId > 0 {
				sinker.RuntimeConfig.Topic = ""
				// get kafka from bk api
				if err = consumer.QueryKafkaMetaWithBkDataId(&sinker, config.MainConfig.BkmApiInfo); err != nil {
					slog.Error("get kafka meta", err, slog.Int("bk_data_id", sink.BkDataId))
					continue
				}
				if sinker.RuntimeConfig.Topic == "" {
					slog.Error("topic is empty", slog.String("table", sink.ModelTable))
					continue
				}
				//sinker.MetaInfo is set// = sinker.RuntimeConfig.KafkaMeta
			} else {
				sinker.MetaInfo = config.MainConfig.KafkaInfo
			}

			cg, err := sinker.NewConsumerGroup()
			if err != nil {
				slog.Error("new consumer group", err,
					slog.String("topic", sinker.RuntimeConfig.Topic),
					slog.String("groupId", sinker.RuntimeConfig.Topic+sinker.RuntimeConfig.GroupIdSuffix))
				continue
				//return err
			}
			consumerHandler, err := sinker.NewSinkHandler()
			if err != nil {
				slog.Error("new sink handler", slog.String("error", err.Error()),
					slog.String("topic", sinker.RuntimeConfig.Topic),
					slog.String("groupId", sinker.RuntimeConfig.Topic+sinker.RuntimeConfig.GroupIdSuffix))
				continue
				//panic(err)
			}
			wg.Add(1)
			go func() {
				defer wg.Done()
				for {
					ctx := context.Background()
					err := cg.Consume(
						ctx,
						[]string{sinker.RuntimeConfig.Topic},
						consumerHandler,
					)
					if err != nil {
						slog.Error("consume message", err)
						break
					}
					if err := ctx.Err(); err != nil {
						slog.Error("consume context", err)
						break
					}
					//consumerHandler.Ready = make(chan bool)
				}
				_ = cg.Close()
			}()
		}
		wg.Wait()
		return nil
	},
}

func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		slog.Error("start", err)
		os.Exit(1)
	}
}
