package consts

import "errors"

// ErrMarkFailed mark as failed, you can retry or skip
var ErrMarkFailed = errors.New("success, but mark as failed, you can retry or skip")
