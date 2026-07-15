//go:build unix

/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 */

package process

// SignalKeepaliveStop is a no-op on Unix; callers force-kill by PID.
func SignalKeepaliveStop(_ string) error {
	return nil
}
