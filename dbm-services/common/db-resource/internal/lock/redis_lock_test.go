package lock_test

import (
	"testing"
	"time"

	"dbm-services/common/db-resource/internal/lock"
	"dbm-services/common/go-pubpkg/cmutil"
)

func TestRedisLock(t *testing.T) {
	t.Log("start testing...")
	// lock.InitRedisDb()
	l := lock.NewSpinLock(&lock.RedisLock{
		Name:    "Tendb",
		RandKey: cmutil.RandStr(16),
		Expiry:  10 * time.Second,
	}, 30, 1*time.Second)
	for i := 0; i < 20; i++ {
		go func(j int) {
			if err := l.Lock(); err != nil {
				t.Log(j, "lock failed")
				return
			}
			t.Log(j, "lock success")
			time.Sleep(100 * time.Millisecond)
			l.Unlock()
		}(i)
	}

	time.Sleep(20 * time.Second)
}
