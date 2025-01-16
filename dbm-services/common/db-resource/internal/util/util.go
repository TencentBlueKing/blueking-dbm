/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package util TODO
package util

import (
	"fmt"
	"hash/crc32"
	"regexp"
	"strings"

	"github.com/samber/lo"
)

// CleanOsName clean os name
func CleanOsName(osName string) string {
	tr := regexp.MustCompile(`(?i)^tencent`)
	if tr.MatchString(strings.TrimSpace(osName)) {
		r := regexp.MustCompile(`\d+(.\d)+`)
		return "tliunx-" + r.FindString(osName)
	}
	wr := regexp.MustCompile(`(?i)Windows\s*Server\s*\d\d\d\d`)
	if wr.MatchString(osName) {
		return strings.TrimSpace(strings.ReplaceAll(wr.FindString(osName), " ", ""))
	}
	return osName
}

// TransInnerSwitchIpAsNetDeviceId  trans inner switch ip as net_device_id
func TransInnerSwitchIpAsNetDeviceId(inner_switch_ips string) string {
	if lo.IsEmpty(inner_switch_ips) {
		return ""
	}
	sep := regexp.MustCompile(";|,")
	ips := sep.Split(inner_switch_ips, -1)
	crc32q := crc32.MakeTable(0xD5828281)
	fakeNetDeviceIdList := []string{}
	for _, ip := range ips {
		fakeNetDeviceIdList = append(fakeNetDeviceIdList, fmt.Sprintf("%08x", crc32.Checksum([]byte(ip), crc32q)))
	}
	return strings.Join(lo.Uniq(fakeNetDeviceIdList), ",")
}
