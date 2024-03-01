package tarball

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/pingcap/errors"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

func DeleteOld(name string, basePath string, days int) error {
	oldFiles, err := findBefore(name, basePath, days)
	if err != nil {
		return err
	}

	for _, oldFile := range oldFiles {
		err := os.RemoveAll(oldFile)
		if err != nil {
			return err
		}
	}

	return nil
}

func findBefore(name string, basePath string, days int) (oldFiles []string, err error) {
	t := time.Now().Add(time.Hour * time.Duration((1-days)*24))
	d := time.Date(t.Year(), t.Month(), t.Day(), 0, 0, 0, 0, t.Location())

	err = filepath.Walk(basePath, func(p string, i fs.FileInfo, e error) error {
		if e != nil {
			return e
		}
		if !i.IsDir() && strings.HasPrefix(i.Name(), name) && i.ModTime().Before(d) {
			oldFiles = append(oldFiles, p)
		}
		return nil
	})

	return
}

func Write(name string, basePath string, content []byte) error {
	now := time.Now()

	return appendToTarGz(
		filepath.Join(
			basePath,
			fmt.Sprintf("%s.%d.%s.tar.gz",
				name, config.MonitorConfig.Port, now.Format("20060102")),
		),
		now.Format("20060102150405"),
		content,
		now,
	)
}

/*
在 golang 里面只能用这样别扭的办法来实现
追加内容到已有的 tar.gz 文件
原因是
1. tar 文件末尾有 1k 的空记录, 追加的时候需要做 Seek
2. tar.gz 的操作要嵌套一层 gzip.Writer/Reader, golang 没办法在 Writer/Reader 上做随机访问
3. 有一个 WriterSeeker interface, 自己实现其实也挺麻烦
*/
func readTarGz(filePath string) (content []byte, err error) {
	content = []byte{}

	file, err := os.OpenFile(filePath, os.O_CREATE|os.O_RDWR, 0777)
	if err != nil {
		return nil, errors.AddStack(err)
	}
	defer func() {
		_ = file.Close()
	}()

	st, err := file.Stat()
	if err != nil {
		return nil, errors.AddStack(err)
	}
	if st.Size() > 0 {
		/*
			如果文件不为空
			把解压后的内容读入 content
		*/
		gzReader, err := gzip.NewReader(file)
		if err != nil {
			return nil, err
		}
		defer func() {
			_ = gzReader.Close()
		}()

		content, err = io.ReadAll(gzReader)
		if err != nil {
			return nil, errors.AddStack(err)
		}

		/*
			content 的内容是 tar 文件内容
			如果长度大于 1k, 则丢弃掉末尾的空 tar 记录
		*/
		if len(content) >= 1024 {
			content = content[:len(content)-1024]
		}
	}

	return content, nil
}

func appendToTarGz(tarGzPath string, appendFileName string, appendContent []byte, now time.Time) error {
	legacyContent, err := readTarGz(tarGzPath)
	if err != nil {
		return errors.AddStack(err)
	}

	/*
		把新增内容写到内存的 []byte 中
		legacyContent
	*/
	buf := bytes.NewBuffer(legacyContent)
	tw := tar.NewWriter(buf)

	err = tw.WriteHeader(&tar.Header{
		Name:       appendFileName,
		Mode:       0644,
		Size:       int64(len(appendContent)),
		ModTime:    now,
		AccessTime: now,
		ChangeTime: now,
	})
	if err != nil {
		return errors.AddStack(err)
	}
	_, err = tw.Write(appendContent)
	if err != nil {
		_ = tw.Close()
		return errors.AddStack(err)
	}
	_ = tw.Flush()
	_ = tw.Close()

	/*
		以覆盖方式把追加后的全量内容回写到归档文件
	*/
	file, err := os.OpenFile(tarGzPath, os.O_TRUNC|os.O_RDWR|os.O_CREATE, 0777)
	if err != nil {
		return errors.AddStack(err)
	}
	defer func() {
		_ = file.Close()
	}()

	gw, err := gzip.NewWriterLevel(file, gzip.BestCompression)
	if err != nil {
		return errors.AddStack(err)
	}
	_, err = gw.Write(buf.Bytes())
	if err != nil {
		return errors.AddStack(err)
	}
	defer func() {
		_ = gw.Close()
	}()

	return nil
}
