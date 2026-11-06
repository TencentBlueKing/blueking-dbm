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

package haprobe

import "testing"

func TestDbTypeConstsAreKnown(t *testing.T) {
	consts := []DbType{
		DbTypeMySql, DbTypeRedis, DbTypeSqlServer, DbTypeMongo, DbTypeRiak,
		DbTypeHdfs, DbTypeEs, DbTypeKafka, DbTypeDoris, DbTypePulsar,
	}
	for _, c := range consts {
		if !c.IsKnown() {
			t.Errorf("DbType %q is not in knownDbTypes", c)
		}
	}
	if len(knownDbTypes) != len(consts) {
		t.Errorf("knownDbTypes has %d entries, want %d", len(knownDbTypes), len(consts))
	}
	if DbTypeNone.IsKnown() {
		t.Error("empty DbType should not be known")
	}
	if DbTypeUnknown.IsKnown() {
		t.Error("unknown DbType should not be known")
	}
	if DbType("tendis").IsKnown() {
		t.Error("arbitrary DbType should not be known")
	}
}

func TestDbTypeNormalize(t *testing.T) {
	cases := []struct {
		in   DbType
		want DbType
	}{
		{in: DbTypeMySql, want: DbTypeMySql},
		{in: DbTypePulsar, want: DbTypePulsar},
		{in: DbTypeNone, want: DbTypeUnknown},
		{in: DbTypeUnknown, want: DbTypeUnknown},
		{in: DbType("tendis"), want: DbTypeUnknown},
	}
	for _, tc := range cases {
		if got := tc.in.Normalize(); got != tc.want {
			t.Errorf("DbType(%q).Normalize()=%q, want %q", tc.in, got, tc.want)
		}
	}
}
