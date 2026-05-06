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

package safe

import (
	"dbm-services/common/dbha-v2/pkg/logger"
)

// Option configures Run, Go, and GoCtx behavior. Later options override earlier ones
// for the same setting.
type Option func(*config)

type config struct {
	label         string
	log           logger.Logger
	onPanic       func(PanicInfo)
	repanic       bool
	stackMaxBytes int
	sanitizer     PanicSanitizer
}

func newConfig(opts []Option) config {
	c := config{}
	for _, o := range opts {
		if o != nil {
			o(&c)
		}
	}
	return c
}

// WithLabel attaches a caller-defined label included in panic logs (empty prints as "-").
func WithLabel(label string) Option {
	return func(c *config) {
		c.label = label
	}
}

// WithLogger uses the given logger for panic records. If unset, package logger.Error is used.
func WithLogger(log logger.Logger) Option {
	return func(c *config) {
		c.log = log
	}
}

// WithOnPanic runs after a panic is logged; use for metrics, alerts, or extra teardown.
// PanicInfo.Ctx is non-nil only when the panic originated from GoCtx or GoCtxWait.
func WithOnPanic(h func(PanicInfo)) Option {
	return func(c *config) {
		c.onPanic = h
	}
}

// WithPanicSanitizer transforms panic reason and stack before they are logged or
// passed to OnPanic. This is useful when panic data may contain secrets.
// See the PanicSanitizer type documentation for the full contract (re-truncation,
// repanic behaviour, and panic-safety guarantees).
func WithPanicSanitizer(s PanicSanitizer) Option {
	return func(c *config) {
		c.sanitizer = s
	}
}

// WithRepanic enables re-panicking after logging and OnPanic in synchronous Run.
// In async helpers (Go/GoWait/GoCtx/GoCtxWait), the repanic request is ignored and
// a warning is logged to prevent the goroutine from crashing the whole process.
//
// The re-panicked value is always the original (unsanitized) reason, regardless
// of any PanicSanitizer. This ensures that upstream recover() callers see the
// real panic value for correct error handling.
func WithRepanic(repanic bool) Option {
	return func(c *config) {
		c.repanic = repanic
	}
}

// WithStackMaxBytes limits the stack trace length copied into logs and PanicInfo (0: no limit).
func WithStackMaxBytes(n int) Option {
	return func(c *config) {
		if n < 0 {
			n = 0
		}
		c.stackMaxBytes = n
	}
}
