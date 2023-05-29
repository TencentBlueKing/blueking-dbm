package model

import (
	"github.com/robfig/cron"

	"bk-dbconfig/pkg/core/logger"
)

// AutoRefreshCache TODO
func AutoRefreshCache() error {
	c := cron.New()
	// 第一次直接load，后续每10分钟拉取一次
	if _, err := CacheSetAndGetConfigFileList("", "", ""); err != nil {
		return err
	}
	err := c.AddFunc("@every 1m", func() {
		if _, err := CacheSetAndGetConfigFileList("", "", ""); err != nil {
			logger.Info("AutoRefreshCache SetAndGetConfigFileList failed")
		}
		logger.Info("AutoRefreshCache SetAndGetConfigFileList success")
	})
	if err != nil {
		logger.Info("AutoRefreshCache AddFunc failed %v", err)
	} else {
		logger.Info("AutoRefreshCache Start")
		c.Start()
	}
	return nil
}
