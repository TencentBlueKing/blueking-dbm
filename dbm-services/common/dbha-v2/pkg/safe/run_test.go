package safe

import (
	"context"
	"errors"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"go.uber.org/zap"
)

func TestRun_OnPanicNilCtx(t *testing.T) {
	t.Parallel()
	var got PanicInfo
	Run(
		func() { panic("boom") },
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	if got.Ctx != nil {
		t.Fatalf("expected nil Ctx from Run, got: %v", got.Ctx)
	}
	if got.Reason != "boom" {
		t.Fatalf("unexpected reason: %v", got.Reason)
	}
	if len(got.Stack) == 0 {
		t.Fatal("expected non-empty stack")
	}
	if got.Truncated {
		t.Fatal("expected non-truncated stack by default")
	}
	if got.RecoveredAt.IsZero() {
		t.Fatal("expected RecoveredAt to be set")
	}
}

func TestRun_Repanic(t *testing.T) {
	t.Parallel()
	defer func() {
		if recover() == nil {
			t.Fatal("expected repanic")
		}
	}()
	Run(func() { panic("x") }, WithRepanic(true))
}

func TestGoCtx_OnPanicCtx(t *testing.T) {
	t.Parallel()
	type ctxKey struct{}
	ctx := context.WithValue(context.Background(), ctxKey{}, "v")
	done := make(chan PanicInfo, 1)
	GoCtx(
		ctx,
		func() { panic(errors.New("e")) },
		WithOnPanic(func(p PanicInfo) { done <- p }),
	)
	select {
	case p := <-done:
		if p.Ctx != ctx {
			t.Fatal("PanicInfo.Ctx should match GoCtx argument")
		}
		if p.Reason == nil {
			t.Fatal("expected reason")
		}
	case <-time.After(2 * time.Second):
		t.Fatal("timeout waiting for goroutine")
	}
}

func TestWithStackMaxBytes(t *testing.T) {
	t.Parallel()
	var got PanicInfo
	Run(
		func() { panic("z") },
		WithStackMaxBytes(64),
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	if len(got.Stack) != 64 {
		t.Fatalf("expected stack len 64, got: %d", len(got.Stack))
	}
	if !got.Truncated {
		t.Fatal("expected Truncated=true when stackMaxBytes clips the stack")
	}
}

func TestRun_OnPanicCallbackPanic_DoesNotCrash(t *testing.T) {
	t.Parallel()
	Run(
		func() { panic("original") },
		WithOnPanic(func(p PanicInfo) {
			panic("callback-panic")
		}),
		WithLabel("callback-crash-test"),
	)
}

func TestGo_OnPanicCallbackPanic_DoesNotCrash(t *testing.T) {
	t.Parallel()
	callbackEntered := make(chan struct{}, 1)
	wait := GoWait(
		func() { panic("original") },
		WithOnPanic(func(p PanicInfo) {
			callbackEntered <- struct{}{}
			panic("callback-panic")
		}),
		WithLabel("go-callback-crash-test"),
	)
	wait()
	select {
	case <-callbackEntered:
	default:
		t.Fatal("onPanic callback was never entered")
	}
}

func TestGoWait_NoPanic(t *testing.T) {
	t.Parallel()
	var called int32
	wait := GoWait(func() {
		atomic.StoreInt32(&called, 1)
	})
	wait()
	if atomic.LoadInt32(&called) != 1 {
		t.Fatal("fn was not called")
	}
}

func TestGoWait_Panic(t *testing.T) {
	t.Parallel()
	var got PanicInfo
	wait := GoWait(
		func() { panic("wait-boom") },
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	wait()
	if got.Reason != "wait-boom" {
		t.Fatalf("unexpected reason: %v", got.Reason)
	}
}

func TestGoWait_RepanicIgnoredInAsyncMode(t *testing.T) {
	t.Parallel()
	mock := &warnLogger{}
	var got PanicInfo
	wait := GoWait(
		func() { panic("async-boom") },
		WithLogger(mock),
		WithRepanic(true),
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	wait()
	if got.Reason != "async-boom" {
		t.Fatalf("unexpected reason: %v", got.Reason)
	}
	if !mock.warnCalled {
		t.Fatal("expected async repanic warning to be logged")
	}
}

func TestGoWaits_NoPanic(t *testing.T) {
	t.Parallel()
	var called int32
	wait := GoWaits([]func(){
		func() { atomic.StoreInt32(&called, 1) },
	})
	wait()
	if atomic.LoadInt32(&called) != 1 {
		t.Fatal("fn was not called")
	}
}

func TestGoWaits_EmptyFns(t *testing.T) {
	t.Parallel()
	var called int32
	wait := GoWaits([]func(){})
	wait()
	if atomic.LoadInt32(&called) != 0 {
		t.Fatal("fn was not called")
	}
}

func TestGoWaits_Panic(t *testing.T) {
	t.Parallel()
	var got PanicInfo
	wait := GoWaits(
		[]func(){
			func() { panic("wait-boom") },
		},
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	wait()
	if got.Reason != "wait-boom" {
		t.Fatalf("unexpected reason: %v", got.Reason)
	}
}

func TestGoWaits_RepanicIgnoredInAsyncMode(t *testing.T) {
	t.Parallel()
	mock := &warnLogger{}
	var got PanicInfo
	wait := GoWaits(
		[]func(){
			func() { panic("async-boom") },
		},
		WithLogger(mock),
		WithRepanic(true),
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	wait()
	if got.Reason != "async-boom" {
		t.Fatalf("unexpected reason: %v", got.Reason)
	}
	if !mock.warnCalled {
		t.Fatal("expected async repanic warning to be logged")
	}
}

func TestGoCtxWait_NoPanic(t *testing.T) {
	t.Parallel()
	var called int32
	ctx := context.Background()
	wait := GoCtxWait(ctx, func() {
		atomic.StoreInt32(&called, 1)
	})
	wait()
	if atomic.LoadInt32(&called) != 1 {
		t.Fatal("fn was not called")
	}
}

func TestGoCtxWait_Panic(t *testing.T) {
	t.Parallel()
	type ctxKey struct{}
	ctx := context.WithValue(context.Background(), ctxKey{}, "val")
	var got PanicInfo
	wait := GoCtxWait(
		ctx,
		func() { panic("ctx-wait-boom") },
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	wait()
	if got.Reason != "ctx-wait-boom" {
		t.Fatalf("unexpected reason: %v", got.Reason)
	}
	if got.Ctx != ctx {
		t.Fatal("PanicInfo.Ctx should match GoCtxWait argument")
	}
}

func TestGoCtxWait_NilCtx(t *testing.T) {
	t.Parallel()
	var got PanicInfo
	wait := GoCtxWait(
		nil,
		func() { panic("nil-ctx") },
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	wait()
	if got.Ctx == nil {
		t.Fatal("nil ctx should be replaced with context.Background()")
	}
}

type panicLogger struct{}

func (panicLogger) OriginLogger() *zap.Logger { return zap.NewNop() }
func (panicLogger) Debug(string, ...any)      {}
func (panicLogger) Info(string, ...any)       {}
func (panicLogger) Warn(string, ...any)       {}
func (panicLogger) Error(string, ...any)      { panic("logger-exploded") }
func (panicLogger) Fatal(string, ...any)      {}

type warnLogger struct {
	warnCalled bool
}

func (w *warnLogger) OriginLogger() *zap.Logger { return zap.NewNop() }
func (w *warnLogger) Debug(string, ...any)      {}
func (w *warnLogger) Info(string, ...any)       {}
func (w *warnLogger) Warn(string, ...any)       { w.warnCalled = true }
func (w *warnLogger) Error(string, ...any)      {}
func (w *warnLogger) Fatal(string, ...any)      {}

func TestRun_LoggerPanic_DoesNotCrash(t *testing.T) {
	t.Parallel()
	Run(
		func() { panic("trigger") },
		WithLogger(panicLogger{}),
		WithLabel("broken-logger"),
	)
}

func TestRun_NoPanic(t *testing.T) {
	t.Parallel()
	var called int32
	Run(func() {
		atomic.StoreInt32(&called, 1)
	})
	if atomic.LoadInt32(&called) != 1 {
		t.Fatal("fn was not called")
	}
}

func TestGo_NoPanic(t *testing.T) {
	t.Parallel()
	done := make(chan struct{})
	Go(func() {
		close(done)
	})
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("timeout: fn was not called")
	}
}

func TestGoCtx_NoPanic(t *testing.T) {
	t.Parallel()
	done := make(chan struct{})
	GoCtx(context.Background(), func() {
		close(done)
	})
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("timeout: fn was not called")
	}
}

func TestCopyStack_TruncatesAndFlags(t *testing.T) {
	t.Parallel()
	got, truncated := copyStack([]byte("abcdefghijklmnopqrstuvwxyz"), 10)
	if !truncated {
		t.Fatal("expected truncated=true")
	}
	if len(got) != 10 {
		t.Fatalf("expected len 10, got: %d", len(got))
	}
	if !strings.HasSuffix(string(got), shortTruncationSuffix) {
		t.Fatalf("expected short truncation suffix, got: %q", string(got))
	}
}

func TestCopyStack_NoTruncationWhenSmallEnough(t *testing.T) {
	t.Parallel()
	full := []byte("abcdefghijklmnopqrstuvwxyz")
	got, truncated := copyStack(full, 0)
	if truncated {
		t.Fatal("expected truncated=false when max=0")
	}
	if string(got) != string(full) {
		t.Fatalf("unexpected stack: %q", string(got))
	}
}

func TestCopyStack_TinyMaxKeepsRealPrefix(t *testing.T) {
	t.Parallel()
	got, truncated := copyStack([]byte("abcdefghijklmnopqrstuvwxyz"), 2)
	if !truncated {
		t.Fatal("expected truncated=true")
	}
	if string(got) != "ab" {
		t.Fatalf("expected real stack prefix, got: %q", string(got))
	}
}

func TestFormatPanicInfo(t *testing.T) {
	t.Parallel()
	recoveredAt := time.Date(2026, 4, 15, 11, 30, 0, 0, time.UTC)
	pi := PanicInfo{
		Reason:      "test-reason",
		Stack:       []byte("goroutine 1 [running]:\nmain.go:10"),
		Truncated:   true,
		RecoveredAt: recoveredAt,
	}
	s := FormatPanicInfo(pi)
	if !strings.Contains(s, "test-reason") {
		t.Fatalf("expected reason in output: %s", s)
	}
	if !strings.Contains(s, "truncated: true") {
		t.Fatalf("expected truncated marker in output: %s", s)
	}
	if !strings.Contains(s, recoveredAt.Format(time.RFC3339)) {
		t.Fatalf("expected recovered time in output: %s", s)
	}
}

func TestWithLabel(t *testing.T) {
	t.Parallel()
	var got PanicInfo
	Run(
		func() { panic("labeled") },
		WithLabel("my-task"),
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	if got.Reason != "labeled" {
		t.Fatalf("unexpected reason: %v", got.Reason)
	}
}

func TestGo_Panic_OnPanic(t *testing.T) {
	t.Parallel()
	done := make(chan PanicInfo, 1)
	Go(
		func() { panic("go-boom") },
		WithOnPanic(func(p PanicInfo) { done <- p }),
	)
	select {
	case p := <-done:
		if p.Reason != "go-boom" {
			t.Fatalf("unexpected reason: %v", p.Reason)
		}
		if p.Ctx != nil {
			t.Fatal("Go should have nil Ctx in PanicInfo")
		}
	case <-time.After(2 * time.Second):
		t.Fatal("timeout waiting for goroutine panic")
	}
}

func TestNilOption(t *testing.T) {
	t.Parallel()
	Run(func() { panic("nil-opt") }, nil, WithOnPanic(func(p PanicInfo) {}), nil)
}

func TestSanitizerApplied(t *testing.T) {
	t.Parallel()
	var got PanicInfo
	Run(
		func() { panic("secret-token") },
		WithPanicSanitizer(func(reason any, stack []byte) (any, []byte) {
			return "masked", []byte("masked-stack")
		}),
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	if got.Reason != "masked" {
		t.Fatalf("unexpected reason: %v", got.Reason)
	}
	if string(got.Stack) != "masked-stack" {
		t.Fatalf("unexpected stack: %s", string(got.Stack))
	}
}

func TestSanitizerPanicDoesNotCrash(t *testing.T) {
	t.Parallel()
	var got PanicInfo
	Run(
		func() { panic("boom") },
		WithPanicSanitizer(func(reason any, stack []byte) (any, []byte) {
			panic("sanitize-panic")
		}),
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	if got.Reason != "boom" {
		t.Fatalf("unexpected reason: %v", got.Reason)
	}
	if len(got.Stack) == 0 {
		t.Fatal("expected original stack after sanitizer panic")
	}
}

func TestSanitizerStackReTruncated(t *testing.T) {
	t.Parallel()
	const maxBytes = 32
	var got PanicInfo
	Run(
		func() { panic("x") },
		WithStackMaxBytes(maxBytes),
		WithPanicSanitizer(func(reason any, stack []byte) (any, []byte) {
			// Return a stack much longer than maxBytes to verify re-truncation.
			longStack := make([]byte, 1024)
			for i := range longStack {
				longStack[i] = 'S'
			}
			return reason, longStack
		}),
		WithOnPanic(func(p PanicInfo) { got = p }),
	)
	if len(got.Stack) != maxBytes {
		t.Fatalf("expected stack len %d after re-truncation, got: %d", maxBytes, len(got.Stack))
	}
	if !got.Truncated {
		t.Fatal("expected Truncated=true when sanitizer output exceeds stackMaxBytes")
	}
}

func TestRepanicUsesOriginalReason(t *testing.T) {
	t.Parallel()
	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected repanic")
		}
		// The re-panicked value must be the original, not sanitized.
		if r != "original-secret" {
			t.Fatalf("expected original reason in repanic, got: %v", r)
		}
	}()
	Run(
		func() { panic("original-secret") },
		WithPanicSanitizer(func(reason any, stack []byte) (any, []byte) {
			return "redacted", []byte("redacted-stack")
		}),
		WithRepanic(true),
	)
}
