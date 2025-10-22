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

package cmds

import (
	"encoding/json"
	"fmt"
	"os"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/process"

	"github.com/spf13/cobra"
)

var JsonFormatter bool

func HealthCmdRunE(cmd *cobra.Command, args []string) error {
	healthInfo := obtainHealthInfo()

	if !JsonFormatter {
		printRawHealth(healthInfo)
		return nil
	}

	data, err := json.Marshal(healthInfo)
	if err != nil {
		return err
	}

	fmt.Fprintln(os.Stdout, string(data))
	return nil
}

func printRawHealth(health *process.HealthInfo) {
	fmt.Fprintln(os.Stdout, "Pid:", health.Pid)
	fmt.Fprintln(os.Stdout, "ProcName:", health.ProcName)
	fmt.Fprintln(os.Stdout, "Status:", health.Status)
	fmt.Fprintln(os.Stdout, "ErrMsg:", health.ErrMsg)
}

func obtainHealthInfo() *process.HealthInfo {
	health := &process.HealthInfo{
		Pid:      process.InvalidPid,
		ProcName: process.NameProbe,
		Status:   process.StatusStopped,
	}

	pid, err := process.ReadPid(config.Cfg.PidFile)
	if err != nil {
		health.ErrMsg = err.Error()
		return health
	}

	health.Pid = pid

	procName, err := process.Name(pid)
	if err != nil {
		health.ErrMsg = err.Error()
	}

	health.ProcName = procName

	alive, err := process.IsAliveWithProcessName(pid, process.NameProbe)
	if err != nil {
		health.ErrMsg = err.Error()
	}

	if alive {
		health.Status = process.StatusRunning
	}

	return health
}
