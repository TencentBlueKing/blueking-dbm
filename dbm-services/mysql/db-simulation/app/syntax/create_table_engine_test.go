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
	"encoding/json"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const engineMismatchPhrase = "与集群默认存储引擎"

func TestEngineMismatch(t *testing.T) {
	tests := []struct {
		name            string
		specified       string
		clusterDefaults []string
		wantHit         bool
		wantSubs        []string
	}{
		{
			name:            "innodb vs rocksdb",
			specified:       "InnoDB",
			clusterDefaults: []string{"rocksdb"},
			wantHit:         true,
			wantSubs:        []string{"innodb", "rocksdb"},
		},
		{
			name:            "same rocksdb",
			specified:       "rocksdb",
			clusterDefaults: []string{"rocksdb"},
			wantHit:         false,
		},
		{
			name:            "mixed case same innodb",
			specified:       "innodb",
			clusterDefaults: []string{"InnoDB"},
			wantHit:         false,
		},
		{
			name:            "empty specified",
			specified:       "",
			clusterDefaults: []string{"rocksdb"},
			wantHit:         false,
		},
		{
			name:            "empty default",
			specified:       "MyISAM",
			clusterDefaults: nil,
			wantHit:         false,
		},
		{
			name:            "blank defaults only",
			specified:       "InnoDB",
			clusterDefaults: []string{"", "  "},
			wantHit:         false,
		},
		{
			name:            "spider vs rocksdb",
			specified:       "SPIDER",
			clusterDefaults: []string{"rocksdb"},
			wantHit:         false,
		},
		{
			name:            "innodb vs mixed rocksdb and innodb",
			specified:       "InnoDB",
			clusterDefaults: []string{"rocksdb", "innodb"},
			wantHit:         true,
			wantSubs:        []string{"innodb", "rocksdb"},
		},
		{
			name:            "innodb vs duplicate rocksdb",
			specified:       "InnoDB",
			clusterDefaults: []string{"rocksdb", "ROCKSDB"},
			wantHit:         true,
			wantSubs:        []string{"innodb", "rocksdb"},
		},
		{
			name:            "innodb vs duplicate innodb",
			specified:       "InnoDB",
			clusterDefaults: []string{"innodb", "InnoDB"},
			wantHit:         false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			hit, msg := EngineMismatch(tt.specified, clusterInfosFromEngines(tt.clusterDefaults))
			assert.Equal(t, tt.wantHit, hit)
			if tt.wantHit {
				require.NotEmpty(t, msg)
				lower := strings.ToLower(msg)
				for _, sub := range tt.wantSubs {
					assert.Contains(t, lower, sub)
				}
				assert.Contains(t, msg, engineMismatchPhrase)
			} else {
				assert.Empty(t, msg)
				assert.NotContains(t, msg, engineMismatchPhrase)
			}
		})
	}
}

func TestGetEngine_FallsBackToTableOptions(t *testing.T) {
	o := CreateTableResult{
		TableOptions: []TableOption{{Key: "engine", Value: "InnoDB"}},
	}
	assert.Equal(t, "InnoDB", o.GetEngine())

	o.TableOptionMap = ConvertTableOptionToMap(o.TableOptions)
	assert.Equal(t, "InnoDB", o.GetEngine())
}

func TestCreateTableResult_Checker_EngineMismatch(t *testing.T) {
	requireCreateTableCheckerRules(t)

	tests := []struct {
		name            string
		specified       string
		clusterDefault  string
		wantMismatch    bool
		wantYamlSuggest bool
	}{
		{
			name:           "innodb vs rocksdb",
			specified:      "InnoDB",
			clusterDefault: "rocksdb",
			wantMismatch:   true,
		},
		{
			name:           "same rocksdb",
			specified:      "rocksdb",
			clusterDefault: "rocksdb",
		},
		{
			name:           "empty specified",
			specified:      "",
			clusterDefault: "rocksdb",
		},
		{
			name:            "empty default myisam",
			specified:       "MyISAM",
			clusterDefault:  "",
			wantYamlSuggest: true,
		},
		{
			name:           "spider vs rocksdb",
			specified:      "SPIDER",
			clusterDefault: "rocksdb",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			c := newCreateTableWithEngine(tt.specified)
			cr := c.checkWithClusterEngines("5.7", clusterEngines(tt.clusterDefault))
			require.NotNil(t, cr)
			joined := strings.Join(cr.RiskWarns, "\n")
			lower := strings.ToLower(joined)
			if tt.wantMismatch {
				require.NotEmpty(t, cr.RiskWarns)
				assert.Contains(t, lower, strings.ToLower(tt.specified))
				assert.Contains(t, lower, strings.ToLower(tt.clusterDefault))
				assert.Contains(t, joined, engineMismatchPhrase)
				return
			}
			assert.NotContains(t, joined, engineMismatchPhrase)
			if tt.wantYamlSuggest {
				require.NotEmpty(t, cr.RiskWarns)
				assert.Contains(t, lower, "innodb")
			}
		})
	}
}

func TestCreateTableResult_Checker_InnoDBDoesNotSuggestInnoDB(t *testing.T) {
	requireCreateTableCheckerRules(t)
	for _, specified := range []string{"InnoDB", "innodb", "INNODB"} {
		t.Run(specified, func(t *testing.T) {
			c := newCreateTableWithEngine(specified)
			cr := c.checkWithClusterEngines("5.7", nil)
			require.NotNil(t, cr)
			joined := strings.Join(cr.RiskWarns, "\n")
			assert.NotContains(t, joined, "建议使用Innodb表")
		})
	}
}

func TestCreateTableResult_SpiderChecker_EngineMismatch(t *testing.T) {
	mismatch := newCreateTableWithEngine("InnoDB")
	mismatch.IsCreateTableLike = true
	cr := mismatch.spiderCheckWithClusterEngines("5.7", []ClusterInfo{{Engine: "rocksdb"}})
	require.NotNil(t, cr)
	joined := strings.Join(cr.RiskWarns, "\n")
	lower := strings.ToLower(joined)
	require.NotEmpty(t, cr.RiskWarns)
	assert.Contains(t, lower, "innodb")
	assert.Contains(t, lower, "rocksdb")
	assert.Equal(t, 1, strings.Count(joined, engineMismatchPhrase))

	spider := newCreateTableWithEngine("SPIDER")
	spider.IsCreateTableLike = true
	cr = spider.spiderCheckWithClusterEngines("5.7", []ClusterInfo{{Engine: "rocksdb"}})
	require.NotNil(t, cr)
	assert.NotContains(t, strings.Join(cr.RiskWarns, "\n"), engineMismatchPhrase)
}

func TestCreateTableResult_Checker_MixedClusterEngines(t *testing.T) {
	requireCreateTableCheckerRules(t)
	c := CreateTableResult{
		TableName:    "t1",
		TableOptions: []TableOption{{Key: "engine", Value: "InnoDB"}},
	}
	cr := c.checkWithClusterEngines("5.7", []ClusterInfo{{Engine: "rocksdb"}, {Engine: "innodb"}})
	require.NotNil(t, cr)
	joined := strings.Join(cr.RiskWarns, "\n")
	require.Contains(t, joined, engineMismatchPhrase)
	assert.Contains(t, strings.ToLower(joined), "rocksdb")
}

func TestAlterTableResult_Checker_EngineMismatch(t *testing.T) {
	requireAlterTableCheckerRules(t)

	mismatch := AlterTableResult{
		TableName: "t1",
		AlterCommands: []AlterCommand{
			{
				Type: AlterTypeTableOptions,
				TableOptions: []TableOption{
					{Key: "engine", Value: "InnoDB"},
				},
			},
		},
	}
	cr := mismatch.checkWithClusterEngines("5.7", []ClusterInfo{{Engine: "rocksdb"}})
	require.NotNil(t, cr)
	joined := strings.Join(cr.RiskWarns, "\n")
	lower := strings.ToLower(joined)
	require.NotEmpty(t, cr.RiskWarns)
	assert.Contains(t, lower, "innodb")
	assert.Contains(t, lower, "rocksdb")
	assert.Contains(t, joined, engineMismatchPhrase)

	same := mismatch
	same.AlterCommands = []AlterCommand{
		{
			Type: AlterTypeTableOptions,
			TableOptions: []TableOption{
				{Key: "engine", Value: "rocksdb"},
			},
		},
	}
	cr = same.checkWithClusterEngines("5.7", []ClusterInfo{{Engine: "rocksdb"}})
	require.NotNil(t, cr)
	assert.NotContains(t, strings.Join(cr.RiskWarns, "\n"), engineMismatchPhrase)
}

func newCreateTableWithEngine(specified string) CreateTableResult {
	c := CreateTableResult{
		TableName: "t1",
	}
	if specified != "" {
		c.TableOptions = []TableOption{{Key: "engine", Value: specified}}
	}
	return c
}

func clusterEngines(clusterDefault string) []ClusterInfo {
	if clusterDefault == "" {
		return nil
	}
	return []ClusterInfo{{Engine: clusterDefault}}
}

func clusterInfosFromEngines(engines []string) []ClusterInfo {
	if len(engines) == 0 {
		return nil
	}
	out := make([]ClusterInfo, 0, len(engines))
	for _, engine := range engines {
		out = append(out, ClusterInfo{Engine: engine})
	}
	return out
}

func requireCreateTableCheckerRules(t *testing.T) {
	t.Helper()
	if R == nil || R.CreateTableRule.SuggestEngine == nil || R.CreateTableRule.SuggestBlobColumCount == nil {
		t.Skip("create table rules not loaded")
	}
}

func requireAlterTableCheckerRules(t *testing.T) {
	t.Helper()
	if R == nil || R.AlterTableRule.HighRiskType == nil ||
		R.AlterTableRule.HighRiskPkAlterType == nil ||
		R.AlterTableRule.AlterUseAfter == nil ||
		R.AlterTableRule.AddColumnMixed == nil {
		t.Skip("alter table rules not loaded")
	}
}

func TestEngineMismatchNamesBothDomains(t *testing.T) {
	clusters := []ClusterInfo{
		{ClusterDomain: "cwncgchendb.test-1.kio.db", Engine: "InnoDB", Version: "MySQL-5.6"},
		{ClusterDomain: "tmpdb.test-1-20250918143959662879.dba.db", Engine: "InnoDB", Version: "MySQL-5.6"},
	}
	hit, msg := EngineMismatch("RocksDB", clusters)
	require.True(t, hit)
	assert.Equal(t,
		"指定 ENGINE=RocksDB，与集群 cwncgchendb.test-1.kio.db、tmpdb.test-1-20250918143959662879.dba.db 的默认存储引擎 InnoDB 不一致",
		msg)
}

func TestEngineMismatchNamesOnlyConflictDomain(t *testing.T) {
	clusters := []ClusterInfo{
		{ClusterDomain: "innodb.example.db", Engine: "InnoDB"},
		{ClusterDomain: "rocks.example.db", Engine: "RocksDB"},
	}
	hit, msg := EngineMismatch("InnoDB", clusters)
	require.True(t, hit)
	assert.Contains(t, msg, "rocks.example.db")
	assert.NotContains(t, msg, "innodb.example.db")
	assert.Contains(t, msg, "RocksDB")
}

func TestEngineMismatchBlankEngineSkipped(t *testing.T) {
	hit, msg := EngineMismatch("InnoDB", []ClusterInfo{{
		ClusterDomain: "a.example.db",
		Engine:        "",
		Version:       "MySQL-5.7-RocksDB",
	}})
	assert.False(t, hit)
	assert.Empty(t, msg)
}

func TestClustersForVersionParsesOncePerToken(t *testing.T) {
	all := []ClusterInfo{
		{ClusterDomain: "a.example.db", Engine: "InnoDB", Version: "MySQL-5.6"},
		{ClusterDomain: "b.example.db", Engine: "InnoDB", Version: "MySQL-5.6"},
		{ClusterDomain: "c.example.db", Engine: "RocksDB", Version: "MySQL-5.7"},
	}
	got := clustersForVersion(all, "5.6.24")
	require.Len(t, got, 2)
	assert.Equal(t, "a.example.db", got[0].ClusterDomain)
	assert.Equal(t, "b.example.db", got[1].ClusterDomain)

	got = clustersForVersion(all, "")
	require.Len(t, got, 3)
}

func TestSyntaxErrorMessageIncludesDomainsWithoutNewFields(t *testing.T) {
	p := &TmysqlParse{Clusters: []ClusterInfo{
		{ClusterDomain: "cwncgchendb.test-1.kio.db", Engine: "InnoDB", Version: "MySQL-5.6"},
		{ClusterDomain: "tmpdb.test-1-20250918143959662879.dba.db", Engine: "InnoDB", Version: "MySQL-5.6"},
		{ClusterDomain: "cwncgchendb.test-1.kio.db", Engine: "InnoDB", Version: "MySQL-5.6"},
	}}
	info := p.getSyntaxErrorResult(ParseLineQueryBase{ErrorMsg: "bad sql", QueryString: "SELECT", ErrorLine: 3}, "5.6.24")
	assert.Contains(t, info.ErrorMsg, "[cwncgchendb.test-1.kio.db、tmpdb.test-1-20250918143959662879.dba.db]")
	assert.Contains(t, info.ErrorMsg, "[MySQL-5.6]: bad sql")
	raw, err := json.Marshal(info)
	require.NoError(t, err)
	assert.NotContains(t, string(raw), "cluster_domain")
}
