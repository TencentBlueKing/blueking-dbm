package sftp

import (
	"fmt"
	"log"
	"os"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// user:pass@host:port:/data/dbbak
// /data/dbbak

// Download TODO
func Download(src Config, srcDir, dstDir string, fileName string, bwlimitMB int64) error {
	remote, err := New(src)
	if err != nil {
		return err
	}
	defer remote.Close()

	srcFile := fmt.Sprintf(`%s/%s`, srcDir, fileName)
	dstFile := fmt.Sprintf(`%s/%s`, dstDir, fileName)
	if fileName == "" {
		srcFile = srcDir
		dstFile = dstDir
	}
	logger.Info("start download to %s", dstFile)
	// Get remote file stats.
	info, err := remote.Info(srcFile)
	if err != nil {
		return err
	}
	fmt.Printf("%+v\n", info)

	// Download remote file.
	r, err := remote.Download(srcFile)
	if err != nil {
		return err
	}
	defer r.Close()

	// create local file
	f, err := os.Create(dstFile)
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()

	done := make(chan int, 1)
	defer close(done)
	go func(chan int) {
		osutil.PrintFileSizeIncr(dstFile, 1, 10, logger.Info, done)
		/*
			for true {
				speed := osutil.CalcFileSizeIncr(dstFile, 1)
				if speed != "0" {
					logger.Info("file %s download current speed %s", dstFile, speed)
				} else {
					break
				}
				time.Sleep(10 * time.Second)
			}
		*/
	}(done)

	// Read downloaded file.
	// data, err := ioutil.ReadAll(file)
	// fmt.Println(string(data))
	// _, err = io.Copy(f, ratelimit.Reader(r, srcBucket))
	_, err = cmutil.IOLimitRate(f, r, bwlimitMB)
	if err != nil {
		return err
	}
	return nil
}
