package atommongodb

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/exporterclean"
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
)

// cleanResidualExporter delete residual exporter related files and directories
// 删除残留的exporter相关文件和目录
// 1. 杀死exporter进程
// 2. 删除exporter目录
// 3. 删除prometheus子配置
// 4. 清理proc文件
// 5. 重新加载bkmonitorbeat
// 6. 返回结果

const (
	defaultBkTeBaseDir  = "/usr/local/gse2_bkte"
	defaultExporterName = "dbm_mongodb_exporter"
)

type cleanResidualExporterParams struct {
	BaseDir      string `json:"base_dir"`
	ExporterName string `json:"exporter_name"`
	DryRun       bool   `json:"dry_run"`
}

type cleanResidualExporterJob struct {
	BaseJob
	params *cleanResidualExporterParams
}

func NewCleanResidualExporterJob() jobruntime.JobRunner {
	return &cleanResidualExporterJob{}
}

func (j *cleanResidualExporterJob) Name() string {
	return "mongodb_clean_residual_exporter"
}

func (j *cleanResidualExporterJob) Param() string {
	o, _ := json.MarshalIndent(cleanResidualExporterParams{
		BaseDir:      defaultBkTeBaseDir,
		ExporterName: defaultExporterName,
		DryRun:       false,
	}, "", "\t")
	return string(o)
}

func (j *cleanResidualExporterJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	j.runtime = runtime
	j.params = &cleanResidualExporterParams{
		BaseDir:      defaultBkTeBaseDir,
		ExporterName: defaultExporterName,
		DryRun:       false,
	}
	if strings.TrimSpace(j.runtime.PayloadDecoded) == "" {
		return j.validateAndNormalizeParams()
	}
	if err := json.Unmarshal([]byte(j.runtime.PayloadDecoded), &j.params); err != nil {
		return fmt.Errorf("payload json.Unmarshal failed: %w", err)
	}
	return j.validateAndNormalizeParams()
}

func (j *cleanResidualExporterJob) Run() error {
	var errs []string

	if err := j.cleanLegacyResidualFiles(); err != nil {
		errs = append(errs, err.Error())
	}
	if err := j.killExporterProcesses(); err != nil {
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
		return fmt.Errorf("cleanup residual exporter has errors: %s", strings.Join(errs, " | "))
	}
	j.runtime.Logger.Info("cleanup residual exporter finished successfully")
	return nil
}

// cleanLegacyResidualFiles 删除GCS环境残留的prome_node_exporter进程
func (j *cleanResidualExporterJob) cleanLegacyResidualFiles() error {
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

// validateAndNormalizeParams validates and normalizes the parameters
// 1. trim spaces
// 2. check if base_dir and exporter_name are required
// 3. check if base_dir is a valid directory
// 4. check if exporter_name is a valid exporter name
// 5. resolve base_dir to an absolute path
// 6. return the normalized parameters
//
// base_dir must be provided by the caller (payload); empty or whitespace-only is rejected—no silent default.
func (j *cleanResidualExporterJob) validateAndNormalizeParams() error {
	j.params.ExporterName = strings.TrimSpace(j.params.ExporterName)
	if j.params.ExporterName == "" {
		return fmt.Errorf("exporter_name is required")
	}
	// ExporterName must be a valid exporter name like dbm_xxx_exporter
	if !strings.HasPrefix(j.params.ExporterName, "dbm_") || !strings.HasSuffix(j.params.ExporterName, "_exporter") {
		return fmt.Errorf("exporter_name must be a valid exporter name like dbm_xxx_exporter")
	}
	j.params.BaseDir = strings.TrimSpace(j.params.BaseDir)
	if j.params.BaseDir == "" {
		return fmt.Errorf("base_dir is required")
	}
	absBaseDir, err := exporterclean.NormalizeBaseDir(j.params.BaseDir)
	if err != nil {
		return err
	}
	j.params.BaseDir = absBaseDir
	return nil
}

func (j *cleanResidualExporterJob) killExporterProcesses() error {
	exporterName := strings.TrimSpace(j.params.ExporterName)
	if exporterName == "" {
		return fmt.Errorf("exporter_name is required")
	}
	if j.params.DryRun {
		j.runtime.Logger.Info("[dry_run] will killall -9 %s", exporterName)
		return nil
	}
	ret, err := mycmd.New("killall", "-9", exporterName).Run(10 * time.Second)
	if err != nil {
		errText := strings.ToLower(strings.TrimSpace(ret.GetStderr() + " " + ret.GetStdout() + " " + err.Error()))
		if strings.Contains(errText, "no process found") {
			return nil
		}
		return fmt.Errorf("run killall -9 %s failed, stderr=%s, stdout=%s, err=%w",
			exporterName, ret.GetStderr(), ret.GetStdout(), err)
	}
	j.runtime.Logger.Info("killed process by command: killall -9 %s", exporterName)
	return nil
}

func (j *cleanResidualExporterJob) removeExporterDirectories() error {
	dirs, err := exporterclean.RemoveExporterDirectories(j.params.BaseDir, []string{j.params.ExporterName}, j.params.DryRun)
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

func (j *cleanResidualExporterJob) removePrometheusSubConfigs() (bool, error) {
	files, err := exporterclean.RemovePrometheusSubConfigs(j.params.BaseDir, []string{j.params.ExporterName}, j.params.DryRun)
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

func (j *cleanResidualExporterJob) cleanProcFile() error {
	changed, removed, restarted, err := exporterclean.CleanStaleProcFileAndRestart(
		j.params.BaseDir, []string{j.params.ExporterName}, j.params.DryRun, nil,
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

// keep for unit tests compatibility; implementation moved to common package
func removeExporterFromProcJSON(content []byte, exporterName string) ([]byte, bool, error) {
	return exporterclean.RemoveExporterFromProcJSON(content, []string{exporterName})
}

func (j *cleanResidualExporterJob) reloadBkmonitorbeat() error {
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
	cmd := fmt.Sprintf("bash %s", reloadScript)
	output, err := util.RunBashCmd(cmd, "", nil, 60*time.Second)
	if err != nil {
		return fmt.Errorf("run reload script failed, output=%s, err=%w", output, err)
	}
	j.runtime.Logger.Info("run reload script success: %s", reloadScript)
	return nil
}
