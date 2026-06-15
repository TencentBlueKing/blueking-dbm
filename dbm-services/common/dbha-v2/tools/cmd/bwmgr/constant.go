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

// Package main implements the bwmgr command-line entrypoint.
package main

import (
	"dbm-services/common/dbha-v2/tools/internal/bwmgr/config"
	"dbm-services/common/dbha-v2/tools/internal/bwmgr/handler"
)

const (
	cmdUseRoot    = "bwmgr"
	cmdUseList    = "list"
	cmdUseAdd     = "add"
	cmdUseUpdate  = "update"
	cmdUseDelete  = "delete"
	cmdUseVersion = "version"
)

const (
	cmdShortRoot    = "DBHA Black-White List Manager"
	cmdShortList    = "List black-white list entries"
	cmdShortAdd     = "Add a new black-white list entry"
	cmdShortUpdate  = "Update an existing black-white list entry"
	cmdShortDelete  = "Delete a black-white list entry"
	cmdShortVersion = "Print version information of bwmgr"
)

const (
	cmdLongRoot   = "A command-line tool for managing DBHA black-white list configurations via HTTP API."
	cmdLongList   = "List all black-white list entries with optional filtering"
	cmdLongAdd    = "Add a new entry to the black-white list"
	cmdLongUpdate = "Update an existing entry in the black-white list. " +
		"At least one of (id, bk-biz-id, cluster-id, cluster-name) is required " +
		"to locate the entry, and at least one of (switch-version, status) is " +
		"required to update."
	cmdLongDelete = "Delete an entry from the black-white list. At least one of " +
		"(id, bk-biz-id, cluster-id, cluster-name) is required to prevent " +
		"unintended full-table deletion."
)

const (
	flagConfig        = "config"
	flagConfigShort   = "c"
	flagAPIEndpoint   = config.CmdFlagAPIEndpoint
	flagAPIBkCloudID  = config.CmdFlagAPIBkCloudID
	flagAPIToken      = config.CmdFlagAPIToken
	flagAPITimeout    = config.CmdFlagAPITimeout
	flagID            = "id"
	flagBkBizID       = "bk-biz-id"
	flagBkCloudID     = "bk-cloud-id"
	flagClusterID     = "cluster-id"
	flagClusterName   = "cluster-name"
	flagSwitchVersion = "switch-version"
	flagStatus        = "status"
	flagOutput        = "output"
	flagOutputFile    = "output-file"
	flagYes           = "yes"
)

const (
	defaultConfigFilePath = "./etc/bwmgr.yaml"
	defaultIntValue       = 0
	defaultStringValue    = ""
	defaultFalseValue     = false
	defaultOutput         = handler.OutputFormatTable
)

const (
	defaultSwitchVersion = "v2"
	defaultStatus        = "enabled"
)

const (
	confirmPromptFormat = "%s [y/N]: "
	confirmChoiceY      = "y"
	confirmChoiceYes    = "yes"
)

const (
	flagUsageConfig         = "Path to configuration file"
	flagUsageAPIEndpoint    = "API endpoint (override config file and " + config.EnvAPIEndpoint + ")"
	flagUsageAPIBkCloudID   = "API bk_cloud_id (override config file and " + config.EnvAPIBkCloudID + ")"
	flagUsageAPIToken       = "API token (override config file and " + config.EnvAPIToken + ")"
	flagUsageAPITimeout     = "API timeout duration, e.g. 30s (override config file and " + config.EnvAPITimeout + ")"
	flagUsageListBizID      = "Filter by business ID"
	flagUsageListCloudID    = "Filter by cloud ID"
	flagUsageListClusterID  = "Filter by cluster ID"
	flagUsageListCluster    = "Filter by cluster name"
	flagUsageListSwitch     = "Filter by switch version (v1/v2)"
	flagUsageListStatus     = "Filter by status (enabled/disabled)"
	flagUsageListOutput     = "Output mode (table/json)"
	flagUsageListOutputFile = "Output file path for file mode"
	flagUsageBizID          = "Business ID"
	flagUsageBizIDRequired  = "Business ID (required)"
	flagUsageCloudID        = "Cloud ID"
	flagUsageCloudDefault   = "Cloud ID (default: 0 for direct region)"
	flagUsageClusterID      = "Cluster ID"
	flagUsageClusterIDReq   = "Cluster ID (required)"
	flagUsageClusterName    = "Cluster name"
	flagUsageClusterNameReq = "Cluster name (required)"
	flagUsageSwitchVersion  = "Switch version (v1/v2)"
	flagUsageSwitchDefault  = "Switch version (v1/v2, default: v2)"
	flagUsageStatus         = "Status (enabled/disabled)"
	flagUsageStatusDefault  = "Status (enabled/disabled, default: enabled)"
	flagUsageYesRisky       = "Skip confirmation prompt for risky operations"
	flagUsageYesDelete      = "Skip confirmation prompt"
	flagUsageEntryID        = "Entry ID"
)

const (
	versionProductName = "DBHA bwmgr"
	versionBlankLine   = ""
	versionNotesTitle  = "Switch version notes:"
	versionV1Title     = "  v1 - Legacy switch version managed by ha-module(v1)."
	versionV1Enabled   = "       When a v2 enabled entry exists for the same cluster,"
	versionV1Skip      = "       v1 will skip switching for that cluster."
	versionV2Title     = "  v2 - New switch version managed by dbha-v2."
	versionV2Enabled   = "       Only entries with switch_version=v2 AND status=enabled"
	versionV2Honored   = "       are honored as the white list by ha-module(v1)."
)

const (
	errLoadConfigFormat        = "failed to load config: %v"
	logExecuteCommandErrFormat = "failed to execute bwmgr command, errmsg: %s"
)
