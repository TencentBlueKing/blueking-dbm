// Package util TODO
package util

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
)

// DiskDfResult disk df output
type DiskDfResult struct {
	Filesystem  string
	TotalSizeMB int64
	UsedMB      int64
	AvailableMB int64
	Use         string
	MountedOn   string

	UsedPct         float32
	TotalSizeMBReal int64
}

// String 用于打印
func (d DiskDfResult) String() string {
	return fmt.Sprintf(
		"{Filesystem:%s, MountedOn:%s, UsedMB:%d, TotalSizeMB:%d}",
		d.Filesystem, d.MountedOn, d.UsedMB, d.TotalSizeMB,
	)
}

func GetDiskPartitionWithDir(dirName string) (*cmutil.DiskPartInfo, error) {
	return cmutil.GetDiskPartInfo(dirName, true)
}

// GetDiskPartitionWithDir2 TODO
func GetDiskPartitionWithDir2(dirName string) (*DiskDfResult, error) {
	/*
		$ df -m /data/dbbak/data1
		Filesystem           1M-blocks      Used Available Use% Mounted on
		/dev/vdc               3604645    175526   3246014   6% /data1
	*/
	// cmd := fmt.Sprintf("-k %s", dirName) // df -k /xx/
	if dirName == "" {
		return nil, errors.New("df -m dirName should not be empty")
	}
	cmdArgs := []string{"-m", dirName}
	stdout, stderr, err := cmutil.ExecCommand(false, "", "df", cmdArgs...)
	if err != nil {
		return nil, errors.Wrapf(err, "dir:%s, err:%+v", dirName, stderr)
	}
	lines := cmutil.SplitAnyRuneTrim(stdout, "\n")
	if len(lines) != 2 {
		return nil, errors.Errorf("df result expect lines 2, got: %v", lines)
	}
	dfLine := squashSpace(lines[1])
	if dfLineVals := cmutil.SplitAnyRuneTrim(dfLine, " "); len(dfLineVals) != 6 {
		return nil, errors.Errorf("df result expect line2 has 6 columns, got: %v", dfLineVals)
	} else {
		res := &DiskDfResult{
			Filesystem:  dfLineVals[0],
			TotalSizeMB: cast.ToInt64(dfLineVals[1]),
			UsedMB:      cast.ToInt64(dfLineVals[2]),
			AvailableMB: cast.ToInt64(dfLineVals[3]),
			MountedOn:   dfLineVals[5],
		}
		res.TotalSizeMBReal = res.UsedMB + res.AvailableMB
		res.UsedPct = float32(res.UsedMB) / float32(res.TotalSizeMBReal)
		return res, nil
	}
}

// GetDirectorySizeMB du 获取 binlog 目录大小
// 如果 binlog 目录有其它文件，会一起计算
// TODO replace with cmutil.DirSize()
func GetDirectorySizeMB(binlogDir string) (int64, error) {
	/*
		du -sm /data/
		du: cannot read directory `/data/lost+found': Permission denied
		27435   /data/
	*/
	// cmdArgs := fmt.Sprintf("-sm %s", binlogDir) // du -sh /xx
	cmdArgs := []string{"-sm", binlogDir}
	stdout, stderr, err := cmutil.ExecCommand(false, "", "du", cmdArgs...)
	errStr := strings.SplitN(stderr, "\n", 1)[0]
	if err != nil {
		if strings.Contains(stdout, binlogDir) && strings.Contains(stderr, "lost+found") {
			// 忽略该错误
		} else {
			// 错误信息只返回第一行
			return 0, errors.Wrap(err, errStr)
		}
	}
	if strings.TrimSpace(stderr) != "" {
		return 0, errors.New(errStr)
	}
	reSize := regexp.MustCompile(`(\d+)\s+`)
	if matches := reSize.FindStringSubmatch(stdout); len(matches) != 2 {
		return 0, errors.Errorf("fail to parse binlogDir du size: %s", stdout)
	} else {
		totalSizeMB, _ := strconv.ParseInt(matches[1], 10, 64)
		return totalSizeMB, nil
	}
}

func squashSpace(ss string) string {
	reSpaces := regexp.MustCompile(`\s+`)
	return reSpaces.ReplaceAllString(ss, " ")
}
