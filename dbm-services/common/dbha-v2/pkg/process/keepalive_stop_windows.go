//go:build windows

/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 */

package process

import "os"

// SignalKeepaliveStop sets the Global keepalive stop event for addr.
func SignalKeepaliveStop(addr string) error {
	return setNamedEvent(DeriveEventName(addr, stopEventSuffix))
}

// TermKeepaliveProc is a no-op on Windows: graceful stop is already requested via
// the named stop event (SignalKeepaliveStop). Callers still force-kill survivors.
func TermKeepaliveProc(_ *os.Process) error {
	return nil
}
