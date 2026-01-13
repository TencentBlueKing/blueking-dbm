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
	"testing"
)

func TestStatus_String(t *testing.T) {
	tests := []struct {
		status Status
		want   string
	}{
		{StatusRunning, "running"},
		{StatusStopped, "stopped"},
	}

	for _, tt := range tests {
		t.Run(tt.want, func(t *testing.T) {
			if got := tt.status.String(); got != tt.want {
				t.Fatalf("Status.String() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestHealthInfo_IsAlive(t *testing.T) {
	tests := []struct {
		name   string
		health HealthInfo
		want   bool
	}{
		{
			name: "running",
			health: HealthInfo{
				Pid:      1234,
				ProcName: "test",
				Status:   StatusRunning,
			},
			want: true,
		},
		{
			name: "stopped",
			health: HealthInfo{
				Pid:      1234,
				ProcName: "test",
				Status:   StatusStopped,
			},
			want: false,
		},
		{
			name: "empty_status",
			health: HealthInfo{
				Pid:      1234,
				ProcName: "test",
				Status:   "",
			},
			want: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.health.IsAlive(); got != tt.want {
				t.Fatalf("HealthInfo.IsAlive() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestHealthInfo_Fields(t *testing.T) {
	health := HealthInfo{
		Pid:      1234,
		ProcName: "test-process",
		Status:   StatusRunning,
		ErrMsg:   "no error",
	}

	if health.Pid != 1234 {
		t.Fatalf("Pid = %v, want 1234", health.Pid)
	}
	if health.ProcName != "test-process" {
		t.Fatalf("ProcName = %v, want test-process", health.ProcName)
	}
	if health.Status != StatusRunning {
		t.Fatalf("Status = %v, want running", health.Status)
	}
	if health.ErrMsg != "no error" {
		t.Fatalf("ErrMsg = %v, want no error", health.ErrMsg)
	}
}

func TestStatusConstants(t *testing.T) {
	if StatusRunning != "running" {
		t.Fatalf("StatusRunning = %v, want running", StatusRunning)
	}
	if StatusStopped != "stopped" {
		t.Fatalf("StatusStopped = %v, want stopped", StatusStopped)
	}
}
