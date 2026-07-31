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

package switchcore

import (
	"testing"
)

// stubSwitchInstance is a local mock SwitchableInstance for hostSwitchGroupKey tests.
type stubSwitchInstance struct {
	BaseSwitchInstance
}

func (s *stubSwitchInstance) DoSwitch() error { return nil }

type scopedStubSwitchInstance struct {
	stubSwitchInstance
	scope  string
	shared bool
}

func (s *scopedStubSwitchInstance) HostSwitchGroupScope() (string, bool) {
	return s.scope, s.shared
}

func TestHostSwitchGroupKey_SharedScope(t *testing.T) {
	ins := &scopedStubSwitchInstance{
		stubSwitchInstance: stubSwitchInstance{
			BaseSwitchInstance: BaseSwitchInstance{BkCloudID: 1, ClusterID: 10},
		},
		scope:  "remote",
		shared: true,
	}
	instKey := GenerateMetadataKey(1, "127.0.0.1", 3306)
	got := hostSwitchGroupKey(instKey, ins)
	want := "1:10|remote"
	if got != want {
		t.Errorf("hostSwitchGroupKey = %q, want %q", got, want)
	}
}

func TestHostSwitchGroupKey_PerInstance(t *testing.T) {
	ins := &stubSwitchInstance{
		BaseSwitchInstance: BaseSwitchInstance{BkCloudID: 1, ClusterID: 10},
	}
	instKey := GenerateMetadataKey(1, "127.0.0.1", 3306)
	got := hostSwitchGroupKey(instKey, ins)
	want := "1:10|" + string(instKey)
	if got != want {
		t.Errorf("hostSwitchGroupKey = %q, want %q", got, want)
	}
}

func TestHostSwitchGroupKey_EmptyScopeFallsBack(t *testing.T) {
	ins := &scopedStubSwitchInstance{
		stubSwitchInstance: stubSwitchInstance{
			BaseSwitchInstance: BaseSwitchInstance{BkCloudID: 2, ClusterID: 20},
		},
		scope:  "",
		shared: true,
	}
	instKey := GenerateMetadataKey(2, "127.0.0.2", 3306)
	got := hostSwitchGroupKey(instKey, ins)
	want := "2:20|" + string(instKey)
	if got != want {
		t.Errorf("hostSwitchGroupKey = %q, want %q", got, want)
	}
}
