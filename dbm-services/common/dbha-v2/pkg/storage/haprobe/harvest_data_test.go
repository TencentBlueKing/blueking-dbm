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

func TestHarvestTypeConstsAreKnown(t *testing.T) {
	consts := []HarvestType{HarvestTypeDefault, HarvestTypeHeartbeat, HarvestTypeReplDelay}
	for _, c := range consts {
		if !c.IsKnown() {
			t.Errorf("HarvestType %q is not in knownHarvestTypes", c)
		}
	}
	if len(knownHarvestTypes) != len(consts) {
		t.Errorf("knownHarvestTypes has %d entries, want %d", len(knownHarvestTypes), len(consts))
	}
	if HarvestType("").IsKnown() {
		t.Error("empty HarvestType should not be known")
	}
	if HarvestType("unknown").IsKnown() {
		t.Error("unknown HarvestType should not be known")
	}
}
