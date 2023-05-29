package osutil

import (
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"time"
)

// TruncateFile TODO
func TruncateFile(file string, bwlimitMB int) error {
	f, err := os.OpenFile(file, os.O_RDWR, 0666)
	if err != nil {
		return err
	}

	defer f.Close()

	fi, err := os.Stat(file)
	if err != nil {
		return err
	}
	totalSize := fi.Size()
	chunkSizeEverySec := bwlimitMB * 1024 * 1024

	// 1s执行多次, >=1, <= 1000
	batchEverySec := 10

	// 每次清理大小
	chunkSize := chunkSizeEverySec / batchEverySec
	// 每次清理间隔
	chunkInterval := 1000 / batchEverySec // 1000 毫秒
	logger.Info("bwlimitMB: %d, chunkSize: %d bytes, chunkInterval: %d ms, ", bwlimitMB, chunkSize, chunkInterval)

	done := make(chan int, 1)
	defer close(done)
	go func(chan int) {
		PrintFileSizeIncr(file, 1, 10, logger.Info, done)
	}(done)
	var endOffset int64 = totalSize
	for {
		endOffset -= int64(chunkSize)
		if endOffset <= 0 {
			break
		}
		if err := f.Truncate(endOffset); err != nil {
			return err
		}
		time.Sleep(time.Duration(chunkInterval) * time.Millisecond)
	}
	// f.Truncate(0)
	f.Seek(0, 0)
	f.Sync()
	if err := os.Remove(file); err != nil {
		return err
	}
	return nil
}

// TruncateDir TODO
func TruncateDir(path string, bwlimitMB int) error {
	LargeFile := int64(500 * 1024 * 1024) // 超过 500MB，我们认为是大文件，采用 truncate 方式删除
	fs, _ := ioutil.ReadDir(path)
	for _, file := range fs {
		fullFile := filepath.Join(path, file.Name())
		if file.IsDir() {
			fmt.Printf("path %s is dir, ignore\n", fullFile)
			continue
		} else {
			fmt.Println(path + file.Name())
			f, e := os.Stat(filepath.Join(path, file.Name()))
			if e != nil {
				return e
			}
			if f.Size() > LargeFile {
				if err := TruncateFile(fullFile, bwlimitMB); err != nil {
					return err
				} else {
					if err := os.Remove(fullFile); err != nil {
						return err
					}
				}
			}
		}
	}
	return nil
}
