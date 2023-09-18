package lock

import (
	"fmt"
	"math/rand"
	"time"
)

// TryLocker TODO
type TryLocker interface {
	TryLock() error
	Unlock() error
}

// NewSpinLock 自旋锁
func NewSpinLock(lock TryLocker, spinTries int, spinInterval time.Duration) *SpinLock {
	return &SpinLock{
		lock:         lock,
		spinTries:    spinTries,
		spinInterval: spinInterval,
	}
}

// SpinLock TODO
type SpinLock struct {
	lock         TryLocker
	spinTries    int
	spinInterval time.Duration
}

// Lock TODO
func (l *SpinLock) Lock() error {
	for i := 0; i < l.spinTries; i++ {
		var err error
		if err = l.lock.TryLock(); err == nil {
			return nil
		}
		time.Sleep(l.spinInterval)
		time.Sleep(time.Duration(rand.Intn(1000)) * time.Millisecond)
	}
	return fmt.Errorf("spin lock failed after %f seconds", float64(l.spinTries)*l.spinInterval.Seconds())
}

// Unlock TODO
func (l *SpinLock) Unlock() error {
	return l.lock.Unlock()
}
