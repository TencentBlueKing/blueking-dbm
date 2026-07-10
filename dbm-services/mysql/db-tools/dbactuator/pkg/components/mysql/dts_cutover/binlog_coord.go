/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dts_cutover

import (
	"strconv"
	"strings"
	"unicode"
)

// BinlogCoord DTS sync_status 位点解析结果。
// 示例输入："(binlog20000.002894, 12105)" → File=binlog20000.002894, Position=12105
type BinlogCoord struct {
	File     string
	Position int64
}

// ParseBinlogCoord 解析 DTS sync_status 中的 binlog 位点字符串。
// 期望形态："(binlog20000.002894, 12105)" 或 "binlog20000.002894, 12105"。
// 空串 / 缺逗号 / position 非整数 → ok=false。
func ParseBinlogCoord(raw string) (coord BinlogCoord, ok bool) {
	text := strings.TrimSpace(raw)
	if text == "" {
		return BinlogCoord{}, false
	}
	if strings.HasPrefix(text, "(") && strings.HasSuffix(text, ")") {
		text = strings.TrimSpace(text[1 : len(text)-1])
	}
	comma := strings.Index(text, ",")
	if comma < 0 {
		return BinlogCoord{}, false
	}
	fileName := strings.TrimSpace(text[:comma])
	posText := strings.TrimSpace(text[comma+1:])
	if fileName == "" || posText == "" {
		return BinlogCoord{}, false
	}
	pos, err := strconv.ParseInt(posText, 10, 64)
	if err != nil || pos < 0 {
		return BinlogCoord{}, false
	}
	return BinlogCoord{File: fileName, Position: pos}, true
}

// binlogFileSeq 取 binlog 文件序号：优先用最后一个 '.' 后的数字（如 binlog.000002 / binlog20000.002894）。
func binlogFileSeq(fileName string) (int64, bool) {
	i := strings.LastIndex(fileName, ".")
	if i < 0 || i+1 >= len(fileName) {
		return 0, false
	}
	suffix := fileName[i+1:]
	for _, r := range suffix {
		if !unicode.IsDigit(r) {
			return 0, false
		}
	}
	n, err := strconv.ParseInt(suffix, 10, 64)
	if err != nil {
		return 0, false
	}
	return n, true
}

// CompareBinlogCoord 比较两个位点：-1 a<b，0 相等，1 a>b。
// 先比 file 序号，同文件再比 position。
func CompareBinlogCoord(a, b BinlogCoord) int {
	aSeq, aOk := binlogFileSeq(a.File)
	bSeq, bOk := binlogFileSeq(b.File)
	if aOk && bOk {
		if aSeq < bSeq {
			return -1
		}
		if aSeq > bSeq {
			return 1
		}
	} else if a.File != b.File {
		// 无法解析序号时退化为字符串序，避免误判为相等
		if a.File < b.File {
			return -1
		}
		return 1
	}
	if a.Position < b.Position {
		return -1
	}
	if a.Position > b.Position {
		return 1
	}
	return 0
}

// IsCaughtUpToSnapshot cutover 持锁复核用的位点条件。
//
// 部分表锁下实时 master 会因未迁移表持续前进，不能用「实时 master≥syncer」。
// 正确条件：SBM==0 且 syncer >= 加锁瞬间的 master 快照（file/pos）。
// 数据一致性依赖编排中已完成的 checksum；非法/空位点串视为未就绪。
func IsCaughtUpToSnapshot(syncerBinlog string, snapshot BinlogCoord, sbm int) bool {
	if sbm != 0 {
		return false
	}
	syncer, ok := ParseBinlogCoord(syncerBinlog)
	if !ok {
		return false
	}
	return CompareBinlogCoord(syncer, snapshot) >= 0
}
