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
	"os/signal"
	"strings"
	"syscall"

	"dbm-services/common/dbha-v2/internal/probe/keepalive"
	"dbm-services/common/dbha-v2/pkg/logger"
)

const pingHTTPAddrFlag = "--ping-http-addr"

// ExtractPingHTTPAddrFromArgs parses raw args and returns ping-http-addr.
func ExtractPingHTTPAddrFromArgs(rawArgs []string) (string, bool, error) {
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

	sigC := make(chan os.Signal, 1)
	signal.Notify(sigC, syscall.SIGINT, syscall.SIGTERM, syscall.SIGHUP)

	for sig := range sigC {
		if sig == syscall.SIGHUP {
			continue
		}
		return nil
	}
	return nil
}
