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

package migrator

import "testing"

func TestSnapshotCloneCopiesIndexSlices(t *testing.T) {
	original := &Snapshot{Tables: map[string]*Table{
		"table": {
			Indexes: []Index{{Columns: []string{"first"}, Prefix: []int{32}}},
		},
	}}
	cloned := original.clone()
	cloned.Tables["table"].Indexes[0].Columns[0] = "changed"
	cloned.Tables["table"].Indexes[0].Prefix[0] = 64

	index := original.Tables["table"].Indexes[0]
	if index.Columns[0] != "first" || index.Prefix[0] != 32 {
		t.Fatalf("clone modified source index, columns: %v, prefix: %v", index.Columns, index.Prefix)
	}
}

func TestUniqueProfileSortsIndexes(t *testing.T) {
	table := &Table{Indexes: []Index{
		{Name: "z_index", Unique: true, Columns: []string{"z"}},
		{Name: "a_index", Unique: true, Columns: []string{"a"}},
	}}
	if got, want := uniqueProfile(table), "a_index(a),z_index(z)"; got != want {
		t.Fatalf("unique profile, got: %s, want: %s", got, want)
	}
}

func TestStepNameKeepsSixDigitVersion(t *testing.T) {
	if got, want := stepName(1, "create_table"), "000001_create_table"; got != want {
		t.Fatalf("step name, got: %s, want: %s", got, want)
	}
}
