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
	"os"

	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/pkg/process"

	"github.com/spf13/cobra"
)

func StartCmdRunE(cmd *cobra.Command, args []string) error {
	pid, err := process.ReadPid(config.Cfg.PidFile)
	if err == nil {
		alive, aliveErr := process.IsAliveWithProcessName(pid, process.NameReceiver)
		if aliveErr == nil && alive {
			_, printErr := fmt.Fprintf(cmd.OutOrStdout(), "%s is already running, pid:%d\n", process.NameReceiver, pid)
			if printErr != nil {
				return printErr
			}
			return nil
		}
	} else if !errors.Is(err, process.ErrPidFileNotExist) &&
		!errors.Is(err, process.ErrInvalidFile) {
		return err
	}
	exePath, err := os.Executable()
	if err != nil {
		return err
	}
	rootCmd := cmd.Root()
	configPath, err := rootCmd.PersistentFlags().GetString("config")
	if err != nil {
		return err
	}

	var childArgs []string
	if configPath != "" {
		childArgs = append(childArgs, "-c", configPath)
	}
	_, err = process.StartDaemon(process.DaemonOptions{
		Executable: exePath,
		Args:       childArgs,
	})
	if err != nil {
		return err
	}

	return nil
}
