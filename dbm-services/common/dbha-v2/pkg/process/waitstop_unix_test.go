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
	"syscall"
	"testing"
	"time"
)

// TestStopWaiter_SighupIsReloadNotShutdown is the R1 regression guard: on Unix a
// SIGHUP must be delivered as Reload and must NOT be folded into Shutdown.
func TestStopWaiter_SighupIsReloadNotShutdown(t *testing.T) {
	w, err := NewStopWaiter("")
	if err != nil {
		t.Fatalf("NewStopWaiter: %v", err)
	}
	defer w.Close()

	if err := syscall.Kill(syscall.Getpid(), syscall.SIGHUP); err != nil {
		t.Fatalf("send SIGHUP: %v", err)
	}

	select {
	case <-w.Reload:
		// expected
	case <-w.Shutdown:
		t.Fatal("SIGHUP incorrectly delivered as Shutdown")
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for Reload on SIGHUP")
	}

	// No shutdown should be pending after a reload-only signal.
	select {
	case <-w.Shutdown:
		t.Fatal("unexpected Shutdown after SIGHUP")
	default:
	}
}

// TestStopWaiter_SigtermIsShutdown verifies SIGTERM maps to Shutdown.
func TestStopWaiter_SigtermIsShutdown(t *testing.T) {
	w, err := NewStopWaiter("")
	if err != nil {
		t.Fatalf("NewStopWaiter: %v", err)
	}
	defer w.Close()

	if err := syscall.Kill(syscall.Getpid(), syscall.SIGTERM); err != nil {
		t.Fatalf("send SIGTERM: %v", err)
	}

	select {
	case <-w.Shutdown:
		// expected
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for Shutdown on SIGTERM")
	}
}
