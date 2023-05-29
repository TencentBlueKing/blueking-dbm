package config

import (
	"fmt"
	"os"

	"golang.org/x/exp/slog"
	"gopkg.in/yaml.v3"
)

// SyncAddJob TODO
func SyncAddJob(newJob *ExternalJob) error {
	content, err := os.ReadFile(RuntimeConfig.JobsConfigFile)
	if err != nil {
		slog.Error("sync add new read config from disk", err)
		return err
	}

	// var jobs []*ExternalJob
	err = yaml.Unmarshal(content, &JobsConfig)
	if err != nil {
		slog.Error("sync add encode config", err)
		return err
	}

	// jobs = append(jobs, newJob)
	JobsConfig.Jobs = append(JobsConfig.Jobs, newJob)

	// output, err := yaml.Marshal(jobs)
	output, err := yaml.Marshal(JobsConfig)
	if err != nil {
		slog.Error("sync add decode updated config", err)
		return err
	}

	err = os.WriteFile(RuntimeConfig.JobsConfigFile, output, 0644)
	if err != nil {
		slog.Error("sync add write to disk", err)
		return err
	}
	return nil
}

// SyncJobEnable TODO
func SyncJobEnable(name string, enable bool) error {
	content, err := os.ReadFile(RuntimeConfig.JobsConfigFile)
	if err != nil {
		slog.Error("sync job enable new read config from disk", err)
		return err
	}

	// var jobs []*ExternalJob
	err = yaml.Unmarshal(content, &JobsConfig)
	if err != nil {
		slog.Error("sync job enable encode config", err)
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
		slog.Error("sync job enable seek target job", err)
		return err
	}

	output, err := yaml.Marshal(JobsConfig)
	if err != nil {
		slog.Error("sync enable decode updated config", err)
		return err
	}

	err = os.WriteFile(RuntimeConfig.JobsConfigFile, output, 0644)
	if err != nil {
		slog.Error("sync enable write to disk", err)
		return err
	}
	return nil
}

// SyncDelete TODO
func SyncDelete(name string) error {
	content, err := os.ReadFile(RuntimeConfig.JobsConfigFile)
	if err != nil {
		slog.Error("sync job enable new read config from disk", err)
		return err
	}

	// var jobs []*ExternalJob
	err = yaml.Unmarshal(content, &JobsConfig)
	if err != nil {
		slog.Error("sync job enable encode config", err)
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

	output, err := yaml.Marshal(JobsConfig)
	if err != nil {
		slog.Error("sync enable decode updated config", err)
		return err
	}

	err = os.WriteFile(RuntimeConfig.JobsConfigFile, output, 0644)
	if err != nil {
		slog.Error("sync enable write to disk", err)
		return err
	}
	return nil
}
