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
	"errors"
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/process"

	"github.com/spf13/cobra"
)

var (
	ForceStop   bool
	StopTimeout int
)

func StopCmdRunE(cmd *cobra.Command, args []string) error {
	opt := process.StopOptions{
		PidFile:  config.Cfg.PidFile,
		ProcName: process.NameAdmin,
		Timeout:  time.Duration(StopTimeout) * time.Second,
		Force:    ForceStop,
	}

	pid, err := process.ReadPid(opt.PidFile)
	if err != nil {
		if errors.Is(err, process.ErrPidFileNotExist) || errors.Is(err, process.ErrInvalidFile) {
			_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, nothing to stop\n", process.NameAdmin)
			if printErr != nil {
				return printErr
			}
			return nil
		}
		return err
	}

	alive, err := process.IsAliveWithProcessName(pid, opt.ProcName)
	if err != nil {
		return err
	}

	if !alive {
		_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, nothing to stop\n", process.NameAdmin)
		if printErr != nil {
			return printErr
		}
		return nil
	}

	if err := process.StopWithPidFile(opt); err != nil {
		if errors.Is(err, process.ErrProcessNotRunning) {
			_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, nothing to stop\n", process.NameAdmin)
			if printErr != nil {
				return printErr
			}
			return nil
		}
		return err
	}

	return nil
}
