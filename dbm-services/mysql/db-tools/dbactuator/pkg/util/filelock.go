package util

import (
	"fmt"
	"io/ioutil"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gofrs/flock"
	"github.com/pkg/errors"
)

// FLock TODO
type FLock struct {
	fileName     string
	file         *os.File
	filedataName string
	filedata     *os.File
	filedataMax  int
}

// NewFlock TODO
func NewFlock(filename string, maxConn int) (*FLock, error) {
	// maxConn cannot be 0

	// check filedataName lastModifyTime
	// 如果 filedataName 文件最后修改时间在 1h 以前，删掉这个文件

	if strings.ContainsAny(filename, " ;'\"") {
		// 非法文件名
		return nil, fmt.Errorf("illegal filename:%s", filename)
	} else if maxConn == 0 {
		return nil, fmt.Errorf("illegal maxConn:%d", maxConn)
	}

	filedataName := filename + ".data"
	if ok, mtimeInt := GetFileModifyTime(filedataName); ok {
		curTime := time.Now()
		mtime := time.Unix(mtimeInt, 0)
		timeDiff := curTime.Sub(mtime)
		if timeDiff.Minutes() > 60 {
			os.Remove(filedataName)
		}
	}

	fl := &FLock{
		fileName:     filename,
		filedataName: filedataName,
		filedataMax:  maxConn,
	}

	return fl, nil
}

// FileFlock TODO
func (fl *FLock) FileFlock() (locked bool, err error) {
	if fl.fileName == "" {
		return false, errors.New("fileLock filename canot be empty")
	}
	fileLock := flock.New(fl.fileName)
	return fileLock.TryLock()
}

// FileUnlock TODO
func (fl *FLock) FileUnlock() error {
	fileLock := flock.New(fl.fileName)
	return fileLock.Unlock()
}

// SetFileLockIncr TODO
func (fl *FLock) SetFileLockIncr(incr int) (succ int, err error) {
	f, err := os.OpenFile(fl.filedataName, os.O_CREATE|os.O_RDWR, 0644)
	if err == nil {
		defer f.Close()
	}
	content, err := ioutil.ReadAll(f)
	contentStr := strings.Trim(strings.ReplaceAll(string(content), " ", ""), "\n")
	if err != nil {
		return -1, fmt.Errorf(`io error:%v`, err.Error())
	} else if contentStr == "" {
		contentStr = fmt.Sprintf(`%d:0`, fl.filedataMax)
	}
	concurrent := strings.Split(contentStr, ":")
	if len(concurrent) != 2 {
		return -1, fmt.Errorf(`error:contentStr=%s`, contentStr)
	}
	maxNum, err1 := strconv.Atoi(concurrent[0])
	CurNum, err2 := strconv.Atoi(concurrent[1])
	if err1 == nil && err2 == nil {
		CurNum += incr
		if CurNum > maxNum && incr > 0 {
			// lock fail
			return 0, nil
		}
		if CurNum < 0 {
			CurNum = 0
		}
		contentStr = fmt.Sprintf(`%d:%d`, maxNum, CurNum)
		f.Seek(0, 0)
		f.Truncate(0)
		f.WriteString(contentStr)
		return 1, nil
	} else {
		return -1, fmt.Errorf(`error:contentStr=%s`, contentStr)
	}
}

// FileIncrSafe TODO
// retryInterval: 如果获取锁失败，下次重试间隔（秒）。为 0 时表示不重试，麻烦返回获取锁失败
// retcode:
// 1: success incr
// 0: full
// -1: operation failed
func (fl *FLock) FileIncrSafe(incr int, retryInterval int) (succ int, err error) {
	intvl := time.Duration(retryInterval)

	fileLock := flock.New(fl.fileName)
	locked, err := fileLock.TryLock()

	if err != nil {
		// handle locking error
		return -1, errors.New(fmt.Sprintf("failed to get lock: %s", err.Error()))
	}
	if locked {
		// open and incr 1 and close
		succ, err2 := fl.SetFileLockIncr(incr)
		fileLock.Unlock()
		if succ == 1 {
			/*
				if err = fileLock.Unlock(); err != nil {
					// handle unlock error
					return false, errors.New(fmt.Sprintf(`failed to unlock: %s`, err.Error()))
				}
			*/
			return 1, nil
		} else if succ == 0 {
			if retryInterval == 0 {
				return 0, nil
			} else {
				time.Sleep(intvl * time.Second)
				return fl.FileIncrSafe(incr, retryInterval)
			}
		} else {
			return -1, errors.New(fmt.Sprintf("failed to incr: %s", err2.Error()))
		}

	} else {
		// wait and retry
		if retryInterval == 0 {
			return 0, nil
		} else {
			// lockWaitMs := IntnRange(500, 3000)
			// time.Sleep(time.Duration(lockWaitMs) * time.Millisecond)
			time.Sleep(time.Duration(IntnRange(500, 3000)) * time.Millisecond)
			return fl.FileIncrSafe(incr, retryInterval)
		}
	}
}

// FileUnlockIncr TODO
func (fl *FLock) FileUnlockIncr(filename string) error {
	fileLock := flock.New(filename)
	return fileLock.Unlock()
}

// Test TODO
func Test() {
	filename := "flashback.lock"
	maxConn := 4
	fl, err := NewFlock(filename, maxConn)
	if err != nil {
		fmt.Println(err)
		return
	}

	wg := &sync.WaitGroup{}
	for i := 0; i <= 8; i++ {
		fmt.Println(i)
		wg.Add(1)
		go func(i int) {
			time.Sleep(time.Duration(IntnRange(100, 2000)) * time.Millisecond)
			defer wg.Done()
			// 这个 retryInterval 尽量跟单个任务处理时间接近
			if succ, err := fl.FileIncrSafe(1, 20); succ == 1 {
				// do
				fmt.Printf("id=%d\n", i)
				time.Sleep(20 * time.Second)
				fl.FileIncrSafe(-1, 1)
			} else if err != nil {
				fmt.Printf("id=%d err=%v\n", i, err.Error())
			}
		}(i)
	}
	wg.Wait()
}
