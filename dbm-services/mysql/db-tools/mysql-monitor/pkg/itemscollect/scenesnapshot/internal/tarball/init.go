package tarball

import (
	"archive/tar"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

func DeleteOld(name string, basePath string, days int) error {
	oldFile := filepath.Join(
		basePath,
		fmt.Sprintf(
			"%s.%d.%s.tar",
			name,
			config.MonitorConfig.Port,
			time.Now().Add(time.Hour*time.Duration(-days*24)).Format("20060102")))

	err := os.RemoveAll(oldFile)
	if err != nil {
		return err
	}

	return nil
}

func Write(name string, basePath string, content []byte) error {
	diskFile, err := os.OpenFile(
		filepath.Join(
			basePath,
			fmt.Sprintf("%s.%d.%s.tar", name, config.MonitorConfig.Port, time.Now().Format("20060102"))),
		os.O_CREATE|os.O_RDWR,
		0777)
	if err != nil {
		return err
	}
	defer func() {
		_ = diskFile.Close()
	}()

	st, err := diskFile.Stat()
	if err != nil {
		return err
	}

	if st.Size() >= 1024 {
		_, err = diskFile.Seek(-1024, io.SeekEnd)
		if err != nil {
			return err
		}
	}

	tarBall := tar.NewWriter(diskFile)
	defer func() {
		_ = tarBall.Close()
	}()

	now := time.Now()
	err = tarBall.WriteHeader(&tar.Header{
		Name:       time.Now().Format("20060102150405"),
		Mode:       0644,
		Size:       int64(len(content)),
		ModTime:    now,
		AccessTime: now,
		ChangeTime: now,
	})
	if err != nil {
		return err
	}

	_, err = tarBall.Write(content)
	if err != nil {
		return err
	}

	return nil
}
