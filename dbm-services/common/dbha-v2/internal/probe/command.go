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

package probe

import (
	"fmt"
	"os"
	"runtime"
	"strings"
	"syscall"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/pidfile"
	"dbm-services/common/dbha-v2/pkg/version"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var VersionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print Version Information",
	Run: func(cmd *cobra.Command, args []string) {
		version.Print("DBHA Probe")
	},
}

func unixKillProbeProcess(pid int, forceStop bool, timeout time.Duration) error {
	/* make sure the process is a probe process */
	commPath := fmt.Sprintf("/proc/%d/comm", pid)
	comm, err := os.ReadFile(commPath)
	if err != nil {
		return fmt.Errorf("read process name from %s failed: %v", commPath, err)
	}
	if strings.TrimSpace(string(comm)) != "probe" {
		return fmt.Errorf("process name of %d is not 'probe'", pid)
	}

	killSignal := syscall.SIGTERM
	if forceStop {
		killSignal = syscall.SIGKILL
	}

	/* send signal to the probe process */
	if err := syscall.Kill(pid, killSignal); err != nil {
		return fmt.Errorf("send signal to %d failed: %v", pid, err)
	}

	/* wait for the process to terminate */
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		exists, err := pidfile.IsProcessExists(pid)
		if err != nil {
			return err
		}
		if !exists {
			return nil
		}
		time.Sleep(100 * time.Millisecond)
	}
	return fmt.Errorf("process %d still exists after timeout", pid)
}

func windowsKillProbeProcess(pid int, forceStop bool, timeout time.Duration) error {
	return fmt.Errorf("termination function for probe on windows is not implemented")
}

func killProbeProcess(pid int, forceStop bool, timeout time.Duration) error {
	if runtime.GOOS == "windows" {
		return windowsKillProbeProcess(pid, forceStop, timeout)
	}
	return unixKillProbeProcess(pid, forceStop, timeout)
}

func runProbeStop() error {
	if logger.Log() == nil {
		return fmt.Errorf("logger is not initialized")
	}

	probe_pid, err := pidfile.ReadPID(config.Cfg.PIDFile)
	if err != nil {
		logger.Error("Failed to get probe pid: %s", err)
		return err
	}
	logger.Info("%s shutting down the probe process %d from %s",
		os.Args[0], probe_pid, viper.ConfigFileUsed())

	err = killProbeProcess(probe_pid, ForceStop,
		time.Duration(StopTimeout)*time.Second)
	if err != nil {
		logger.Error("%s shutdown error: %v", os.Args[0], err)
		return err
	}
	return nil
}

var StopCmd = &cobra.Command{
	Use:   "stop",
	Short: "Stop the probe process corresponding to the configuration file",
	PreRunE: func(cmd *cobra.Command, args []string) error {
		if StopTimeout > uint(86400) {
			return fmt.Errorf("invalid timeout %d, out of range", StopTimeout)
		}
		return nil
	},
	RunE: func(cmd *cobra.Command, args []string) error {
		if err := initProbeLogger(); err != nil {
			return err
		}

		return runProbeStop()
	},
}

var RestartCmd = &cobra.Command{
	Use:   "restart",
	Short: "Restart the probe process corresponding to the configuration file",
	PreRunE: func(cmd *cobra.Command, args []string) error {
		if StopTimeout > uint(86400) {
			return fmt.Errorf("invalid timeout %d, out of range", StopTimeout)
		}
		return nil
	},
	RunE: func(cmd *cobra.Command, args []string) error {
		if err := initProbeLogger(); err != nil {
			return err
		}
		if err := runProbeStop(); err != nil {
			return err
		}
		return runProbeService()
	},
}

var ReloadCmd = &cobra.Command{
	Use:   "reload",
	Short: "Reload the probe process corresponding to the configuration file",
	RunE: func(cmd *cobra.Command, args []string) error {
		// TODO
		return nil
	},
}
