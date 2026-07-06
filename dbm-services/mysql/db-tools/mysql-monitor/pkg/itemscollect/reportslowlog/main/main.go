package main

import (
	"log"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/reportslowlog"
)

func main() {
	config.MonitorConfig = &config.Config{
		Port: 20000,
	}
	r := reportslowlog.NewSlowlogReport(nil)

	slowLogPath := "/Users/xiaogz/Downloads/slow-query-162.log"

	if msg, err := r.ProcessSlowLog(slowLogPath); err != nil {
		log.Fatal(msg, err)
	}
}
