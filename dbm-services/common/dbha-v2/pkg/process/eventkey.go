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

import "path/filepath"

// EventKeyFromPidFile normalizes a pid-file path into a stable key used to derive
// per-process control event names on Windows. It is effectively unused on Unix
// (where signals, not named events, drive stop/reload) but is defined for all
// platforms so cross-platform callers can build the key uniformly.
//
// Normalization (absolute + cleaned path) is required so the stop command and the
// running process derive the same event name regardless of the working directory
// each was invoked from; a relative default pid file (e.g. ./pids/probe.pid)
// would otherwise hash differently and make stop silently miss the process.
func EventKeyFromPidFile(pidFile string) string {
	if pidFile == "" {
		return ""
	}
	// filepath.Abs also cleans the result.
	if abs, err := filepath.Abs(pidFile); err == nil {
		return abs
	}
	return filepath.Clean(pidFile)
}
