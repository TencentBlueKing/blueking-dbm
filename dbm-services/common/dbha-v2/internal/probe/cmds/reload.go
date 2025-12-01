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
	"syscall"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/process"

	"github.com/spf13/cobra"
)

func ReloadCmdRunE(cmd *cobra.Command, args []string) error {
	pid, err := process.ReadPid(config.Cfg.PidFile)
	if err != nil {
		if errors.Is(err, process.ErrPidFileNotExist) || errors.Is(err, process.ErrInvalidFile) {
			_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is not running (no valid pid file)\n", process.NameProbe)
			if printErr != nil {
				return printErr
			}
			return nil
		}

		return err
	}

	alive, err := process.IsAliveWithProcessName(pid, process.NameProbe)
	if err != nil {
		return err
	}

	if !alive {
		_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is not running, stale pid=%d\n", process.NameProbe, pid)
		if printErr != nil {
			return printErr
		}
		return nil
	}

	if err := syscall.Kill(int(pid), syscall.SIGHUP); err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to stop the process: %s, errmsg: %s", process.NameProbe, err)
	}

	return nil
}
