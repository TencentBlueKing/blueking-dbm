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

package workflow

import (
	"testing"
)

// generateDoubleCheckID must be deterministic: repeated calls with the same
// (switchID, bkCloudID, ip) return the same id, so all instances on the same
// machine within one switch request share a single id.
func TestGenerateDoubleCheckID_Deterministic(t *testing.T) {
	const (
		switchID  = "switch-001"
		bkCloudID = 0
		ip        = "1.1.1.1"
	)

	want := generateDoubleCheckID(switchID, bkCloudID, ip)
	for i := 0; i < 100; i++ {
		if got := generateDoubleCheckID(switchID, bkCloudID, ip); got != want {
			t.Fatalf("not deterministic: call %d got %d, want %d", i, got, want)
		}
	}
}

// generateDoubleCheckID must distinguish different switch requests, cloud ids and ips.
func TestGenerateDoubleCheckID_Distinct(t *testing.T) {
	base := generateDoubleCheckID("switch-001", 0, "1.1.1.1")

	cases := map[string]int64{
		"different switchID":  generateDoubleCheckID("switch-002", 0, "1.1.1.1"),
		"different bkCloudID": generateDoubleCheckID("switch-001", 1, "1.1.1.1"),
		"different ip":        generateDoubleCheckID("switch-001", 0, "1.1.1.2"),
	}

	for name, got := range cases {
		if got == base {
			t.Errorf("%s: expected a different id from base %d, got the same", name, base)
		}
	}
}

// generateDoubleCheckID must never return 0 (0 is reserved for "uninitialized")
// and must always be a positive int64.
func TestGenerateDoubleCheckID_PositiveNonZero(t *testing.T) {
	switchIDs := []string{"", "s", "switch-001", "a-very-long-switch-id-value-1234567890"}
	ips := []string{"", "0.0.0.0", "10.0.0.1", "255.255.255.255"}
	cloudIDs := []int{0, 1, 1000}

	for _, switchID := range switchIDs {
		for _, ip := range ips {
			for _, cloudID := range cloudIDs {
				id := generateDoubleCheckID(switchID, cloudID, ip)
				if id <= 0 {
					t.Errorf("generateDoubleCheckID(%q, %d, %q) = %d, want positive non-zero",
						switchID, cloudID, ip, id)
				}
			}
		}
	}
}
