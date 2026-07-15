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
	"errors"
	"unsafe"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"golang.org/x/sys/windows"
)

func stopEventName(pidFile string) string {
	return DeriveEventName(EventKeyFromPidFile(pidFile), stopEventSuffix)
}

func reloadEventName(pidFile string) string {
	return DeriveEventName(EventKeyFromPidFile(pidFile), reloadEventSuffix)
}

// setStopEvent opens the target process's named stop event and signals it. A
// missing event object means no process is listening, which is treated as
// "not running" (equivalent to the Unix ErrProcessNotRunning path).
func setStopEvent(pidFile string) error {
	return setNamedEvent(stopEventName(pidFile))
}

// setReloadEvent opens the target process's named reload event and signals it.
func setReloadEvent(pidFile string) error {
	return setNamedEvent(reloadEventName(pidFile))
}

func setNamedEvent(name string) error {
	namePtr, err := windows.UTF16PtrFromString(name)
	if err != nil {
		return gerrors.NewE(gerrors.Failure, err)
	}
	h, err := windows.OpenEvent(windows.EVENT_MODIFY_STATE, false, namePtr)
	if err != nil {
		if errors.Is(err, windows.ERROR_FILE_NOT_FOUND) {
			return ErrProcessNotRunning
		}
		return gerrors.NewE(gerrors.Failure, err)
	}
	defer windows.CloseHandle(h)

	if err := windows.SetEvent(h); err != nil {
		return gerrors.NewE(gerrors.Failure, err)
	}
	return nil
}

// eventSecurityAttributes returns a SECURITY_ATTRIBUTES for Global\ events:
// SYSTEM and Administrators get full access; Authenticated Users get
// EVENT_MODIFY_STATE|SYNCHRONIZE so an interactive stop/reload can OpenEvent
// a Session-0 SYSTEM-owned probe.
func eventSecurityAttributes() (*windows.SecurityAttributes, error) {
	// EVENT_MODIFY_STATE=0x0002, SYNCHRONIZE=0x00100000 → 0x00100002
	const sddl = "D:(A;;GA;;;SY)(A;;GA;;;BA)(A;;0x00100002;;;AU)"
	sd, err := windows.SecurityDescriptorFromString(sddl)
	if err != nil {
		return nil, gerrors.NewE(gerrors.Failure, err)
	}
	return &windows.SecurityAttributes{
		Length:             uint32(unsafe.Sizeof(windows.SecurityAttributes{})),
		SecurityDescriptor: sd,
		InheritHandle:      0,
	}, nil
}

// createManualResetEvent creates (or opens) a manual-reset named event, initially
// non-signaled. Manual-reset is required because both the guard and worker wait
// on the same stop event; an auto-reset event would only wake one of them.
//
// If the object already existed, CreateEvent returns the existing handle without
// resetting its state. A previous run's stop event may still be signaled if a
// handle to it is briefly open elsewhere; starting on such a stale signaled event
// would make the new process observe "stop" immediately and self-terminate
// (notably on restart / fast relaunch). To avoid this we reset the event once
// when it already existed, guaranteeing a clean non-signaled start.
func createManualResetEvent(name string) (windows.Handle, error) {
	namePtr, err := windows.UTF16PtrFromString(name)
	if err != nil {
		return 0, gerrors.NewE(gerrors.Failure, err)
	}

	sa, err := eventSecurityAttributes()
	if err != nil {
		return 0, err
	}

	// manualReset=1, initialState=0 (non-signaled).
	h, err := windows.CreateEvent(sa, 1, 0, namePtr)
	if err != nil {
		if errors.Is(err, windows.ERROR_ALREADY_EXISTS) && h != 0 {
			if rerr := windows.ResetEvent(h); rerr != nil {
				windows.CloseHandle(h)
				return 0, gerrors.NewE(gerrors.Failure, rerr)
			}
			return h, nil
		}
		return 0, gerrors.NewE(gerrors.Failure, err)
	}
	return h, nil
}
