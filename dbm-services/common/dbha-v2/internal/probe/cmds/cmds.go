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

// Package cmds provides cobra command implementations for probe (start, stop, restart, reload, health, gen-config).
package cmds

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"
	"unicode"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/spf13/cobra"
)

var (
	ForceStop      bool
	StopTimeout    int
	JsonFormatter  bool
	ConfigFilePath string
)

// DefaultGenConfigTimeout is the default deadline applied to gen-config when --timeout
// is omitted or non-positive; covers the entire admin-endpoints fan-out.
const DefaultGenConfigTimeout = 30 * time.Second

// DefaultGenConfigLockTimeout is the default deadline applied to gen-config when
// --lock-timeout is omitted or non-positive; covers waiting for the config file lock
// held by a concurrent gen-config.
const DefaultGenConfigLockTimeout = 10 * time.Second

// ProbeHealthInfo extends base process health with probe-specific db types (MySQL, Redis, etc.).
type ProbeHealthInfo struct {
	*process.HealthInfo
	DbTypes []haprobe.DbType `json:"db_types,omitempty"`
}

func procName() string {
	if n := process.BinaryName(); n != "" {
		return n
	}
	return process.NameProbe
}

func getConfiguredDbTypes() []haprobe.DbType {
	seen := map[haprobe.DbType]struct{}{}
	var dbTypes []haprobe.DbType
	for _, e := range harvester.Entries() {
		if !config.Cfg.Harvester.HasEndpoints(e.BlockName) {
			continue
		}
		if _, ok := seen[e.DbType]; ok {
			continue
		}
		seen[e.DbType] = struct{}{}
		dbTypes = append(dbTypes, e.DbType)
	}
	return dbTypes
}

// StartCmdRunE runs the probe process in foreground.
func StartCmdRunE(cmd *cobra.Command, args []string) error {
	return process.StartCmdRunE(cmd, args, config.Cfg.PidFile, procName())
}

// StopCmdRunE stops the running probe process.
func StopCmdRunE(cmd *cobra.Command, args []string) error {
	return process.StopCmdRunE(cmd, args, config.Cfg.PidFile, procName(), StopTimeout, ForceStop)
}

// RestartCmdRunE stops the probe then starts it again (daemon or foreground based on how it was started).
func RestartCmdRunE(cmd *cobra.Command, args []string) error {
	configPath, _ := cmd.Root().PersistentFlags().GetString("config")
	if err := config.Load(configPath); err != nil {
		return err
	}
	useDaemonStart, _ := process.WasRunningWithDaemonStart(config.Cfg.PidFile, procName())
	if err := process.StopCmdRunE(cmd, args, config.Cfg.PidFile, procName(), StopTimeout, ForceStop); err != nil {
		return err
	}
	waitDur := time.Duration(StopTimeout) * time.Second
	if err := process.WaitForProcessExit(config.Cfg.PidFile, procName(), waitDur); err != nil {
		return err
	}
	if useDaemonStart {
		return DaemonStartCmdRunE(cmd, args)
	}
	return StartCmdRunE(cmd, args)
}

// chdirInstallRootIfPackaged switches to InstallRoot when the binary lives in
// <root>/bin. Unpackaged layouts (go test, go run) keep the current directory.
func chdirInstallRootIfPackaged() {
	_, _ = process.ChdirInstallRoot()
}

// ReloadCmdRunE sends reload signal to the running probe process.
func ReloadCmdRunE(cmd *cobra.Command, args []string) error {
	chdirInstallRootIfPackaged()
	return process.ReloadCmdRunE(cmd, args, config.Cfg.PidFile, procName(), StopTimeout, ForceStop)
}

// DaemonStartCmdRunE starts the probe as a daemon (background) with guard restart.
func DaemonStartCmdRunE(cmd *cobra.Command, args []string) error {
	configPath, _ := cmd.Root().PersistentFlags().GetString("config")
	if err := config.Load(configPath); err != nil {
		return err
	}
	return process.DaemonStartCmdRunE(cmd, args, config.Cfg.PidFile, procName(), process.DefaultGuardRestartDelay)
}

// HealthCmdRunE prints probe health info (base + db types) to stdout, optionally as JSON.
func HealthCmdRunE(cmd *cobra.Command, _ []string) error {
	if err := config.Load(ConfigFilePath); err != nil {
		baseHealth := process.GetBaseHealthInfo(config.Cfg.PidFile, procName())
		if !JsonFormatter {
			process.PrintBaseHealth(cmd.OutOrStdout(), baseHealth)
			return nil
		}
		data, _ := json.Marshal(baseHealth)
		fmt.Fprintln(cmd.OutOrStdout(), string(data))
		return nil
	}

	baseHealth := process.GetBaseHealthInfo(config.Cfg.PidFile, procName())

	probeHealth := &ProbeHealthInfo{
		HealthInfo: baseHealth,
		DbTypes:    getConfiguredDbTypes(),
	}

	if !JsonFormatter {
		process.PrintBaseHealth(cmd.OutOrStdout(), baseHealth)
		if len(probeHealth.DbTypes) > 0 {
			fmt.Fprintln(cmd.OutOrStdout(), "DbTypes:", probeHealth.DbTypes)
		}
		return nil
	}

	data, err := json.Marshal(probeHealth)
	if err != nil {
		return err
	}
	fmt.Fprintln(cmd.OutOrStdout(), string(data))
	return nil
}

func genConfigDuration(cmd *cobra.Command, name string, fallback time.Duration) time.Duration {
	d, _ := cmd.Flags().GetDuration(name)
	if d <= 0 {
		return fallback
	}
	return d
}

// resolveGenConfigLocalIP picks a local IP for gen-config when --local-ip is unset.
// It tries the named interface first, then falls back to physical-interface scan
// and UDP route detection toward the first admin endpoint host.
func resolveGenConfigLocalIP(localIPInterface, adminEndpointsStr string) (string, error) {
	ifName := constant.DefaultLocalIPInterface
	if trimmed := strings.TrimSpace(localIPInterface); trimmed != "" {
		ifName = trimmed
	}
	localIP, err := machine.GetLocalIPWithInterface(ifName)
	if err == nil {
		return localIP, nil
	}

	detectHost := ""
	endpoints := parseAdminEndpoints(adminEndpointsStr)
	if len(endpoints) > 0 {
		detectHost, _ = machine.HostFromEndpoint(endpoints[0])
	}

	outboundIP, obErr := machine.GetOutboundIP(detectHost)
	if obErr != nil {
		return "", fmt.Errorf(
			"local-ip not set and failed to get %s internal ip (%v) and outbound ip fallback failed: %w",
			ifName, err, obErr,
		)
	}
	return outboundIP, nil
}

// validateGenConfigFlags checks the gen-config flag combinations that do not depend on
// admin, so a bad invocation fails before any network call. It returns the parsed
// --clear-port list for the caller to persist and apply through LocalFields.
func validateGenConfigFlags(clearPortStr, outputPath string, reload bool) ([]int, error) {
	clearPorts, err := parseClearPorts(clearPortStr)
	if err != nil {
		return nil, err
	}
	if reload && outputPath == "" {
		return nil, fmt.Errorf("--reload requires --output")
	}
	return clearPorts, nil
}

// parseClearPorts splits a --clear-port value into ports. Only comma and semicolon
// separate entries: whitespace inside a token (e.g. "100 200") is rejected rather than
// treated as a separator, so a mistyped value cannot silently drop an extra port.
// Empty segments from repeated or trailing separators are ignored, but a non-empty
// value that yields no port at all is an error instead of a silent no-op.
func parseClearPorts(s string) ([]int, error) {
	if strings.TrimSpace(s) == "" {
		return nil, nil
	}

	seen := make(map[int]struct{})
	var ports []int
	for _, token := range strings.FieldsFunc(s, func(r rune) bool { return r == ',' || r == ';' }) {
		token = strings.TrimSpace(token)
		if token == "" {
			continue
		}
		port, err := strconv.Atoi(token)
		if err != nil {
			return nil, fmt.Errorf("clear-port has an invalid port: %q", token)
		}
		if port < 1 || port > 65535 {
			return nil, fmt.Errorf("clear-port is out of range 1-65535: %d", port)
		}
		if _, dup := seen[port]; dup {
			continue
		}
		seen[port] = struct{}{}
		ports = append(ports, port)
	}

	if len(ports) == 0 {
		return nil, fmt.Errorf("clear-port has no valid port: %q", s)
	}
	return ports, nil
}

func parseAdminEndpoints(s string) []string {
	sep := constant.Delimiter
	raw := strings.FieldsFunc(s, func(r rune) bool {
		return (len(sep) > 0 && strings.ContainsRune(sep, r)) || unicode.IsSpace(r)
	})

	var out []string
	for _, ep := range raw {
		if e := strings.TrimSpace(ep); e != "" {
			out = append(out, e)
		}
	}
	return out
}
