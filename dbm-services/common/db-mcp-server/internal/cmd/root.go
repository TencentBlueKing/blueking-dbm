package cmd

import (
	"os"
	"time"

	"dbm-services/common/db-mcp-server/internal/config"
	"dbm-services/common/db-mcp-server/internal/tools"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/mark3labs/mcp-go/server"
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "db-mcp-server",
	Short: "db-mcp-server",
	RunE: func(cmd *cobra.Command, args []string) error {
		config.InitConfig()

		//backend.InitClient()

		s := server.NewMCPServer(
			"db-mcp-server",
			"1.0.0",
			server.WithLogging(),
		)

		err := tools.LoadTools(s)
		if err != nil {
			logger.Error("init load tools failed: %s", err.Error())
		} else {
			logger.Info("init load tools success")
		}

		errCh := make(chan error)
		go func() {
			ticker := time.NewTicker(5 * time.Second)
			defer func() {
				ticker.Stop()
			}()
			for {
				select {
				case <-ticker.C:
					err := tools.LoadTools(s)
					if err != nil {
						logger.Error("update tools failed: %s", err.Error())
						//errCh <- nil
					} /* else {
						logger.Info("update tools done")
					}*/
				}
			}
		}()

		go func() {
			sseServer := server.NewSSEServer(s)
			err = sseServer.Start(config.Config.BindAddress)
			if err != nil {
				logger.Error("start sse server failed: %s", err.Error())
				errCh <- err
			}
		}()

		err = <-errCh
		logger.Error(err.Error())
		return err
	},
}

func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		logger.Error("root cmd failed: %s", err.Error())
		os.Exit(1)
	}
}
