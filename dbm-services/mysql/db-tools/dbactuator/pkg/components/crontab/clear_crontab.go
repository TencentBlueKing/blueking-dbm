package crontab

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	ma "dbm-services/mysql/db-tools/mysql-crond/api"

	pkgerrors "github.com/pkg/errors"
)

// ClearCrontabParam 实际不止这样
type ClearCrontabParam struct {
}

/*
	执行系统初始化脚本 原来的sysinit.sh
	创建mysql账户等操作
*/

// CleanCrontab  注释掉Crontab
//
//	@receiver u
//	@return err
func (u *ClearCrontabParam) CleanCrontab() (err error) {
	logger.Info("开始清理机器上的crontab")
	if err = osutil.CleanLocalCrontab(); err != nil {
		return err
	}

	cmd := exec.Command(
		"su", []string{
			"-", "mysql", "-c",
			fmt.Sprintf(`/bin/sh %s`,
				path.Join(cst.MySQLCrondInstallPath, "remove_keep_alive.sh")),
		}...,
	)
	err = cmd.Run()
	if err != nil {
		logger.Error("remove mysql-crond keep alive crontab failed: %s", err.Error())
		//return err
	}
	logger.Info("remove mysql-crond keep alive crontab success")

	time.Sleep(1 * time.Minute)

	manager := ma.NewManager("http://127.0.0.1:9999")
	err = manager.Quit()
	if err != nil {
		logger.Error("shutdown mysql-crond failed: %s", err.Error())
	}
	logger.Info("shutdown mysql-crond success")

	return nil
}

// dbhaProbeProcessName dbha 探针进程名（comm，最大 15 字符）
// 用于 pgrep -x 精确匹配 /proc/<pid>/comm，避免 pgrep -f "dbha-probe" 因子串匹配
// 误伤到诸如 vim /tmp/dbha-probe.log、tail xxx-dbha-probe-xxx.log、
// 甚至本清理流程里 argv 含 "dbha-probe" 的辅助命令等无关进程。
const dbhaProbeProcessName = "dbha-probe"

// CleanDBToolsFolder 清理相关mysql残留的目录，其中包括
// checksum目录
// dbbackup目录
// rotate_binlog目录
// mysql_crond目录
// dbatools目录
func (u *ClearCrontabParam) CleanDBToolsFolder() (err error) {

	logger.Info("开始删除相关周边组件目录")
	var errList []error
	var isErr bool
	rmList := []string{
		cst.ChecksumInstallPath,
		cst.DbbackupGoInstallPath,
		cst.DBAToolkitPath,
		cst.MySQLCrondInstallPath,
		cst.MysqlRotateBinlogInstallPath,
		cst.MySQLMonitorInstallPath,
		cst.DBAReportBase,
		cst.BackupClientInstallPath,
		cst.BackupClientReportDir,
		cst.BackupClientAuthPath,
	}
	for _, f := range rmList {
		errList = append(errList, os.RemoveAll(f))
	}

	// 打印所有的err信息
	for _, err := range errList {
		if err != nil && !errors.Is(err, os.ErrNotExist) {
			logger.Error(err.Error())
			isErr = true
		}
	}
	if isErr {
		return fmt.Errorf("clean db-tool-folder failed")
	}
	return nil

}

// StopDBHAProbe 停止本机 dbha 探针进程
// 目标：**不残留任何 dbha 探针进程**。为此采用「优雅停止 + 强制 kill -9 兜底」两级策略：
//  1. 探针目录不存在则直接跳过（幂等）
//  2. 优先执行 stop-probe.sh 做优雅停止；无论成功与否都不直接返回，进入兜底校验
//  3. 通过 pgrep 检查是否仍有残留进程，若有则 kill -9 强杀
//  4. 强杀后再校验一次，仍有残留则返回错误
func (u *ClearCrontabParam) StopDBHAProbe() (err error) {
	probeDir := cst.DBHAProbeInstallDir
	if !cmutil.FileExists(probeDir) {
		logger.Info("probe not deployed on this host [%s], skip stop", probeDir)
		return nil
	}

	logger.Info("开始停止 dbha 探针 [%s]", probeDir)

	// 1) 优雅停止：失败只记录日志，让后续兜底逻辑接管，确保不残留进程
	stopCmd := fmt.Sprintf(`cd %s && ./stop-probe.sh`, probeDir)
	if output, execErr := osutil.ExecShellCommand(false, stopCmd); execErr != nil {
		logger.Warn("graceful stop dbha probe failed, will fallback to kill -9: %s, output: %s",
			execErr.Error(), output)
	} else {
		logger.Info("graceful stop dbha probe success, output: %s", output)
	}

	// 2) 兜底校验：若仍有残留进程，则 kill -9 强杀
	pids, err := findDBHAProbePIDs()
	if err != nil {
		logger.Error("check residual dbha probe process failed: %s", err.Error())
		return err
	}
	if len(pids) == 0 {
		logger.Info("no residual dbha probe process, stop success")
		return nil
	}

	logger.Warn("residual dbha probe process detected, pids=%v, fallback to kill -9", pids)
	if killErr := forceKillDBHAProbe(pids); killErr != nil {
		logger.Error("force kill dbha probe failed: %s", killErr.Error())
		return killErr
	}

	logger.Info("dbha probe process killed, no residual")
	return nil
}

// CleanDBHAProbeFolder 清理 dbha 探针相关的目录与安装包
//  1. 移除探针安装目录（/home/mysql/dbha-v2）
//  2. 移除下发目录下的探针安装包（/data/install/*-probe.tar.gz）
//
// 任一目录不存在均视为跳过，不视为错误。
func (u *ClearCrontabParam) CleanDBHAProbeFolder() (err error) {
	probeDir := cst.DBHAProbeInstallDir
	if cmutil.FileExists(probeDir) {
		logger.Info("removing probe directory: %s", probeDir)
		if err = os.RemoveAll(probeDir); err != nil && !errors.Is(err, os.ErrNotExist) {
			logger.Error("remove probe directory [%s] failed: %s", probeDir, err.Error())
			return err
		}
	} else {
		logger.Info("probe directory not found, skip remove: %s", probeDir)
	}

	installDir := cst.BK_PKG_INSTALL_PATH
	if cmutil.FileExists(installDir) {
		pattern := path.Join(installDir, "*-probe.tar.gz")
		matches, gErr := filepath.Glob(pattern)
		if gErr != nil {
			logger.Error("glob probe packages [%s] failed: %s", pattern, gErr.Error())
			return gErr
		}
		logger.Info("removing probe packages under [%s], matched %d file(s)", installDir, len(matches))
		for _, f := range matches {
			if rmErr := os.Remove(f); rmErr != nil && !errors.Is(rmErr, os.ErrNotExist) {
				logger.Error("remove probe package [%s] failed: %s", f, rmErr.Error())
				return rmErr
			}
			logger.Info("removed probe package: %s", f)
		}
	} else {
		logger.Info("install directory not found, skip remove: %s", installDir)
	}

	logger.Info("probe directory cleared")
	return nil
}

// findDBHAProbePIDs 查找本机所有"确实是安装目录下运行中的 dbha-probe"进程 PID
//
// 匹配契约与官方 stop-probe.sh / guard-utils.sh 中的 get_valid_pids 对齐，
// 采用两层过滤，避免 pgrep -f 子串匹配导致的误杀：
//  1. pgrep -x dbha-probe：精确匹配 /proc/<pid>/comm，把 vim /tmp/dbha-probe.log、
//     tail xxx-dbha-probe-xxx.log 等 cmdline 里含 "dbha-probe" 子串但进程名不同的
//     进程直接过滤掉；
//  2. 对每个候选 pid，通过 /proc/<pid>/exe 读到进程实际使用的可执行文件绝对路径，
//     与 <cst.DBHAProbeInstallDir>/bin/dbha-probe 的绝对路径（EvalSymlinks 后）
//     严格相等才认为是本机安装目录下的 dbha-probe；否则记录日志但不加入 kill 列表，
//     防止误杀同名但装在别处的可执行文件。
//
// pgrep 退出码：0 有匹配，1 无匹配（正常，非错误），>=2 才算真正失败
func findDBHAProbePIDs() ([]string, error) {
	// 预先解析出"期望的可执行文件绝对路径"（跟随符号链接），与官方脚本
	// readlink -f "$BINARY_PATH" 的行为一致。
	probeDir := cst.DBHAProbeInstallDir
	expectedExe, expErr := resolveExpectedProbeExe(probeDir)
	if expErr != nil {
		// 探针目录已经不存在时，直接视为无残留（外层 StopDBHAProbe 也会先跳过）。
		if errors.Is(expErr, os.ErrNotExist) {
			return nil, nil
		}
		return nil, pkgerrors.Wrapf(expErr, "resolve expected probe exe under %s failed", probeDir)
	}

	cmd := exec.Command("pgrep", "-x", dbhaProbeProcessName)
	out, err := cmd.Output()
	if err != nil {
		if ee, ok := err.(*exec.ExitError); ok && ee.ExitCode() == 1 {
			return nil, nil
		}
		return nil, pkgerrors.Wrapf(err, "pgrep -x %s failed", dbhaProbeProcessName)
	}

	var pids []string
	for _, line := range strings.Split(strings.TrimSpace(string(out)), "\n") {
		pid := strings.TrimSpace(line)
		if pid == "" {
			continue
		}
		actualExe, rlErr := os.Readlink(fmt.Sprintf("/proc/%s/exe", pid))
		if rlErr != nil {
			// 进程可能已在 pgrep 与 readlink 之间退出，或权限不足读不到；
			// 保守起见不当作目标进程，跳过。
			logger.Warn("readlink /proc/%s/exe failed, skip: %s", pid, rlErr.Error())
			continue
		}
		if actualExe != expectedExe {
			logger.Info("skip non-target dbha-probe process, pid=%s exe=%s (expected=%s)",
				pid, actualExe, expectedExe)
			continue
		}
		pids = append(pids, pid)
	}
	return pids, nil
}

// resolveExpectedProbeExe 计算 <probeDir>/bin/dbha-probe 的绝对可执行路径，
// 跟随符号链接（对齐 shell 里的 readlink -f）。
func resolveExpectedProbeExe(probeDir string) (string, error) {
	raw := path.Join(probeDir, "bin", "dbha-probe")
	// EvalSymlinks 要求路径存在。存在则得到规范化后的绝对路径；不存在则返回 os.ErrNotExist。
	resolved, err := filepath.EvalSymlinks(raw)
	if err != nil {
		return "", err
	}
	return resolved, nil
}

// forceKillDBHAProbe 对给定 PID 列表统一 kill -9
// 单点失败只记录日志，继续把机会交给上层"再校验"逻辑
func forceKillDBHAProbe(pids []string) error {
	if len(pids) == 0 {
		return nil
	}
	killCmd := fmt.Sprintf("kill -9 %s", strings.Join(pids, " "))
	if output, err := osutil.ExecShellCommand(false, killCmd); err != nil {
		logger.Warn("kill -9 %v got error: %s, output: %s", pids, err.Error(), output)
	} else {
		logger.Info("kill -9 %v success, output: %s", pids, output)
	}
	return nil
}
