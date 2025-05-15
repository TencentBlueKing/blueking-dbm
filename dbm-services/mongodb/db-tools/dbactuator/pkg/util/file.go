package util

import (
	"bufio"
	"bytes"
	"crypto/md5"
	"fmt"
	"io"
	"os"

	"github.com/pkg/errors"
)

// FileExists 检查path是否已经存在
func FileExists(path string) bool {
	_, err := os.Stat(path)
	if err != nil {
		return os.IsExist(err)
	}
	return true
}

// DirExists 检查目录是否已经存在
func DirExists(path string) bool {
	f, err := os.Stat(path)
	if err != nil {
		return os.IsExist(err)
	}
	return f.IsDir()
}

// GetFileMd5 求文件md5sum值
func GetFileMd5(fileAbPath string) (md5sum string, err error) {
	rFile, err := os.Open(fileAbPath)
	if err != nil {
		return "", fmt.Errorf("GetFileMd5 fail,err:%v,file:%s", err, fileAbPath)
	}
	defer func(rFile *os.File) {
		_ = rFile.Close()
	}(rFile)
	h := md5.New()
	if _, err := io.Copy(h, rFile); err != nil {
		return "", fmt.Errorf("GetFileMd5 io.Copy fail,err:%v,file:%s", err, fileAbPath)
	}
	return fmt.Sprintf("%x", h.Sum(nil)), nil
}

// FileLineCounter 计算文件行数
// 参考: https://stackoverflow.com/questions/24562942/golang-how-do-i-determine-the-number-of-lines-in-a-file-efficiently
func FileLineCounter(filename string) (lineCnt uint64, err error) {
	_, err = os.Stat(filename)
	if err != nil && os.IsNotExist(err) == true {
		return 0, fmt.Errorf("file:%s not exists", filename)
	}
	file, err := os.Open(filename)
	if err != nil {
		return 0, fmt.Errorf("file:%s open fail,err:%v", filename, err)
	}
	defer file.Close()
	reader01 := bufio.NewReader(file)
	buf := make([]byte, 32*1024)
	lineCnt = 0
	lineSep := []byte{'\n'}

	for {
		c, err := reader01.Read(buf)
		lineCnt += uint64(bytes.Count(buf[:c], lineSep))

		switch {
		case err == io.EOF:
			return lineCnt, nil

		case err != nil:
			return lineCnt, fmt.Errorf("file:%s read fail,err:%v", filename, err)
		}
	}
}

// GetLastLine 获取文件最后n行
func GetLastLine(filename string, n int) (lines []string, err error) {
	file, err := os.Open(filename)
	if err != nil {
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	var line string
	for scanner.Scan() {
		line = scanner.Text()
		lines = append(lines, line)
		if len(lines) > n {
			lines = lines[1:]
		}
	}
	err = scanner.Err()
	return
}

// TryDeleteBadLink 删除不存在的软链接
// 如果软链接不存在，直接返回 nil
// 如果软链接存在，检查软链接指向的文件是否存在, 不存在时删除软链接
func TryDeleteBadLink(linkPath string) (deleted bool, err error) {
	fileInfo, err := os.Lstat(linkPath)
	if err != nil {
		if os.IsNotExist(err) {
			// 链接不存在，直接返回true
			return true, nil
		}
		return false, err
	}

	// 2. 检查文件类型，如果不是软链接，直接返回ok
	if fileInfo.Mode()&os.ModeSymlink == 0 {
		return false, nil
	}

	// 3. 检查链接指向的目标是否存在
	targetPath, err := os.Readlink(linkPath)
	if err != nil {
		return false, fmt.Errorf("failed to read link: %v", err)
	}

	// 4. 判断目标文件是否存在
	if _, err := os.Stat(targetPath); os.IsNotExist(err) {
		// 目标不存在，删除链接
		if err := os.Remove(linkPath); err != nil {
			return false, errors.Wrap(err, "remove")
		} else {
			return true, nil
		}
	} else if err != nil {
		return false, errors.Wrap(err, "readlink")
	} else {
		// target exists，ok
		return false, nil
	}
}
