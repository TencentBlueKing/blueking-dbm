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

package hamodel

import "testing"

func TestActionScopeTypeIsKnown(t *testing.T) {
	known := []ActionScopeType{
		ActionScopeTypeCluster, ActionScopeTypeHost, ActionScopeTypeDbInstance,
	}
	for _, scope := range known {
		if !scope.IsKnown() {
			t.Errorf("ActionScopeType %q should be known", scope)
		}
	}
	notKnown := []ActionScopeType{
		ActionScopeTypeNone, ActionScopeTypeUnknown, "", ActionScopeType("bogus"),
	}
	for _, scope := range notKnown {
		if scope.IsKnown() {
			t.Errorf("ActionScopeType %q should not be known", scope)
		}
	}
	if _, ok := ActionScopeTypeMap[ActionScopeTypeUnknown]; ok {
		t.Fatal("ActionScopeTypeUnknown must not be accepted as a strategy scope")
	}
}

func TestActionScopeTypeNormalize(t *testing.T) {
	cases := []struct {
		in   ActionScopeType
		want ActionScopeType
	}{
		{in: ActionScopeTypeCluster, want: ActionScopeTypeCluster},
		{in: ActionScopeTypeHost, want: ActionScopeTypeHost},
		{in: ActionScopeTypeDbInstance, want: ActionScopeTypeDbInstance},
		{in: ActionScopeTypeNone, want: ActionScopeTypeUnknown},
		{in: ActionScopeTypeUnknown, want: ActionScopeTypeUnknown},
		{in: "", want: ActionScopeTypeUnknown},
		{in: ActionScopeType("bogus"), want: ActionScopeTypeUnknown},
	}
	for _, tc := range cases {
		if got := tc.in.Normalize(); got != tc.want {
			t.Errorf("ActionScopeType(%q).Normalize()=%q, want %q", tc.in, got, tc.want)
		}
	}
}
