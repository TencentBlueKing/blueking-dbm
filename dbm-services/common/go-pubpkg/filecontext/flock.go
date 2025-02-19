package filecontext

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

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// FLock 文件锁
// 可用于多进程间共享并发数，也可以简单控制进程间互斥
type FLock struct {
	fileName string
	//fileNameData string
	//fileData *os.File
	dataMax  int
	fileLock *flock.Flock
}

var ErrLockFull = errors.New("lock full")

// NewFlock	创建一个文件锁，用于多进程间共享并发数
// 如果 maxConn 为 0，表示不启用并发数控制，只用到文件锁本身
func NewFlock(filename string, maxConn int) (*FLock, error) {
	// check filedataName lastModifyTime
	// 如果 filedataName 文件最后修改时间在 1h 以前，删掉这个文件
	if strings.ContainsAny(filename, " ;'\"") {
		// 非法文件名
		return nil, fmt.Errorf("illegal filename:%s", filename)
	}
	if maxConn > 0 {
		filename = filename + ".data"
	}
	if ok, mtimeInt := cmutil.GetFileModifyTime(filename); ok {
		curTime := time.Now()
		mtime := time.Unix(mtimeInt, 0)
		timeDiff := curTime.Sub(mtime)
		if timeDiff.Minutes() > 60 {
			os.Remove(filename)
		}
	}

	fl := &FLock{
		fileName: filename,
		dataMax:  maxConn,
	}
	fl.fileLock = flock.New(fl.fileName)
	return fl, nil
}

// FileFlock 获取文件锁
func (fl *FLock) FileFlock() (locked bool, err error) {
	if fl.fileName == "" {
		return false, errors.New("fileLock filename canot be empty")
	}
	return fl.fileLock.TryLock()
}

// FileUnlock 释放文件锁
func (fl *FLock) FileUnlock() error {
	return fl.fileLock.Unlock()
}

// setFileLockIncr 在已经获得锁的情况下，执行操作（自增并发数）
func (fl *FLock) setFileLockIncr(incr int) (succ bool, err error) {
	f, err := os.OpenFile(fl.fileName, os.O_CREATE|os.O_RDWR, 0644)
	if err == nil {
		defer f.Close()
	}
	content, err := ioutil.ReadAll(f)
	contentStr := strings.Trim(strings.ReplaceAll(string(content), " ", ""), "\n")
	if err != nil {
		return false, fmt.Errorf(`io error:%v`, err.Error())
	} else if contentStr == "" {
		contentStr = fmt.Sprintf(`%d:0`, fl.dataMax)
	}
	concurrent := strings.Split(contentStr, ":")
	if len(concurrent) != 2 {
		return false, fmt.Errorf(`error:contentStr=%s`, contentStr)
	}
	maxNum, err1 := strconv.Atoi(concurrent[0])
	CurNum, err2 := strconv.Atoi(concurrent[1])
	if err1 == nil && err2 == nil {
		CurNum += incr
		if CurNum > maxNum && incr > 0 {
			// lock fail because lock full
			return false, errors.WithMessage(ErrLockFull, contentStr)
		}
		if CurNum < 0 {
			CurNum = 0
		}
		contentStr = fmt.Sprintf(`%d:%d`, maxNum, CurNum)
		f.Seek(0, 0)
		f.Truncate(0)
		f.WriteString(contentStr)
		return true, nil
	} else {
		return false, fmt.Errorf(`error:contentStr=%s`, contentStr)
	}
}

// FileIncrSafe
// retryIntervalWhenFull: 如果当前并发数已满，则等待多少秒。同时用于判断，如果获取 flock 失败，是否重试
// 如果 retryIntervalWhenFull > 0，会一直重试
// succ: true: 成功，false: 失败
// 失败返回可能因为获取不到锁，可能因为并发数已满(retryIntervalWhenFull>0时)
// 即如果 retryIntervalWhenFull>0 则如果失败则阻塞，直到成功
func (fl *FLock) FileIncrSafe(incr int, retryIntervalWhenFull int) (succ bool, err error) {
	locked, err := fl.fileLock.TryLock()
	if err != nil {
		return false, errors.WithMessagef(err, "get lock has unknown error: %s", fl.fileName)
	}
	if locked {
		// open and incr 1 and close
		succ, err2 := fl.setFileLockIncr(incr)
		fl.fileLock.Unlock()
		if succ {
			return true, nil
		} else if errors.Is(err2, ErrLockFull) { // lock full
			if retryIntervalWhenFull == 0 {
				return false, err2
			} else {
				//logInfoFunc("failed to get lock: %s, retry after %d seconds", fl.fileName, intvl)
				logger.Info(fmt.Sprintf("lock data full: %s, retry after %d seconds",
					fl.fileName, retryIntervalWhenFull))
				time.Sleep(time.Duration(retryIntervalWhenFull) * time.Second)
				return fl.FileIncrSafe(incr, retryIntervalWhenFull)
			}
		} else {
			return false, errors.WithMessage(err2, "unknown error to incr")
		}

	} else {
		// 获取文件锁失败，wait and retry
		if retryIntervalWhenFull == 0 {
			return false, fmt.Errorf("failed to get lock: %s", fl.fileName)
		} else {
			// 随机休眠 500-3000 ms，再尝试获取flock，直到成功
			retryIntervalWhenLockFail := cmutil.IntnRange(500, 3000)
			logger.Info(fmt.Sprintf("get filelock failed: %s, retry after %d mills",
				fl.fileName, retryIntervalWhenLockFail))
			time.Sleep(time.Duration(retryIntervalWhenLockFail) * time.Millisecond)
			return fl.FileIncrSafe(incr, retryIntervalWhenFull)
		}
	}
	//return 1, nil
}

func (fl *FLock) Add(incr int) error {
	_, err := fl.FileIncrSafe(incr, 10)
	return err
}

func (fl *FLock) Done() error {
	_, err := fl.FileIncrSafe(-1, 10)
	return err
}

func test1() {
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
			time.Sleep(time.Duration(cmutil.IntnRange(100, 2000)) * time.Millisecond)
			defer wg.Done()
			// 这个 retryInterval 尽量跟单个任务处理时间接近
			if succ, err := fl.FileIncrSafe(1, 20); succ {
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
