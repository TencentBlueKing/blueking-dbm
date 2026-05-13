//go:build linux

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

package keepalive

import (
	"fmt"
	"os"
	"strings"
	"syscall"
)

const (
	// KeepaliveProcessNameFull is the full process name shown in args.
	KeepaliveProcessNameFull = "dbha-v2-keepalive"
	// KeepaliveProcessNameComm is the comm name shown in top/ps -o comm.
	KeepaliveProcessNameComm = "dbha-keepalive"

	keepaliveExecEnv = "DBHA_KEEPALIVE_EXECED"
	maxCommNameLen   = 15
)

// EnsureExecWithKeepaliveArgv0 re-execs current binary once to make argv[0]
// visible as KeepaliveProcessNameFull in command-line views.
func EnsureExecWithKeepaliveArgv0(rawArgs []string) error {
	if os.Getenv(keepaliveExecEnv) == "1" {
		return nil
	}

	exePath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("resolve executable path failed, errmsg: %w", err)
	}

	argv := make([]string, 0, len(rawArgs)+1)
	argv = append(argv, KeepaliveProcessNameFull)
	argv = append(argv, rawArgs...)

	env := append(os.Environ(), keepaliveExecEnv+"=1")
	if err := syscall.Exec(exePath, argv, env); err != nil {
		return fmt.Errorf("re-exec keepalive process failed, errmsg: %w", err)
	}
	return nil
}

// SetCommName sets /proc/self/comm (max 15 chars on Linux).
func SetCommName(name string) error {
	trimmed := strings.TrimSpace(name)
	if trimmed == "" {
		return fmt.Errorf("set keepalive comm name failed, errmsg: empty comm name")
	}
	if len(trimmed) > maxCommNameLen {
		return fmt.Errorf(
			"set keepalive comm name failed, errmsg: comm name exceeds %d chars",
			maxCommNameLen,
		)
	}
	if err := os.WriteFile("/proc/self/comm", []byte(trimmed+"\n"), 0644); err != nil {
		return fmt.Errorf("set keepalive comm name failed, errmsg: %w", err)
	}
	return nil
}
