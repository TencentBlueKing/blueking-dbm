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
	"syscall"

	"golang.org/x/sys/windows"
)

// newDetachedSysProcAttr returns the SysProcAttr used to fully detach a daemon
// child on Windows. There is no Setsid; instead we set creation flags:
//   - DETACHED_PROCESS: the child gets no console and is decoupled from the
//     parent's console (analogous to leaving the controlling terminal on Unix).
//   - CREATE_NEW_PROCESS_GROUP: the child starts a new process group so it does
//     not receive console control events (e.g. Ctrl-C) sent to the parent group.
//
// DETACHED_PROCESS is NOT defined in the standard library syscall package on
// Windows (only CREATE_NEW_PROCESS_GROUP is), so it is taken from
// golang.org/x/sys/windows and applied via the CreationFlags field.
func newDetachedSysProcAttr() *syscall.SysProcAttr {
	return &syscall.SysProcAttr{
		CreationFlags: windows.CREATE_NEW_PROCESS_GROUP | windows.DETACHED_PROCESS,
	}
}
