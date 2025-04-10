// Package session 用于实现一个简单的线程池，用于控制后台任务
package session

import (
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// Job is a routine that can be run and stopped.
type Job interface {
	Run(startWg *sync.WaitGroup, logger *slog.Logger) error
	Stop()
	SendMsg(in []byte) (n int, err error)
	ReceiveMsg(timeout int64) (out []byte, err error)
}

// MySession is a go routine.
type MySession struct {
	logger       *slog.Logger
	Name         string
	stopped      bool
	deleted      bool
	stoppedMutex sync.Mutex
	job          Job
	RunningLock  sync.Mutex // 同一时刻只能有一个routine在运行
	LastRunTime  time.Time
}

// Run starts the routine.
func (r *MySession) Run(j Job) error {
	r.stoppedMutex.Lock()
	defer r.stoppedMutex.Unlock()
	if !r.stopped {
		r.logger.Info(fmt.Sprintf("routine %s is already running", r.Name))
		return nil
	}

	r.logger.Info(fmt.Sprintf("start %s", r.Name))
	r.job = j
	wg := sync.WaitGroup{}
	wg.Add(1)
	errChan := make(chan error, 1)
	go func() {
		r.stopped = false
		err := r.job.Run(&wg, r.logger)
		if err != nil {
			errChan <- err
			r.logger.Info(fmt.Sprintf("routine %s done, err: %s", r.Name, err))
			wg.Done()
		}
		// todo: 这里不加锁有风险吗？
		r.stopped = true
	}()
	wg.Wait() // wait for the routine to start. 最多2秒.
	select {
	case err := <-errChan:
		r.logger.Info(fmt.Sprintf("routine %s done, err: %s", r.Name, err))
		return err
	default:
		r.logger.Info(fmt.Sprintf("routine %s started", r.Name))
		return nil
	}
}

// IsTimeout todo check if the routine is timeout.
func (r *MySession) IsTimeout(timeoutSecond int64) bool {
	if time.Now().Sub(r.LastRunTime) > time.Duration(timeoutSecond)*time.Second {
		return true
	}
	return false
}

// IsStopped stops the routine.
func (r *MySession) IsStopped() bool {
	r.stoppedMutex.Lock()
	defer r.stoppedMutex.Unlock()
	return r.stopped
}

// Stop stops the routine.
func (r *MySession) Stop() {
	r.stoppedMutex.Lock()
	defer r.stoppedMutex.Unlock()
	if r.stopped {
		return
	}
	// try to stop the routine. may be failed.
	r.job.Stop()
	// set stopped flag
	r.stopped = true
}

// SendMsg send request to routine.
func (r *MySession) SendMsg(in []byte) (n int, err error) {
	if !r.stoppedMutex.TryLock() {
		return 0, fmt.Errorf("busy")
	}
	defer r.stoppedMutex.Unlock()
	if r.stopped {
		return 0, fmt.Errorf("routine %s is stopped", r.Name)
	}
	// try to stop the routine. may be failed.
	return r.job.SendMsg(in)
}

// ReceiveMsg read response from routine.
func (r *MySession) ReceiveMsg(timeout int64) (out []byte, err error) {
	r.stoppedMutex.Lock()
	defer r.stoppedMutex.Unlock()
	if r.stopped {
		return nil, fmt.Errorf("routine %s is stopped", r.Name)
	}
	// try to stop the routine. may be failed.
	return r.job.ReceiveMsg(timeout)
}

// Pool is a collection of routines.
type Pool struct {
	routines map[string]*MySession
	logger   *slog.Logger
	mutex    sync.Mutex
}

// NewPool creates a new Pool.
func NewPool(logger *slog.Logger) *Pool {
	return &Pool{
		routines: make(map[string]*MySession, 0),
		logger:   logger,
	}
}

// CheckTimeout checks if any routine is timeout.
func (p *Pool) CheckTimeout(timeout int64) {
	ticker := time.NewTicker(time.Duration(timeout) * time.Second)
	for range ticker.C {
		// p.logger.Info("check timeout start", slog.Int("timeout", int(timeout)))
		t := time.Now()
		p.mutex.Lock()
		var stopped []string
		var runningCount int
		for _, r := range p.routines {
			if r.IsTimeout(timeout) {
				p.logger.Info(fmt.Sprintf("routine %s is stopped by timeout", r.Name))
				r.Stop()
				delete(p.routines, r.Name)
				stopped = append(stopped, r.Name)
			} else if r.IsStopped() {
				p.logger.Info(fmt.Sprintf("routine %s is stopped", r.Name))
				stopped = append(stopped, r.Name)
				delete(p.routines, r.Name)
			} else {
				runningCount++
			}
		}
		p.mutex.Unlock()
		p.logger.Info("check timeout",
			slog.Int("timeout", int(timeout)),
			slog.String("elapsed", fmt.Sprintf("%0.6f seconds", time.Since(t).Seconds())),
			slog.Int("stopped_count", len(stopped)),
			slog.Int("running_count", runningCount),
			slog.String("stopped", fmt.Sprintf("%+v", stopped)))

	}
}

// Add adds a routine to the pool.
func (p *Pool) Add(name string) *MySession {
	p.mutex.Lock()
	defer p.mutex.Unlock()
	// check if routine already exists
	if _, ok := p.routines[name]; !ok {
		p.routines[name] = &MySession{
			Name:         name,
			stopped:      true,
			stoppedMutex: sync.Mutex{},
			logger:       p.logger.With(slog.String("routine", name)),
			RunningLock:  sync.Mutex{},
		}
	}
	return p.routines[name]
}

func (p *Pool) find(name string) *MySession {
	p.mutex.Lock()
	defer p.mutex.Unlock()
	if r, ok := p.routines[name]; ok {
		return r
	}
	return nil
}

// Stop stops a routine in the pool.
func (p *Pool) Stop(name string) {
	var r = p.find(name)
	if r == nil {
		p.logger.Warn(fmt.Sprintf("routine %s not found\n", name))
		return
	}
	r.Stop()
}

// RemoveStopped removes a routine from the pool if it is stopped.
func (p *Pool) RemoveStopped(name string) error {
	var r = p.find(name)
	if r == nil {
		return fmt.Errorf("routine %s not found", name)
	}
	if !r.IsStopped() {
		return fmt.Errorf("routine %s is not stopped", name)
	}
	// remove from pool
	p.mutex.Lock()
	defer p.mutex.Unlock()
	delete(p.routines, name)
	return nil
}

// Status prints the status of all routines in the pool.
func (p *Pool) Status() {
	p.logger.Info(fmt.Sprintf("len(p.routines): %d", len(p.routines)))
	for i, r := range p.routines {
		p.logger.Info(fmt.Sprintf("routine idx:%d %s %+v", i, r.Name, r))
	}
}

// GetRoutineNames  prints the status of all routines in the pool.
func (p *Pool) GetRoutineNames() []string {
	p.mutex.Lock()
	defer p.mutex.Unlock()
	var names []string
	for _, r := range p.routines {
		names = append(names, r.Name)
	}
	return names
}
