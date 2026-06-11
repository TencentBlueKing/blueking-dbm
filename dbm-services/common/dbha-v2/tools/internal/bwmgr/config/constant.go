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

// Package config loads and validates bwmgr configuration.
package config

import "time"

const (
	// EnvAPIEndpoint is the environment variable key for the API endpoint override.
	EnvAPIEndpoint = "BWMGR_API_ENDPOINT"
	// EnvAPIBkCloudID is the environment variable key for the API bk_cloud_id override.
	EnvAPIBkCloudID = "BWMGR_API_BK_CLOUD_ID"
	// EnvAPITimeout is the environment variable key for the API timeout override.
	EnvAPITimeout = "BWMGR_API_TIMEOUT"
	// EnvAPIToken is the environment variable key for the API token override.
	EnvAPIToken = "BWMGR_API_TOKEN"
)

const (
	// CmdFlagAPIEndpoint is the command flag key for the API endpoint override.
	CmdFlagAPIEndpoint = "api-endpoint"
	// CmdFlagAPIBkCloudID is the command flag key for the API bk_cloud_id override.
	CmdFlagAPIBkCloudID = "api-bk-cloud-id"
	// CmdFlagAPITimeout is the command flag key for the API timeout override.
	CmdFlagAPITimeout = "api-timeout"
	// CmdFlagAPIToken is the command flag key for the API token override.
	CmdFlagAPIToken = "api-token"
)

const (
	defaultAPIEndpoint  = "http://127.0.0.1:8090/blackwhitelist/"
	defaultAPIBkCloudID = 0
	defaultAPITimeout   = 30 * time.Second
	defaultAPIToken     = ""
)

const (
	pathSeparator = "/"
	dirPerm       = 0755
	filePerm      = 0644
)

const (
	errReadConfigFormat      = "failed to read config file: %v"
	errParseConfigFormat     = "failed to parse config: %v"
	errAPIEndpointRequired   = "API endpoint is required"
	errAPIBkCloudIDInvalid   = "API bk_cloud_id must be greater than or equal to 0"
	errAPITokenRequired      = "API token is required"
	errMarshalConfigFormat   = "failed to marshal default config: %v"
	errCreateConfigDirFormat = "failed to create config directory: %v"
	errWriteConfigFileFormat = "failed to write config file: %v"
)
