package offsetlinescanner

import (
	"bufio"
	"io"
	"os"
	"strconv"
)

type OffsetScanner struct {
	filePath string
	regPath  string
	f        *os.File
	rf       *os.File
	err      error
	*bufio.Scanner
}

func (c *OffsetScanner) Scan() bool {
	rt := c.Scanner.Scan()
	if rt {
		offset, err := c.f.Seek(0, io.SeekCurrent)
		if err != nil {
			c.err = err
		}

		_, err = c.rf.Seek(0, 0)
		if err != nil {
			c.err = err
			return false
		}

		err = c.rf.Truncate(0)
		if err != nil {
			c.err = err
			return false
		}

		_, err = c.rf.WriteString(strconv.FormatInt(offset, 10))
		if err != nil {
			c.err = err
			return false
		}
	}
	return rt
}

func (c *OffsetScanner) Err() error {
	if c.Scanner.Err() != nil {
		return c.Scanner.Err()
	}
	return c.err
}

func NewOffsetScanner(filePath string, regPath string) (scanner *OffsetScanner, err error) {
	var rf *os.File
	defer func() {
		if err != nil && rf != nil {
			_ = rf.Close()
		}
	}()

	var lastOffset int64

	_, err = os.Stat(regPath)
	if err == nil {
		rf, err = os.OpenFile(regPath, os.O_RDWR, 0755)
		if err != nil {
			return nil, err
		}
		content, err := io.ReadAll(rf)
		if err != nil {
			return nil, err
		}
		lastOffset, err = strconv.ParseInt(string(content), 10, 64)
		if err != nil {
			return nil, err
		}
	} else if os.IsNotExist(err) {
		rf, err = os.OpenFile(regPath, os.O_RDWR|os.O_CREATE, 0755)
		if err != nil {
			return nil, err
		}
		lastOffset = -1
	} else {
		return nil, err
	}

	fst, err := os.Stat(filePath)
	if err != nil {
		return nil, err
	}
	fileSize := fst.Size()

	if lastOffset < 0 { // 冷启动
		lastOffset = fileSize
		_, err = rf.WriteString(strconv.FormatInt(lastOffset, 10))
		if err != nil {
			return nil, err
		}
	} else if fileSize < lastOffset { // 源文件被重建
		err = rf.Truncate(0)
		if err != nil {
			return nil, err
		}
		_, err = rf.WriteString(strconv.FormatInt(lastOffset, 10))
		if err != nil {
			return nil, err
		}
		lastOffset = 0
	}

	f, err := os.OpenFile(filePath, os.O_RDONLY, 0)
	if err != nil {
		return nil, err
	}

	_, err = f.Seek(lastOffset, 0)
	if err != nil {
		_ = f.Close()
		return nil, err
	}

	sc := bufio.NewScanner(f)
	sc.Split(bufio.ScanLines)
	return &OffsetScanner{
		filePath: filePath,
		regPath:  regPath,
		f:        f,
		rf:       rf,
		Scanner:  sc,
	}, nil
}
