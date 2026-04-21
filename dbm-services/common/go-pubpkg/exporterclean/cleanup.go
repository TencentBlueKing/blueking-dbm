package exporterclean

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
)

type LegacyCleanResult struct {
	PromeNodeExporterPIDs string
	DropCachesCrontabRows string
}

const defaultGSEAgentBin = "/usr/local/gse2_bkte/agent/bin/gse_agent"

var ErrGSEAgentRestartFailed = errors.New("gse agent restart failed")

var packageLogger = log.Printf

func logf(format string, args ...any) {
	packageLogger("[exporterclean] "+format, args...)
}

func NormalizeBaseDir(baseDir string) (string, error) {
	baseDir = strings.TrimSpace(baseDir)
	if baseDir == "" {
		return "", fmt.Errorf("base_dir is required")
	}
	absBaseDir, err := filepath.Abs(baseDir)
	if err != nil {
		return "", fmt.Errorf("resolve base_dir %s failed: %w", baseDir, err)
	}
	if absBaseDir == "/" {
		return "", fmt.Errorf("invalid base_dir: %s", baseDir)
	}
	return absBaseDir, nil
}

// NormalizeExporterNames normalizes exporter names, supports legacy exporter_name fallback and default values.
func NormalizeExporterNames(exporterName string, exporterNames []string, defaults []string) ([]string, error) {
	if len(exporterNames) == 0 {
		if strings.TrimSpace(exporterName) != "" {
			exporterNames = []string{strings.TrimSpace(exporterName)}
		} else {
			exporterNames = append([]string{}, defaults...)
		}
	}

	normalized := make([]string, 0, len(exporterNames))
	seen := make(map[string]struct{}, len(exporterNames))
	for _, name := range exporterNames {
		name = strings.TrimSpace(name)
		if name == "" {
			continue
		}
		if !strings.HasPrefix(name, "dbm_") || !strings.HasSuffix(name, "_exporter") {
			return nil, fmt.Errorf("invalid exporter name: %s", name)
		}
		if _, ok := seen[name]; ok {
			continue
		}
		seen[name] = struct{}{}
		normalized = append(normalized, name)
	}
	if len(normalized) == 0 {
		return nil, fmt.Errorf("exporter_names is required")
	}
	return normalized, nil
}

// EnsurePathUnderBaseDir ensures target is inside baseDir to avoid deleting unexpected paths.
func EnsurePathUnderBaseDir(baseDir, target string) error {
	absTarget, err := filepath.Abs(target)
	if err != nil {
		return fmt.Errorf("resolve path %s failed: %w", target, err)
	}
	if absTarget == "/" {
		return fmt.Errorf("refuse to operate on root path")
	}
	if absTarget != baseDir && !strings.HasPrefix(absTarget, baseDir+string(os.PathSeparator)) {
		return fmt.Errorf("path %s is outside base_dir %s", absTarget, baseDir)
	}
	return nil
}

// ContainsAnyExporterName returns true if content contains any exporter name.
func ContainsAnyExporterName(content string, exporterNames []string) bool {
	for _, name := range exporterNames {
		if strings.Contains(content, name) {
			return true
		}
	}
	return false
}

// RemoveExporterDirectories removes matched exporter plugin directories and returns matched paths.
func RemoveExporterDirectories(baseDir string, exporterNames []string, dryRun bool) ([]string, error) {
	removedOrMatched := make([]string, 0)
	for _, exporterName := range exporterNames {
		pattern := filepath.Join(baseDir, "external_plugins", "sub_*_service_*", exporterName)
		targetDirs, err := filepath.Glob(pattern)
		if err != nil {
			return nil, fmt.Errorf("glob exporter dir failed: %w", err)
		}
		for _, dir := range targetDirs {
			if err := EnsurePathUnderBaseDir(baseDir, dir); err != nil {
				return nil, err
			}
			removedOrMatched = append(removedOrMatched, dir)
			logf("matched exporter directory: %s", dir)
			if dryRun {
				logf("dry-run skip remove exporter directory: %s", dir)
				continue
			}
			if err := os.RemoveAll(dir); err != nil {
				logf("remove exporter directory failed: %s, err=%v", dir, err)
				return nil, fmt.Errorf("remove exporter dir %s failed: %w", dir, err)
			}
			logf("removed exporter directory: %s", dir)
		}
	}
	return removedOrMatched, nil
}

// RemovePrometheusSubConfigs removes prometheus sub-config files that reference exporter names.
func RemovePrometheusSubConfigs(baseDir string, exporterNames []string, dryRun bool) ([]string, error) {
	pattern := filepath.Join(baseDir, "plugins", "etc", "bkmonitorbeat", "bkmonitorbeat_prometheus_sub_*")
	configFiles, err := filepath.Glob(pattern)
	if err != nil {
		return nil, fmt.Errorf("glob prometheus config failed: %w", err)
	}
	removedOrMatched := make([]string, 0)
	for _, file := range configFiles {
		if err := EnsurePathUnderBaseDir(baseDir, file); err != nil {
			return nil, err
		}
		content, err := os.ReadFile(file)
		if err != nil {
			return nil, fmt.Errorf("read prometheus config %s failed: %w", file, err)
		}
		if !ContainsAnyExporterName(string(content), exporterNames) {
			continue
		}
		removedOrMatched = append(removedOrMatched, file)
		logf("matched prometheus sub-config: %s", file)
		if dryRun {
			logf("dry-run skip remove prometheus sub-config: %s", file)
			continue
		}
		if err := os.Remove(file); err != nil && !os.IsNotExist(err) {
			logf("remove prometheus sub-config failed: %s, err=%v", file, err)
			return nil, fmt.Errorf("remove prometheus config %s failed: %w", file, err)
		}
		logf("removed prometheus sub-config: %s", file)
	}
	return removedOrMatched, nil
}

// CleanProcFile removes exporter items from .proc and writes file back when changed.
func CleanProcFile(baseDir string, exporterNames []string, dryRun bool) (changed bool, err error) {
	procFile := filepath.Join(baseDir, "agent", "etc", ".proc")
	if err = EnsurePathUnderBaseDir(baseDir, procFile); err != nil {
		return false, err
	}
	logf("start clean .proc by procName: file=%s dry_run=%t", procFile, dryRun)
	content, err := os.ReadFile(procFile)
	if err != nil {
		if os.IsNotExist(err) {
			logf(".proc not found, skip: %s", procFile)
			return false, nil
		}
		return false, fmt.Errorf("read proc file %s failed: %w", procFile, err)
	}

	newContent, changed, err := RemoveExporterFromProcJSON(content, exporterNames)
	if err != nil {
		return false, fmt.Errorf("parse proc file %s as json failed: %w", procFile, err)
	}
	if !changed || dryRun {
		logf("finish clean .proc by procName: changed=%t dry_run=%t", changed, dryRun)
		return changed, nil
	}

	if err := os.WriteFile(procFile, newContent, 0644); err != nil {
		return false, fmt.Errorf("write proc file %s failed: %w", procFile, err)
	}
	logf("persisted .proc by procName cleanup: %s", procFile)
	return true, nil
}

// CleanStaleProcFile removes stale exporter entries from .proc by setupPath existence check.
// A stale entry is: procName in exporterNames AND setupPath non-empty AND setupPath not exists.
func CleanStaleProcFile(baseDir string, exporterNames []string, dryRun bool) (changed bool, removed []string, err error) {
	procFile := filepath.Join(baseDir, "agent", "etc", ".proc")
	if err = EnsurePathUnderBaseDir(baseDir, procFile); err != nil {
		return false, nil, err
	}
	logf("start clean stale .proc by setupPath: file=%s dry_run=%t", procFile, dryRun)
	content, err := os.ReadFile(procFile)
	if err != nil {
		if os.IsNotExist(err) {
			logf(".proc not found, skip stale cleanup: %s", procFile)
			return false, nil, nil
		}
		return false, nil, fmt.Errorf("read proc file %s failed: %w", procFile, err)
	}

	newContent, changed, removed, err := RemoveStaleExporterFromProcJSON(content, exporterNames)
	if err != nil {
		return false, nil, fmt.Errorf("parse proc file %s as json failed: %w", procFile, err)
	}
	if !changed || dryRun {
		logf("finish stale .proc cleanup: changed=%t removed=%v dry_run=%t", changed, removed, dryRun)
		return changed, removed, nil
	}
	if err := os.WriteFile(procFile, newContent, 0644); err != nil {
		return false, nil, fmt.Errorf("write proc file %s failed: %w", procFile, err)
	}
	logf("persisted stale .proc cleanup: removed=%v file=%s", removed, procFile)
	return true, removed, nil
}

// CleanStaleProcFileAndRestart cleans stale .proc entries and restarts gse_agent when changes are persisted.
func CleanStaleProcFileAndRestart(
	baseDir string,
	exporterNames []string,
	dryRun bool,
	restartFn func() error,
) (changed bool, removed []string, restarted bool, err error) {
	changed, removed, err = CleanStaleProcFile(baseDir, exporterNames, dryRun)
	if err != nil || !changed || dryRun {
		return changed, removed, false, err
	}
	if restartFn == nil {
		restartFn = RestartGSEAgent
	}
	logf("stale .proc changed, restart gse_agent: removed=%v", removed)
	if err := restartFn(); err != nil {
		logf("restart gse_agent failed after stale .proc cleanup: err=%v", err)
		return changed, removed, false, fmt.Errorf("%w: %v", ErrGSEAgentRestartFailed, err)
	}
	logf("restart gse_agent success after stale .proc cleanup")
	return changed, removed, true, nil
}

// RemoveExporterFromProcJSON removes exporter entries from proc JSON bytes.
func RemoveExporterFromProcJSON(content []byte, exporterNames []string) ([]byte, bool, error) {
	var root any
	if err := json.Unmarshal(content, &root); err != nil {
		return nil, false, err
	}

	filtered, removed := filterProcJSONValue(root, exporterNames)
	if !removed {
		return content, false, nil
	}
	out, err := json.MarshalIndent(filtered, "", "  ")
	if err != nil {
		return nil, false, err
	}
	return out, true, nil
}

// RemoveStaleExporterFromProcJSON removes stale exporter entries from ".proc" json payload.
//
// Supported layout (typical GSE .proc): top-level JSON object with key "proc" whose value is a JSON array
// of objects; each object may contain "procName" and "setupPath". If "proc" is not an array (e.g. object or
// different schema), this function skips stale cleanup and returns unchanged content without error, so the
// overall cleanup flow is not blocked by format drift.
func RemoveStaleExporterFromProcJSON(content []byte, exporterNames []string) ([]byte, bool, []string, error) {
	var root map[string]json.RawMessage
	if err := json.Unmarshal(content, &root); err != nil {
		return nil, false, nil, err
	}
	procRaw, ok := root["proc"]
	if !ok {
		return content, false, nil, nil
	}

	var procs []map[string]json.RawMessage
	if err := json.Unmarshal(procRaw, &procs); err != nil {
		logf("skip stale .proc cleanup: proc field is not a JSON array or unsupported schema: %v", err)
		return content, false, nil, nil
	}

	exporterSet := make(map[string]struct{}, len(exporterNames))
	for _, n := range exporterNames {
		exporterSet[n] = struct{}{}
	}
	newProcs := make([]map[string]json.RawMessage, 0, len(procs))
	removed := make([]string, 0)
	for _, p := range procs {
		procName := jsonString(p["procName"])
		setupPath := jsonString(p["setupPath"])
		if _, ok := exporterSet[procName]; !ok {
			newProcs = append(newProcs, p)
			continue
		}
		if strings.TrimSpace(setupPath) == "" {
			// keep conservative behavior: skip if setupPath missing
			newProcs = append(newProcs, p)
			continue
		}
		if _, err := os.Stat(setupPath); os.IsNotExist(err) {
			removed = append(removed, procName)
			continue
		}
		newProcs = append(newProcs, p)
	}

	if len(removed) == 0 {
		return content, false, nil, nil
	}
	updatedProcRaw, err := json.Marshal(newProcs)
	if err != nil {
		return nil, false, nil, err
	}
	root["proc"] = updatedProcRaw
	out, err := json.MarshalIndent(root, "", "  ")
	if err != nil {
		return nil, false, nil, err
	}
	return out, true, removed, nil
}

// RestartGSEAgent triggers gse_agent --restart.
func RestartGSEAgent() error {
	logf("execute command: %s --restart", defaultGSEAgentBin)
	ret, err := runCmd(mycmd.New(defaultGSEAgentBin, "--restart"))
	if err != nil {
		logf("command failed: %s --restart, stderr=%s, err=%v", defaultGSEAgentBin, ret.GetStderr(), err)
		return fmt.Errorf("run gse_agent --restart failed, stderr=%s, err=%w", ret.GetStderr(), err)
	}
	logf("command success: %s --restart", defaultGSEAgentBin)
	return nil
}

// CleanLegacyResidualFiles cleans legacy prome_node_exporter process and drop_caches root crontab rows.
func CleanLegacyResidualFiles(dryRun bool) (LegacyCleanResult, error) {
	var result LegacyCleanResult
	var errs []string

	pids, err := findPromeNodeExporterPIDs()
	if err != nil {
		errs = append(errs, err.Error())
	} else {
		result.PromeNodeExporterPIDs = pids
		logf("legacy prome_node_exporter pid scan result: %q", pids)
		if pids != "" && !dryRun {
			if err := killPromeNodeExporter(pids); err != nil {
				errs = append(errs, err.Error())
			}
		} else if pids != "" && dryRun {
			logf("dry-run skip kill legacy prome_node_exporter pids: %q", pids)
		}
	}

	rows, err := findDropCachesCrontabRows()
	if err != nil {
		errs = append(errs, err.Error())
	} else {
		result.DropCachesCrontabRows = rows
		logf("legacy drop_caches crontab rows result: %q", rows)
		if rows != "" && !dryRun {
			if err := removeDropCachesCrontabRows(); err != nil {
				errs = append(errs, err.Error())
			}
		} else if rows != "" && dryRun {
			logf("dry-run skip remove drop_caches crontab rows")
		}
	}

	if len(errs) > 0 {
		return result, fmt.Errorf("clean legacy residual files failed: %s", strings.Join(errs, " | "))
	}
	return result, nil
}

func findPromeNodeExporterPIDs() (string, error) {
	pidList, err := listProcPIDs()
	if err != nil {
		return "", fmt.Errorf("list proc pids failed: %w", err)
	}
	matched := make([]string, 0)
	for _, pid := range pidList {
		cmdline, err := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", pid))
		if err != nil {
			continue
		}
		cmdlineText := strings.ReplaceAll(string(cmdline), "\x00", " ")
		if strings.Contains(cmdlineText, "prome_node_exporter") {
			matched = append(matched, strconv.Itoa(pid))
		}
	}
	return strings.Join(matched, " "), nil
}

func killPromeNodeExporter(pids string) error {
	safePIDs, err := filterSafePromeNodeExporterPIDs(pids)
	if err != nil {
		return err
	}
	if safePIDs == "" {
		logf("no safe prome_node_exporter pids to kill")
		return nil
	}
	logf("safe prome_node_exporter pids to kill: %q", safePIDs)

	for _, pidStr := range strings.Fields(safePIDs) {
		pid, err := strconv.Atoi(pidStr)
		if err != nil {
			return fmt.Errorf("invalid pid %s: %w", pidStr, err)
		}
		if err := syscall.Kill(pid, syscall.SIGKILL); err != nil && err != syscall.ESRCH {
			logf("kill pid failed: %d err=%v", pid, err)
			return fmt.Errorf("kill legacy prome_node_exporter pid %d failed: %w", pid, err)
		}
		logf("kill pid success(or already exited): %d", pid)
	}
	return nil
}

func filterSafePromeNodeExporterPIDs(pids string) (string, error) {
	pidList := strings.Fields(pids)
	safe := make([]string, 0, len(pidList))

	for _, pid := range pidList {
		// Read /proc/<pid>/exe and only keep exact prome_node_exporter process.
		logf("execute command: readlink -f /proc/%s/exe", pid)
		ret, err := runCmd(mycmd.New("readlink", "-f", fmt.Sprintf("/proc/%s/exe", pid)))
		if err != nil {
			// Process may already exit between pgrep and readlink.
			if ret != nil && ret.ExitCode != 0 {
				logf("skip pid due to readlink non-zero exit: pid=%s exit=%d stderr=%s", pid, ret.ExitCode, ret.GetStderr())
				continue
			}
			return "", fmt.Errorf("check /proc/%s/exe failed, stderr=%s, err=%w", pid, ret.GetStderr(), err)
		}
		exePath := strings.TrimSpace(ret.GetStdout())
		if filepath.Base(exePath) == "prome_node_exporter" {
			safe = append(safe, pid)
		}
	}

	return strings.Join(safe, " "), nil
}

func listProcPIDs() ([]int, error) {
	entries, err := os.ReadDir("/proc")
	if err != nil {
		return nil, err
	}
	pids := make([]int, 0, len(entries))
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		pid, err := strconv.Atoi(entry.Name())
		if err != nil {
			continue
		}
		pids = append(pids, pid)
	}
	return pids, nil
}

func findDropCachesCrontabRows() (string, error) {
	crontabText, err := readRootCrontab()
	if err != nil {
		return "", err
	}
	lines := strings.Split(crontabText, "\n")
	matches := make([]string, 0)
	for idx, line := range lines {
		if strings.Contains(line, "/proc/sys/vm/drop_caches") {
			matches = append(matches, fmt.Sprintf("%d:%s", idx+1, line))
		}
	}
	return strings.TrimSpace(strings.Join(matches, "\n")), nil
}

func removeDropCachesCrontabRows() error {
	crontabText, err := readRootCrontab()
	if err != nil {
		return err
	}
	lines := strings.Split(crontabText, "\n")
	filtered := make([]string, 0, len(lines))
	for _, line := range lines {
		if strings.Contains(line, "/proc/sys/vm/drop_caches") {
			continue
		}
		filtered = append(filtered, line)
	}
	tempFile, err := os.CreateTemp("", "root-crontab-*.tmp")
	if err != nil {
		return fmt.Errorf("create temp crontab file failed: %w", err)
	}
	defer os.Remove(tempFile.Name())
	if _, err := tempFile.WriteString(strings.Join(filtered, "\n")); err != nil {
		tempFile.Close()
		return fmt.Errorf("write temp crontab file failed: %w", err)
	}
	if err := tempFile.Close(); err != nil {
		return fmt.Errorf("close temp crontab file failed: %w", err)
	}
	logf("execute command: crontab -u root %s", tempFile.Name())
	ret, err := runCmd(mycmd.New("crontab", "-u", "root", tempFile.Name()))
	if err != nil {
		logf("command failed: crontab -u root %s stderr=%s err=%v", tempFile.Name(), ret.GetStderr(), err)
		return fmt.Errorf("remove root crontab drop_caches failed, stderr=%s, err=%w", ret.GetStderr(), err)
	}
	logf("command success: crontab -u root %s", tempFile.Name())
	return nil
}

func readRootCrontab() (string, error) {
	ret, err := runCmd(mycmd.New("crontab", "-l", "-u", "root"))
	if err != nil {
		stderr := strings.TrimSpace(ret.GetStderr())
		if strings.Contains(stderr, "no crontab for root") {
			logf("command result: no crontab for root")
			return "", nil
		}
		logf("command failed: crontab -l -u root stderr=%s err=%v", stderr, err)
		return "", fmt.Errorf("read root crontab failed, stderr=%s, err=%w", stderr, err)
	}
	return ret.GetStdout(), nil
}

func runCmd(cmd *mycmd.CmdBuilder) (*mycmd.ExecResult, error) {
	out := bytes.NewBuffer(nil)
	er := bytes.NewBuffer(nil)
	return cmd.Run3(10*time.Second, out, er)
}

func jsonString(raw json.RawMessage) string {
	if raw == nil {
		return ""
	}
	var s string
	_ = json.Unmarshal(raw, &s)
	return s
}

func filterProcJSONValue(v any, exporterNames []string) (any, bool) {
	switch typed := v.(type) {
	case map[string]any:
		newMap := make(map[string]any, len(typed))
		removed := false
		for key, value := range typed {
			if item, ok := value.(map[string]any); ok && procJSONEntryMatchesExporter(item, exporterNames) {
				removed = true
				continue
			}
			filtered, childRemoved := filterProcJSONValue(value, exporterNames)
			if childRemoved {
				removed = true
			}
			newMap[key] = filtered
		}
		return newMap, removed
	case []any:
		newSlice := make([]any, 0, len(typed))
		removed := false
		for _, value := range typed {
			if item, ok := value.(map[string]any); ok && procJSONEntryMatchesExporter(item, exporterNames) {
				removed = true
				continue
			}
			filtered, childRemoved := filterProcJSONValue(value, exporterNames)
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

func procJSONEntryMatchesExporter(m map[string]any, exporterNames []string) bool {
	procName, ok := m["procName"].(string)
	if !ok {
		return false
	}
	for _, name := range exporterNames {
		if procName == name {
			return true
		}
	}
	return false
}
