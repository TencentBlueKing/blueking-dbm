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

// probeHarvesterYAML uses string for Interval/Timeout in YAML output; reuses DbEndpointConfig for Endpoints.
type probeMySQLHarvesterYAML struct {
	User              string             `yaml:"user"`
	Password          string             `yaml:"password"`
	Interval          string             `yaml:"interval"`
	HeartbeatInterval string             `yaml:"heartbeatInterval"`
	ReplDelayInterval string             `yaml:"replDelayInterval"`
	Timeout           string             `yaml:"timeout"`
	Endpoints         []DbEndpointConfig `yaml:"endpoints"`
}

type probeRedisHarvesterYAML struct {
	User      string             `yaml:"user"`
	Password  string             `yaml:"password"`
	Interval  string             `yaml:"interval"`
	Timeout   string             `yaml:"timeout"`
	Endpoints []DbEndpointConfig `yaml:"endpoints"`
}

type probeHarvesterYAML struct {
	MySQL           *probeMySQLHarvesterYAML `yaml:"mysql,omitempty"`
	MySQLProxyAdmin *probeMySQLHarvesterYAML `yaml:"mysqlProxyAdmin,omitempty"`
	Redis           *probeRedisHarvesterYAML `yaml:"redis,omitempty"`
}
