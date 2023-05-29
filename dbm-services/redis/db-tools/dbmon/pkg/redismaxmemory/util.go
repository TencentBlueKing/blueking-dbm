package redismaxmemory

import (
	"sync"

	"github.com/dustin/go-humanize"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
)

var thresholdOnce sync.Once
var thresholdValue uint64

// GetUsedMemoryChangeThreshold get used memory change threshold
func GetUsedMemoryChangeThreshold(conf *config.Configuration) float64 {
	thresholdOnce.Do(func() {
		var err error
		if conf.RedisMaxmemorySet.UsedMemoryChangeThreshold == "" {
			thresholdValue = 200 * consts.MiByte
		} else {
			thresholdValue, err = humanize.ParseBytes(conf.RedisMaxmemorySet.UsedMemoryChangeThreshold)
			if err != nil {
				thresholdValue = 200 * consts.MiByte
			}
		}
	})
	return float64(thresholdValue)
}

// GetUsedMemoryChangePercent TODO
func GetUsedMemoryChangePercent(conf *config.Configuration) float64 {
	if conf.RedisMaxmemorySet.UsedMemoryChangePercent != 0 {
		return float64(conf.RedisMaxmemorySet.UsedMemoryChangePercent)
	}
	return 20
}
