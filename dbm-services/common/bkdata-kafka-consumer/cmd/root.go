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

	"dbm-services/common/bkdata-kafka-consumer/pkg/config"
	"dbm-services/common/bkdata-kafka-consumer/pkg/consumer"

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

		r := gin.Default()
		r.Handle("GET", "/ping", func(context *gin.Context) {
			context.String(http.StatusOK, "pong")
		})

		go func() {
			_ = r.Run("127.0.0.1:8001")
		}()

		wg := &sync.WaitGroup{}
		for _, sink := range config.SinkerConfigs {
			sinker := consumer.Sinker{
				RuntimeConfig: sink,
			}
			cg, err := consumer.NewOneConsumerGroup(&sinker) // set MetaInfo
			if err != nil {
				slog.Error("new consumer group", err,
					slog.String("topic", sinker.MetaInfo.StorageConfig.Topic),
					slog.String("groupId", sinker.RuntimeConfig.GroupId))
				continue
				//return err
			}

			consumerHandler, err := sinker.NewSinkHandler()
			if err != nil {
				slog.Error("new sink handler", err,
					slog.String("topic", sinker.MetaInfo.StorageConfig.Topic),
					slog.String("groupId", sinker.RuntimeConfig.GroupId))
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
						[]string{sinker.MetaInfo.StorageConfig.Topic},
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
