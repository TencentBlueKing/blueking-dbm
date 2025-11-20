package config

import (
	"time"

	"golang.org/x/time/rate"
)

var GlobalLimiter *rate.Limiter

func InitGlobalLimiter() {
	GlobalLimiter = rate.NewLimiter(
		rate.Every(
			time.Duration(1000*1000/RuntimeConfig.Concurrent)*time.Microsecond),
		1,
	)
}
