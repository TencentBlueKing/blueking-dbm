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

func TestIsShutdownPending_Unix_NoSignal(t *testing.T) {
	waiter, err := NewStopWaiter("")
	if err != nil {
		t.Fatalf("NewStopWaiter failed, errmsg: %s", err)
	}
	defer waiter.Close()

	if isShutdownPending(waiter, "ignored-on-unix") {
		t.Fatal("expected no pending shutdown before signal")
	}
}

func TestIsShutdownPending_Unix_AfterSignal(t *testing.T) {
	waiter, err := NewStopWaiter("")
	if err != nil {
		t.Fatalf("NewStopWaiter failed, errmsg: %s", err)
	}
	defer waiter.Close()

	if err := syscall.Kill(syscall.Getpid(), syscall.SIGTERM); err != nil {
		t.Fatalf("kill self failed, errmsg: %s", err)
	}

	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if isShutdownPending(waiter, "") {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatal("expected pending shutdown after SIGTERM")
}
