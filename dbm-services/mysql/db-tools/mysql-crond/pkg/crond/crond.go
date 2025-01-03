// Package crond TODO
package crond

import (
	"dbm-services/mysql/db-tools/mysql-crond/pkg/third_party"
	"log/slog"
	"sync"

	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/schedule"

	"github.com/robfig/cron/v3"
	"github.com/spf13/viper"
)

// DisabledJobs store *config.ExternalJob by name
var DisabledJobs sync.Map

// cronJob all active cronjob entries
var cronJob *cron.Cron

func init() {
	cronJob = cron.New(
		cron.WithParser(
			cron.NewParser(
				cron.SecondOptional |
					cron.Minute |
					cron.Hour |
					cron.Dom |
					cron.Month |
					cron.Dow |
					cron.Descriptor,
			),
		),
	)
}

// Stop TODO
func Stop() {
	cronJob.Stop()
}

// Start TODO
func Start() error {
	for _, j := range config.JobsConfig.Jobs {
		entryID, err := Add(j, false)
		if err != nil {
			slog.Error("load job from config", slog.String("error", err.Error()))
			return err
		}
		slog.Info(
			"load job from config",
			slog.Int("entry id", entryID),
			slog.String("name", j.Name),
		)
	}

	// 专门清理执行过的一次性任务
	entryID, err := cronJob.AddFunc(
		"@every 1s", func() {
			for _, entry := range cronJob.Entries() {
				if s, ok := entry.Schedule.(*schedule.OnceSchedule); ok {
					if s.IsExecuted() {
						cronJob.Remove(entry.ID)
					}
				}
			}
		},
	)
	if err != nil {
		slog.Error("add clearance job", slog.String("error", err.Error()))
		return err
	}
	slog.Info("add clearance job", slog.Int("entry id", int(entryID)))

	// 心跳
	if !viper.GetBool("without-heart-beat") {
		entryID, err = cronJob.AddFunc(
			"@every 1m", func() {
				err := config.SendMetrics(
					"mysql_crond_heart_beat",
					1,
					map[string]interface{}{},
				)
				if err != nil {
					slog.Error("heart beat", slog.String("error", err.Error()))
				} else {
					slog.Info("heart beat success")
				}
			},
		)
		slog.Info("add heart beat job", slog.Int("entry id", int(entryID)))
	}

	// 第三方
	for _, rg := range third_party.ThirdPartyRegisters {
		rg(cronJob)
	}

	cronJob.Start()
	slog.Info("crond start")
	return nil
}

// Reload TODO
func Reload() error {
	cronJob.Stop()
	for _, e := range cronJob.Entries() {
		cronJob.Remove(e.ID)
	}
	DisabledJobs.Range(
		func(key, value any) bool {
			DisabledJobs.Delete(key)
			return true
		},
	)

	err := config.InitJobsConfig()
	if err != nil {
		slog.Error("reload re-init jobs-config", slog.String("error", err.Error()))
		return err
	}
	err = Start()
	if err != nil {
		slog.Error("reload start crond", slog.String("error", err.Error()))
	}
	return err
}
