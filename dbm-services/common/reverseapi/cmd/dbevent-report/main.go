package main

import (
	"encoding/json"
	"os"
	"time"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"

	reapisync "dbm-services/common/reverseapi/apis/common"
	recore "dbm-services/common/reverseapi/pkg/core"
)

func main() {
	err := rootCmd.Execute()
	if err != nil {
		_, _ = os.Stderr.WriteString(err.Error() + "\n")
		os.Exit(1)
	}
}

var rootCmd = &cobra.Command{
	Use:   "dbevent-report",
	Short: "dbevent-report go binary",
	Long:  "dbevent-report go binary",
	RunE: func(cmd *cobra.Command, args []string) error {
		var event = &oneEvent{}
		var err error
		event.eventName, _ = cmd.PersistentFlags().GetString("event-name")
		eventBodyRaw, _ := cmd.PersistentFlags().GetString("event-body")

		if err = json.Unmarshal([]byte(eventBodyRaw), &event.eventBody); err != nil {
			return err
		}
		event.clusterType, _ = cmd.PersistentFlags().GetString("cluster-type")
		event.eventBkBizId, _ = cmd.PersistentFlags().GetInt64("bk-biz-id")
		if reportAddrs, _ := cmd.PersistentFlags().GetString("report-addr"); reportAddrs != "" {
			apiCore, err := recore.NewCoreWithAddr(0, []string{reportAddrs})
			if err != nil {
				return err
			}
			ret, err := reapisync.SyncReport(apiCore, event)
			if err != nil {
				return errors.WithMessage(err, string(ret))
			}
		} else {
			apiCore, err := recore.NewCore(0)
			if err != nil {
				return err
			}
			ret, err := reapisync.SyncReport(apiCore, event)
			if err != nil {
				return errors.WithMessage(err, string(ret))
			}
		}
		return nil
	},
}

func init() {
	rootCmd.PersistentFlags().String("event-name", "", "event name, need be registered from server-side")
	rootCmd.PersistentFlags().String("event-body", "", "event body")
	rootCmd.PersistentFlags().String("cluster-type", "", "event cluster-type")
	rootCmd.PersistentFlags().Int64("bk-biz-id", 0, "event bk-biz-id")
	rootCmd.PersistentFlags().String("report-addr", "", "Host:Port or BkCloudId:Host:Port")

	_ = rootCmd.MarkPersistentFlagRequired("event-name")
	_ = rootCmd.MarkPersistentFlagRequired("event-body")
	_ = rootCmd.MarkPersistentFlagRequired("cluster-type")
}

type oneEvent struct {
	eventBkBizId int64
	eventName    string
	clusterType  string
	eventBody    map[string]interface{}
}

func (c *oneEvent) EventCreateTimeStamp() int64 {
	return time.Now().UnixMilli()
}

func (c *oneEvent) ClusterType() string {
	return c.clusterType
}

func (c *oneEvent) EventType() string {
	return c.eventName
}

func (c *oneEvent) EventBkBizId() int64 {
	return c.eventBkBizId
}

func (c *oneEvent) MarshalJSON() ([]byte, error) {
	return json.Marshal(c.eventBody)
}
