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

package handler

import (
	"reflect"
	"testing"
)

func TestXlsxVerifyFlagsInvalidSourceDomain(t *testing.T) {
	t.Parallel()

	rawDomain := "a.exa\u3000mple.db"
	paths, params := prepareTestVerifySource(t, []testCluster{{id: "1001", domain: rawDomain, cloud: "0"}})
	records := []importAddTemplateRecord{testRecord(1001, rawDomain, 0)}
	if err := writeXlsxTemplateTemp(paths.Temp, records); err != nil {
		t.Fatalf("write temp failed: %s", err)
	}

	result := runTestVerify(t, paths, params)
	assertTestVerifyFailed(t, paths, result)

	want := []xlsxMismatch{{
		Check: xlsxCheckIDC5, Row: 2, Line: 1, Field: xlsxFieldClusterName, Xlsx: rawDomain, JSON: rawDomain,
		Reason: xlsxReasonSrcDomainBad,
	}}
	if got := testMismatches(result.report, xlsxCheckIDC5); !reflect.DeepEqual(got, want) {
		t.Fatalf("C5 mismatches = %+v, want %+v", got, want)
	}
}

func TestXlsxDomainNormalizers(t *testing.T) {
	t.Parallel()

	tests := []struct {
		raw         string
		wantDomain  string
		wantRemoved bool
		wantValid   bool
	}{
		{raw: "A.Example.db", wantDomain: "A.Example.db", wantValid: true},
		{raw: " a.example.db\t", wantDomain: "a.example.db", wantValid: true},
		{raw: "\u3000a.example.db\u00a0", wantDomain: "a.example.db", wantValid: true},
		{raw: "a.example.db:3306", wantDomain: "a.example.db", wantRemoved: true, wantValid: true},
		{raw: "a-1.example.db:0", wantDomain: "a-1.example.db", wantRemoved: true, wantValid: true},
		{raw: "a_b.example.db", wantDomain: "a_b.example.db", wantValid: true},
		{raw: "a.example.db,b.example.db"},
		{raw: "a.example.db b.example.db"},
		{raw: "a.example.db；b.example.db"},
		{raw: "a.example.db:abc"},
		{raw: "a.example.db:"},
		{raw: "a.example.db:1:2"},
		{raw: ":3306"},
		{raw: ""},
		{raw: "   "},
		{raw: "a.exa\u00a0mple.db"},
		{raw: "a.exa\u3000mple.db"},
		{raw: "a.exa\vmple.db"},
		{raw: "a.example\u200b.db"},
		{raw: "a.example.db\u200b"},
		{raw: "\ufeffa.example.db"},
		{raw: "a.example.db\u200b:3306"},
		{raw: "ａ.example.db"},
		{raw: "a。example.db"},
		{raw: "a/b.example.db"},
		{raw: "*.example.db"},
	}

	for _, tt := range tests {
		genDomain, genRemoved, reason := normalizeXlsxDomain(tt.raw)
		if genDomain != tt.wantDomain || genRemoved != tt.wantRemoved || (reason == "") != tt.wantValid {
			t.Fatalf("generation normalize %q = %q/%v/%q, want %q/%v/valid: %v",
				tt.raw, genDomain, genRemoved, reason, tt.wantDomain, tt.wantRemoved, tt.wantValid)
		}

		domain, removed, valid := verifyXlsxDomain(tt.raw)
		if domain != tt.wantDomain || removed != tt.wantRemoved || valid != tt.wantValid {
			t.Fatalf("verify normalize %q = %q/%v/%v, want %q/%v/%v",
				tt.raw, domain, removed, valid, tt.wantDomain, tt.wantRemoved, tt.wantValid)
		}
	}
}

func TestXlsxBkBizIDParsers(t *testing.T) {
	t.Parallel()

	tests := []struct {
		file    string
		flag    int
		flagSet bool
		want    int
	}{
		{file: "/tmp/x/mapleleaf(591)mysql_cluster_20261104101251.xlsx", want: 591},
		{file: "mapleleaf(591)mysql_cluster.xlsx", want: 591},
		{file: "biz(591)k8s_milvus_cluster.xlsx", want: 591},
		{file: "biz(591)k8s_milvus_cluster_20261104101251.xlsx", want: 591},
		{file: "biz(591)sqlserver_cluster.xlsx", want: 591},
		{file: "biz(591)tendbcluster_cluster.xlsx", want: 591},
		{file: "biz(12)name(591)mysql_cluster.xlsx", want: 591},
		{file: "biz(591)mysql_cluster_cluster.xlsx", want: 591},
		{file: "mapleleaf(591)mysql_cluster (1).xlsx", want: -1},
		{file: "mapleleaf(591)mysql_instances.xlsx", want: -1},
		{file: "mapleleaf(0)mysql_cluster.xlsx", want: -1},
		{file: "mapleleaf()mysql_cluster.xlsx", want: -1},
		{file: "mapleleaf(591)_cluster.xlsx", want: -1},
		{file: "mapleleaf(591)MySQL_cluster.xlsx", want: -1},
		{file: "mapleleaf(591)mysql_cluster.XLSX", want: -1},
		{file: "mapleleaf(591)mysql_cluster_2026110410125.xlsx", want: -1},
		{file: "mapleleaf(5a1)mysql_cluster.xlsx", want: -1},
		{file: "mapleleaf591)mysql_cluster.xlsx", want: -1},
		{file: "biz(99999999999999999999)mysql_cluster.xlsx", want: -1},
		{file: "mapleleaf(591)mysql_cluster.xlsx", flag: 7, flagSet: true, want: 7},
	}

	for _, tt := range tests {
		genID, from, err := resolveXlsxBkBizID(XlsxTemplateOptions{
			XlsxFile: tt.file, BkBizID: tt.flag, BkBizIDSet: tt.flagSet,
		})
		if err != nil {
			genID = -1
		}
		if genID != tt.want {
			t.Fatalf("generation bk_biz_id of %q = %d/%v, want %d", tt.file, genID, err, tt.want)
		}

		params := xlsxParams{BkBizID: genID, BkBizIDFrom: from}
		if err != nil {
			params.BkBizIDFrom = xlsxBizFromFilename
		}
		if got := verifyXlsxBkBizID(tt.file, params); got != tt.want {
			t.Fatalf("verify bk_biz_id of %q = %d, want %d", tt.file, got, tt.want)
		}
	}
}
