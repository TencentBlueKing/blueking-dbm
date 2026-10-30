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
	"fmt"
	"io"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester"
	"dbm-services/common/dbha-v2/internal/probe/harvester/base"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/process"

	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"
)

const (
	// DefaultPauseDuration is how long a port stays paused when --duration is omitted.
	DefaultPauseDuration = 10 * time.Minute

	// pausePortsKey is the top-level probe.yaml key holding the paused ports.
	pausePortsKey = "pausePorts"

	// portListLimit is how many ports are spelled out before the list is shortened.
	portListLimit = 20
)

// knownHarvesterBlocks are the harvester blocks this command covers. Blocks
// registered beyond these are reported by reportUnknownHarvesterBlocks.
var knownHarvesterBlocks = []string{
	config.HarvesterBlockMySQL,
	config.HarvesterBlockMySQLProxyAdmin,
	config.HarvesterBlockRedis,
}

// pauseFlags carries what the command read from the command line.
type pauseFlags struct {
	configPath string
	ports      []int
	hasPorts   bool
	duration   time.Duration
}

// pauseRequest is one pause or resume change applied to the configuration.
type pauseRequest struct {
	ports    []int
	hasPorts bool
	pause    bool
	duration time.Duration
	now      time.Time
}

// CollectPauseCmdRunE temporarily stops collecting the given ports. The ports
// come from the positional arguments; none of them means every collected port.
func CollectPauseCmdRunE(cmd *cobra.Command, args []string) error {
	return applyPausePorts(cmd, args, true)
}

// CollectResumeCmdRunE resumes collecting the given ports, or every paused port
// when no argument is given.
func CollectResumeCmdRunE(cmd *cobra.Command, args []string) error {
	return applyPausePorts(cmd, args, false)
}

// applyPausePorts rewrites the pausePorts block of the probe config file and
// nudges the running probe to pick it up. The whole read-modify-write runs under
// the config file lock so a concurrent sync cannot slip in between the read and
// the write and get its own harvester render reverted.
func applyPausePorts(cmd *cobra.Command, args []string, pause bool) error {
	chdirInstallRootIfPackaged()

	flags, err := pauseFlagsFromCmd(cmd, args, pause)
	if err != nil {
		return err
	}

	if show, _ := cmd.Flags().GetBool("show"); show {
		return showPausePorts(cmd, flags.configPath)
	}

	lockPath, err := process.LockPathFor(flags.configPath)
	if err != nil {
		return fmt.Errorf("resolve config lock path: %w", err)
	}
	fl, err := process.AcquireFileLock(lockPath, DefaultGenConfigLockTimeout)
	if err != nil {
		return fmt.Errorf("acquire config lock: %w", err)
	}
	defer func() { _ = fl.Unlock() }()

	disk, err := config.Parse(flags.configPath)
	if err != nil {
		return fmt.Errorf("parse config file: %w", err)
	}
	reportUnknownHarvesterBlocks()

	writePorts, reported, ignored := resolvePauseTargets(disk, flags, pause)
	req := pauseRequest{
		ports:    writePorts,
		hasPorts: flags.hasPorts,
		pause:    pause,
		duration: flags.duration,
		now:      time.Now(),
	}

	if len(reported) == 0 {
		printPauseResult(cmd.OutOrStdout(), req, nil)
		return nil
	}
	if ignored > 0 {
		fmt.Fprintf(cmd.OutOrStdout(), "%d requested ports are not in the current collection scope\n", ignored)
	}

	parsed, changed, err := commitPausePorts(flags.configPath, mergePausePorts(disk.PausePorts, req))
	if err != nil {
		return err
	}

	printPauseResult(cmd.OutOrStdout(), req, reported)
	printPausedPorts(cmd.OutOrStdout(), activePausePorts(parsed))
	if !changed {
		return nil
	}

	return process.ReloadCmdRunE(cmd, nil, parsed.PidFile, procName(), 0, false)
}

// showPausePorts prints the pause entries that have not expired yet. It only
// reads, so it takes no lock and notifies nobody.
func showPausePorts(cmd *cobra.Command, configPath string) error {
	disk, err := config.Parse(configPath)
	if err != nil {
		return fmt.Errorf("parse config file: %w", err)
	}

	printPausedPorts(cmd.OutOrStdout(), activePausePorts(disk))
	return nil
}

// resolvePauseTargets works out which ports the command writes and which ones it
// reports back. Only ports the config actually collects are paused: a range typed
// by accident would otherwise put thousands of useless entries into the file.
//
// Without a port argument a resume clears every paused port, including entries
// whose port left the configuration while it was paused.
func resolvePauseTargets(
	disk config.Configuration, flags pauseFlags, pause bool,
) (writePorts, reported []int, ignored int) {
	if pause {
		collected := collectedPorts(disk)
		if !flags.hasPorts {
			return collected, collected, 0
		}

		writePorts, ignored = intersectPorts(flags.ports, collected)
		return writePorts, writePorts, ignored
	}

	paused := pausePortNumbers(activePausePorts(disk))
	if !flags.hasPorts {
		return nil, paused, 0
	}

	reported, _ = intersectPorts(flags.ports, paused)
	return flags.ports, reported, 0
}

// commitPausePorts renders the new pause list, checks the result still parses and
// replaces the config file. It returns the parsed result and whether the file
// content really changed.
func commitPausePorts(path string, ports []config.PausePort) (config.Configuration, bool, error) {
	rendered, err := renderWithPausePorts(path, ports)
	if err != nil {
		return config.Configuration{}, false, err
	}

	parsed, err := config.ParseBytes(rendered)
	if err != nil {
		return config.Configuration{}, false,
			fmt.Errorf("the rewritten config does not parse, keeping the current file: %w", err)
	}

	changed, err := process.WriteFileLocked(path, rendered)
	if err != nil {
		return config.Configuration{}, false, fmt.Errorf("write config file: %w", err)
	}
	return parsed, changed, nil
}

// mergePausePorts folds the requested ports into the current list. Pausing adds
// (or refreshes) each port; resuming drops them, or drops everything when no
// port was given. Duplicate ports keep the last entry so a second command
// overwrites the expiry set by the first one.
func mergePausePorts(current []config.PausePort, req pauseRequest) []config.PausePort {
	// Resuming without a port clears the whole list, so none of the merge below
	// has to run.
	if !req.pause && len(req.ports) == 0 {
		return nil
	}

	nowUnix := req.now.Unix()
	byPort := make(map[int]config.PausePort, len(current)+len(req.ports))
	for _, p := range current {
		if p.ExpireAt <= nowUnix {
			continue
		}
		byPort[p.Port] = p
	}

	if req.pause {
		expireAt := req.now.Add(req.duration).Unix()
		for _, port := range req.ports {
			byPort[port] = config.PausePort{Port: port, Duration: req.duration, ExpireAt: expireAt}
		}
	} else {
		for _, port := range req.ports {
			delete(byPort, port)
		}
	}

	out := make([]config.PausePort, 0, len(byPort))
	for _, p := range byPort {
		out = append(out, p)
	}
	return config.NormalizePausePorts(out)
}

// intersectPorts keeps the requested ports that are in scope and reports how
// many were dropped.
func intersectPorts(requested, scope []int) ([]int, int) {
	inScope := make(map[int]struct{}, len(scope))
	for _, port := range scope {
		inScope[port] = struct{}{}
	}

	kept := make([]int, 0, len(requested))
	for _, port := range requested {
		if _, ok := inScope[port]; ok {
			kept = append(kept, port)
		}
	}
	return kept, len(requested) - len(kept)
}

// pauseFlagsFromCmd reads the ports from the positional arguments, the config
// path from the root --config flag and, when pausing, --duration.
func pauseFlagsFromCmd(cmd *cobra.Command, args []string, pause bool) (pauseFlags, error) {
	flags := pauseFlags{duration: DefaultPauseDuration}

	if cmd.Root() != nil {
		flags.configPath, _ = cmd.Root().PersistentFlags().GetString("config")
	}
	if flags.configPath == "" {
		return flags, fmt.Errorf("config file path is empty, pass --config")
	}

	// Space, comma and semicolon all separate ports, so joining the arguments
	// with a comma lets one parser handle every spelling.
	ports, err := parsePausePorts(strings.Join(args, ","))
	if err != nil {
		return flags, err
	}
	flags.ports, flags.hasPorts = ports, len(ports) > 0

	if !pause {
		return flags, nil
	}

	duration, _ := cmd.Flags().GetDuration("duration")
	if duration <= 0 {
		return flags, fmt.Errorf("duration must be positive, got: %s", duration)
	}
	flags.duration = duration
	return flags, nil
}

// parsePausePorts splits the positional port arguments into ports. Comma and
// semicolon separate entries, a dash introduces an inclusive range, so
// "3306,30000-30010" is valid, and several arguments are already joined with a
// comma by the caller. An empty value means "every port".
func parsePausePorts(s string) ([]int, error) {
	if strings.TrimSpace(s) == "" {
		return nil, nil
	}

	seen := map[int]struct{}{}
	var ports []int
	for _, token := range strings.FieldsFunc(s, func(r rune) bool { return r == ',' || r == ';' }) {
		token = strings.TrimSpace(token)
		if token == "" {
			continue
		}

		expanded, err := base.ParsePorts(token)
		if err != nil {
			return nil, fmt.Errorf("port has an invalid value: %q", token)
		}
		for _, port := range expanded {
			if port < 1 || port > 65535 {
				return nil, fmt.Errorf("port is out of range 1-65535: %d", port)
			}
			if _, dup := seen[port]; dup {
				continue
			}
			seen[port] = struct{}{}
			ports = append(ports, port)
		}
	}

	if len(ports) == 0 {
		return nil, fmt.Errorf("port has no valid value: %q", s)
	}
	sort.Ints(ports)
	return ports, nil
}

// collectedPorts returns every port the config currently collects, expanding
// range notation, so "pause everything" can act as a snapshot of this moment.
func collectedPorts(cfg config.Configuration) []int {
	seen := map[int]struct{}{}
	var ports []int

	appendPorts := func(list []string) {
		for _, item := range list {
			expanded, err := base.ParsePorts(item)
			if err != nil {
				continue
			}
			for _, port := range expanded {
				if _, ok := seen[port]; ok {
					continue
				}
				seen[port] = struct{}{}
				ports = append(ports, port)
			}
		}
	}

	for _, name := range knownHarvesterBlocks {
		block := cfg.Harvester.Block(name)
		if block == nil {
			continue
		}
		for _, e := range block.Endpoints {
			appendPorts(e.Ports)
			appendPorts(e.AdminPorts)
		}
	}

	sort.Ints(ports)
	return ports
}

// reportUnknownHarvesterBlocks logs the harvester blocks this command does not
// cover: their ports are neither paused nor collected into the snapshot.
//
// It is driven by the plugin registry on purpose: the point is to notice a DB
// type that exists in the code but was never added to the covered list, and
// that is a code-adaptation hint rather than a failure of this command, so it
// is a warning and not an error.
func reportUnknownHarvesterBlocks() {
	known := make(map[string]struct{}, len(knownHarvesterBlocks))
	for _, name := range knownHarvesterBlocks {
		known[dbtype.NormalizeBlockName(name)] = struct{}{}
	}

	for _, e := range harvester.Entries() {
		if _, ok := known[dbtype.NormalizeBlockName(e.BlockName)]; ok {
			continue
		}
		logger.Warn("pause ports: harvester block is not covered, its ports stay collected, block: %s",
			e.BlockName)
	}
}

// renderWithPausePorts rewrites only the pausePorts key of the config file,
// keeping the rest of the document (including comments) as it is.
func renderWithPausePorts(path string, ports []config.PausePort) ([]byte, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config file: %w", err)
	}

	var root yaml.Node
	if err := yaml.Unmarshal(data, &root); err != nil {
		return nil, fmt.Errorf("decode config yaml: %w", err)
	}
	if root.Kind != yaml.DocumentNode || len(root.Content) == 0 {
		return nil, fmt.Errorf("config yaml has no document node, path: %s", path)
	}

	mapping := root.Content[0]
	if mapping.Kind != yaml.MappingNode {
		return nil, fmt.Errorf("config yaml root is not a mapping, path: %s", path)
	}

	if err := setMappingValue(mapping, pausePortsKey, ports); err != nil {
		return nil, err
	}

	return yaml.Marshal(&root)
}

// setMappingValue sets key to value, or removes the key when value is empty.
func setMappingValue(mapping *yaml.Node, key string, value []config.PausePort) error {
	idx := -1
	for i := 0; i+1 < len(mapping.Content); i += 2 {
		if mapping.Content[i].Value == key {
			idx = i
			break
		}
	}

	if len(value) == 0 {
		if idx >= 0 {
			mapping.Content = append(mapping.Content[:idx], mapping.Content[idx+2:]...)
		}
		return nil
	}

	valueNode := &yaml.Node{}
	if err := valueNode.Encode(value); err != nil {
		return fmt.Errorf("encode pause ports: %w", err)
	}

	if idx >= 0 {
		mapping.Content[idx+1] = valueNode
		return nil
	}

	mapping.Content = append(mapping.Content, &yaml.Node{Kind: yaml.ScalarNode, Value: key}, valueNode)
	return nil
}

// printPauseResult prints what the command did: the ports it set with their
// expiry when pausing, the ports it brought back when resuming, or the single
// reason nothing happened when no port was affected.
func printPauseResult(out io.Writer, req pauseRequest, ports []int) {
	if len(ports) == 0 {
		printNoChangeReason(out, req)
		return
	}

	if !req.pause {
		fmt.Fprintf(out, "resumed %d ports: %s\n", len(ports), formatPortList(ports))
		return
	}

	fmt.Fprintf(out, "paused %d ports: %s\n", len(ports), formatPortList(ports))
	fmt.Fprintf(out, "duration %s, expire at %s\n",
		req.duration, req.now.Add(req.duration).Format(time.RFC3339))
}

// printNoChangeReason explains why the command changed nothing. It is printed
// alone so a no-op cannot look like the ports were applied.
func printNoChangeReason(out io.Writer, req pauseRequest) {
	switch {
	case req.pause && req.hasPorts:
		fmt.Fprintln(out, "the requested ports are not in the current collection scope")
	case req.pause:
		fmt.Fprintln(out, "no port is being collected")
	case req.hasPorts:
		fmt.Fprintln(out, "no paused port matches the requested ports")
	default:
		fmt.Fprintln(out, "no paused port to resume")
	}
}

// printPausedPorts prints every port still paused after the command ran.
func printPausedPorts(out io.Writer, ports []config.PausePort) {
	if len(ports) == 0 {
		fmt.Fprintln(out, "currently paused: none")
		return
	}

	fmt.Fprintf(out, "currently paused (%d): %s\n", len(ports), formatPortList(pausePortNumbers(ports)))
}

// formatPortList renders the ports, shortening lists longer than portListLimit
// so a whole-machine pause does not flood the terminal.
func formatPortList(ports []int) string {
	if len(ports) == 0 {
		return ""
	}

	shown, suffix := ports, ""
	if len(ports) > portListLimit {
		shown, suffix = ports[:portListLimit], fmt.Sprintf(" ... (+%d more)", len(ports)-portListLimit)
	}

	parts := make([]string, 0, len(shown))
	for _, port := range shown {
		parts = append(parts, strconv.Itoa(port))
	}
	return strings.Join(parts, ", ") + suffix
}

// activePausePorts returns the pause entries that have not expired yet, sorted by port.
func activePausePorts(cfg config.Configuration) []config.PausePort {
	now := time.Now().Unix()
	out := make([]config.PausePort, 0, len(cfg.PausePorts))
	for _, p := range cfg.PausePorts {
		if p.ExpireAt > now {
			out = append(out, p)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Port < out[j].Port })
	return out
}

func pausePortNumbers(ports []config.PausePort) []int {
	out := make([]int, 0, len(ports))
	for _, p := range ports {
		out = append(out, p.Port)
	}
	return out
}
