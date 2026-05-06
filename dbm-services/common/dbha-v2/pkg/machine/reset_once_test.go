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

package machine

import (
	"errors"
	"sync"
	"sync/atomic"
	"testing"
)

func TestResetOnce_Do(t *testing.T) {
	var once ResetOnce
	var counter int32

	f := func() error {
		atomic.AddInt32(&counter, 1)
		return nil
	}

	err := once.Do(f)
	if err != nil {
		t.Fatalf("Do() unexpected error: %v", err)
	}
	if atomic.LoadInt32(&counter) != 1 {
		t.Fatalf("counter = %v, want 1", counter)
	}

	err = once.Do(f)
	if err != nil {
		t.Fatalf("Do() unexpected error: %v", err)
	}
	if atomic.LoadInt32(&counter) != 1 {
		t.Fatalf("counter = %v, want 1 (should not increment)", counter)
	}

	err = once.Do(f)
	if err != nil {
		t.Fatalf("Do() unexpected error: %v", err)
	}
	if atomic.LoadInt32(&counter) != 1 {
		t.Fatalf("counter = %v, want 1 (should not increment)", counter)
	}
}

func TestResetOnce_DoWithError(t *testing.T) {
	var once ResetOnce
	var counter int32
	expectedErr := errors.New("test error")

	f := func() error {
		atomic.AddInt32(&counter, 1)
		return expectedErr
	}

	err := once.Do(f)
	if !errors.Is(err, expectedErr) {
		t.Fatalf("Do() error = %v, want %v", err, expectedErr)
	}
	if atomic.LoadInt32(&counter) != 1 {
		t.Fatalf("counter = %v, want 1", counter)
	}

	err = once.Do(f)
	if !errors.Is(err, expectedErr) {
		t.Fatalf("Do() error = %v, want %v", err, expectedErr)
	}
	if atomic.LoadInt32(&counter) != 2 {
		t.Fatalf("counter = %v, want 2 (should increment on retry)", counter)
	}
}

func TestResetOnce_Reset(t *testing.T) {
	var once ResetOnce
	var counter int32

	f := func() error {
		atomic.AddInt32(&counter, 1)
		return nil
	}

	once.Do(f)
	if atomic.LoadInt32(&counter) != 1 {
		t.Fatalf("counter = %v, want 1", counter)
	}

	once.Do(f)
	if atomic.LoadInt32(&counter) != 1 {
		t.Fatalf("counter = %v, want 1", counter)
	}

	once.Reset()

	once.Do(f)
	if atomic.LoadInt32(&counter) != 2 {
		t.Fatalf("counter = %v, want 2 (should execute after reset)", counter)
	}

	once.Do(f)
	if atomic.LoadInt32(&counter) != 2 {
		t.Fatalf("counter = %v, want 2", counter)
	}
}

func TestResetOnce_Concurrent(t *testing.T) {
	var once ResetOnce
	var counter int32
	var wg sync.WaitGroup

	f := func() error {
		atomic.AddInt32(&counter, 1)
		return nil
	}

	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			once.Do(f)
		}()
	}

	wg.Wait()

	if atomic.LoadInt32(&counter) != 1 {
		t.Fatalf("counter = %v, want 1 (only one goroutine should execute)", counter)
	}
}

func TestResetOnce_ConcurrentWithReset(t *testing.T) {
	var once ResetOnce
	var counter int32

	f := func() error {
		atomic.AddInt32(&counter, 1)
		return nil
	}

	once.Do(f)
	if atomic.LoadInt32(&counter) != 1 {
		t.Fatalf("counter = %v, want 1", counter)
	}

	once.Reset()

	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			once.Do(f)
		}()
	}

	wg.Wait()

	if atomic.LoadInt32(&counter) != 2 {
		t.Fatalf("counter = %v, want 2", counter)
	}
}

func TestResetOnce_MultipleResets(t *testing.T) {
	var once ResetOnce
	var counter int32

	f := func() error {
		atomic.AddInt32(&counter, 1)
		return nil
	}

	for i := 0; i < 5; i++ {
		once.Do(f)
		once.Reset()
	}

	once.Do(f)

	if atomic.LoadInt32(&counter) != 6 {
		t.Fatalf("counter = %v, want 6", counter)
	}
}

func TestResetOnce_ZeroValue(t *testing.T) {
	var once ResetOnce
	called := false

	once.Do(func() error {
		called = true
		return nil
	})

	if !called {
		t.Fatal("function should be called on zero value ResetOnce")
	}
}
