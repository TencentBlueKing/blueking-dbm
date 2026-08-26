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
	"strings"

	"dbm-services/common/dbha-v2/internal/probe/keepalive"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/process"
)

const pingHTTPAddrFlag = "--ping-http-addr"

// cobraSubcommands owns args that should never enter RunKeepaliveMode even if
// --ping-http-addr is present (e.g. ensure-keepalive).
var cobraSubcommands = map[string]struct{}{
	"version":          {},
	"health":           {},
	"start":            {},
	"daemon-start":     {},
	"stop":             {},
	"restart":          {},
	"reload":           {},
	"gen-config":       {},
	"ensure":           {},
	"ensure-keepalive": {},
	"help":             {},
	"completion":       {},
}

func hasCobraSubcommand(rawArgs []string) bool {
	for _, arg := range rawArgs {
		if _, ok := cobraSubcommands[arg]; ok {
			return true
		}
	}
	return false
}

// ExtractPingHTTPAddrFromArgs parses raw args and returns ping-http-addr.
// Keepalive mode is the no-subcommand entry (`dbha-probe --ping-http-addr …`).
// Known cobra subcommands are never treated as keepalive mode, even when a
// split flag value (such as -c PATH) appears before the subcommand token.
func ExtractPingHTTPAddrFromArgs(rawArgs []string) (string, bool, error) {
	if hasCobraSubcommand(rawArgs) {
		return "", false, nil
	}

	for i, arg := range rawArgs {
		if !strings.HasPrefix(arg, pingHTTPAddrFlag) {
			continue
		}

		if arg == pingHTTPAddrFlag {
			if i+1 >= len(rawArgs) {
				return "", true, fmt.Errorf("invalid ping-http-addr flag, errmsg: empty value")
			}
			value := strings.TrimSpace(rawArgs[i+1])
			if value == "" {
				return "", true, fmt.Errorf("invalid ping-http-addr flag, errmsg: empty value")
			}
			return value, true, nil
		}

		prefix := pingHTTPAddrFlag + "="
		if !strings.HasPrefix(arg, prefix) {
			continue
		}
		value := strings.TrimSpace(strings.TrimPrefix(arg, prefix))
		if value == "" {
			return "", true, fmt.Errorf("invalid ping-http-addr flag, errmsg: empty value")
		}
		return value, true, nil
	}
	return "", false, nil
}

// RunKeepaliveMode starts keepalive ping server and blocks until termination signal.
func RunKeepaliveMode(pingAddr string, rawArgs []string) error {
	if err := keepalive.EnsureExecWithKeepaliveArgv0(rawArgs); err != nil {
		return err
	}
	if err := keepalive.SetCommName(keepalive.KeepaliveProcessNameComm); err != nil {
		return err
	}

	server := keepalive.NewPingServer(pingAddr)
	if err := server.Start(); err != nil {
		return err
	}
	defer func() {
		if err := server.Close(); err != nil {
			logger.Warn("close keepalive ping server failed, errmsg: %s", err)
		}
	}()

	// keepalive holds no pid file (the deploy scripts manage probe-keepalive.pid),
	// so its stop/reload events are keyed off the ping-http-addr, which both the
	// running process and the stop script hold. On Unix this reduces to the usual
	// signal handling (SIGINT/SIGTERM stop, SIGHUP reload -> no-op).
	waiter, err := process.NewStopWaiter(pingAddr)
	if err != nil {
		return err
	}
	defer waiter.Close()

	for {
		select {
		case <-waiter.Reload:
			continue
		case <-waiter.Shutdown:
			return nil
		}
	}
}
