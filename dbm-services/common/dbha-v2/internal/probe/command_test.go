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

package probe

import (
	"testing"

	"dbm-services/common/dbha-v2/internal/probe/cmds"
)

// TestGenConfigCmdLockTimeoutFlag guards the flag gen-config uses to bound the wait
// for the output file lock: dropping it would silently fall back to cobra's zero
// value and make the write unbounded from the caller's point of view.
func TestGenConfigCmdLockTimeoutFlag(t *testing.T) {
	flag := GenConfigCmd.Flags().Lookup("lock-timeout")
	if flag == nil {
		t.Fatal("gen-config must expose a lock-timeout flag")
	}

	got, err := GenConfigCmd.Flags().GetDuration("lock-timeout")
	if err != nil {
		t.Fatalf("read lock-timeout: %v", err)
	}
	if got != cmds.DefaultGenConfigLockTimeout {
		t.Fatalf("unexpected default, got: %s, want: %s", got, cmds.DefaultGenConfigLockTimeout)
	}
}

// TestGenConfigCmdClearPortFlag guards the flag that drops ports from the generated
// config. It must default to empty so callers that omit it keep the previous output.
func TestGenConfigCmdClearPortFlag(t *testing.T) {
	if GenConfigCmd.Flags().Lookup("clear-port") == nil {
		t.Fatal("gen-config must expose a clear-port flag")
	}

	got, err := GenConfigCmd.Flags().GetString("clear-port")
	if err != nil {
		t.Fatalf("read clear-port: %v", err)
	}
	if got != "" {
		t.Fatalf("unexpected default, got: %q, want empty", got)
	}
}

// TestGenConfigCmdReloadFlag guards the flag that signals the running probe after
// the config file is written. It must default to false so gen-config keeps leaving
// the running process untouched.
func TestGenConfigCmdReloadFlag(t *testing.T) {
	if GenConfigCmd.Flags().Lookup("reload") == nil {
		t.Fatal("gen-config must expose a reload flag")
	}

	got, err := GenConfigCmd.Flags().GetBool("reload")
	if err != nil {
		t.Fatalf("read reload: %v", err)
	}
	if got {
		t.Fatal("unexpected default, got: true, want: false")
	}
}
