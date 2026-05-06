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

package switchmutex

import (
	"sync"
	"time"
)

// SwitchMutex is an in-memory mutex used for switching coordination.
type SwitchMutex struct {
	ch chan struct{}
}

var mutexes sync.Map

// Get returns a mutex by key, creating it if needed.
func Get(key string) *SwitchMutex {
	mutex, _ := mutexes.LoadOrStore(key, &SwitchMutex{
		ch: make(chan struct{}, 1),
	})
	return mutex.(*SwitchMutex)
}

// TryLock tries to acquire the mutex within the timeout.
func (m *SwitchMutex) TryLock(timeout time.Duration) bool {
	if timeout <= 0 {
		return m.tryLockNoWait()
	}

	timer := time.NewTimer(timeout)
	defer timer.Stop()

	select {
	case m.ch <- struct{}{}:
		return true
	case <-timer.C:
		return false
	}
}

func (m *SwitchMutex) tryLockNoWait() bool {
	select {
	case m.ch <- struct{}{}:
		return true
	default:
		return false
	}
}

// Unlock releases the mutex.
func (m *SwitchMutex) Unlock() {
	select {
	case <-m.ch:
	default:
	}
}
