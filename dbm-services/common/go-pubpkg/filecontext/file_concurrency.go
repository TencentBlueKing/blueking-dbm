package filecontext

import (
	"encoding/gob"
	"fmt"
	"os"
	"time"

	"github.com/gofrs/flock"
	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// Concurrency is a concurrency control struct.
type Concurrency struct {
	Max     int `json:"max" yaml:"max" mapstructure:"max"`
	Current int `json:"current" yaml:"current" mapstructure:"current"`
}

// IncrFileContext is a FileContext with concurrency control across processes.
type IncrFileContext struct {
	*FileContext
	key string
	max int
	//current int

	maxRetries    int
	retryInterval time.Duration
}

func NewIncrFile(contextFile string, max int, retryInterval time.Duration) (*IncrFileContext, error) {
	incrLockFile := IncrFileContext{max: max, maxRetries: 1, retryInterval: retryInterval}
	keyCurr := "current"
	keyMax := "max"
	fc := NewFileContext(contextFile)
	if fi, err := os.Stat(fc.contextFile); err == nil && fi != nil {
		if time.Now().Sub(fi.ModTime()).Seconds() > 60*60*24 {
			logger.Info("remove expired context file %s", fc.contextFile)
			err = os.Remove(fc.contextFile)
			if err != nil {
				return nil, errors.WithMessage(err, "remove expired context file")
			}
		}
	}
	if maxVal, err := fc.GetInt(keyMax); err != nil || maxVal == 0 {
		fc.Set(keyMax, max, false)
	}
	if _, err := fc.GetInt("current"); err != nil {
		fc.Set(keyCurr, 0, false)
	}
	if err := fc.Save(); err != nil {
		return nil, err
	}
	incrLockFile.FileContext = fc
	return &incrLockFile, nil
}

// TryIncr increments the value of the given key in the FileContext.
// None blocking if incr full
func (c *IncrFileContext) TryIncr(incr int) error {
	return c.IncrWithRetries(incr, 0)
}

// Incr increments the value of the given key in the FileContext.
// Blocking if incr full
func (c *IncrFileContext) Incr(incr int) error {
	return c.IncrWithRetries(incr, -1)
}

// IncrWithRetries increments the value of the given key in the FileContext.
// retryInterval set the interval between retries when lock full(not include get lock failed)
// maxRetries = 0: no retry
// maxRetries = -1: retry forever
// maxRetries > 0: retry times
func (c *IncrFileContext) IncrWithRetries(incr int, maxRetries int) error {
	keyCurr := "current"
	keyMax := "max"
	c.fl = flock.New(c.contextFile)
	lockSucc, err := c.fl.TryLock() // 因为其他进程已经获得锁，返回的是 err = nil
	if err != nil {
		// 可能因为文件权限或其他未知异常，导致的不可重试错误
		return fmt.Errorf("TryLock %s failed: %s", c.contextFile, err.Error())
	}
	if lockSucc {
		defer c.fl.Unlock()
	} else { // 获取文件锁失败，需要排队阻塞
		if maxRetries == 0 {
			return fmt.Errorf("file lock is acquired by other process: %s", c.contextFile)
		}
		if maxRetries > 1 || maxRetries < 0 {
			// 随机休眠 500-3000 ms，再尝试获取flock，直到成功
			retryIntervalWhenLockFail := cmutil.IntnRange(500, 3000)
			logger.Info("get file lock failed from %s, random sleep %d mills",
				c.contextFile, retryIntervalWhenLockFail)
			time.Sleep(time.Duration(retryIntervalWhenLockFail) * time.Millisecond)
			maxRetries--
			return c.IncrWithRetries(incr, maxRetries)
		} else {
			return fmt.Errorf("failed to acquire file lock after retries %s", c.contextFile)
		}
	}
	// 每次从磁盘文件获取
	if err := c.FileContext.decodeData(); err != nil {
		return err
	}
	curVal, err := c.GetInt(keyCurr)
	if err != nil { // will decode all data
		return err
	}
	maxVal, err := c.GetInt(keyMax)
	if err != nil {
		return err
	}

	if curVal+incr > maxVal && incr > 0 {
		if maxRetries == 0 {
			return fmt.Errorf("lock full: incr %s (%d+%d) > max %d",
				c.contextFile, curVal, incr, maxVal)
		}
		if maxRetries > 1 || maxRetries < 0 {
			c.fl.Unlock() // 在进入递归之前释放锁
			logger.Info("lock full: incr %s (%d+%d) > max %d, sleep %v secs",
				c.contextFile, curVal, incr, maxVal, c.retryInterval)
			time.Sleep(c.retryInterval)
			return c.IncrWithRetries(incr, maxRetries)
		}
	}
	return c.Set(keyCurr, curVal+incr, true)
}

func NewIncrFileWithKey(contextFile string, key string, max int, maxRetries int, retryInterval time.Duration) (*IncrFileContext, error) {
	if key == "" {
		return nil, fmt.Errorf("incr key is empty")
	}
	incrLockFile := IncrFileContext{key: key, max: max, maxRetries: maxRetries, retryInterval: retryInterval}

	fc := NewFileContext(contextFile)
	if fi, err := os.Stat(fc.contextFile); err == nil && fi != nil {
		if time.Now().Sub(fi.ModTime()).Seconds() > 60*60*24 {
			logger.Info("remove expired context file %s", fc.contextFile)
			err = os.Remove(fc.contextFile)
			if err != nil {
				return nil, errors.WithMessage(err, "remove expired context file")
			}
		}
	}

	conc := Concurrency{}
	if fc.format == FileCtxFormatGob {
		gob.Register(conc)
	}
	if !cmutil.FileExists(fc.contextFile) {
		conc.Max = max
	} else {
		if err := fc.GetValuePersistent(key, &conc); err != nil { // will decode all data
			return nil, err
		}
		if conc.Max == 0 {
			conc.Max = max
		}
	}

	if err := fc.Set(key, conc, true); err != nil {
		return nil, err
	}
	incrLockFile.FileContext = fc
	return &incrLockFile, nil
}

// IncrWithKey increments the value of the given key in the FileContext.
//
//	前提是 contextFile already exists
//
// retryInterval set the interval between retries when lock full(not include get lock failed)
// maxRetries = 0: no retry
// maxRetries = -1: retry forever
// maxRetries > 0: retry times
func (c *IncrFileContext) IncrWithKey(incr int, maxRetries int) error {
	if c.key == "" {
		return fmt.Errorf("incr key is empty")
	}
	c.fl = flock.New(c.contextFile)
	lockSucc, err := c.fl.TryLock() // 因为其他进程已经获得锁，返回的是 err = nil
	if err != nil {
		// 可能因为文件权限或文件不存在等错误，不可重试
		return fmt.Errorf("TryLock %s failed: %s", c.contextFile, err.Error())
	}
	if lockSucc {
		defer c.fl.Unlock()
	} else { // 获取文件锁失败，需要排队阻塞
		if maxRetries == 0 {
			return fmt.Errorf("file lock is acquired by other process: %s", c.contextFile)
		}
		if maxRetries > 1 || maxRetries < 0 {
			// 随机休眠 500-3000 ms，再尝试获取flock，直到成功
			retryIntervalWhenLockFail := cmutil.IntnRange(500, 3000)
			logger.Info("get file lock failed from %s, random sleep %d mills",
				c.contextFile, retryIntervalWhenLockFail)
			time.Sleep(time.Duration(retryIntervalWhenLockFail) * time.Millisecond)
			maxRetries--
			return c.IncrWithKey(incr, maxRetries)
		} else {
			return fmt.Errorf("failed to acquire file lock after retries %s", c.contextFile)
		}
	}

	conc := Concurrency{}
	if err = c.GetValuePersistent(c.key, &conc); err != nil { // will decode all data
		return err
	}
	conc.Current += incr
	if conc.Current > conc.Max && incr > 0 {
		if maxRetries == 0 {
			return fmt.Errorf("lock full(%s:%s): incr current %d > max %d",
				c.contextFile, c.key, conc.Current-1, conc.Max)
		}
		if maxRetries > 1 || maxRetries < 0 {
			c.fl.Unlock() // 在进入递归之前释放锁
			logger.Info("lock full(%s:%s): incr current %d > max %d, sleep %v secs",
				c.contextFile, c.key, conc.Current-1, conc.Max, c.retryInterval)
			time.Sleep(c.retryInterval)
			return c.IncrWithKey(incr, maxRetries)
		}
	}
	return c.Set(c.key, conc, true)
}
