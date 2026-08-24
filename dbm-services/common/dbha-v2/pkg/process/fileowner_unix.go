//go:build unix

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
	"syscall"
)

// preserveOwner changes the ownership of tmpPath to the uid/gid recorded in info,
// so replacing a file through rename does not silently transfer it to the caller.
// info may be nil (target does not exist yet) or carry a non-unix Sys() value, in
// which case nothing is done and nil is returned.
// It returns the chown error, which callers treat as non-fatal: an unprivileged
// user cannot chown a file owned by somebody else.
func preserveOwner(tmpPath string, info os.FileInfo) error {
	if info == nil {
		return nil
	}

	st, ok := info.Sys().(*syscall.Stat_t)
	if !ok {
		return nil
	}

	return os.Chown(tmpPath, int(st.Uid), int(st.Gid))
}
