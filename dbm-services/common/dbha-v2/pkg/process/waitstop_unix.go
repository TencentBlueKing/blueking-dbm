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
	"os/signal"
	"sync"
	"syscall"
)

// StopWaiter delivers shutdown and reload notifications for the current process.
// Callers select on Shutdown and Reload, and must call Close when done to stop
// the underlying signal/event delivery.
type StopWaiter struct {
	Shutdown <-chan struct{}
	Reload   <-chan struct{}
	stop     func()
	once     sync.Once
}

// Close releases the resources backing the waiter.
func (w *StopWaiter) Close() {
	if w == nil {
		return
	}
	w.once.Do(func() {
		if w.stop != nil {
			w.stop()
		}
	})
}

// NewStopWaiter creates a signal-based stop waiter on Unix. eventKey is ignored
// here; POSIX signals drive the notifications and their semantics are preserved
// exactly: SIGINT/SIGTERM request shutdown, SIGHUP requests reload (never folded
// into shutdown).
func NewStopWaiter(_ string) (*StopWaiter, error) {
	sigC := make(chan os.Signal, 1)
	signal.Notify(sigC, syscall.SIGINT, syscall.SIGTERM, syscall.SIGHUP)

	shutdownC := make(chan struct{}, 1)
	reloadC := make(chan struct{}, 1)
	done := make(chan struct{})

	go func() {
		for {
			select {
			case <-done:
				signal.Stop(sigC)
				return
			case sig := <-sigC:
				if sig == syscall.SIGHUP {
					select {
					case reloadC <- struct{}{}:
					default:
					}
					continue
				}
				select {
				case shutdownC <- struct{}{}:
				default:
				}
			}
		}
	}()

	return &StopWaiter{
		Shutdown: shutdownC,
		Reload:   reloadC,
		stop:     func() { close(done) },
	}, nil
}
