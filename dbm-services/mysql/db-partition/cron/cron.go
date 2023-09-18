// Package cron TODO
package cron

import (
	"errors"
	"fmt"
	"log"
	"strings"
	"time"

	"dbm-services/mysql/db-partition/model"

	"github.com/robfig/cron/v3"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

// RegisterCron 注册定时任务
func RegisterCron() ([]*cron.Cron, error) {
	cronList := make([]*cron.Cron, 24)
	timingHour := viper.GetString("cron.timing_hour")
	retryHour := viper.GetString("cron.retry_hour")
	if timingHour == "" || retryHour == "" {
		err := errors.New("cron.partition_hour or cron.retry_hour was not set")
		slog.Error("msg", "cron error", err)
		return cronList, err
	}
	timing := fmt.Sprintf("2 %s * * * ", timingHour)
	retry := fmt.Sprintf("2 %s * * * ", retryHour)
	fmt.Println(retry)
	var debug bool
	if strings.ToLower(strings.TrimSpace(viper.GetString("log.level"))) == "debug" {
		debug = true
	}
	timezone := map[string]int{
		"UTC": 0, "UTC+1": 1, "UTC+2": 2, "UTC+3": 3, "UTC+4": 4, "UTC+5": 5, "UTC+6": 6, "UTC+7": 7, "UTC+8": 8,
		"UTC+9": 9, "UTC+10": 10, "UTC+11": 11, "UTC+12": 12, "UTC-11": -11, "UTC-10": -10, "UTC-9": -9,
		"UTC-8": -8, "UTC-7": -7, "UTC-6": -6, "UTC-5": -5, "UTC-4": -4, "UTC-3": -3, "UTC-2": -2, "UTC-1": -1,
	}
	for name, offset := range timezone {
		offetSeconds := offset * 60 * 60
		zone := time.FixedZone(name, offetSeconds)
		date := time.Now().In(zone).Format("20060102")
		var c *cron.Cron
		if debug {
			c = cron.New(cron.WithLocation(zone), cron.WithLogger(cron.VerbosePrintfLogger(log.New(model.NewWriter(
				"log/cron.log"), fmt.Sprintf("timezone: %+03d:00  ", offset), log.LstdFlags))))
		} else {
			c = cron.New(cron.WithLocation(zone))
		}
		_, err := c.AddJob(timing, PartitionJob{CronType: Daily, ZoneOffset: offset, CronDate: date})
		if err != nil {
			slog.Error("msg", "cron add daily job error", err)
			return cronList, err
		}
		_, err = c.AddJob(retry, PartitionJob{CronType: Retry, ZoneOffset: offset, CronDate: date})
		if err != nil {
			slog.Error("msg", "cron add retry job error", err)
			return cronList, err
		}
		if offset == 0 {
			_, err = c.AddJob("@every 1s", PartitionJob{CronType: Heartbeat, ZoneOffset: offset, CronDate: date})
			if err != nil {
				slog.Error("msg", "cron add heartbeat job error", err)
				return cronList, err
			}
		}
		cronList = append(cronList, c)
		c.Start()
	}
	return cronList, nil
}
