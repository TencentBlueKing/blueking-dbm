package atommongodb

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"time"

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
	defaultBkTeBaseDir     = "/usr/local/gse2_bkte"
	defaultExporterName    = "dbm_mongodb_exporter"
	exporterStopWait       = 8 * time.Second
	exporterKillRetryDelay = 200 * time.Millisecond
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

// validateAndNormalizeParams validates and normalizes the parameters
// 1. trim spaces
// 2. check if base_dir and exporter_name are required
// 3. check if base_dir is a valid directory
// 4. check if exporter_name is a valid exporter name
// 5. resolve base_dir to an absolute path
// 6. return the normalized parameters
func (j *cleanResidualExporterJob) validateAndNormalizeParams() error {
	j.params.BaseDir = strings.TrimSpace(j.params.BaseDir)
	j.params.ExporterName = strings.TrimSpace(j.params.ExporterName)
	if j.params.BaseDir == "" {
		return fmt.Errorf("base_dir is required")
	}
	if j.params.ExporterName == "" {
		return fmt.Errorf("exporter_name is required")
	}
	// ExporterName must be a valid exporter name like dbm_xxx_exporter
	if !strings.HasPrefix(j.params.ExporterName, "dbm_") || !strings.HasSuffix(j.params.ExporterName, "_exporter") {
		return fmt.Errorf("exporter_name must be a valid exporter name like dbm_xxx_exporter")
	}
	absBaseDir, err := filepath.Abs(j.params.BaseDir)
	if err != nil {
		return fmt.Errorf("resolve base_dir %s failed: %w", j.params.BaseDir, err)
	}
	if absBaseDir == "/" {
		return fmt.Errorf("invalid base_dir: %s", j.params.BaseDir)
	}
	j.params.BaseDir = absBaseDir
	return nil
}

func (j *cleanResidualExporterJob) killExporterProcesses() error {
	processes, err := util.ListProcess()
	if err != nil {
		return fmt.Errorf("list process failed: %w", err)
	}
	var targetPids []int
	for _, p := range processes {
		cmdlineBytes, err := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", p.Pid))
		if err != nil {
			continue
		}
		cmdline := strings.ReplaceAll(string(cmdlineBytes), "\x00", " ")
		if strings.Contains(cmdline, j.params.ExporterName) {
			targetPids = append(targetPids, p.Pid)
		}
	}
	if len(targetPids) == 0 {
		j.runtime.Logger.Info("no %s process found", j.params.ExporterName)
		return nil
	}

	for _, pid := range targetPids {
		if j.params.DryRun {
			j.runtime.Logger.Info("[dry_run] will terminate pid=%d", pid)
			continue
		}
		if err := syscall.Kill(pid, syscall.SIGTERM); err != nil && err != syscall.ESRCH {
			return fmt.Errorf("kill -15 pid %d failed: %w", pid, err)
		}
		if waitErr := waitProcessExit(pid, exporterStopWait); waitErr == nil {
			j.runtime.Logger.Info("gracefully stopped exporter process pid=%d", pid)
			continue
		}
		if err := syscall.Kill(pid, syscall.SIGKILL); err != nil && err != syscall.ESRCH {
			return fmt.Errorf("kill -9 pid %d failed: %w", pid, err)
		}
		if err := waitProcessExit(pid, 3*time.Second); err != nil {
			return fmt.Errorf("pid %d still exists after kill -9", pid)
		}
		j.runtime.Logger.Info("force killed exporter process pid=%d", pid)
	}
	return nil
}

func (j *cleanResidualExporterJob) removeExporterDirectories() error {
	pattern := filepath.Join(j.params.BaseDir, "external_plugins", "sub_*_service_*", j.params.ExporterName)
	targetDirs, err := filepath.Glob(pattern)
	if err != nil {
		return fmt.Errorf("glob exporter dir failed: %w", err)
	}
	for _, dir := range targetDirs {
		if err := j.ensurePathUnderBaseDir(dir); err != nil {
			return err
		}
		if j.params.DryRun {
			j.runtime.Logger.Info("[dry_run] will remove dir: %s", dir)
			continue
		}
		if err := os.RemoveAll(dir); err != nil {
			return fmt.Errorf("remove exporter dir %s failed: %w", dir, err)
		}
		j.runtime.Logger.Info("removed exporter dir: %s", dir)
	}
	return nil
}

func (j *cleanResidualExporterJob) removePrometheusSubConfigs() (bool, error) {
	pattern := filepath.Join(j.params.BaseDir, "plugins", "etc", "bkmonitorbeat", "bkmonitorbeat_prometheus_sub_*")
	configFiles, err := filepath.Glob(pattern)
	if err != nil {
		return false, fmt.Errorf("glob prometheus config failed: %w", err)
	}
	changed := false
	for _, file := range configFiles {
		if err := j.ensurePathUnderBaseDir(file); err != nil {
			return changed, err
		}
		content, err := os.ReadFile(file)
		if err != nil {
			return changed, fmt.Errorf("read prometheus config %s failed: %w", file, err)
		}
		if !strings.Contains(string(content), j.params.ExporterName) {
			continue
		}
		if j.params.DryRun {
			j.runtime.Logger.Info("[dry_run] will remove prometheus config: %s", file)
			changed = true
			continue
		}
		if err := os.Remove(file); err != nil && !os.IsNotExist(err) {
			return changed, fmt.Errorf("remove prometheus config %s failed: %w", file, err)
		}
		changed = true
		j.runtime.Logger.Info("removed prometheus config: %s", file)
	}
	return changed, nil
}

func (j *cleanResidualExporterJob) cleanProcFile() error {
	procFile := filepath.Join(j.params.BaseDir, "agent", "etc", ".proc")
	if err := j.ensurePathUnderBaseDir(procFile); err != nil {
		return err
	}
	content, err := os.ReadFile(procFile)
	if err != nil {
		if os.IsNotExist(err) {
			j.runtime.Logger.Info("proc file not found, skip: %s", procFile)
			return nil
		}
		return fmt.Errorf("read proc file %s failed: %w", procFile, err)
	}
	newContent, changed, err := removeExporterFromProcJSON(content, j.params.ExporterName)
	if err != nil {
		return fmt.Errorf("parse proc file %s as json failed: %w", procFile, err)
	}
	if !changed {
		return nil
	}
	if j.params.DryRun {
		j.runtime.Logger.Info("[dry_run] will update proc file and remove exporter entries: %s", procFile)
		return nil
	}
	if err := os.WriteFile(procFile, newContent, 0644); err != nil {
		return fmt.Errorf("write proc file %s failed: %w", procFile, err)
	}
	j.runtime.Logger.Info("updated proc file: %s", procFile)
	return nil
}

func removeExporterFromProcJSON(content []byte, exporterName string) ([]byte, bool, error) {
	var root any
	if err := json.Unmarshal(content, &root); err != nil {
		return nil, false, err
	}

	filtered, removed := filterProcJSONValue(root, exporterName)
	if !removed {
		return content, false, nil
	}

	out, err := json.MarshalIndent(filtered, "", "  ")
	if err != nil {
		return nil, false, err
	}
	return out, true, nil
}

// procJSONEntryMatchesExporter 仅当 JSON 对象存在 "procName" 且与 exporterName 完全一致时视为目标进程项。
func procJSONEntryMatchesExporter(m map[string]any, exporterName string) bool {
	pn, ok := m["procName"].(string)
	return ok && pn == exporterName
}

func filterProcJSONValue(v any, exporterName string) (any, bool) {
	switch tv := v.(type) {
	case map[string]any:
		newMap := make(map[string]any, len(tv))
		removed := false
		for k, value := range tv {
			if m, ok := value.(map[string]any); ok && procJSONEntryMatchesExporter(m, exporterName) {
				removed = true
				continue
			}
			filtered, childRemoved := filterProcJSONValue(value, exporterName)
			if childRemoved {
				removed = true
			}
			newMap[k] = filtered
		}
		return newMap, removed
	case []any:
		newSlice := make([]any, 0, len(tv))
		removed := false
		for _, value := range tv {
			if m, ok := value.(map[string]any); ok && procJSONEntryMatchesExporter(m, exporterName) {
				removed = true
				continue
			}
			filtered, childRemoved := filterProcJSONValue(value, exporterName)
			if childRemoved {
				removed = true
			}
			newSlice = append(newSlice, filtered)
		}
		return newSlice, removed
	default:
		return v, false
	}
}

func (j *cleanResidualExporterJob) reloadBkmonitorbeat() error {
	reloadScript := filepath.Join(j.params.BaseDir, "plugins", "bin", "reload.sh")
	if err := j.ensurePathUnderBaseDir(reloadScript); err != nil {
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

// ensurePathUnderBaseDir ensures the target path is under the base directory
func (j *cleanResidualExporterJob) ensurePathUnderBaseDir(target string) error {
	absTarget, err := filepath.Abs(target)
	if err != nil {
		return fmt.Errorf("resolve path %s failed: %w", target, err)
	}
	if absTarget == "/" {
		return fmt.Errorf("refuse to operate on root path")
	}
	base := j.params.BaseDir
	if absTarget != base && !strings.HasPrefix(absTarget, base+string(os.PathSeparator)) {
		return fmt.Errorf("path %s is outside base_dir %s", absTarget, base)
	}
	return nil
}

func waitProcessExit(pid int, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	for {
		if err := syscall.Kill(pid, 0); err != nil {
			if err == syscall.ESRCH {
				return nil
			}
			return err
		}
		if time.Now().After(deadline) {
			return fmt.Errorf("process %d still exists after %s", pid, timeout)
		}
		time.Sleep(exporterKillRetryDelay)
	}
}
