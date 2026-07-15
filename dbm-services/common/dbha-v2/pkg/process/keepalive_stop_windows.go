//go:build windows

/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 */

package process

// SignalKeepaliveStop sets the Global keepalive stop event for addr.
func SignalKeepaliveStop(addr string) error {
	return setNamedEvent(DeriveEventName(addr, stopEventSuffix))
}
