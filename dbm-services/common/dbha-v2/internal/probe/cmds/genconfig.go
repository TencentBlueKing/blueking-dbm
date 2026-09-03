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
	"context"
	"fmt"
	"os"
	"reflect"
	"sort"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/configsync"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/proto"

	"github.com/spf13/cobra"
)

// genConfigFlags is the subset of gen-config CLI state that participates in parameter resolution.
type genConfigFlags struct {
	endpointsStr     string
	endpoints        []string
	cloudID          uint64
	cloudIDSet       bool
	localIP          string
	localIPInterface string
	clearPorts       []int
	clearPortsSet    bool
}

// genConfigResolved is the fetch-and-write parameter set. The three admin pull fields must equal
// what this round actually used to call admin; otherwise periodic sync would pull a different
// payload and the two writers would oscillate.
type genConfigResolved struct {
	endpoints  []string
	bkCloudID  uint64
	localIP    string
	clearPorts []int
}

// genConfigBaseline is the slice of an existing file that stage 1 used to resolve parameters.
// Stage 3 compares it under the file lock and aborts if another writer changed those fields
// during the fetch.
type genConfigBaseline struct {
	exists     bool
	usable     bool
	endpoints  []string
	bkCloudID  uint64
	localIP    string
	clearPorts []int
}

type genConfigFile struct {
	baseline genConfigBaseline
	local    config.Configuration
	parseErr error
}

// GenConfigCmdRunE fetches probe metadata from admin, generates YAML locally, writes to file or stdout.
func GenConfigCmdRunE(cmd *cobra.Command, args []string) error {
	chdirInstallRootIfPackaged()
	flags, outputPath, timeout, lockTimeout, reload, err := parseGenConfigFlags(cmd)
	if err != nil {
		return err
	}

	if outputPath == "" {
		return runGenConfigStdout(cmd, flags, timeout)
	}
	return runGenConfigToFile(cmd, flags, outputPath, timeout, lockTimeout, reload)
}

func parseGenConfigFlags(cmd *cobra.Command) (
	genConfigFlags, string, time.Duration, time.Duration, bool, error,
) {
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
		return genConfigFlags{}, "", 0, 0, false, fmt.Errorf("admin-endpoints is required")
	}
	clearPorts, err := validateGenConfigFlags(clearPortStr, outputPath, reload)
	if err != nil {
		return genConfigFlags{}, "", 0, 0, false, err
	}
	endpoints := parseAdminEndpoints(adminEndpointsStr)
	if len(endpoints) == 0 {
		return genConfigFlags{}, "", 0, 0, false, fmt.Errorf("admin-endpoints has no valid address")
	}

	flags := genConfigFlags{
		endpointsStr:     adminEndpointsStr,
		endpoints:        endpoints,
		cloudID:          cloudID,
		cloudIDSet:       cmd.Flags().Changed("cloud-id"),
		localIP:          localIP,
		localIPInterface: localIPInterface,
		clearPorts:       clearPorts,
		clearPortsSet:    cmd.Flags().Changed("clear-port"),
	}
	return flags, outputPath, timeout, lockTimeout, reload, nil
}

func runGenConfigStdout(cmd *cobra.Command, flags genConfigFlags, timeout time.Duration) error {
	resolved, err := resolveGenConfigParams(flags, config.Configuration{}, false)
	if err != nil {
		return err
	}
	payload, err := fetchProbePayload(timeout, resolved)
	if err != nil {
		return err
	}
	yamlStr, err := renderNewProbeYAML(payload, resolved)
	if err != nil {
		return err
	}
	fmt.Fprint(cmd.OutOrStdout(), yamlStr)
	return nil
}

func runGenConfigToFile(
	cmd *cobra.Command, flags genConfigFlags, outputPath string,
	timeout, lockTimeout time.Duration, reload bool,
) error {
	stage1, err := readGenConfigFile(outputPath)
	if err != nil {
		return err
	}
	resolved, err := resolveGenConfigParams(flags, stage1.local, stage1.baseline.usable)
	if err != nil {
		return err
	}
	payload, err := fetchProbePayload(timeout, resolved)
	if err != nil {
		return err
	}

	parsed, err := commitGenConfigFile(cmd, genConfigCommit{
		outputPath:  outputPath,
		lockTimeout: lockTimeout,
		stage1:      stage1,
		resolved:    resolved,
		payload:     payload,
		cloudIDSet:  flags.cloudIDSet,
	})
	if err != nil {
		return err
	}
	if !reload {
		return nil
	}
	return process.ReloadIfRunning(cmd, parsed.PidFile, procName())
}

// genConfigCommit carries what stage 3 needs from the two stages before it.
type genConfigCommit struct {
	outputPath  string
	lockTimeout time.Duration
	stage1      genConfigFile
	resolved    genConfigResolved
	payload     probeconfig.ProbeConfigPayload
	cloudIDSet  bool
}

// commitGenConfigFile is stage 3: take the file lock, re-read the file, verify nobody changed the
// fields stage 1 resolved against, then render and write. It returns the parsed rendering so the
// caller can signal the pid file that the new content itself declares.
//
// A baseline mismatch aborts instead of re-resolving under the lock: re-resolving would pair the
// new file state with a payload already fetched under the old parameters, which is exactly the
// mix this whole structure exists to prevent. gen-config is a manual or crontab operation, so
// failing and asking for a retry is cheap.
func commitGenConfigFile(cmd *cobra.Command, c genConfigCommit) (config.Configuration, error) {
	lockPath, err := process.LockPathFor(c.outputPath)
	if err != nil {
		return config.Configuration{}, fmt.Errorf("resolve config lock path: %w", err)
	}
	fl, err := process.AcquireFileLock(lockPath, c.lockTimeout)
	if err != nil {
		return config.Configuration{}, fmt.Errorf("acquire config lock: %w", err)
	}
	defer func() { _ = fl.Unlock() }()

	stage3, err := readGenConfigFile(c.outputPath)
	if err != nil {
		return config.Configuration{}, err
	}
	if !baselinesMatch(c.stage1.baseline, stage3.baseline) {
		return config.Configuration{}, fmt.Errorf("config file changed while fetching from admin, retry gen-config")
	}

	yamlStr, parsed, err := renderLockedProbeYAML(c.payload, c.resolved, c.cloudIDSet, stage3)
	if err != nil {
		return config.Configuration{}, err
	}
	if _, err := process.WriteFileLocked(c.outputPath, []byte(yamlStr)); err != nil {
		return config.Configuration{}, fmt.Errorf("write config file: %w", err)
	}
	printAdminEndpointChange(cmd, stage3, c.resolved)
	fmt.Fprintln(cmd.OutOrStdout(), "Config written to", c.outputPath)
	return parsed, nil
}

func renderLockedProbeYAML(
	payload probeconfig.ProbeConfigPayload, resolved genConfigResolved, cloudIDSet bool, src genConfigFile,
) (string, config.Configuration, error) {
	if !src.baseline.usable {
		if src.parseErr != nil {
			logger.Warn("config file cannot be parsed, writing a new one, errmsg: %s", src.parseErr)
		}
		yamlStr, err := renderNewProbeYAML(payload, resolved)
		if err != nil {
			return "", config.Configuration{}, err
		}
		parsed, err := config.ParseBytes([]byte(yamlStr))
		if err != nil {
			return "", config.Configuration{}, fmt.Errorf("rendered config does not parse: %w", err)
		}
		return yamlStr, parsed, nil
	}

	local, err := applyResolvedLocal(src.local, resolved, cloudIDSet)
	if err != nil {
		return "", config.Configuration{}, err
	}
	yamlStr, err := configsync.Render(payload, config.LocalFields(local)...)
	if err != nil {
		return "", config.Configuration{}, err
	}
	parsed, err := config.ParseBytes([]byte(yamlStr))
	if err != nil {
		return "", config.Configuration{}, fmt.Errorf(
			"rendered config does not parse, keeping the current file: %w", err)
	}
	return yamlStr, parsed, nil
}

// renderNewProbeYAML renders a file that has no local content to preserve. Only two options
// apply: the ports the operator asked to exclude, and the admin block.
//
// The admin block is written even though there is no file to inherit it from. Its three fields
// are the parameters this run actually used to reach admin, so the same-source invariant holds,
// and without them a first deployment would produce a config that can never sync or be extended
// by a later gen-config. Nothing else from LocalFields is injected: those values would come from
// defaultConfiguration() rather than from an operator, and writing them would pin defaults the
// code may later revise.
func renderNewProbeYAML(payload probeconfig.ProbeConfigPayload, resolved genConfigResolved) (string, error) {
	return configsync.Render(payload,
		config.WithClearPorts(resolved.clearPorts),
		config.WithAdmin(adminFromResolved(resolved)),
	)
}

// adminFromResolved leaves SyncInterval at zero: it has no flag and no file to inherit from, so
// the mirror struct omits it and periodic sync stays off until an operator sets it.
func adminFromResolved(resolved genConfigResolved) config.AdminConfig {
	return config.AdminConfig{
		Endpoints: resolved.endpoints,
		BkCloudID: resolved.bkCloudID,
		LocalIP:   resolved.localIP,
	}
}

func fetchProbePayload(timeout time.Duration, resolved genConfigResolved) (probeconfig.ProbeConfigPayload, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	return configsync.Fetch(ctx, resolved.endpoints, probeConfigRequest(resolved))
}

// probeConfigRequest is the other half of the same-source invariant: the request has to be built
// from the resolved parameters, never from the raw flags, because those same resolved values are
// what applyResolvedLocal writes into the admin block. Sourcing either side from anywhere else
// would make periodic sync pull a different payload than the file describes.
func probeConfigRequest(resolved genConfigResolved) *proto.ProbeConfigRequest {
	return &proto.ProbeConfigRequest{
		BkCloudId:   resolved.bkCloudID,
		Ip:          resolved.localIP,
		ClientID:    "",
		Version:     "",
		UpdatedTime: 0,
	}
}

func readGenConfigFile(path string) (genConfigFile, error) {
	info, err := os.Stat(path)
	if err != nil {
		if os.IsNotExist(err) {
			return genConfigFile{}, nil
		}
		return genConfigFile{}, fmt.Errorf("stat config file: %w", err)
	}
	out := genConfigFile{baseline: genConfigBaseline{exists: true}}
	if info.Size() == 0 {
		return out, nil
	}
	parsed, parseErr := config.Parse(path)
	if parseErr != nil {
		out.parseErr = parseErr
		return out, nil
	}
	out.local = parsed
	out.baseline.usable = true
	out.baseline.endpoints = copyStrings(parsed.Admin.Endpoints)
	out.baseline.bkCloudID = parsed.Admin.BkCloudID
	out.baseline.localIP = parsed.Admin.LocalIP
	out.baseline.clearPorts = copyInts(parsed.ClearPorts)
	return out, nil
}

func resolveGenConfigParams(flags genConfigFlags, local config.Configuration, usable bool) (genConfigResolved, error) {
	out := genConfigResolved{endpoints: copyStrings(flags.endpoints)}
	out.bkCloudID = flags.cloudID
	if !flags.cloudIDSet && usable {
		out.bkCloudID = local.Admin.BkCloudID
	}

	// An explicit empty --local-ip counts as "not provided": callers pass it from a shell
	// variable that may be unset, and fetching with an empty IP only yields ErrNoData.
	switch {
	case flags.localIP != "":
		out.localIP = flags.localIP
	case usable && local.Admin.LocalIP != "":
		out.localIP = local.Admin.LocalIP
	default:
		resolved, err := resolveGenConfigLocalIP(flags.localIPInterface, flags.endpointsStr)
		if err != nil {
			return genConfigResolved{}, err
		}
		out.localIP = resolved
	}

	if flags.clearPortsSet {
		out.clearPorts = copyInts(flags.clearPorts)
	} else if usable {
		out.clearPorts = copyInts(local.ClearPorts)
	}
	return out, nil
}

func applyResolvedLocal(
	local config.Configuration, resolved genConfigResolved, cloudIDSet bool,
) (config.Configuration, error) {
	local.Admin.Endpoints = copyStrings(resolved.endpoints)
	local.Admin.BkCloudID = resolved.bkCloudID
	local.Admin.LocalIP = resolved.localIP
	local.ClearPorts = copyInts(resolved.clearPorts)
	if !cloudIDSet {
		return local, nil
	}
	reporterID, err := reporterBkCloudIDFromUint64(resolved.bkCloudID)
	if err != nil {
		return config.Configuration{}, err
	}
	local.Reporter = reporterWithBkCloudID(local.Reporter, reporterID)
	return local, nil
}

func reporterWithBkCloudID(src *config.ReporterConfig, id int) *config.ReporterConfig {
	if src == nil {
		return &config.ReporterConfig{BkCloudID: id}
	}
	copied := *src
	copied.BkCloudID = id
	return &copied
}

func reporterBkCloudIDFromUint64(id uint64) (int, error) {
	const maxInt = int(^uint(0) >> 1)
	if id > uint64(maxInt) {
		return 0, fmt.Errorf("cloud-id exceeds reporter bkCloudID range: %d", id)
	}
	return int(id), nil
}

func baselinesMatch(a, b genConfigBaseline) bool {
	if a.exists != b.exists || a.usable != b.usable {
		return false
	}
	if !a.usable {
		return true
	}
	return reflect.DeepEqual(a.endpoints, b.endpoints) &&
		a.bkCloudID == b.bkCloudID &&
		a.localIP == b.localIP &&
		clearPortsEqual(a.clearPorts, b.clearPorts)
}

func clearPortsEqual(a, b []int) bool {
	aa := append([]int(nil), a...)
	bb := append([]int(nil), b...)
	sort.Ints(aa)
	sort.Ints(bb)
	return reflect.DeepEqual(aa, bb)
}

// printAdminEndpointChange warns that the file's endpoint list is being replaced. A file that
// carried no list yet has nothing to warn about, so only a real replacement prints.
func printAdminEndpointChange(cmd *cobra.Command, src genConfigFile, resolved genConfigResolved) {
	if !src.baseline.usable || len(src.baseline.endpoints) == 0 {
		return
	}
	if reflect.DeepEqual(src.baseline.endpoints, resolved.endpoints) {
		return
	}
	fmt.Fprintf(cmd.OutOrStdout(),
		"admin endpoints updated, previous: %s, current: %s\n",
		strings.Join(src.baseline.endpoints, ";"),
		strings.Join(resolved.endpoints, ";"))
}

func copyStrings(in []string) []string {
	if len(in) == 0 {
		return nil
	}
	out := make([]string, len(in))
	copy(out, in)
	return out
}

func copyInts(in []int) []int {
	if len(in) == 0 {
		return nil
	}
	out := make([]int, len(in))
	copy(out, in)
	return out
}
