/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package syntax

import (
	"slices"
	"strings"

	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/pkg/util"
)

// SpiderChecker TODO
func (c CreateTableResult) SpiderChecker(spiderVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	if R.BuiltInRule.TableNameSpecification.KeyWord {
		r.ParseBultinRisk(func() (bool, string) {
			return KeyWordValidator(spiderVersion, c.TableName)
		})
	}
	if R.BuiltInRule.TableNameSpecification.SpeicalChar {
		r.ParseBultinBan(func() (bool, string) {
			return SpecialCharValidator(c.TableName)
		})
	}
	if c.IsCreateTableSelect {
		r.Trigger(SR.SpiderCreateTableRule.CreateWithSelect, "")
	}
	if c.ColCharsetNotEqTbCharset() {
		r.Trigger(SR.SpiderCreateTableRule.ColChasetNotEqTbChaset, "")
	}
	// when sql is create table like, no check shard key
	if !c.IsCreateTableLike {
		c.shardKeyChecker(r)
	}
	return r
}

// shardKeyChecker 分片键检查
// nolint
func (c CreateTableResult) shardKeyChecker(r *CheckerResult) {
	var commentSpecialShardKey bool
	var shardKeyCol string
	var err error
	var pubCols []string

	if len(c.CreateDefinitions.KeyDefs) == 0 {
		r.Trigger(SR.SpiderCreateTableRule.NoIndexExists, "")
		return
	}
	_, uks, keys := c.findTablesIndex()
	// 如果存在多个唯一健（含主键),多个唯一键都没有包含相同的字段也是不允许的
	logger.Info("uniqueKeys is %v,len is %d", uks, len(uks))
	if len(uks) > 1 {
		pubCols = findCommonColByKeys(uks)
		if len(pubCols) < 1 {
			r.Trigger(SR.SpiderCreateTableRule.NoPubColAtMultUniqueIndex, "")
			return
		}
	}
	tableComment := c.GetComment()
	logger.Info("tableComment is %s", tableComment)
	if lo.IsNotEmpty(tableComment) {
		// table comment 不为空的时候 先校验comment 格式是否合法
		legal, msg := c.validateSpiderComment(tableComment)
		if !legal {
			r.Trigger(SR.SpiderCreateTableRule.IllegalComment, msg)
			return
		}
		shardKeyCol, err = util.ParseGetShardKeyForSpider(tableComment)
		if err != nil {
			logger.Error("parse %s comment %s shard key failed %s", c.TableName, tableComment, err.Error())
			return
		}
		commentSpecialShardKey = true
	}
	// 如果table comment 为空,表示没有指定shard key,或table comnent 没有指定shardkey 由中控自主选择
	if !commentSpecialShardKey {
		switch {
		case len(uks) == 1:
			return
		case len(uks) > 1:
			// 如果没有显示的指定shard key,多个唯一键必须要包含相同的字段，且是第一个字段
			pubPreCols := findCommonPreColByKeys(uks)
			if len(pubPreCols) != 1 {
				r.Trigger(SR.SpiderCreateTableRule.NoPubColAtMultUniqueIndex, "")
				return
			}
		case len(keys) > 1:
			// 如果没有唯一索引，如果包含多个普通索引，则必须指定shard_key,否则需要报错
			r.Trigger(SR.SpiderCreateTableRule.MustSpecialShardKeyOnlyHaveCommonIndex, "")
			return
		}
	} else {
		// 如果存在索引,但是shard key不属于任何索引
		if !c.shardKeyIsIndex(shardKeyCol) {
			r.Trigger(SR.SpiderCreateTableRule.ShardKeyNotIndex, "")
			return
		}
		switch {
		case len(uks) == 1:
			if !c.shardKeyExistInKeys(shardKeyCol, uks) {
				r.Trigger(SR.SpiderCreateTableRule.NoPubColAtMultUniqueIndex, shardKeyCol)
				return
			}
		// 如果存在 一个或者多个唯一索引(包含主键)
		case len(uks) > 1:
			// shard_key只能是其中的共同部分；否则无法建表；
			if !slices.Contains(pubCols, shardKeyCol) {
				r.Trigger(SR.SpiderCreateTableRule.NoPubColAtMultUniqueIndex, shardKeyCol)
				return
			}
		// 如果只存在多个普通索引，shard_key只能是其中任意一个的一部分
		case len(uks) < 1 && len(keys) > 1:
			if !c.shardKeyExistInKeys(shardKeyCol, keys) {
				r.Trigger(SR.SpiderCreateTableRule.MustSpecialShardKeyOnlyHaveCommonIndex, shardKeyCol)
				return
			}
		}
		shardKeyColDef := c.getColDef(shardKeyCol)
		// 如果shard key 列允许为null
		if shardKeyColDef.Nullable {
			r.Trigger(SR.SpiderCreateTableRule.ShardKeyNotNull, shardKeyColDef.ColName)
		}
	}
}

// findTablesIndex 寻找表中的主键,唯一键,普通索引
func (c CreateTableResult) findTablesIndex() (hasPk bool, uks []KeyDef, keys []KeyDef) {
	hasPk = false
	for _, key := range c.CreateDefinitions.KeyDefs {
		switch {
		case key.PrimaryKey:
			hasPk = true
			uks = append(uks, key)
		case key.UniqueKey:
			uks = append(uks, key)
		default:
			keys = append(keys, key)
		}
	}
	return hasPk, uks, keys
}

// findCommonColByKeys 寻找多个唯一键中的公共列
func findCommonColByKeys(keys []KeyDef) (cols []string) {
	colmap := make(map[string]int)
	for _, key := range keys {
		for _, keyPart := range key.KeyParts {
			colmap[keyPart.ColName]++
		}
	}
	for colName, count := range colmap {
		if count == len(keys) {
			cols = append(cols, colName)
		}
	}
	return cols
}

// findCommonPreColByKeys 寻找多个唯一键中的公共前缀列
func findCommonPreColByKeys(keys []KeyDef) (cols []string) {
	for _, key := range keys {
		if len(key.KeyParts) > 0 {
			cols = append(cols, key.KeyParts[0].ColName)
		}
	}
	return lo.Uniq(cols)
}

func (c CreateTableResult) validateSpiderComment(comment string) (legal bool, prompt string) {
	ret := util.ParseGetSpiderUserComment(comment)
	switch ret {
	case 0:
		return true, "OK"
	case 1:
		return false, "SQL CREATE TABLE WITH ERROR TABLE COMMENT"
	case 2:
		return false, "UNSUPPORT CREATE TABLE WITH ERROR COMMENT"
	}
	return false, ""
}

// shardKeyIsIndex TODO
func (c CreateTableResult) shardKeyIsIndex(shardKeyCol string) bool {
	for _, v := range c.CreateDefinitions.KeyDefs {
		for _, k := range v.KeyParts {
			if strings.Compare(k.ColName, shardKeyCol) == 0 {
				logger.Info("the shard key %s is index", shardKeyCol)
				return true
			}
		}
	}
	return false
}

func (c CreateTableResult) shardKeyExistInKeys(shardKeyCol string, keys []KeyDef) bool {
	for _, v := range keys {
		for _, k := range v.KeyParts {
			if strings.Compare(k.ColName, shardKeyCol) == 0 {
				return true
			}
		}
	}
	return false
}

func (c CreateTableResult) getColDef(colName string) (colDef ColDef) {
	for _, col := range c.CreateDefinitions.ColDefs {
		if strings.Compare(col.ColName, colName) == 0 {
			colDef = col
			break
		}
	}
	return colDef
}
