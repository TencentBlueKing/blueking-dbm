/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package util

import (
	"errors"
	"fmt"
	"strings"

	util "dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// ParseGetShardKeyForSpider TODO
func ParseGetShardKeyForSpider(tableComment string) (string, error) {
	pos := strings.Index(tableComment, "shard_key")
	if pos == -1 {
		return "", errors.New("not found shard_key")
	}
	pos += len("shard_key")

	// ignore the space
	for pos < len(tableComment) && (tableComment[pos] == ' ' || tableComment[pos] == '\t') {
		pos++
	}

	// find the beginning "
	if pos < len(tableComment) && tableComment[pos] == '"' {
		pos++
	} else {
		return "", errors.New("parse error")
	}

	// find the ending "
	end := strings.Index(tableComment[pos:], "\"")
	if end == -1 {
		return "", errors.New("parse error")
	}

	end += pos

	if end-pos <= 0 {
		return "", errors.New("parse error")
	}

	len := uint(end - pos)
	keyBuf := make([]byte, len+1)
	copy(keyBuf, tableComment[pos:end])
	return string(keyBuf), nil
}

const (
	// TCADMIN_PARSE_TABLE_COMMENT_OK TODO
	TCADMIN_PARSE_TABLE_COMMENT_OK = 0
	// TCADMIN_PARSE_TABLE_COMMENT_ERROR TODO
	TCADMIN_PARSE_TABLE_COMMENT_ERROR = 1
	// TCADMIN_PARSE_TABLE_COMMENT_UNSUPPORTED TODO
	TCADMIN_PARSE_TABLE_COMMENT_UNSUPPORTED = 2
	// TRIM TODO
	TRIM = 0
	// PARSE_KEY TODO
	PARSE_KEY = 1
	// PARSE_VALUE TODO
	PARSE_VALUE = 2
	// PARSE_DONE TODO
	PARSE_DONE = 3
)

// ParseGetSpiderUserComment TODO
func ParseGetSpiderUserComment(tableComment string) (ret int) {
	bs := []byte(tableComment)
	keywordBuf := []byte{}
	valueBuf := []byte{}
	stage := 0
	get_key := 0
	get_value := 0
	pos := 0
	for {
		switch stage {
		case TRIM:
			if pos >= len(bs)-1 {
				goto parseAllDone
			}
			if bs[pos] == 0x20 || bs[pos] == 0x09 {
				pos++
				continue
			}
			if get_key != 0 && get_value != 0 {
				stage = PARSE_DONE
			} else if get_key != 0 {
				stage = PARSE_VALUE
			} else {
				stage = PARSE_KEY
			}
		case PARSE_KEY:
			for {
				keywordBuf = append(keywordBuf, bs[pos])
				pos++
				if bs[pos] == 0x20 || pos >= len(bs)-1 {
					break
				}
			}
			kw := string(keywordBuf)
			if !validateCommentKeyWord(kw) {
				logger.Info(" illegal keyword:%s", kw)
				return TCADMIN_PARSE_TABLE_COMMENT_UNSUPPORTED
			}
			get_key = 1
			stage = TRIM
			keywordBuf = []byte{}
		case PARSE_VALUE:
			if bs[pos] != 0x22 {
				return TCADMIN_PARSE_TABLE_COMMENT_ERROR
			}
			pos++
			for {
				if bs[pos] == 0x22 || pos >= len(bs)-1 {
					break
				}
				valueBuf = append(valueBuf, bs[pos])
				pos++
			}
			pos++
			get_value = 1
			stage = TRIM
			valueBuf = []byte{}
		case PARSE_DONE:
			if pos >= len(bs)-1 {
				return 0
			}
			fmt.Println(bs[pos])
			if bs[pos] == 0x2c {
				stage = TRIM
				get_key = 0
				get_value = 0
				pos++
			} else {
				return TCADMIN_PARSE_TABLE_COMMENT_ERROR
			}
		default:
			continue
		}
	}
parseAllDone:
	return ret
}

// validateCommentKeyWord TODO
func validateCommentKeyWord(keyword string) bool {
	return util.StringsHas([]string{"shard_count", "shard_func", "shard_type", "shard_key", "config_table"}, keyword)
}
