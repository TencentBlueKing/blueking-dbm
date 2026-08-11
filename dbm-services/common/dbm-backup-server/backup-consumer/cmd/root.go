package cmd

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"sync"

	"dbm-services/common/dbm-backup-server/backup-consumer/pkg/config"
	"dbm-services/common/dbm-backup-server/backup-consumer/pkg/consumer"
	"dbm-services/common/dbm-backup-server/backup-consumer/pkg/handler"

	"github.com/Shopify/sarama"
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
		initLogger(config.RuntimeConfig.Log)

		r := gin.Default()
		r.Handle("GET", "/ping", func(context *gin.Context) {
			context.String(http.StatusOK, "pong")
		})

		go func() {
			_ = r.Run("127.0.0.1:80")
		}()
		if bkDataId, err := getBkDataId(); err != nil {
			return err
		} else {
			config.RuntimeConfig.BkDataId = bkDataId
		}

		pool, err := consumer.NewConsumerGroupPool()
		if err != nil {
			return err
		}

		wg := &sync.WaitGroup{}
		for _, group := range pool {
			wg.Add(1)
			go func(group sarama.ConsumerGroup) {
				consumerHandler, err := handler.NewHandler()
				if err != nil {
					slog.Error("new handler", err)
					panic(err)
				}

				for {
					ctx := context.Background()

					err := group.Consume(
						ctx,
						[]string{config.MetaInfo.StorageConfig.Topic},
						consumerHandler,
					)
					if err != nil {
						slog.Error("consume message", err)
						// wg.Done()
						panic(err)
					}
					if cerr := ctx.Err(); cerr != nil {
						slog.Error("consume context", cerr)
						// wg.Done()
						panic(cerr)
					}
					consumerHandler.Ready = make(chan bool)
				}
				// wg.Done()
			}(group)
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

func getBkDataId() (int, error) {
	if config.RuntimeConfig.BkDataId > 0 {
		return config.RuntimeConfig.BkDataId, nil
	} else if config.RuntimeConfig.BkCollectorName != "" {
		collectorsMap, err := consumer.ListBkDataId(&config.RuntimeConfig.BkmApiInfo)
		if err != nil {
			slog.Warn("list bk_data_id from collectors failed", slog.Any("err", err))
		}
		collectorCfg, ok := collectorsMap[config.RuntimeConfig.BkCollectorName]
		if !ok {
			slog.Error("collector not found in list",
				slog.String("bk_collector_name", config.RuntimeConfig.BkCollectorName))
			return 0, fmt.Errorf("collector not found in list: %s", config.RuntimeConfig.BkCollectorName)
		}
		config.RuntimeConfig.BkDataId = collectorCfg.BkDataId
		return config.RuntimeConfig.BkDataId, nil
	}
	return 0, fmt.Errorf("bk_data_id or bk_collector_name is required")
}
