/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package config

import (
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
)

const (
	defaultRetentionAge             = 14 * 24 * time.Hour
	defaultRetentionInterval        = 6 * time.Hour
	defaultRetentionDrainInterval   = 5 * time.Minute
	defaultRetentionScanWindowRows  = 20000
	defaultRetentionMaxRowsPerRound = 10000
	defaultRetentionBatchSize       = 500
	defaultRetentionBatchSleep      = 200 * time.Millisecond
	defaultRetentionStmtTimeout     = 10 * time.Second
	defaultRetentionSlowDelete      = time.Second
	defaultRetentionRoundBudget     = 60 * time.Second
	defaultRetentionMetaHealth      = 10 * time.Minute
	defaultRetentionStatusHealth    = 5 * time.Minute
	defaultRetentionStallAlertAfter = 24 * time.Hour

	minRetentionAge            = 24 * time.Hour
	minRetentionScanWindowRows = 1000
	maxRetentionScanWindowRows = 100000
	retentionWindowFactor      = 3
)

// RetentionConfig controls the physical cleanup of stale rows in t_dbm_metadata and t_dbha_status.
type RetentionConfig struct {
	Enabled              bool          `yaml:"enabled"              mapstructure:"enabled"`
	MetadataRetention    time.Duration `yaml:"metadataRetention"    mapstructure:"metadataRetention"`
	StatusRetention      time.Duration `yaml:"statusRetention"      mapstructure:"statusRetention"`
	Interval             time.Duration `yaml:"interval"             mapstructure:"interval"`
	DrainInterval        time.Duration `yaml:"drainInterval"        mapstructure:"drainInterval"`
	ScanWindowRows       int           `yaml:"scanWindowRows"       mapstructure:"scanWindowRows"`
	MaxRowsPerRound      int           `yaml:"maxRowsPerRound"      mapstructure:"maxRowsPerRound"`
	BatchSize            int           `yaml:"batchSize"            mapstructure:"batchSize"`
	BatchSleep           time.Duration `yaml:"batchSleep"           mapstructure:"batchSleep"`
	ScanTimeout          time.Duration `yaml:"scanTimeout"          mapstructure:"scanTimeout"`
	HealthCheckTimeout   time.Duration `yaml:"healthCheckTimeout"   mapstructure:"healthCheckTimeout"`
	DeleteTimeout        time.Duration `yaml:"deleteTimeout"        mapstructure:"deleteTimeout"`
	SlowDeleteThreshold  time.Duration `yaml:"slowDeleteThreshold"  mapstructure:"slowDeleteThreshold"`
	RoundTimeBudget      time.Duration `yaml:"roundTimeBudget"      mapstructure:"roundTimeBudget"`
	MetadataHealthWindow time.Duration `yaml:"metadataHealthWindow" mapstructure:"metadataHealthWindow"`
	StatusHealthWindow   time.Duration `yaml:"statusHealthWindow"   mapstructure:"statusHealthWindow"`
	StallAlertAfter      time.Duration `yaml:"stallAlertAfter"      mapstructure:"stallAlertAfter"`
}

// DefaultRetentionConfig returns the built-in retention settings. They apply to every key that the
// analysis config file leaves out, so an upgraded config without a retention block runs with them.
func DefaultRetentionConfig() RetentionConfig {
	return RetentionConfig{
		Enabled:              true,
		MetadataRetention:    defaultRetentionAge,
		StatusRetention:      defaultRetentionAge,
		Interval:             defaultRetentionInterval,
		DrainInterval:        defaultRetentionDrainInterval,
		ScanWindowRows:       defaultRetentionScanWindowRows,
		MaxRowsPerRound:      defaultRetentionMaxRowsPerRound,
		BatchSize:            defaultRetentionBatchSize,
		BatchSleep:           defaultRetentionBatchSleep,
		ScanTimeout:          defaultRetentionStmtTimeout,
		HealthCheckTimeout:   defaultRetentionStmtTimeout,
		DeleteTimeout:        defaultRetentionStmtTimeout,
		SlowDeleteThreshold:  defaultRetentionSlowDelete,
		RoundTimeBudget:      defaultRetentionRoundBudget,
		MetadataHealthWindow: defaultRetentionMetaHealth,
		StatusHealthWindow:   defaultRetentionStatusHealth,
		StallAlertAfter:      defaultRetentionStallAlertAfter,
	}
}

// NormalizeRetention returns wf.Retention with every invalid setting replaced by a safe value.
// Each replacement is logged as a warning; the function never fails, so a bad retention block can
// not stop analysis from starting. The read windows of wf bound the retention ages and the health
// windows, so cleanup never removes rows that detection may still read.
func NormalizeRetention(wf WorkflowConfig) RetentionConfig {
	cfg := wf.Retention
	def := DefaultRetentionConfig()

	metaReadWindow := absDuration(wf.ReadDbMetaOffsetDuration)
	statusReadWindow := absDuration(wf.ReadDbMetricOffsetDuration)

	cfg.MetadataRetention = retentionAtLeast("metadataRetention", cfg.MetadataRetention,
		def.MetadataRetention, maxDuration(minRetentionAge, metaReadWindow))
	cfg.StatusRetention = retentionAtLeast("statusRetention", cfg.StatusRetention,
		def.StatusRetention, maxDuration(minRetentionAge, statusReadWindow))
	cfg.MetadataHealthWindow = retentionAtLeast("metadataHealthWindow", cfg.MetadataHealthWindow,
		def.MetadataHealthWindow, maxDuration(defaultRetentionMetaHealth, retentionWindowFactor*wf.UpdateDbmCacheInterval))
	cfg.StatusHealthWindow = retentionAtLeast("statusHealthWindow", cfg.StatusHealthWindow,
		def.StatusHealthWindow, maxDuration(defaultRetentionStatusHealth, retentionWindowFactor*statusReadWindow))

	cfg.Interval = retentionPositive("interval", cfg.Interval, def.Interval)
	cfg.DrainInterval = retentionPositive("drainInterval", cfg.DrainInterval, def.DrainInterval)
	cfg.HealthCheckTimeout = retentionPositive("healthCheckTimeout", cfg.HealthCheckTimeout,
		def.HealthCheckTimeout)
	cfg.StallAlertAfter = retentionPositive("stallAlertAfter", cfg.StallAlertAfter, def.StallAlertAfter)
	if cfg.BatchSleep < 0 {
		logger.Warn("invalid retention config, field: batchSleep, configured: %s, fallback: %s",
			cfg.BatchSleep, def.BatchSleep)
		cfg.BatchSleep = def.BatchSleep
	}

	normalizeRetentionTimeouts(&cfg, def)
	normalizeRetentionSizes(&cfg, def)

	return cfg
}

// normalizeRetentionTimeouts keeps slowDeleteThreshold below deleteTimeout and scanTimeout below
// roundTimeBudget, resetting the related pair to defaults when either side is invalid.
func normalizeRetentionTimeouts(cfg *RetentionConfig, def RetentionConfig) {
	if cfg.DeleteTimeout <= 0 || cfg.SlowDeleteThreshold <= 0 || cfg.SlowDeleteThreshold >= cfg.DeleteTimeout {
		logger.Warn("invalid retention config, field: slowDeleteThreshold/deleteTimeout, configured: %s/%s, "+
			"fallback: %s/%s", cfg.SlowDeleteThreshold, cfg.DeleteTimeout, def.SlowDeleteThreshold, def.DeleteTimeout)
		cfg.SlowDeleteThreshold = def.SlowDeleteThreshold
		cfg.DeleteTimeout = def.DeleteTimeout
	}

	if cfg.ScanTimeout <= 0 || cfg.RoundTimeBudget <= 0 || cfg.ScanTimeout >= cfg.RoundTimeBudget {
		logger.Warn("invalid retention config, field: scanTimeout/roundTimeBudget, configured: %s/%s, "+
			"fallback: %s/%s", cfg.ScanTimeout, cfg.RoundTimeBudget, def.ScanTimeout, def.RoundTimeBudget)
		cfg.ScanTimeout = def.ScanTimeout
		cfg.RoundTimeBudget = def.RoundTimeBudget
	}
}

// normalizeRetentionSizes enforces batchSize <= maxRowsPerRound <= scanWindowRows and the window
// range, resetting all three to defaults when the combination is invalid.
func normalizeRetentionSizes(cfg *RetentionConfig, def RetentionConfig) {
	valid := cfg.BatchSize > 0 &&
		cfg.BatchSize <= cfg.MaxRowsPerRound &&
		cfg.MaxRowsPerRound <= cfg.ScanWindowRows &&
		cfg.ScanWindowRows >= minRetentionScanWindowRows &&
		cfg.ScanWindowRows <= maxRetentionScanWindowRows
	if valid {
		return
	}

	logger.Warn("invalid retention config, field: batchSize/maxRowsPerRound/scanWindowRows, "+
		"configured: %d/%d/%d, fallback: %d/%d/%d", cfg.BatchSize, cfg.MaxRowsPerRound, cfg.ScanWindowRows,
		def.BatchSize, def.MaxRowsPerRound, def.ScanWindowRows)
	cfg.BatchSize = def.BatchSize
	cfg.MaxRowsPerRound = def.MaxRowsPerRound
	cfg.ScanWindowRows = def.ScanWindowRows
}

// retentionAtLeast returns value when it is not below floor; otherwise it falls back to the default,
// raised to floor when the default itself is too small.
func retentionAtLeast(field string, value, def, floor time.Duration) time.Duration {
	if value >= floor {
		return value
	}

	fallback := maxDuration(def, floor)
	logger.Warn("invalid retention config, field: %s, configured: %s, minimum: %s, fallback: %s",
		field, value, floor, fallback)

	return fallback
}

func retentionPositive(field string, value, def time.Duration) time.Duration {
	if value > 0 {
		return value
	}

	logger.Warn("invalid retention config, field: %s, configured: %s, fallback: %s", field, value, def)

	return def
}

func absDuration(d time.Duration) time.Duration {
	if d < 0 {
		return -d
	}

	return d
}

func maxDuration(a, b time.Duration) time.Duration {
	if a > b {
		return a
	}

	return b
}
