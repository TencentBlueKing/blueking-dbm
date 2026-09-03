/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package agent

import (
	"regexp"
	"strings"
)

// storageDeviceJSONPath 生成 storage_device 的 MySQL JSON Path。
// 挂载点含 "/"，必须用双引号包起来，否则 JSON_EXTRACT 永远返回 NULL。
//
//	storageDeviceJSONPath("/data")            → $."/data"
//	storageDeviceJSONPath("/data", "size")    → $."/data".size
//	storageDeviceJSONPath("/data", "disk_type") → $."/data".disk_type
func storageDeviceJSONPath(mountPoint string, fields ...string) string {
	path := `$."` + mountPoint + `"`
	for _, field := range fields {
		path += "." + field
	}
	return path
}

// storageDeviceJSONFields 挂载点对象上的已知字段。
// Agent 常把这些字段写成文件系统路径（/data/size），需要还原成 JSON Path。
var storageDeviceJSONFields = []string{"size", "disk_type", "file_type", "disk_id"}

var storageDeviceExtractRe = regexp.MustCompile(
	`(?i)JSON_EXTRACT\s*\(\s*` + "`?" + `storage_device` + "`?" + `\s*,\s*(['"])([^'"]*)['"]\s*\)`,
)

// rewriteStorageDeviceJSONExtract 把 Agent 写错的 JSON_EXTRACT 路径改成合法 MySQL JSON Path。
// 常见错法：
//
//	JSON_EXTRACT(storage_device, '/data/size')     → '$."/data".size'
//	JSON_EXTRACT(storage_device, '$./data.size')   → '$."/data".size'
//
// 已经是 $."/data".size 的路径原样保留。
func rewriteStorageDeviceJSONExtract(sql string) (rewritten string, changed bool) {
	rewritten = storageDeviceExtractRe.ReplaceAllStringFunc(sql, func(match string) string {
		sub := storageDeviceExtractRe.FindStringSubmatch(match)
		if len(sub) != 3 {
			return match
		}
		path := sub[2]
		normalized := normalizeStorageDeviceJSONPath(path)
		if normalized == path {
			return match
		}
		changed = true
		// 规范路径恒含双引号（$."/data".size），必须用单引号包一层，不能复用模型原引号。
		return "JSON_EXTRACT(storage_device, '" + strings.ReplaceAll(normalized, "'", "''") + "')"
	})
	return rewritten, changed
}

// normalizeStorageDeviceJSONPath 把各种错写的路径归一成 $."/data".size 这种形式。
func normalizeStorageDeviceJSONPath(path string) string {
	path = strings.TrimSpace(path)
	if path == "" {
		return path
	}
	// 已经用双引号包了挂载点：$."/data" 或 $."/data".size
	if strings.HasPrefix(path, `$.`) && strings.Contains(path, `"`) {
		return path
	}
	// 文件系统写法：/data/size、/data/disk_type、/data
	if strings.HasPrefix(path, "/") {
		return filesystemPathToJSONPath(path)
	}
	// 漏了引号：$./data.size、$./data
	if strings.HasPrefix(path, "$./") {
		return quoteUnquotedMountPath(strings.TrimPrefix(path, "$."))
	}
	return path
}

func filesystemPathToJSONPath(path string) string {
	for _, field := range storageDeviceJSONFields {
		suffix := "/" + field
		if strings.HasSuffix(path, suffix) {
			mount := strings.TrimSuffix(path, suffix)
			if mount != "" {
				return storageDeviceJSONPath(mount, field)
			}
		}
	}
	return storageDeviceJSONPath(path)
}

func quoteUnquotedMountPath(rest string) string {
	dot := strings.Index(rest, ".")
	if dot < 0 {
		return storageDeviceJSONPath(rest)
	}
	mount := rest[:dot]
	fields := strings.Split(rest[dot+1:], ".")
	return storageDeviceJSONPath(mount, fields...)
}
