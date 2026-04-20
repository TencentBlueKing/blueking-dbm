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

// Package safe provides panic-safe wrappers for running work synchronously or in goroutines.
package safe

import (
	"context"
	"fmt"
	"log"
	"runtime/debug"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
)

const shortTruncationSuffix = "..."

type execMode uint8

const (
	execModeSync execMode = iota
	execModeAsync
)

// PanicSanitizer transforms panic reason and stack before they are logged or
// passed to OnPanic. It is useful when production environments need redaction.
//
// Contract:
//   - The returned safeStack will be re-truncated to WithStackMaxBytes (if set),
//     so the sanitizer does not need to honour the byte limit itself.
//   - The sanitized values are used for logging and OnPanic only; if WithRepanic
//     is enabled, the original (unsanitized) reason is re-panicked so that
//     upstream recover() callers see the real value.
//   - If the sanitizer itself panics, the original reason and stack are used
//     instead, and the incident is logged via the standard library log package.
type PanicSanitizer func(reason any, stack []byte) (safeReason any, safeStack []byte)

// PanicInfo is passed to OnPanic after a panic is recovered.
type PanicInfo struct {
	// Ctx is set only for panics from GoCtx and GoCtxWait; otherwise nil.
	Ctx context.Context
	// Reason is the final panic reason after optional sanitization.
	// Note: if WithRepanic is set and the call is synchronous, the original
	// (unsanitized) reason is re-panicked, not this value.
	Reason any
	// Stack is the final stack after truncation and optional sanitization.
	// If both WithStackMaxBytes and WithPanicSanitizer are set, the sanitizer
	// runs first, then the result is re-truncated to stackMaxBytes.
	Stack []byte
	// Truncated reports whether the original debug.Stack output was shortened.
	Truncated bool
	// RecoveredAt is when the panic was recovered by this package.
	RecoveredAt time.Time
}

// Run executes fn in the current goroutine and recovers panics, logging reason and stack.
func Run(fn func(), opts ...Option) {
	cfg := newConfig(opts)
	guard(&cfg, nil, false, execModeSync, fn)
}

// Go starts fn in a new goroutine with panic recovery, logging, and optional OnPanic.
// The goroutine is fire-and-forget; use GoWait if you need to wait for completion.
func Go(fn func(), opts ...Option) {
	cfg := newConfig(opts)

	go func() {
		guard(&cfg, nil, false, execModeAsync, fn)
	}()
}

// GoWait starts fn in a new goroutine with panic recovery like Go, and returns a
// wait function. Calling the returned function blocks until the goroutine finishes.
func GoWait(fn func(), opts ...Option) func() {
	return GoWaits([]func(){
		fn,
	}, opts...)
}

// GoWaits starts each fn in its own goroutine with panic recovery like Go, and returns a
// wait function. Calling the returned function blocks until all goroutines finish.
func GoWaits(fns []func(), opts ...Option) func() {
	cfg := newConfig(opts)
	var wg sync.WaitGroup

	for _, fn := range fns {
		wg.Add(1)
		go func() {
			defer wg.Done()
			guard(&cfg, nil, false, execModeAsync, fn)
		}()
	}

	return wg.Wait
}

// GoCtx starts fn in a new goroutine like Go; PanicInfo.Ctx is set to ctx (or Background if nil).
// Note: ctx is only passed into PanicInfo for the OnPanic callback; ctx cancellation does NOT
// stop fn. The caller is responsible for checking ctx.Done() inside fn if cancellation is needed.
func GoCtx(ctx context.Context, fn func(), opts ...Option) {
	if ctx == nil {
		ctx = context.Background()
	}

	cfg := newConfig(opts)
	captured := ctx

	go func() {
		guard(&cfg, captured, true, execModeAsync, fn)
	}()
}

// GoCtxWait is like GoCtx but returns a wait function, similar to GoWait.
func GoCtxWait(ctx context.Context, fn func(), opts ...Option) func() {
	if ctx == nil {
		ctx = context.Background()
	}

	cfg := newConfig(opts)
	captured := ctx

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		guard(&cfg, captured, true, execModeAsync, fn)
	}()

	return wg.Wait
}

// FormatPanicInfo returns a human-readable summary of a PanicInfo, useful for
// structured logging or alert messages.
func FormatPanicInfo(pi PanicInfo) string {
	return fmt.Sprintf(
		"reason: %v, truncated: %t, recoveredAt: %s, stack: %s",
		pi.Reason,
		pi.Truncated,
		pi.RecoveredAt.Format(time.RFC3339),
		string(pi.Stack),
	)
}

func guard(cfg *config, opCtx context.Context, ctxForPanic bool, mode execMode, fn func()) {
	defer func() {
		if r := recover(); r != nil {
			handlePanic(cfg, opCtx, ctxForPanic, mode, r)
		}
	}()

	fn()
}

// safeLog wraps logPanic with its own recover so that a broken logger can never
// propagate a panic out of handlePanic.
func safeLog(cfg *config, label, stackStr string, reason any) {
	defer func() {
		if r := recover(); r != nil {
			log.Printf(
				"[safe] panic in logger itself, label: %s, logPanic: %v, originalReason: %v, stack: %s",
				label, r, reason, stackStr,
			)
		}
	}()

	logPanic(cfg, label, stackStr, reason)
}

func logPanic(cfg *config, label, stackStr string, reason any) {
	if err, ok := reason.(error); ok {
		if cfg.log != nil {
			cfg.log.Error("panic recovered, label: %s, errmsg: %s, stack: %s", label, err.Error(), stackStr)
		} else {
			logger.Error("panic recovered, label: %s, errmsg: %s, stack: %s", label, err.Error(), stackStr)
		}
		return
	}

	if cfg.log != nil {
		cfg.log.Error("panic recovered, label: %s, reason: %v, stack: %s", label, reason, stackStr)
	} else {
		logger.Error("panic recovered, label: %s, reason: %v, stack: %s", label, reason, stackStr)
	}
}

// safeOnPanic calls cfg.onPanic inside its own recover so a buggy callback can
// never crash the process.
func safeOnPanic(cfg *config, label string, pi PanicInfo) {
	defer func() {
		if r := recover(); r != nil {
			log.Printf(
				"[safe] panic in OnPanic callback, label: %s, callbackPanic: %v, originalReason: %v, stack: %s",
				label, r, pi.Reason, string(pi.Stack),
			)
		}
	}()

	cfg.onPanic(pi)
}

func safeWarn(cfg *config, format string, args ...any) {
	defer func() {
		if r := recover(); r != nil {
			log.Printf("[safe] logger panic while writing warning: "+format, args...)
		}
	}()

	if cfg.log != nil {
		cfg.log.Warn(format, args...)
		return
	}

	logger.Warn(format, args...)
}

func safeSanitize(
	s PanicSanitizer,
	reason any,
	stack []byte,
	label string,
) (safeReason any, safeStack []byte) {
	safeReason = reason
	safeStack = stack

	defer func() {
		if r := recover(); r != nil {
			log.Printf(
				"[safe] panic in PanicSanitizer, label: %s, sanitizerPanic: %v",
				label, r,
			)
			safeReason = reason
			safeStack = stack
		}
	}()

	return s(reason, stack)
}

// handlePanic processes a recovered panic: truncate stack, sanitize, log, notify, and optionally re-panic.
//
// Flow: debug.Stack → copyStack (1st truncation) → sanitizer → re-truncation → log → onPanic → repanic.
// The original (unsanitized) reason is kept for maybeRepanic so that callers' recover() sees the real value.
func handlePanic(cfg *config, opCtx context.Context, ctxForPanic bool, mode execMode, reason any) {
	full := debug.Stack()
	stack, truncated := copyStack(full, cfg.stackMaxBytes)
	label := cfg.label

	if label == "" {
		label = "-"
	}

	recoveredAt := time.Now()
	finalReason := reason
	finalStack := stack

	if cfg.sanitizer != nil {
		finalReason, finalStack = safeSanitize(cfg.sanitizer, reason, stack, label)
		// Re-truncate: the sanitizer may return a longer stack than stackMaxBytes allows.
		var reTruncated bool
		finalStack, reTruncated = copyStack(finalStack, cfg.stackMaxBytes)
		if reTruncated {
			truncated = true
		}
	}

	stackStr := string(finalStack)
	safeLog(cfg, label, stackStr, finalReason)

	pi := PanicInfo{
		Reason:      finalReason,
		Stack:       finalStack,
		Truncated:   truncated,
		RecoveredAt: recoveredAt,
	}

	if ctxForPanic {
		pi.Ctx = opCtx
	}

	if cfg.onPanic != nil {
		safeOnPanic(cfg, label, pi)
	}

	maybeRepanic(cfg, label, mode, reason)
}

// maybeRepanic re-panics with the original (unsanitized) reason in synchronous mode.
// In async mode the request is silently ignored with a warning, because re-panicking
// inside a goroutine would crash the entire process.
func maybeRepanic(cfg *config, label string, mode execMode, reason any) {
	if !cfg.repanic {
		return
	}

	if mode == execModeAsync {
		safeWarn(cfg, "WithRepanic is ignored in async mode, label: %s", label)
		return
	}

	panic(reason)
}

func copyStack(full []byte, max int) ([]byte, bool) {
	if max <= 0 || len(full) <= max {
		return cloneBytes(full), false
	}

	out := cloneBytes(full[:max])
	if max > len(shortTruncationSuffix) {
		copy(out[max-len(shortTruncationSuffix):], shortTruncationSuffix)
	}
	return out, true
}

func cloneBytes(src []byte) []byte {
	out := make([]byte, len(src))
	copy(out, src)
	return out
}
