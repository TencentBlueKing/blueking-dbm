package config

import (
	"fmt"
	"log/slog"
	"os"

	"gopkg.in/yaml.v3"
)

// loadAndCleanJobsConfig 从磁盘读取配置并清理 nil 项
func loadAndCleanJobsConfig() error {
	content, err := os.ReadFile(RuntimeConfig.JobsConfigFile)
	if err != nil {
		slog.Error("read config from disk", slog.String("error", err.Error()))
		return err
	}

	err = yaml.Unmarshal(content, &JobsConfig)
	if err != nil {
		slog.Error("unmarshal config", slog.String("error", err.Error()))
		return err
	}

	// 清理 nil 项
	validJobs := make([]*ExternalJob, 0, len(JobsConfig.Jobs))
	for _, j := range JobsConfig.Jobs {
		if j != nil {
			validJobs = append(validJobs, j)
		}
	}
	JobsConfig.Jobs = validJobs

	return nil
}

// saveJobsConfig 将配置序列化并写入磁盘
func saveJobsConfig() error {
	output, err := yaml.Marshal(JobsConfig)
	if err != nil {
		slog.Error("marshal config", slog.String("error", err.Error()))
		return err
	}

	err = os.WriteFile(RuntimeConfig.JobsConfigFile, output, 0644)
	if err != nil {
		slog.Error("write config to disk", slog.String("error", err.Error()))
		return err
	}
	return nil
}

// SyncAddJob TODO
func SyncAddJob(newJob *ExternalJob) error {
	if err := loadAndCleanJobsConfig(); err != nil {
		return err
	}

	JobsConfig.Jobs = append(JobsConfig.Jobs, newJob)

	return saveJobsConfig()
}

// SyncJobEnable TODO
func SyncJobEnable(name string, enable bool) error {
	if err := loadAndCleanJobsConfig(); err != nil {
		return err
	}

	idx := -1
	for i, j := range JobsConfig.Jobs {
		if j.Name == name {
			idx = i
			*j.Enable = enable
		}
	}
	if idx < 0 {
		err := fmt.Errorf(
			"target job %s not found in %s",
			name, RuntimeConfig.JobsConfigFile,
		)
		slog.Error("sync job enable seek target job", slog.String("error", err.Error()))
		return err
	}

	return saveJobsConfig()
}

// SyncDelete TODO
func SyncDelete(name string) error {
	if err := loadAndCleanJobsConfig(); err != nil {
		return err
	}

	idx := -1
	for i, j := range JobsConfig.Jobs {
		if j.Name == name {
			idx = i
		}
	}
	if idx < 0 {
		err := fmt.Errorf(
			"target job %s not found in %s",
			name, RuntimeConfig.JobsConfigFile,
		)
		slog.Error("sync job enable seek target job", err)
		return err
	}

	JobsConfig.Jobs = append(JobsConfig.Jobs[:idx], JobsConfig.Jobs[idx+1:]...)

	return saveJobsConfig()
}
