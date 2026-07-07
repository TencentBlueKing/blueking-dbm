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

package process

import (
	"os"
	"path/filepath"
	"testing"
)

// TestEventKeyFromPidFile_Deterministic ensures that different relative spellings
// of the same pid file (resolved against the same cwd) normalize to one key, so
// the stop command and the running process derive the same Windows event name
// regardless of how the path was written (D1).
func TestEventKeyFromPidFile_Deterministic(t *testing.T) {
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}

	rel := filepath.Join("pids", "probe.pid")
	dotted := filepath.Join(".", "pids", "..", "pids", "probe.pid")
	abs := filepath.Join(cwd, "pids", "probe.pid")

	kRel := EventKeyFromPidFile(rel)
	kDotted := EventKeyFromPidFile(dotted)
	kAbs := EventKeyFromPidFile(abs)

	if kRel != kAbs {
		t.Fatalf("relative key %q != absolute key %q", kRel, kAbs)
	}
	if kDotted != kAbs {
		t.Fatalf("dotted key %q != absolute key %q", kDotted, kAbs)
	}
	if !filepath.IsAbs(kAbs) {
		t.Fatalf("expected absolute key, got %q", kAbs)
	}
}

// TestEventKeyFromPidFile_Empty checks the empty-input contract.
func TestEventKeyFromPidFile_Empty(t *testing.T) {
	if got := EventKeyFromPidFile(""); got != "" {
		t.Fatalf("EventKeyFromPidFile(\"\") = %q, want empty", got)
	}
}
