//go:build unix

/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 */

package process

import (
	"os"
	"syscall"
)

// SignalKeepaliveStop is a no-op on Unix; callers use TermKeepaliveProc then force-kill.
func SignalKeepaliveStop(_ string) error {
	return nil
}

// TermKeepaliveProc requests graceful termination of a keepalive process (SIGTERM).
// Callers should wait briefly and force-kill survivors.
func TermKeepaliveProc(proc *os.Process) error {
	if proc == nil {
		return nil
	}
	return proc.Signal(syscall.SIGTERM)
}
