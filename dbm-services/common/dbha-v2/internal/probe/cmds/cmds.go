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
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"
	"unicode"

	"dbm-services/common/dbha-v2/internal/probe/client"
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/proto"
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

func mysqlHarvesterHasEndpoints(c *config.MySqlHarvesterConfig) bool {
	return c != nil && len(c.Endpoints) > 0
}

func redisHarvesterHasEndpoints(c *config.RedisHarvesterConfig) bool {
	return c != nil && len(c.Endpoints) > 0
}

func getConfiguredDbTypes() []haprobe.DbType {
	var dbTypes []haprobe.DbType
	if mysqlHarvesterHasEndpoints(config.Cfg.Harvester.MySql) ||
		mysqlHarvesterHasEndpoints(config.Cfg.Harvester.MySqlProxyAdmin) {
		dbTypes = append(dbTypes, haprobe.DbTypeMySql)
	}
	if redisHarvesterHasEndpoints(config.Cfg.Harvester.Redis) {
		dbTypes = append(dbTypes, haprobe.DbTypeRedis)
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

func unmarshalProbeConfigPayload(raw string) (probeconfig.ProbeConfigPayload, error) {
	var payload probeconfig.ProbeConfigPayload
	if err := json.Unmarshal([]byte(raw), &payload); err != nil {
		// Legacy admin returns a raw metadata list ([]ProbeMetadataItem) instead of ProbeConfigPayload;
		// detect this to provide a clear version-mismatch error rather than a generic unmarshal error.
		if len(raw) > 0 && raw[0] == '[' {
			return payload, fmt.Errorf(
				"admin returned legacy metadata array instead of ProbeConfigPayload, "+
					"please upgrade admin to match the probe version: %w", err)
		}
		return payload, fmt.Errorf("parse probe config payload from admin: %w", err)
	}
	return payload, nil
}

func fetchAndRenderProbeYAML(
	timeout time.Duration, cloudID uint64, localIP string, endpoints []string, clearPorts []int,
) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	req := &proto.ProbeConfigRequest{
		BkCloudId:   cloudID,
		Ip:          localIP,
		ClientID:    "",
		Version:     "",
		UpdatedTime: 0,
	}

	raw, err := getProbeConfigPayload(ctx, endpoints, req)
	if err != nil {
		return "", err
	}
	payload, err := unmarshalProbeConfigPayload(raw)
	if err != nil {
		return "", err
	}
	applyClearPorts(payload.Metadata, clearPorts)
	yamlStr, err := config.GenProbeYAML(payload)
	if err != nil {
		return "", fmt.Errorf("generate probe config: %w", err)
	}
	return yamlStr, nil
}

func writeOrPrintProbeYAML(
	cmd *cobra.Command, outputPath, yamlStr string, lockTimeout time.Duration, reload bool,
) error {
	if outputPath == "" {
		fmt.Fprint(cmd.OutOrStdout(), yamlStr)
		return nil
	}
	// Skipping an unchanged file stays internal: this line is the output contract
	// callers already had, so both paths must keep printing it.
	if _, err := process.WriteFileWithLock(outputPath, []byte(yamlStr), lockTimeout); err != nil {
		return fmt.Errorf("write config file: %w", err)
	}
	fmt.Fprintln(cmd.OutOrStdout(), "Config written to", outputPath)
	if !reload {
		return nil
	}
	// Deliberately not config.Load(outputPath): that would rewrite Cfg for the
	// rest of this process. The default pid file matches what GenProbeYAML rendered.
	return process.ReloadIfRunning(cmd, config.Cfg.PidFile, procName())
}

// GenConfigCmdRunE fetches probe metadata from admin, generates YAML locally, writes to file or stdout.
func GenConfigCmdRunE(cmd *cobra.Command, args []string) error {
	chdirInstallRootIfPackaged()
	adminEndpointsStr, _ := cmd.Flags().GetString("admin-endpoints")
	cloudID, _ := cmd.Flags().GetUint64("cloud-id")
	localIP, _ := cmd.Flags().GetString("local-ip")
	localIPInterface, _ := cmd.Flags().GetString("local-ip-interface")
	outputPath, _ := cmd.Flags().GetString("output")
	timeout := genConfigDuration(cmd, "timeout", DefaultGenConfigTimeout)
	lockTimeout := genConfigDuration(cmd, "lock-timeout", DefaultGenConfigLockTimeout)
	clearPortStr, _ := cmd.Flags().GetString("clear-port")
	reload, _ := cmd.Flags().GetBool("reload")

	if adminEndpointsStr == "" {
		return fmt.Errorf("admin-endpoints is required")
	}
	clearPorts, err := validateGenConfigFlags(clearPortStr, outputPath, reload)
	if err != nil {
		return err
	}
	if localIP == "" {
		resolved, err := resolveGenConfigLocalIP(localIPInterface, adminEndpointsStr)
		if err != nil {
			return err
		}
		localIP = resolved
	}

	endpoints := parseAdminEndpoints(adminEndpointsStr)
	if len(endpoints) == 0 {
		return fmt.Errorf("admin-endpoints has no valid address")
	}

	yamlStr, err := fetchAndRenderProbeYAML(timeout, cloudID, localIP, endpoints, clearPorts)
	if err != nil {
		return err
	}
	return writeOrPrintProbeYAML(cmd, outputPath, yamlStr, lockTimeout, reload)
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
// --clear-port list for the caller to apply to the payload.
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

// applyClearPorts drops the given ports from the metadata by zeroing the matching
// Port / AdminPort fields; GenProbeYAML already skips zero ports, so they never reach
// the rendered config. Items are not removed outright because one entry can carry both
// a data port and an admin port, and only the matching one may disappear.
func applyClearPorts(metadata []probeconfig.ProbeMetadataItem, ports []int) {
	if len(ports) == 0 {
		return
	}

	cleared := make(map[int]struct{}, len(ports))
	for _, port := range ports {
		cleared[port] = struct{}{}
	}

	for i := range metadata {
		if _, ok := cleared[metadata[i].Port]; ok {
			metadata[i].Port = 0
		}
		if _, ok := cleared[metadata[i].AdminPort]; ok {
			metadata[i].AdminPort = 0
		}
	}
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

func getProbeConfigPayload(ctx context.Context, endpoints []string, req *proto.ProbeConfigRequest) (string, error) {
	var lastErr error
	for _, endpoint := range endpoints {
		adminClient, err := client.NewAdminClient(ctx, endpoint, "")
		if err != nil {
			lastErr = fmt.Errorf("create admin client for %s: %w", endpoint, err)
			continue
		}
		resp, err := adminClient.GetProbeConfig(ctx, req)
		adminClient.Close()
		if err != nil {
			lastErr = fmt.Errorf("get probe config from %s: %w", endpoint, err)
			continue
		}
		if resp.GetCode() != proto.ProbeConfigCode_PROBE_CONFIG_SUCCESS {
			lastErr = fmt.Errorf("admin %s returned code:%s, errmsg:%s",
				endpoint, resp.GetCode().String(), resp.GetErrmsg())

			continue
		}
		return resp.GetPayload(), nil
	}
	return "", fmt.Errorf("all admin endpoints failed, last error: %w", lastErr)
}
