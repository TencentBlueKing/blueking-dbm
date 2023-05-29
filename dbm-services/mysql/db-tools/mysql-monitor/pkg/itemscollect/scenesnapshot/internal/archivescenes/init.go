package archivescenes

import (
	"compress/gzip"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"time"

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
		if strings.HasPrefix(i.Name(), name) && i.ModTime().Before(d) {
			oldFiles = append(oldFiles, p)
		}
		return nil
	})

	return
}

func Write(name string, basePath string, content []byte) error {
	now := time.Now()

	archivePath := filepath.Join(
		basePath,
		fmt.Sprintf("%s.%d.%s",
			name,
			config.MonitorConfig.Port,
			now.Format("20060102"),
		),
	)

	err := os.MkdirAll(archivePath, 0777)
	if err != nil {
		return err
	}

	filePath := filepath.Join(archivePath, fmt.Sprintf("%s.gz", now.Format("20060102150405")))
	file, err := os.OpenFile(filePath, os.O_CREATE|os.O_RDWR, 0777)
	if err != nil {
		return err
	}
	defer func() {
		_ = file.Close()
	}()

	gw := gzip.NewWriter(file)
	_, err = gw.Write(content)
	if err != nil {
		return err
	}
	defer func() {
		_ = gw.Close()
	}()

	return nil
}
