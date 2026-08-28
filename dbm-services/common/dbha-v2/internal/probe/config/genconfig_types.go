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
//
// The blocks the probe owns locally (ServiceID, Client, Admin) are pointers with omitempty and
// are only filled in by the options in genconfig.go, so a plain gen-config renders exactly what
// it always did instead of gaining empty blocks.
type probeYAML struct {
	Name      string             `yaml:"name"`
	Version   string             `yaml:"version"`
	ServiceID string             `yaml:"serviceID,omitempty"`
	PidFile   string             `yaml:"pidFile"`
	Reporter  probeReporterYAML  `yaml:"reporter"`
	Client    *probeClientYAML   `yaml:"client,omitempty"`
	Admin     *probeAdminYAML    `yaml:"admin,omitempty"`
	Harvester probeHarvesterYAML `yaml:"harvester"`
	Log       LogConfig          `yaml:"log"`
}

// probeReporterYAML has ConnTimeout as string for YAML output (e.g. "5s"); ReporterConfig uses time.Duration.
type probeReporterYAML struct {
	Name        string `yaml:"name"`
	Endpoint    string `yaml:"endpoint"`
	DataID      uint64 `yaml:"dataID"`
	ConnTimeout string `yaml:"connTimeout"`
	// omitempty: admin does not send it; 0 keeps existing YAML unchanged.
	BkCloudID int `yaml:"bkCloudID,omitempty"`
	// omitempty: omit when 0 so Linux YAML stays byte-identical.
	LocalSocketPort uint `yaml:"localSocketPort,omitempty"`
}

// probeClientYAML mirrors ClientConfig, and probeAdminYAML mirrors AdminConfig.
//
// They exist because of a convention this file already follows for the harvester blocks:
// durations render as strings here ("5s"), while the Configuration side uses time.Duration.
// Reusing the Configuration types directly would write durations as their nanosecond count,
// which is both unreadable and not what an operator editing the file expects.
//
// Every field carries omitempty, which matters most for the durations: a zero time.Duration
// renders to the empty string and viper refuses to parse `pingTime: ""` back into a duration,
// so an omitted key is the only correct rendering of a zero value. Omitting it round-trips
// cleanly, since a missing key parses back to zero.
//
// TestMirrorStructsCoverSource keeps these in step with the types they mirror.
type probeClientYAML struct {
	PingTime                     string `yaml:"pingTime,omitempty"`
	PingTimeout                  string `yaml:"pingTimeout,omitempty"`
	MaxReceiveMessageSize        int    `yaml:"maxReceiveMessageSize,omitempty"`
	MaxSendMessageSize           int    `yaml:"maxSendMessageSize,omitempty"`
	ReceiverReconnectInterval    string `yaml:"receiverReconnectInterval,omitempty"`
	ReceiverMaxReconnectAttempts int    `yaml:"receiverMaxReconnectAttempts,omitempty"`
}

type probeAdminYAML struct {
	Endpoints    []string `yaml:"endpoints,omitempty"`
	BkCloudID    uint64   `yaml:"bkCloudID,omitempty"`
	LocalIP      string   `yaml:"localIP,omitempty"`
	SyncInterval string   `yaml:"syncInterval,omitempty"`
}

// probeHarvesterYAML uses string for Interval/Timeout in YAML output; reuses DbEndpointConfig for Endpoints.
type probeMySQLHarvesterYAML struct {
	User              string             `yaml:"user"`
	Password          string             `yaml:"password"`
	Interval          string             `yaml:"interval"`
	HeartbeatInterval string             `yaml:"heartbeatInterval,omitempty"`
	ReplDelayInterval string             `yaml:"replDelayInterval,omitempty"`
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
