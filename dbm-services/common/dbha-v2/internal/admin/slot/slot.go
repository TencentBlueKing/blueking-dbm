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

// Package slot provides a generic resource slot used by admin hot-reload.
//
// Framework contracts (enforced by tests and comments):
//  1. Fingerprint return values must not contain map/slice (or other reference) types.
//  2. Build must release any partially created resources on failure.
//  3. Build must not touch the previous generation; components that need cross-generation
//     reuse (gRPC listener reuse) should implement Ops by hand instead of Slot[T].
package slot

import (
	"context"
	"fmt"
	"reflect"
	"sync"
	"sync/atomic"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/logger"
)

// SwapPolicy selects how Rebuild transitions from the current generation to the next.
type SwapPolicy int

const (
	// SwapCoexist builds the next generation first, swaps the pointer, then closes the old one.
	SwapCoexist SwapPolicy = iota
	// SwapReplace closes the old generation first, then builds the next. On Build failure it
	// attempts an in-place recovery using the previous curCfg.
	SwapReplace
)

// DefaultRetireWait is how long Rebuild waits for the previous generation's async Close
// before proceeding. Prevents unbounded stacking of retiring generations under rapid reload.
const DefaultRetireWait = 3 * time.Second

// Spec declares how a resource type is fingerprinted, built, closed, and swapped.
type Spec[T any] struct {
	Name        string
	Fingerprint func(config.Configuration) any
	Build       func(context.Context, config.Configuration) (*T, error)
	Close       func(context.Context, *T)
	Swap        func(old, next config.Configuration) SwapPolicy
}

// Ops is the non-generic interface the reload orchestrator drives.
type Ops interface {
	Name() string
	NeedsRebuild(next config.Configuration) bool
	Rebuild(ctx context.Context, next config.Configuration) error
	Close(ctx context.Context)
}

// Slot holds the current generation of a resource and owns its rebuild lifecycle.
type Slot[T any] struct {
	spec       Spec[T]
	current    atomic.Pointer[T]
	fp         any
	curCfg     config.Configuration
	mu         sync.Mutex
	retireDone chan struct{} // closed when the in-flight retire finishes; nil if idle
	retireWait time.Duration
}

// New creates a Slot from Spec. The slot starts empty; call Rebuild to build the first generation.
func New[T any](spec Spec[T]) *Slot[T] {
	if spec.Swap == nil {
		spec.Swap = AlwaysCoexist
	}
	return &Slot[T]{
		spec:       spec,
		retireWait: DefaultRetireWait,
	}
}

// AlwaysCoexist is a Swap helper for resources that can overlap during rebuild.
func AlwaysCoexist(_, _ config.Configuration) SwapPolicy { return SwapCoexist }

// AlwaysReplace is a Swap helper for resources that cannot overlap (e.g. same listen address).
func AlwaysReplace(_, _ config.Configuration) SwapPolicy { return SwapReplace }

// Get returns the current generation, or nil if the slot is empty.
func (s *Slot[T]) Get() *T {
	return s.current.Load()
}

// Name returns the slot name.
func (s *Slot[T]) Name() string { return s.spec.Name }

// NeedsRebuild reports whether next differs from the fingerprint of the current generation.
// An empty slot always needs a rebuild.
func (s *Slot[T]) NeedsRebuild(next config.Configuration) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.current.Load() == nil && s.fp == nil {
		return true
	}
	return !reflect.DeepEqual(s.fp, s.spec.Fingerprint(next))
}

// Rebuild builds or replaces the current generation according to Swap.
// fp and curCfg are updated only after a successful generation change (except Replace recovery,
// which restores current but leaves fp/curCfg unchanged so the next reload retries).
func (s *Slot[T]) Rebuild(ctx context.Context, next config.Configuration) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if err := s.waitRetireLocked(ctx); err != nil {
		logger.Warn("slot retire wait failed, slot: %s, errmsg: %s", s.spec.Name, err)
		return err
	}

	policy := SwapCoexist
	if s.current.Load() != nil {
		policy = s.spec.Swap(s.curCfg, next)
	}

	switch policy {
	case SwapReplace:
		return s.rebuildReplaceLocked(ctx, next)
	default:
		return s.rebuildCoexistLocked(ctx, next)
	}
}

// Close stops the current generation and waits for any in-flight retire (best-effort).
func (s *Slot[T]) Close(ctx context.Context) {
	s.mu.Lock()
	defer s.mu.Unlock()

	_ = s.waitRetireLocked(ctx)

	cur := s.current.Swap(nil)
	if cur != nil && s.spec.Close != nil {
		s.spec.Close(ctx, cur)
	}
	s.fp = nil
}

func (s *Slot[T]) rebuildCoexistLocked(ctx context.Context, next config.Configuration) error {
	built, err := s.spec.Build(ctx, next)
	if err != nil {
		return err
	}
	old := s.current.Swap(built)
	s.fp = s.spec.Fingerprint(next)
	s.curCfg = next
	if old != nil {
		s.startRetireLocked(old)
	}
	return nil
}

func (s *Slot[T]) rebuildReplaceLocked(ctx context.Context, next config.Configuration) error {
	old := s.current.Swap(nil)
	if old != nil && s.spec.Close != nil {
		// Replace must release the old resource synchronously (e.g. free a listen port).
		s.spec.Close(ctx, old)
	}

	built, err := s.spec.Build(ctx, next)
	if err != nil {
		recovered, rerr := s.spec.Build(ctx, s.curCfg)
		if rerr != nil {
			return fmt.Errorf(
				"slot %s replace failed, errmsg: %w; recover failed, errmsg: %s",
				s.spec.Name, err, rerr,
			)
		}
		s.current.Store(recovered)
		// fp and curCfg stay on the old values so NeedsRebuild remains true.
		return fmt.Errorf(
			"slot %s replace failed after close, recovered previous config, errmsg: %w",
			s.spec.Name, err,
		)
	}

	s.current.Store(built)
	s.fp = s.spec.Fingerprint(next)
	s.curCfg = next
	return nil
}

func (s *Slot[T]) startRetireLocked(old *T) {
	done := make(chan struct{})
	s.retireDone = done
	closeFn := s.spec.Close
	go func() {
		defer close(done)
		if closeFn != nil {
			closeFn(context.Background(), old)
		}
	}()
}

func (s *Slot[T]) waitRetireLocked(ctx context.Context) error {
	done := s.retireDone
	if done == nil {
		return nil
	}
	wait := s.retireWait
	if wait <= 0 {
		wait = DefaultRetireWait
	}
	timer := time.NewTimer(wait)
	defer timer.Stop()

	select {
	case <-done:
		s.retireDone = nil
		return nil
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return fmt.Errorf("retire wait timed out after %s", wait)
	}
}

// Ensure Slot implements Ops.
var _ Ops = (*Slot[struct{}])(nil)
