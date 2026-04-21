package atomsys

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/exporterclean"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

const (
	defaultRedisBkTeBaseDir = "/usr/local/gse2_bkte"
)

var defaultRedisExporterNames = []string{"dbm_redis_exporter", "dbm_predixy_exporter", "dbm_twemproxy_exporter"}

type redisCleanResidualExporterParams struct {
	BaseDir       string   `json:"base_dir"`
	ExporterName  string   `json:"exporter_name"`
	ExporterNames []string `json:"exporter_names"`
	DryRun        bool     `json:"dry_run"`
}

type redisCleanResidualExporterJob struct {
	runtime *jobruntime.JobGenericRuntime
	params  *redisCleanResidualExporterParams
}

func NewRedisCleanResidualExporter() jobruntime.JobRunner {
	return &redisCleanResidualExporterJob{}
}

func (j *redisCleanResidualExporterJob) Name() string {
	return "redis_clean_residual_exporter"
}

func (j *redisCleanResidualExporterJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	j.runtime = runtime
	j.params = &redisCleanResidualExporterParams{
		BaseDir:       defaultRedisBkTeBaseDir,
		ExporterNames: append([]string{}, defaultRedisExporterNames...),
		DryRun:        false,
	}

	if strings.TrimSpace(j.runtime.PayloadDecoded) == "" {
		return j.validateAndNormalizeParams()
	}
	if err := json.Unmarshal([]byte(j.runtime.PayloadDecoded), j.params); err != nil {
		return fmt.Errorf("payload json.Unmarshal failed: %w", err)
	}
	return j.validateAndNormalizeParams()
}

func (j *redisCleanResidualExporterJob) Run() error {
	var errs []string

	if err := j.cleanLegacyResidualFiles(); err != nil {
		errs = append(errs, err.Error())
	}
	if err := j.killExporterProcess(); err != nil {
		errs = append(errs, err.Error())
	}
	if err := j.removeExporterDirectories(); err != nil {
		errs = append(errs, err.Error())
	}

	prometheusChanged, err := j.removePrometheusSubConfigs()
	if err != nil {
		errs = append(errs, err.Error())
	}
	if err := j.cleanProcFile(); err != nil {
		errs = append(errs, err.Error())
	}
	if prometheusChanged {
		if err := j.reloadBkmonitorbeat(); err != nil {
			errs = append(errs, err.Error())
		}
	}

	if len(errs) > 0 {
		return fmt.Errorf("cleanup residual redis exporter has errors: %s", strings.Join(errs, " | "))
	}
	j.runtime.Logger.Info("cleanup residual redis exporter finished successfully")
	return nil
}

func (j *redisCleanResidualExporterJob) cleanLegacyResidualFiles() error {
	result, err := exporterclean.CleanLegacyResidualFiles(j.params.DryRun)
	j.runtime.Logger.Info(
		"clean_residual_exporter step=legacy_clean dry_run=%t prome_node_exporter_pids=%q drop_caches_rows=%q",
		j.params.DryRun, result.PromeNodeExporterPIDs, result.DropCachesCrontabRows,
	)
	if err != nil {
		return err
	}
	return nil
}

func (j *redisCleanResidualExporterJob) Retry() uint {
	return 2
}

func (j *redisCleanResidualExporterJob) Rollback() error {
	return nil
}

func (j *redisCleanResidualExporterJob) validateAndNormalizeParams() error {
	absBaseDir, err := exporterclean.NormalizeBaseDir(j.params.BaseDir)
	if err != nil {
		return err
	}
	j.params.BaseDir = absBaseDir
	j.params.ExporterNames, err = exporterclean.NormalizeExporterNames(
		j.params.ExporterName, j.params.ExporterNames, defaultRedisExporterNames,
	)
	if err != nil {
		return err
	}
	return nil
}

func (j *redisCleanResidualExporterJob) killExporterProcess() error {
	if j.params.DryRun {
		for _, exporterName := range j.params.ExporterNames {
			j.runtime.Logger.Info("[dry_run] will killall -9 %s", exporterName)
		}
		return nil
	}
	for _, exporterName := range j.params.ExporterNames {
		cmd := fmt.Sprintf("killall -9 %s", exporterName)
		if output, err := util.RunBashCmd(cmd, "", nil, 10*time.Second); err != nil {
			errText := strings.ToLower(strings.TrimSpace(output + " " + err.Error()))
			if strings.Contains(errText, "no process found") {
				continue
			}
			return fmt.Errorf("run %s failed, output=%s, err=%w", cmd, output, err)
		}
		j.runtime.Logger.Info("killed process by command: %s", cmd)
	}
	return nil
}

func (j *redisCleanResidualExporterJob) removeExporterDirectories() error {
	dirs, err := exporterclean.RemoveExporterDirectories(j.params.BaseDir, j.params.ExporterNames, j.params.DryRun)
	if err != nil {
		return err
	}
	for _, dir := range dirs {
		if j.params.DryRun {
			j.runtime.Logger.Info("[dry_run] will remove dir: %s", dir)
			continue
		}
		j.runtime.Logger.Info("removed exporter dir: %s", dir)
	}
	return nil
}

func (j *redisCleanResidualExporterJob) removePrometheusSubConfigs() (bool, error) {
	files, err := exporterclean.RemovePrometheusSubConfigs(j.params.BaseDir, j.params.ExporterNames, j.params.DryRun)
	if err != nil {
		return false, err
	}
	changed := len(files) > 0
	for _, file := range files {
		if j.params.DryRun {
			j.runtime.Logger.Info("[dry_run] will remove prometheus config: %s", file)
			continue
		}
		j.runtime.Logger.Info("removed prometheus config: %s", file)
	}
	return changed, nil
}

func (j *redisCleanResidualExporterJob) cleanProcFile() error {
	changed, removed, restarted, err := exporterclean.CleanStaleProcFileAndRestart(
		j.params.BaseDir, j.params.ExporterNames, j.params.DryRun, nil,
	)
	if err != nil {
		if errors.Is(err, exporterclean.ErrGSEAgentRestartFailed) {
			// Older gse_agent versions may not support "--restart"; treat as non-fatal and continue.
			j.runtime.Logger.Warn("clean_residual_exporter step=proc_clean dry_run=%t restart_result=failed_nonfatal err=%v", j.params.DryRun, err)
			return nil
		}
		return err
	}
	j.runtime.Logger.Info(
		"clean_residual_exporter step=proc_clean dry_run=%t changed=%t restarted=%t removed=%v",
		j.params.DryRun, changed, restarted, removed,
	)
	return nil
}

func (j *redisCleanResidualExporterJob) reloadBkmonitorbeat() error {
	reloadScript := filepath.Join(j.params.BaseDir, "plugins", "bin", "reload.sh")
	if err := exporterclean.EnsurePathUnderBaseDir(j.params.BaseDir, reloadScript); err != nil {
		return err
	}
	if _, err := os.Stat(reloadScript); err != nil {
		if os.IsNotExist(err) {
			j.runtime.Logger.Warn("reload script not found, skip: %s", reloadScript)
			return nil
		}
		return fmt.Errorf("stat reload script %s failed: %w", reloadScript, err)
	}
	if j.params.DryRun {
		j.runtime.Logger.Info("[dry_run] will run reload script: %s", reloadScript)
		return nil
	}
	cmd := fmt.Sprintf("bash %s bkmonitorbeat", reloadScript)
	output, err := util.RunBashCmd(cmd, "", nil, 60*time.Second)
	if err != nil {
		return fmt.Errorf("run reload script failed, output=%s, err=%w", output, err)
	}
	j.runtime.Logger.Info("run reload script success: %s", reloadScript)
	return nil
}
