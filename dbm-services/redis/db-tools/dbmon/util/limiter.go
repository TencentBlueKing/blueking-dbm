package util

import (
	"sync"
	"time"
)

// FixedWindowLimiter 固定窗口限流器
type FixedWindowLimiter struct {
	limit    int           // 窗口请求上限
	window   time.Duration // 窗口时间大小
	counter  int           // 计数器
	lastTime time.Time     // 上一次请求的时间
	mutex    sync.Mutex    // 避免并发问题
}

func NewFixedWindowLimiter(limit int, window time.Duration) *FixedWindowLimiter {
	return &FixedWindowLimiter{
		limit:    limit,
		window:   window,
		lastTime: time.Now(),
	}
}

func (l *FixedWindowLimiter) TryAcquire() bool {
	l.mutex.Lock()
	defer l.mutex.Unlock()
	// 获取当前时间
	now := time.Now()
	// 如果当前窗口失效，计数器清0，开启新的窗口
	if now.Sub(l.lastTime) > l.window {
		l.counter = 0
		l.lastTime = now
	}
	// 若到达窗口请求上限，请求失败
	if l.counter >= l.limit {
		return false
	}
	// 若没到窗口请求上限，计数器+1，请求成功
	l.counter++
	return true
}
