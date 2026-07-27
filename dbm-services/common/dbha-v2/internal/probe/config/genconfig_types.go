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

package config

import (
	"sort"

	"gopkg.in/yaml.v3"
)

// probeYAML is used only for GenProbeYAML output. Reuses LogConfig from config.go.
type probeYAML struct {
	Name      string             `yaml:"name"`
	Version   string             `yaml:"version"`
	PidFile   string             `yaml:"pidFile"`
	Reporter  probeReporterYAML  `yaml:"reporter"`
	Harvester probeHarvesterYAML `yaml:"harvester"`
	Log       LogConfig          `yaml:"log"`
}

// probeReporterYAML has ConnTimeout as string for YAML output (e.g. "5s"); ReporterConfig uses time.Duration.
type probeReporterYAML struct {
	Name            string `yaml:"name"`
	Endpoint        string `yaml:"endpoint"`
	DataID          uint64 `yaml:"dataID"`
	ConnTimeout     string `yaml:"connTimeout"`
	LocalSocketPort uint   `yaml:"localSocketPort,omitempty"` // omitempty: omit when 0 so Linux YAML stays byte-identical
}

// probeGenericHarvesterYAML is the on-wire shape shared by named and extra harvester blocks.
type probeGenericHarvesterYAML struct {
	User      string             `yaml:"user"`
	Password  string             `yaml:"password"`
	Interval  string             `yaml:"interval"`
	Timeout   string             `yaml:"timeout"`
	Endpoints []DbEndpointConfig `yaml:"endpoints"`
}

type probeMySQLHarvesterYAML = probeGenericHarvesterYAML
type probeRedisHarvesterYAML = probeGenericHarvesterYAML

// probeHarvesterYAML keeps named mysql/redis/proxyAdmin blocks for zero regression and
// Extra for newly added DB types. MarshalYAML emits a flat mapping.
type probeHarvesterYAML struct {
	MySQL           *probeMySQLHarvesterYAML
	MySQLProxyAdmin *probeMySQLHarvesterYAML
	Redis           *probeRedisHarvesterYAML
	Extra           map[string]*probeGenericHarvesterYAML
}

// MarshalYAML flattens named + Extra blocks into one harvester mapping.
// Relies on yaml.v3 sorting map keys; the three well-known blocks' lexicographic
// order happens to match the historical field order. Adding a new named block
// may change the emitted key order relative to Extra keys.
func (h probeHarvesterYAML) MarshalYAML() (interface{}, error) {
	out := map[string]*probeGenericHarvesterYAML{}
	if h.MySQL != nil {
		out[HarvesterBlockMySQL] = h.MySQL
	}
	if h.MySQLProxyAdmin != nil {
		out[HarvesterBlockMySQLProxyAdmin] = h.MySQLProxyAdmin
	}
	if h.Redis != nil {
		out[HarvesterBlockRedis] = h.Redis
	}
	for name, block := range h.Extra {
		if block == nil {
			continue
		}
		out[name] = block
	}
	return out, nil
}

// Ensure yaml.Marshaler is satisfied at compile time.
var _ yaml.Marshaler = probeHarvesterYAML{}

// sortedExtraBlockNames returns Extra keys in deterministic order (for tests / callers).
func sortedExtraBlockNames(extra map[string][]DbEndpointConfig) []string {
	names := make([]string, 0, len(extra))
	for name := range extra {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}
