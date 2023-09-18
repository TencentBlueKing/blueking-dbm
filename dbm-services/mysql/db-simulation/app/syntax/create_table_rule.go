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
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/pkg/util"
)

// SpiderChecker TODO
func (c CreateTableResult) SpiderChecker(spiderVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	if R.BuiltInRule.TableNameSpecification.KeyWord {
		r.ParseBultinBan(func() (bool, string) {
			return KeyWordValidator(spiderVersion, c.TableName)
		})
	}
	if R.BuiltInRule.TableNameSpecification.SpeicalChar {
		r.ParseBultinBan(func() (bool, string) {
			return SpecialCharValidator(c.TableName)
		})
	}
	r.Parse(SR.SpiderCreateTableRule.CreateTbLike, !c.IsCreateTableLike, "")
	r.Parse(SR.SpiderCreateTableRule.CreateWithSelect, !c.IsCreateTableSelect, "")
	r.Parse(SR.SpiderCreateTableRule.ColChasetNotEqTbChaset, c.ColCharsetEqTbCharset(), "")
	ilegal, msg := c.ValidateSpiderComment()
	r.Parse(SR.SpiderCreateTableRule.IllegalComment, ilegal, msg)
	// comment 合法且非空
	if ilegal {
		b_shardKeyIsIndex := c.ShardKeyIsIndex()
		r.Parse(SR.SpiderCreateTableRule.ShardKeyNotIndex, b_shardKeyIsIndex, "")
		if !b_shardKeyIsIndex {
			r.Parse(SR.SpiderCreateTableRule.ShardKeyNotPk, c.ShardKeyIsNotPrimaryKey(), "")
		}
	}
	return
}

// Checker TODO
func (c CreateTableResult) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	r.Parse(R.CreateTableRule.SuggestEngine, c.GetEngine(), "")
	r.Parse(R.CreateTableRule.SuggestBlobColumCount, c.BlobColumCount(), "")
	if R.BuiltInRule.TableNameSpecification.KeyWord {
		r.ParseBultinBan(func() (bool, string) {
			return KeyWordValidator(mysqlVersion, c.TableName)
		})
	}
	if R.BuiltInRule.TableNameSpecification.SpeicalChar {
		r.ParseBultinBan(func() (bool, string) {
			return SpecialCharValidator(c.TableName)
		})
	}
	return
}

// BlobColumCount TODO
// ExceedMaxBlobColum 检查创建表时blob/text字段最大数，是否超过
func (c CreateTableResult) BlobColumCount() (blobColumCount int) {
	for _, v := range c.CreateDefinitions.ColDefs {
		if v.Type == "blob" {
			blobColumCount++
		}
	}
	logger.Info("blobColumCount:%d", blobColumCount)
	return
}

// ShardKeyIsIndex TODO
func (c CreateTableResult) ShardKeyIsIndex() bool {
	cmt := c.GetComment()
	if cmutil.IsEmpty(cmt) {
		return len(c.CreateDefinitions.KeyDefs) > 0
	}
	if !strings.Contains(cmt, "shard_key") {
		return true
	}
	sk, err := util.ParseGetShardKeyForSpider(cmt)
	if err != nil {
		logger.Error("parse get shardkey %s", err.Error())
		return false
	}
	for _, v := range c.CreateDefinitions.KeyDefs {
		for _, k := range v.KeyParts {
			if strings.Compare(k.ColName, sk) == 0 {
				return true
			}
		}
	}
	return false
}

// ShardKeyIsNotPrimaryKey TODO
func (c CreateTableResult) ShardKeyIsNotPrimaryKey() bool {
	cmt := c.GetComment()
	logger.Info("will check %s ,ShardKeyIsNotPrimaryKey", cmt)
	if cmutil.IsEmpty(cmt) {
		return true
	}
	if !strings.Contains(cmt, "shard_key") {
		return true
	}
	sk, err := util.ParseGetShardKeyForSpider(cmt)
	if err != nil {
		logger.Error("parse get shardkey %s", err.Error())
		return false
	}
	for _, v := range c.CreateDefinitions.ColDefs {
		if v.PrimaryKey {
			logger.Info("get sk %s,pk:%s", sk, v.ColName)
			if strings.Compare(sk, v.ColName) == 0 {
				return true
			}
		}
	}
	return false
}

// GetValFromTbOptions TODO
func (c CreateTableResult) GetValFromTbOptions(key string) (val string) {
	for _, tableOption := range c.TableOptions {
		if tableOption.Key == key {
			val = tableOption.Value.(string)
		}
	}
	logger.Info("%s:%s", key, val)
	return val
}

// GetEngine TODO
func (c CreateTableResult) GetEngine() (engine string) {
	if v, ok := c.TableOptionMap["engine"]; ok {
		return v.(string)
	}
	return ""
}

// GetComment TODO
// comment
func (c CreateTableResult) GetComment() (engine string) {
	if v, ok := c.TableOptionMap["comment"]; ok {
		return v.(string)
	}
	return ""
}

// GetTableCharset TODO
// character_set
func (c CreateTableResult) GetTableCharset() (engine string) {
	if v, ok := c.TableOptionMap["character_set"]; ok {
		return v.(string)
	}
	return ""
}

// ValidateSpiderComment TODO
func (c CreateTableResult) ValidateSpiderComment() (bool, string) {
	comment := c.GetComment()
	if cmutil.IsEmpty(comment) {
		return true, ""
	}
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

// GetAllColCharsets TODO
func (c CreateTableResult) GetAllColCharsets() (charsets []string) {
	for _, colDef := range c.CreateDefinitions.ColDefs {
		if !cmutil.IsEmpty(colDef.CharacterSet) {
			charsets = append(charsets, colDef.CharacterSet)
		}
	}
	return cmutil.RemoveDuplicate(charsets)
}

// ColCharsetEqTbCharset TODO
func (c CreateTableResult) ColCharsetEqTbCharset() bool {
	colCharsets := c.GetAllColCharsets()
	fmt.Println("colCharsets", colCharsets, len(colCharsets))
	if len(colCharsets) == 0 {
		return true
	}
	if len(colCharsets) > 1 {
		return false
	}
	if strings.Compare(strings.ToUpper(colCharsets[0]), c.GetTableCharset()) == 0 {
		return true
	}
	return false
}
