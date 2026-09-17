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

	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/logger"
)

// Checker type create table checker
func (c CreateTableResult) Checker(mysqlVersion string) (r *CheckerResult) {
	return c.checkWithClusterEngines(mysqlVersion, nil)
}

func (c CreateTableResult) checkWithClusterEngines(mysqlVersion string, clusterDefaultEngines []string) (r *CheckerResult) {
	r = &CheckerResult{
		ObjName: c.TableName,
	}
	parseCreateTableEngineRule(r, c.GetEngine(), clusterDefaultEngines)
	r.Parse(R.CreateTableRule.SuggestBlobColumCount, c.BlobColumCount(), "")
	if R.BuiltInRule.TableNameSpecification.KeyWord {
		r.ParseBuiltinRisk(func() (bool, string) {
			return KeyWordValidator(mysqlVersion, c.TableName)
		})
	}
	if R.BuiltInRule.TableNameSpecification.SpecialChar {
		r.ParseBuiltinBan(func() (bool, string) {
			return SpecialCharValidator(c.TableName)
		})
	}
	r.ParseBuiltinBan(c.JsonColumInvalidDefaultCheck)
	return
}

// BlobColumCount ExceedMaxBlobColum 检查创建表时blob/text字段最大数，是否超过
func (c CreateTableResult) BlobColumCount() (blobColumCount int) {
	for _, v := range c.CreateDefinitions.ColDefs {
		if v.Type == "blob" {
			blobColumCount++
		}
	}
	logger.Info("blobColumCount:%d", blobColumCount)
	return
}

// GetValFromTbOptions  get table option
func (c CreateTableResult) GetValFromTbOptions(key string) (val string) {
	val = optionStringValue(c.TableOptions, key)
	logger.Info("%s:%s", key, val)
	return val
}

// GetEngine get engine
func (c CreateTableResult) GetEngine() (engine string) {
	for k, v := range c.TableOptionMap {
		if strings.EqualFold(k, "engine") {
			if s, ok := v.(string); ok {
				return s
			}
		}
	}
	return c.GetValFromTbOptions("engine")
}

// GetComment get sql comment
func (c CreateTableResult) GetComment() (engine string) {
	if v, ok := c.TableOptionMap["comment"]; ok {
		return v.(string)
	}
	return ""
}

// GetTableCharset get character_set
func (c CreateTableResult) GetTableCharset() (engine string) {
	if v, ok := c.TableOptionMap["character_set"]; ok {
		return v.(string)
	}
	return ""
}

// GetAllColCharacterSets get columns defined charset
func (c CreateTableResult) GetAllColCharacterSets() (charSets []string) {
	haveDefaultCharSetTypes := []string{
		"timestamp", "time", "datetime", "date",
		"tinyblob", "blob", "mediumblob", "longblob",
		"string", "varchar", "json",
	}
	for _, colDef := range c.CreateDefinitions.ColDefs {
		// Mysql会对MYSQL_TYPE_TIME，MYSQL_TYPE_TIMESTAMP，MYSQL_TYPE_DATETIME这三种类型的字段默认设置字符集为latin1
		if lo.IsNotEmpty(colDef.CharacterSet) && !lo.Contains(haveDefaultCharSetTypes, colDef.DataType) {
			charSets = append(charSets, colDef.CharacterSet)
		}
	}
	return lo.Uniq(charSets)
}

// ColCharsetNotEqTbCharset 字段的字符集合和表的字符集合相同
func (c CreateTableResult) ColCharsetNotEqTbCharset() bool {
	colCharSets := c.GetAllColCharacterSets()
	if len(colCharSets) == 0 {
		return false
	}
	if len(colCharSets) > 1 {
		return true
	}
	tableDefineCharset := c.GetTableCharset()
	if lo.IsEmpty(tableDefineCharset) {
		return false
	}
	if strings.Compare(strings.ToLower(colCharSets[0]), strings.ToLower(tableDefineCharset)) == 0 {
		return false
	}
	return true
}

// JsonDataType JSON 数据类型常量
const JsonDataType = "json"

// JsonColumInvalidDefaultCheck 检查创建表时 json 字段是否设置了无效的默认值
// 无效的默认值包括：字符串 'null'（DEFAULT 'null'）、空字符串 ”（DEFAULT ”）
// 有效的默认值包括：DEFAULT NULL（NULL 关键字，MySQL 5.7 仅允许此形态；
// 8.0.13+ 还允许 DEFAULT (expr) 表达式形式，如 DEFAULT (JSON_ARRAY()))
//
// 实现说明：必须遍历完所有列再返回，避免因第一个 JSON 列合法而提前 return，
// 导致后续违规的 JSON 列被漏检。
func (c CreateTableResult) JsonColumInvalidDefaultCheck() (bool, string) {
	var invalidCols []string
	for _, colDef := range c.CreateDefinitions.ColDefs {
		if colDef.DataType == JsonDataType && colDef.HasInvalidJsonDefault() {
			invalidCols = append(invalidCols, colDef.ColName)
		}
	}
	if len(invalidCols) == 0 {
		return false, ""
	}
	return true, fmt.Sprintf("json 列 %s 的默认值无效，不允许为 '' 或 'null'", strings.Join(invalidCols, ", "))
}

func optionStringValue(options []TableOption, key string) string {
	for _, opt := range options {
		if !strings.EqualFold(opt.Key, key) {
			continue
		}
		if s, ok := opt.Value.(string); ok {
			return s
		}
	}
	return ""
}

// EngineMismatch reports whether SQL specified ENGINE is incompatible with
// every selected cluster default. SQL is applied to all selected clusters, so
// any distinct default that does not equal specified is a hit.
// empty specified, empty defaults, or specified engine spider => no mismatch.
// names are canonicalized (InnoDB, RocksDB, TokuDB, ...) so case does not matter.
// duplicates and blank entries are ignored.
func EngineMismatch(specified string, clusterDefaults []string) (hit bool, msg string) {
	specified = canonicalStorageEngine(specified)
	defaults := normalizeStorageEngines(clusterDefaults)
	if specified == "" || len(defaults) == 0 {
		return false, ""
	}
	if strings.EqualFold(specified, "spider") {
		return false, ""
	}
	var conflicts []string
	for _, clusterDefault := range defaults {
		if specified == clusterDefault {
			continue
		}
		conflicts = append(conflicts, clusterDefault)
	}
	if len(conflicts) == 0 {
		return false, ""
	}
	return true, fmt.Sprintf("指定 ENGINE=%s，与集群默认存储引擎 %s 不一致", specified, strings.Join(conflicts, ", "))
}

func parseCreateTableEngineRule(r *CheckerResult, specified string, clusterDefaultEngines []string) {
	if len(normalizeStorageEngines(clusterDefaultEngines)) > 0 {
		parseEngineMismatch(r, specified, clusterDefaultEngines)
		return
	}
	r.Parse(R.CreateTableRule.SuggestEngine, specified, "")
}

func parseEngineMismatch(r *CheckerResult, specified string, clusterDefaultEngines []string) {
	if len(normalizeStorageEngines(clusterDefaultEngines)) == 0 {
		return
	}
	r.ParseBuiltinRisk(func() (bool, string) {
		return EngineMismatch(specified, clusterDefaultEngines)
	})
}

// ResolveDefaultStorageEngines returns explicit engines when present.
// Otherwise it picks known engine literals from three-part version tags
// such as MySQL-5.7-RocksDB. Community and other non-engine suffixes are ignored.
func ResolveDefaultStorageEngines(explicit, versionTags []string) []string {
	if engines := normalizeStorageEngines(explicit); len(engines) > 0 {
		return engines
	}
	return enginesFromVersionTags(versionTags)
}

func enginesFromVersionTags(versionTags []string) []string {
	extracted := make([]string, 0, len(versionTags))
	for _, tag := range versionTags {
		tag = strings.TrimSpace(tag)
		parts := strings.Split(tag, "-")
		if len(parts) < 3 {
			continue
		}
		last := strings.TrimSpace(parts[len(parts)-1])
		if !isKnownStorageEngine(last) {
			continue
		}
		extracted = append(extracted, last)
	}
	return normalizeStorageEngines(extracted)
}

func isKnownStorageEngine(name string) bool {
	_, ok := knownStorageEngines[strings.ToLower(strings.TrimSpace(name))]
	return ok
}

func canonicalStorageEngine(name string) string {
	name = strings.TrimSpace(name)
	if name == "" {
		return ""
	}
	key := strings.ToLower(name)
	if canon, ok := knownStorageEngines[key]; ok {
		return canon
	}
	return name
}

var knownStorageEngines = map[string]string{
	"innodb":     "InnoDB",
	"rocksdb":    "RocksDB",
	"tokudb":     "TokuDB",
	"myisam":     "MyISAM",
	"memory":     "MEMORY",
	"csv":        "CSV",
	"archive":    "ARCHIVE",
	"blackhole":  "BLACKHOLE",
	"federated":  "FEDERATED",
	"spider":     "SPIDER",
	"ndb":        "NDB",
	"ndbcluster": "ndbcluster",
}

func normalizeStorageEngines(engines []string) []string {
	seen := make(map[string]struct{}, len(engines))
	out := make([]string, 0, len(engines))
	for _, engine := range engines {
		canon := canonicalStorageEngine(engine)
		if canon == "" {
			continue
		}
		key := strings.ToLower(canon)
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}
		out = append(out, canon)
	}
	return out
}
