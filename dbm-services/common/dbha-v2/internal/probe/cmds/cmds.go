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
	"os"
	"strings"
	"time"

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
	var dbTypes []haprobe.DbType
	if config.Cfg.Harvester.MySql != nil && len(config.Cfg.Harvester.MySql.Endpoints) > 0 {
		dbTypes = append(dbTypes, haprobe.DbTypeMySql)
	}
	if config.Cfg.Harvester.Redis != nil && len(config.Cfg.Harvester.Redis.Endpoints) > 0 {
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

// ReloadCmdRunE sends reload signal to the running probe process.
func ReloadCmdRunE(cmd *cobra.Command, args []string) error {
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

// GenConfigCmdRunE fetches probe metadata from admin, generates YAML locally, writes to file or stdout.
func GenConfigCmdRunE(cmd *cobra.Command, args []string) error {
	adminEndpointsStr, _ := cmd.Flags().GetString("admin-endpoints")
	cloudID, _ := cmd.Flags().GetUint64("cloud-id")
	localIP, _ := cmd.Flags().GetString("local-ip")
	outputPath, _ := cmd.Flags().GetString("output")

	if adminEndpointsStr == "" {
		return fmt.Errorf("admin-endpoints is required")
	}
	if localIP == "" {
		var err error
		localIP, err = machine.GetLocalIPWithInterface(constant.DefaultLocalIPInterface)
		if err != nil {
			return fmt.Errorf("local-ip not set and failed to get %s internal ip: %w",
				constant.DefaultLocalIPInterface, err)
		}
	}

	endpoints := parseAdminEndpoints(adminEndpointsStr)
	if len(endpoints) == 0 {
		return fmt.Errorf("admin-endpoints has no valid address")
	}

	ctx := context.Background()
	req := &proto.ProbeConfigRequest{
		BkCloudId:   cloudID,
		Ip:          localIP,
		ClientID:    "",
		Version:     "",
		UpdatedTime: 0,
	}

	payload, err := getProbeConfigPayload(ctx, endpoints, req)
	if err != nil {
		return err
	}

	var metadata []probeconfig.ProbeMetadataItem
	if err := json.Unmarshal([]byte(payload), &metadata); err != nil {
		return fmt.Errorf("parse metadata from admin: %w", err)
	}

	yamlStr, err := config.GenProbeYAML(metadata)
	if err != nil {
		return fmt.Errorf("generate probe config: %w", err)
	}

	if outputPath != "" {
		if err := os.WriteFile(outputPath, []byte(yamlStr), 0644); err != nil {
			return fmt.Errorf("write config file: %w", err)
		}
		fmt.Fprintln(cmd.OutOrStdout(), "Config written to", outputPath)
		return nil
	}
	fmt.Fprint(cmd.OutOrStdout(), yamlStr)
	return nil
}

func parseAdminEndpoints(s string) []string {
	raw := strings.Split(s, constant.Delimiter)
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
			lastErr = fmt.Errorf("admin %s returned code:%d, errmsg:%s",
				endpoint, resp.GetCode().String(), resp.GetErrmsg())

			continue
		}
		return resp.GetPayload(), nil
	}
	return "", fmt.Errorf("all admin endpoints failed, last error: %w", lastErr)
}
