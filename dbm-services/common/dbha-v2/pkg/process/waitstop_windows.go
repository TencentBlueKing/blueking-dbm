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
	"sync"

	"golang.org/x/sys/windows"
)

// waitPollMillis bounds how long the wait goroutine blocks in a single
// WaitForMultipleObjects call, so it can observe Close() promptly.
const waitPollMillis = 500

// StopWaiter delivers shutdown and reload notifications for the current process.
// Callers select on Shutdown and Reload, and must call Close when done to stop
// the underlying event delivery.
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

// NewStopWaiter creates a Windows named-event based stop waiter. eventKey is the
// opaque key used to derive the stop and reload event names: the pid-file key
// (via EventKeyFromPidFile) for the worker/guard, or the ping-http-addr for
// keepalive. The stop event is a single manual-reset event shared by guard and
// worker so a single set wakes both.
func NewStopWaiter(eventKey string) (*StopWaiter, error) {
	stopEvt, err := createManualResetEvent(DeriveEventName(eventKey, stopEventSuffix))
	if err != nil {
		return nil, err
	}
	reloadEvt, err := createManualResetEvent(DeriveEventName(eventKey, reloadEventSuffix))
	if err != nil {
		windows.CloseHandle(stopEvt)
		return nil, err
	}

	shutdownC := make(chan struct{}, 1)
	reloadC := make(chan struct{}, 1)
	done := make(chan struct{})

	go func() {
		// The goroutine owns the handles and closes them on exit, so we never
		// close a handle from another goroutine while a wait is in flight.
		defer windows.CloseHandle(stopEvt)
		defer windows.CloseHandle(reloadEvt)

		handles := []windows.Handle{stopEvt, reloadEvt}
		for {
			ev, werr := windows.WaitForMultipleObjects(handles, false, waitPollMillis)

			select {
			case <-done:
				return
			default:
			}

			if werr != nil {
				// Unexpected wait failure; loop to re-check done and retry.
				continue
			}

			switch ev {
			case windows.WAIT_OBJECT_0:
				// Stop event: deliver once and exit (shutdown is terminal). The
				// manual-reset event stays signaled so any other waiter (e.g. the
				// guard sharing the same event) also wakes.
				select {
				case shutdownC <- struct{}{}:
				default:
				}
				return
			case windows.WAIT_OBJECT_0 + 1:
				// Reload event: reset it so we don't spin on the still-signaled
				// manual-reset object, then deliver.
				_ = windows.ResetEvent(reloadEvt)
				select {
				case reloadC <- struct{}{}:
				default:
				}
			default:
				// WAIT_TIMEOUT (or any other value): loop and re-check done.
			}
		}
	}()

	return &StopWaiter{
		Shutdown: shutdownC,
		Reload:   reloadC,
		stop:     func() { close(done) },
	}, nil
}
