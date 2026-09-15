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

package slot

import (
	"context"
	"errors"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/config"

	"github.com/stretchr/testify/require"
)

type res struct {
	id     int
	closed atomic.Bool
}

func TestCoexistKeepsOldOnBuildFailure(t *testing.T) {
	var builds atomic.Int32
	s := New(Spec[res]{
		Name:        "coexist",
		Fingerprint: func(c config.Configuration) any { return c.Apm.ListenAddress },
		Build: func(_ context.Context, c config.Configuration) (*res, error) {
			n := int(builds.Add(1))
			if c.Apm.ListenAddress == "bad" {
				return nil, errors.New("build failed")
			}
			return &res{id: n}, nil
		},
		Close: func(_ context.Context, r *res) { r.closed.Store(true) },
		Swap:  AlwaysCoexist,
	})

	cfg1 := config.Configuration{Apm: config.ApmConfig{ListenAddress: "127.0.0.1:1"}}
	require.NoError(t, s.Rebuild(context.Background(), cfg1))
	first := s.Get()
	require.NotNil(t, first)

	cfgBad := config.Configuration{Apm: config.ApmConfig{ListenAddress: "bad"}}
	require.Error(t, s.Rebuild(context.Background(), cfgBad))
	require.Same(t, first, s.Get())
	require.False(t, first.closed.Load())
	require.True(t, s.NeedsRebuild(cfgBad))
}

func TestCoexistSwapsAndRetiresOld(t *testing.T) {
	var builds atomic.Int32
	s := New(Spec[res]{
		Name:        "coexist-ok",
		Fingerprint: func(c config.Configuration) any { return c.Apm.ListenAddress },
		Build: func(_ context.Context, c config.Configuration) (*res, error) {
			return &res{id: int(builds.Add(1))}, nil
		},
		Close: func(_ context.Context, r *res) {
			time.Sleep(20 * time.Millisecond)
			r.closed.Store(true)
		},
		Swap: AlwaysCoexist,
	})
	s.retireWait = time.Second

	cfg1 := config.Configuration{Apm: config.ApmConfig{ListenAddress: "127.0.0.1:1"}}
	cfg2 := config.Configuration{Apm: config.ApmConfig{ListenAddress: "127.0.0.1:2"}}
	require.NoError(t, s.Rebuild(context.Background(), cfg1))
	first := s.Get()
	require.NoError(t, s.Rebuild(context.Background(), cfg2))
	second := s.Get()
	require.NotSame(t, first, second)

	require.Eventually(t, func() bool { return first.closed.Load() }, time.Second, 10*time.Millisecond)
	require.False(t, second.closed.Load())
}

func TestReplaceRecoversPreviousConfig(t *testing.T) {
	var builds atomic.Int32
	s := New(Spec[res]{
		Name:        "replace",
		Fingerprint: func(c config.Configuration) any { return c.Web.ListenAddress },
		Build: func(_ context.Context, c config.Configuration) (*res, error) {
			n := int(builds.Add(1))
			if c.Web.ListenAddress == "bad" {
				return nil, errors.New("cannot bind")
			}
			return &res{id: n}, nil
		},
		Close: func(_ context.Context, r *res) { r.closed.Store(true) },
		Swap:  AlwaysReplace,
	})

	cfg1 := config.Configuration{Web: config.WebConfig{ListenAddress: "127.0.0.1:1"}}
	require.NoError(t, s.Rebuild(context.Background(), cfg1))
	first := s.Get()
	require.NotNil(t, first)

	cfgBad := config.Configuration{Web: config.WebConfig{ListenAddress: "bad"}}
	err := s.Rebuild(context.Background(), cfgBad)
	require.Error(t, err)
	recovered := s.Get()
	require.NotNil(t, recovered)
	require.True(t, first.closed.Load(), "old generation closed before replace build")
	require.NotSame(t, first, recovered, "recovery builds a new object from curCfg")
	require.True(t, s.NeedsRebuild(cfgBad), "fp stays old so reload retries")
}

func TestCoexistRetireTimeoutDoesNotStackGenerations(t *testing.T) {
	var builds atomic.Int32
	var retiring atomic.Int32
	s := New(Spec[res]{
		Name:        "coexist-retire",
		Fingerprint: func(c config.Configuration) any { return c.Apm.ListenAddress },
		Build: func(_ context.Context, _ config.Configuration) (*res, error) {
			return &res{id: int(builds.Add(1))}, nil
		},
		Close: func(_ context.Context, r *res) {
			retiring.Add(1)
			time.Sleep(200 * time.Millisecond)
			r.closed.Store(true)
			retiring.Add(-1)
		},
		Swap: AlwaysCoexist,
	})
	s.retireWait = 50 * time.Millisecond

	cfg1 := config.Configuration{Apm: config.ApmConfig{ListenAddress: "127.0.0.1:1"}}
	cfg2 := config.Configuration{Apm: config.ApmConfig{ListenAddress: "127.0.0.1:2"}}
	cfg3 := config.Configuration{Apm: config.ApmConfig{ListenAddress: "127.0.0.1:3"}}
	require.NoError(t, s.Rebuild(context.Background(), cfg1))
	first := s.Get()
	require.NoError(t, s.Rebuild(context.Background(), cfg2))
	second := s.Get()
	require.NotSame(t, first, second)

	err := s.Rebuild(context.Background(), cfg3)
	require.Error(t, err)
	require.Same(t, second, s.Get())
	require.LessOrEqual(t, retiring.Load(), int32(1), "only one generation may retire at a time")

	require.Eventually(t, func() bool { return first.closed.Load() }, time.Second, 10*time.Millisecond)
	require.NoError(t, s.Rebuild(context.Background(), cfg3))
	third := s.Get()
	require.NotSame(t, second, third)
	require.Eventually(t, func() bool { return second.closed.Load() }, time.Second, 10*time.Millisecond)
}

func TestReplaceRecoverFailureLeavesSlotEmpty(t *testing.T) {
	var builds atomic.Int32
	s := New(Spec[res]{
		Name:        "replace-recover-fail",
		Fingerprint: func(c config.Configuration) any { return c.Web.ListenAddress },
		Build: func(_ context.Context, c config.Configuration) (*res, error) {
			n := int(builds.Add(1))
			if n == 1 {
				return &res{id: n}, nil
			}
			return nil, errors.New("cannot bind")
		},
		Close: func(_ context.Context, r *res) { r.closed.Store(true) },
		Swap:  AlwaysReplace,
	})

	cfg1 := config.Configuration{Web: config.WebConfig{ListenAddress: "127.0.0.1:1"}}
	require.NoError(t, s.Rebuild(context.Background(), cfg1))
	require.NotNil(t, s.Get())

	cfgBad := config.Configuration{Web: config.WebConfig{ListenAddress: "127.0.0.1:2"}}
	err := s.Rebuild(context.Background(), cfgBad)
	require.Error(t, err)
	require.Contains(t, err.Error(), "recover failed")
	require.Nil(t, s.Get())
	require.True(t, s.NeedsRebuild(cfgBad))
}

func TestNeedsRebuildFalseWhenUnchanged(t *testing.T) {
	s := New(Spec[res]{
		Name:        "fp",
		Fingerprint: func(c config.Configuration) any { return c.Apm },
		Build:       func(_ context.Context, _ config.Configuration) (*res, error) { return &res{id: 1}, nil },
		Close:       func(_ context.Context, _ *res) {},
		Swap:        AlwaysCoexist,
	})
	cfg := config.Configuration{Apm: config.ApmConfig{ListenAddress: "127.0.0.1:9"}}
	require.NoError(t, s.Rebuild(context.Background(), cfg))
	require.False(t, s.NeedsRebuild(cfg))
	cfg2 := cfg
	cfg2.Apm.ListenAddress = "127.0.0.1:10"
	require.True(t, s.NeedsRebuild(cfg2))
}
