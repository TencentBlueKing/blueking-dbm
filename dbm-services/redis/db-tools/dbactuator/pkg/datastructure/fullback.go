package datastructure

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/customtime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// TendisFullBackItem 全备信息项
type TendisFullBackItem struct {
	Incr       int    `json:"incr"`
	NodeIP     string `json:"node_ip"`
	FileName   string `json:"filename"`
	BackupFile string `json:"backup_file"`
	//DecpDir: 全备解压目录
	//如全备名是 3-TENDISPLUS-FULL-slave-127.0.0.x-30002-20230810-050140.tar
	//则值为 3-TENDISPLUS-FULL-slave-127.0.0.x-30002-20230810-050140
	DecpDir         string                `json:"decpDir"`
	ClusterMeataDir string                `json:"decompressedFile"` //解压后,全备clusterMeta所在目录
	BackupTaskid    int64                 `json:"backup_taskid"`
	BackupSize      int64                 `json:"backup_size"`
	SplitFileIdx    int                   `json:"split_file_idx"`
	BackupStart     customtime.CustomTime `json:"backup_start"` //备份开始时间,从备份文件名中获取
	BackupEnd       customtime.CustomTime `json:"backup_end"`   //备份结束时间
	StartPos        uint64                `json:"startPos"`     //ssd 回档导入增备时,--start-position

}

// TendisFullBackPull  拉取全备
type TendisFullBackPull struct {
	FileHead string `json:"fileHead"` // 文件正则匹配过滤查询
	SourceIP string `json:"sourceIp"`

	//保存备份文件的本地目录 ：传入的 task.RecoverDir
	SaveDir         string    `json:"saveDir"`
	SaveHost        string    `json:"saveHost"`
	RollbackDstTime time.Time `json:"rollbackDstTime"` //回档目标时间,拉取离这个时间点最近的备份
	//2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30000-20230311-214752.split.000
	//2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30000-20230311-214752.split.001
	//2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30000-20230311-214752.split.002
	//key: 0 1 2 ... 文件分割后缀
	//value: 文件对应的fullbackup项
	ResultFullbackup []*TendisFullBackItem `json:"resultFullbackup"`
	//key: fullbackup file name -> 去重
	//value: 文件对应的fullbackup项
	ResultFullbackMap map[string]*TendisFullBackItem `json:"resultFullbackMap"`

	//全备文件去掉后缀
	LocalFullBackupDir string `json:"local_full_backup_dir"`
	Err                error  `json:"-"` //错误信息
	KvstoreNums        int
	TendisType         string `json:"tendis_type"`
}

// NewFullbackPull 新建全备拉取任务
func NewFullbackPull(sourceIP, filehead, rollbackTime,
	saveHost, saveDir string, kvstoreNums int, tendisType string) (ret *TendisFullBackPull) {
	ret = &TendisFullBackPull{
		SourceIP:    sourceIP,
		FileHead:    filehead,
		SaveHost:    saveHost,
		SaveDir:     saveDir,
		KvstoreNums: kvstoreNums,
		TendisType:  tendisType,
	}
	mylog.Logger.Info("NewFullbackPull rollbackTime:%v", rollbackTime)
	ret.RollbackDstTime, ret.Err = time.ParseInLocation(time.RFC3339, rollbackTime, time.Local)
	mylog.Logger.Info("NewFullbackPull time.RFC3339 ret.RollbackDstTime:%v",
		ret.RollbackDstTime.Format(time.RFC3339))
	mylog.Logger.Info("NewFullbackPull ret.RollbackDstTime:%v", ret.RollbackDstTime)
	if ret.Err != nil {
		ret.Err = fmt.Errorf("rollbackTime:%s time.parese fail,err:%s,time.RFC3339:%s",
			rollbackTime, ret.Err, time.RFC3339)
		mylog.Logger.Error(ret.Err.Error())
		return ret
	}
	if ret.RollbackDstTime.After(time.Now()) == true {
		//未来时间
		ret.Err = fmt.Errorf("rollbackTime:%s > time.Now()", ret.RollbackDstTime)
		mylog.Logger.Error(ret.Err.Error())
		return ret
	}
	ret.ResultFullbackup = []*TendisFullBackItem{}
	ret.ResultFullbackMap = make(map[string]*TendisFullBackItem)
	mylog.Logger.Info("FileHead:%s", ret.FileHead)
	return
}

// LastNDaysFullBack 需要最近N天的全备
func LastNDaysFullBack() int {
	lastNDays := 2
	return lastNDays
}

// GetFullFilesSpecTimeRange 获取某个正则指定时间的全备文件和时间
// NOCC:golint/fnsize(设计如此)
func (full *TendisFullBackPull) GetFullFilesSpecTimeRange(fullFileList []FileDetail) (backs []*TendisFullBackItem) {
	mylog.Logger.Info("GetFullFilesSpecTimeRange start ... ")
	mylog.Logger.Info("fileName 正则匹配:%s", full.FileHead)
	// 如没有切割的备份文件：
	// 2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30008-20230323-214618.tar
	// 2005000191-TENDISSSD-FULL-slave-127.0.0.x-30000-20230418-050000-227999.tar
	// REDIS-FULL-rocksdb-127.0.0.xx-30000-20231227-000154-1634640184.tar
	// 有切割的备份文件：
	// 2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30008-20230326-131129.split.000
	// 2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30008-20230326-131129.split.001
	// 2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30003-20230629-130151.tar
	// 获得最后的: 20230326-131129
	// 定义正则表达式
	var lastDateReg *regexp.Regexp
	var lastDateReg1 *regexp.Regexp
	var lastDateReg2 *regexp.Regexp

	switch full.TendisType {
	case consts.TendisTypeTendisplusInsance:
		lastDateReg = regexp.MustCompile(`^.*?(\d+-\d+).tar`)
		lastDateReg1 = regexp.MustCompile(`^.*?(\d+-\d+).split.(\d+)`)
	case consts.TendisTypeTendisSSDInsance:
		lastDateReg = regexp.MustCompile(`^.*?(\d+-\d+)-(\d+).tar`)
		lastDateReg1 = regexp.MustCompile(`^.*?(\d+-\d+-\d+).split.(\d+)`)
	default:
		// tendis cache  （cache 这里没有做文件分割）
		// 2005000194-redis-master-127.0.0.x-30000-20230426-210004.rdb
		// 2005000194-redis-slave-127.0.0.x-30000-20230508-130108.aof.zst
		// 127.0.0.xx-30000-20231219-200152-appendonly.aof.lzo
		// rdb 文件不会压缩，因为redis本身有做压缩
		// aof 文件会压缩，需要解压
		lastDateReg = regexp.MustCompile(`^.*?(\d+-\d+).aof.zst`)
		lastDateReg1 = regexp.MustCompile(`^.*?(\d+-\d+).rdb`)
		lastDateReg2 = regexp.MustCompile(`^.*?(\d+-\d+)-appendonly.aof.lzo`)
	}

	for _, str01 := range fullFileList {
		back01 := &TendisFullBackItem{}
		taskID, _ := strconv.Atoi(str01.TaskID)

		if taskID < 0 || str01.Size < 0 {
			msg := fmt.Sprintf("fileNameHead:%s fullbackup:%s backupTaskid:%s<0  backupSize:%d<0 is invalid,skip...",
				full.FileHead, str01.FileName, str01.TaskID, str01.Size)
			mylog.Logger.Info(msg)
			continue
		}

		back01.BackupTaskid, _ = strconv.ParseInt(str01.TaskID, 10, 64)
		back01.BackupSize, _ = strconv.ParseInt(strconv.Itoa(str01.Size), 10, 64)
		mylog.Logger.Info("back01.BackupSize:%d", back01.BackupSize)

		back01.BackupFile = str01.FileName
		back01.NodeIP = str01.SourceIP
		mylog.Logger.Debug("str01.FileName:%s", str01.FileName)

		match01 := lastDateReg.FindStringSubmatch(str01.FileName)
		mylog.Logger.Debug("match01:%s", match01)
		//match01=nil，备份文件有切割
		if match01 == nil {
			match01 = lastDateReg1.FindStringSubmatch(str01.FileName)
			if full.TendisType == consts.TendisTypeTendisSSDInsance || full.TendisType == consts.TendisTypeTendisplusInsance {
				back01.SplitFileIdx, _ = strconv.Atoi(match01[2])
			}
		}
		// xx-appendonly.aof.lzo`
		if match01 == nil {
			match01 = lastDateReg2.FindStringSubmatch(str01.FileName)
		}

		if len(match01) < 2 {
			err := fmt.Errorf("filename:%s  backup:%v format not correct,cann't find createTime", full.FileHead, str01)
			mylog.Logger.Error(err.Error())
			full.Err = err
			return
		}

		bkCreateTime, err01 := time.ParseInLocation(consts.FilenameTimeLayout, match01[1], time.Local)
		// 3-TENDISPLUS-FULL-slave-127.0.0.x-30002-20230810-050140.tar
		// 3-TENDISSSD-FULL-slave-127.0.0.x-30000-20230809-105510-52447.tar
		if full.TendisType == consts.TendisTypeTendisSSDInsance {
			back01.StartPos, _ = strconv.ParseUint(match01[2], 10, 64)
			mylog.Logger.Info("全备文件名中获取的 StartPos:%d,文件:%s", back01.StartPos, back01.BackupFile)
		}

		if err01 != nil {
			full.Err = fmt.Errorf("backup file createTime:%s time.parese fail,err:%s,consts.FilenameTimeLayout:%s",
				match01[1], err01, consts.FilenameTimeLayout)
			mylog.Logger.Error(full.Err.Error())
			return
		}

		back01.BackupStart.Time = bkCreateTime
		back01.FileName = str01.FileName
		// 过滤节点维度的文件,这里比较重要，因为flow传下来的是这台机器涉及到的所有节点信息，
		// 这里是针对单节点的，所以需要过滤出来，这个值返回给前置函数
		if strings.Contains(back01.BackupFile, full.FileHead) {
			backs = append(backs, back01)
		}
	}
	for _, bk02 := range backs {
		mylog.Logger.Info("GetFullFilesSpecTimeRange bk:%v", bk02)
	}

	return
}

// GetTendisFullbackNearestRkTime 获取Trendis最靠近 回档目的时间 的全备
func (full *TendisFullBackPull) GetTendisFullbackNearestRkTime(fullFileList []FileDetail) {
	mylog.Logger.Info("Check TendisFullbackNearestRkTime start ... ")
	//从备份列表中选择最靠近 回档目标时间 的备份
	var nearestFullbk *TendisFullBackItem = nil
	mylog.Logger.Info("GetTendisFullbackNearestRkTime fullFileList:%v", fullFileList)
	backs := full.GetFullFilesSpecTimeRange(fullFileList)
	if full.Err != nil {
		err := fmt.Errorf("Check GetFullFilesSpecTimeRange failed :%v", full.Err)
		mylog.Logger.Error(err.Error())
		full.Err = err
		return
	}
	mylog.Logger.Info("GetTendisFullbackNearestRkTime len(backs):%d", len(backs))
	mylog.Logger.Info("GetTendisFullbackNearestRkTime backs[0]:%v", backs[0])
	mylog.Logger.Info("Check GetFullFilesSpecTimeRange finish ")
	// 1、先找到一个最靠近 回档目标时间 的备份文件
	for _, bk01 := range backs {
		bkItem := bk01
		mylog.Logger.Info("GetTendisFullbackNearestRkTime bkItem:%v", bkItem)
		//只需要那些BackupStart 小于等于 回档目标时间 的备份
		if bkItem.BackupStart.Before(full.RollbackDstTime) == true ||
			bkItem.BackupStart.Time == full.RollbackDstTime {
			if nearestFullbk == nil {
				//第一次找到 开始时间 小于 回档目标时间的备份
				nearestFullbk = bkItem
			} else {
				// nearestFullbk.BackupStart < 该备份BackupStart <= full.RollbackDstTime
				if bkItem.BackupStart.After(nearestFullbk.BackupStart.Time) == true {
					nearestFullbk = bkItem
				}
			}
		}
	}
	if nearestFullbk != nil {
		//已经找到
		mylog.Logger.Info("GetTendisFullbackNearestRkTime filename 正则:%s nearestFullbk:%v", full.FileHead, nearestFullbk)
		// 2、再查找同时段的其他分割文件,怎么判断分割文件是否完备呢？ -》 isGetAllFileInfo
		for _, bk01 := range backs {
			bkItem := bk01
			//找到同一时间的分割文件
			if bkItem.BackupStart.Time == nearestFullbk.BackupStart.Time {
				if _, ok := full.ResultFullbackMap[bkItem.BackupFile]; ok == true {
					//去重
					return
				}
				full.ResultFullbackMap[bkItem.BackupFile] = bkItem
				full.ResultFullbackup = append(full.ResultFullbackup, bkItem)

			}
		}
		if nearestFullbk == nil {
			full.Err = fmt.Errorf("filename 正则:%s 最近%d天内没找到小于回档目标时间[%s]的全备",
				full.FileHead, LastNDaysFullBack(), full.RollbackDstTime)
			mylog.Logger.Error(full.Err.Error())
			return
		}
		msg := fmt.Sprintf("找到距离回档目标时间:%s最近的全备:%s",
			full.RollbackDstTime, nearestFullbk.BackupFile)
		mylog.Logger.Info(msg)

		//按照splitfile index排序
		sort.Slice(full.ResultFullbackup, func(i, j int) bool {
			return full.ResultFullbackup[i].SplitFileIdx < full.ResultFullbackup[j].SplitFileIdx
		})
		// 校验获取到的分割/tar文件信息:检查是否完整
		full.isGetAllFileInfo()
		if full.Err != nil {
			mylog.Logger.Error("isGetAllFileInfo failed,err:%v", full.Err.Error())
			return
		}
		return
	}
	full.Err = fmt.Errorf("GetTendisFullbackNearestRkTime: filename 正则:%s 最近%d天内没找到小于回档目标时间[%s]的全备",
		full.FileHead, LastNDaysFullBack(), full.RollbackDstTime)
	mylog.Logger.Error(full.Err.Error())

	return
}

/*
判断split文件是否连续,是否重复;
- 重复则报错;
- 不连续则返回缺失的split index,如 2,3,5,8 则返回缺失的4,6,7
*/
func getNotReadySplitFile(resultBackItem []*TendisFullBackItem) ([]string, error) {
	var ret []string
	var err error
	prelistIdx := 000
	preSplitFileIdx := resultBackItem[0].SplitFileIdx
	for idx, item := range resultBackItem {
		if idx == prelistIdx {
			// 第一个元素忽略
			continue
		}
		if item.SplitFileIdx <= preSplitFileIdx {
			//如果后面的split index小于等于前一个 index
			err = fmt.Errorf("当前split index:%d <= 前一个split index:%d", item.SplitFileIdx, preSplitFileIdx)
			mylog.Logger.Error(err.Error())
			mylog.Logger.Error(err.Error())
			return ret, err
		}
		if item.SplitFileIdx == preSplitFileIdx+1 {
			// 递增符合预期
			preSplitFileIdx = item.SplitFileIdx
			continue
		}
		preSplitFileIdx++
		for preSplitFileIdx < item.SplitFileIdx {
			ret = append(ret, fmt.Sprintf("%d", preSplitFileIdx))
			preSplitFileIdx++
		}

	}
	return ret, nil
}

/*
判断所需split/tar file文件信息是否已全部获取到;
- ResultFullbackup 第二个split文件序号 必须 只比 第一个split 文件序号大1
- ResultFullbackup 倒数第一个split文件序号 必须 只比 倒数第二个split文件序号大 1
- 最后一个文件序号 减去 第一个文件序号 等于 len(ResultFullbackup)+1
- ResultFullbackup split.BackupStart都相等
*/
func (full *TendisFullBackPull) isGetAllFileInfo() (ret bool) {
	mylog.Logger.Info("isGetAllFileInfo start ...")
	cnt := len(full.ResultFullbackup)
	mylog.Logger.Info("ResultFullbackup len:%d", cnt)
	// 没有分割，文件小于8G
	if cnt == 1 {
		for _, bk01 := range full.ResultFullbackup {
			mylog.Logger.Info(bk01.BackupFile)
			msg := fmt.Sprintf(`filename:%s  找到所有[%s~%s]时间段的tar文件,共%d个:%s`,
				full.FileHead,
				full.ResultFullbackup[0].BackupStart,
				full.ResultFullbackup[0].BackupEnd,
				cnt,
				bk01.BackupFile,
			)
			mylog.Logger.Info(msg)
			return

		}
	}
	firstSplit := full.ResultFullbackup[0]
	secondSplit := full.ResultFullbackup[1]

	lastSplit := full.ResultFullbackup[cnt-1]
	beforeLastSplit := full.ResultFullbackup[cnt-2]

	//第二个split文件序号 必须 只比 第一个split 文件序号大1
	if secondSplit.SplitFileIdx-firstSplit.SplitFileIdx != 1 {
		full.Err = fmt.Errorf("filename:%s 拉取[%s ~ %s] 时间段的split file,第一个分割文件:%s 和 第二个分割文件:%s 不连续",
			full.FileHead, full.ResultFullbackup[0].BackupStart, full.ResultFullbackup[0].BackupEnd,
			firstSplit.BackupFile, secondSplit.BackupFile)
		mylog.Logger.Error(full.Err.Error())
		return
	}

	//倒数第一个split文件序号 必须 只比 倒数第二个split文件序号大 1
	if lastSplit.SplitFileIdx-beforeLastSplit.SplitFileIdx != 1 {
		full.Err = fmt.Errorf("filename:%s 拉取[%s ~ %s] 时间段的split file,倒数第一个分割文件:%s 和 倒数第二个分割文件:%s 不连续",
			full.FileHead, full.ResultFullbackup[0].BackupStart, full.ResultFullbackup[0].BackupEnd,
			lastSplit.BackupFile, beforeLastSplit.BackupFile)
		mylog.Logger.Error(full.Err.Error())
		return
	}
	//全部是否连续
	splitIndexList, err := getNotReadySplitFile(full.ResultFullbackup)
	if err != nil {
		full.Err = err
		return false
	}

	if len(splitIndexList) > 0 {
		full.Err = fmt.Errorf("缺失的split共%d个,缺失的split index是:%s",
			len(splitIndexList), strings.Join(splitIndexList, ","))
		mylog.Logger.Error(full.Err.Error())
		return false
	}
	// 判断时间相等
	baseTime := full.ResultFullbackup[0].BackupStart
	if len(full.ResultFullbackup) > 1 {
		for _, bk01 := range full.ResultFullbackup {
			if bk01.BackupStart != baseTime {
				full.Err = fmt.Errorf("filename:%s 拉取[%s ~ %s] 时间段的split file 的时间不一致,第一个文件是:%s,不一致的文件是:%s",
					full.FileHead, full.ResultFullbackup[0].BackupStart, full.ResultFullbackup[0].BackupEnd,
					full.ResultFullbackup[0].BackupFile, bk01.BackupFile)
			}
		}

	}
	msg := fmt.Sprintf(`filename:%s  找到所有[%s~%s]时间段的splitFile,共%d个,第一个splitFile:%s,最后一个splitFile:%s`,
		full.FileHead,
		full.ResultFullbackup[0].BackupStart,
		full.ResultFullbackup[0].BackupEnd,
		cnt,
		firstSplit.BackupFile,
		lastSplit.BackupFile,
	)
	mylog.Logger.Info(msg)
	return

}

// RetryDownloadFiles 需要flow重新下载文件到对应位置
func (full *TendisFullBackPull) RetryDownloadFiles() {

	full.Err = fmt.Errorf("no all files need retryDownloadFiles")

}

// TotalSize 全备文件的大小
func (full *TendisFullBackPull) TotalSize() int64 {
	var ret int64 = 0
	for _, bk01 := range full.ResultFullbackup {
		bkItem := bk01
		ret = ret + bkItem.BackupSize
	}
	return ret
}

// findDstFileInDir 在指定文件夹下找到目标文件
func findDstFileInDir(dir string, dstFile string) (dstFilePos string, err error) {
	err = filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.Name() == dstFile {
			dstFilePos = path
			return nil
		}
		return nil
	})
	if err != nil {
		err = fmt.Errorf("findDstFileInDir filepath.Walk fail,err:%v,dir:%s dstFile:%s", err, dir, dstFile)
		mylog.Logger.Error(err.Error())
		return "", err
	}
	if dstFilePos == "" {
		err = fmt.Errorf("the destination file was not found in dir,dstFile:%s,dir:%s",
			dstFile, dir)
		mylog.Logger.Error(err.Error())
		return "", util.NewNotFoundErr()
	}
	return
}

// GetBackupFileExt 获取全备文件后缀
func (full *TendisFullBackPull) GetBackupFileExt() (fileExt string) {

	if len(full.ResultFullbackup) != 0 {
		fileExt = filepath.Ext(full.ResultFullbackup[0].BackupFile)
	} else {
		full.Err = fmt.Errorf("结果文件为空，无法获取文件后缀，请检查")
		mylog.Logger.Error(full.Err.Error())
		return
	}

	if fileExt == ".tar" || fileExt == ".tgz" {
		return fileExt
	} else if strings.HasSuffix(full.ResultFullbackup[0].BackupFile, ".tar.gz") {
		fileExt = ".tar.gz"
	} else if strings.HasSuffix(full.ResultFullbackup[0].BackupFile, ".zst") {
		fileExt = ".zst"
	} else if strings.HasSuffix(full.ResultFullbackup[0].BackupFile, ".rdb") {
		fileExt = ".rdb"
	} else if strings.HasSuffix(full.ResultFullbackup[0].BackupFile, ".lzo") {
		fileExt = ".lzo"
	} else if strings.Contains(full.ResultFullbackup[0].BackupFile, ".split.") {
		fileExt = "split"
	} else {
		full.Err = fmt.Errorf("不支持解压的全备文件类型:%s", full.ResultFullbackup[0].BackupFile)
		mylog.Logger.Error(full.Err.Error())
		return
	}
	mylog.Logger.Info("GetBackupFileExt: fileExt is %s", fileExt)
	return
}

// SetDecompressedDir 设置解压目录
func (full *TendisFullBackPull) SetDecompressedDir() {
	bkFileExt := full.GetBackupFileExt()
	if full.Err != nil {
		return
	}
	mylog.Logger.Info("SetDecompressedDir bkFileExt:%s", bkFileExt)
	var prefix, cmd01 string
	if bkFileExt == "split" {
		// 2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30000-20230311-214752.split.004
		// 需要的：2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30000-20230311-214752
		prefix = strings.Split(full.ResultFullbackup[0].BackupFile, ".split")[0]
		cmd01 := fmt.Sprintf("cd %s && mkdir -p %s ", full.SaveDir, prefix)
		mylog.Logger.Info("SetDecompressedDir bkFileExt:%s, cmd01:%s", bkFileExt, cmd01)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", cmd01}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}
	} else if bkFileExt == ".tar" {
		prefix = strings.TrimSuffix(full.ResultFullbackup[0].BackupFile, bkFileExt)
		cmd01 := fmt.Sprintf("cd %s && mkdir -p %s ", full.SaveDir, prefix)
		mylog.Logger.Info("SetDecompressedDir bkFileExt:%s, cmd01:%s", bkFileExt, cmd01)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", cmd01}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}
	} else if bkFileExt == ".zst" {
		// xx-xx-xx.aof.zst
		prefix = strings.TrimSuffix(full.ResultFullbackup[0].BackupFile, ".aof.zst")
		mylog.Logger.Info("prefix:%s", prefix)
		cmd01 := fmt.Sprintf("cd %s && mkdir -p %s ", full.SaveDir, prefix)
		mylog.Logger.Info("SetDecompressedDir bkFileExt:%s, cmd01:%s", bkFileExt, cmd01)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", cmd01}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}
	} else if bkFileExt == ".lzo" {
		// xx-xx-xx.aof.lzo
		prefix = strings.TrimSuffix(full.ResultFullbackup[0].BackupFile, ".aof.lzo")
		mylog.Logger.Info("prefix:%s", prefix)
		cmd01 := fmt.Sprintf("cd %s && mkdir -p %s ", full.SaveDir, prefix)
		mylog.Logger.Info("SetDecompressedDir bkFileExt:%s, cmd01:%s", bkFileExt, cmd01)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", cmd01}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}
	} else if bkFileExt == ".rdb" {
		// xx-xx.rdb
		prefix = strings.TrimSuffix(full.ResultFullbackup[0].BackupFile, ".rdb")
		mylog.Logger.Info("prefix:%s", prefix)
		cmd01 := fmt.Sprintf("cd %s && mkdir -p %s ", full.SaveDir, prefix)
		mylog.Logger.Info("SetDecompressedDir bkFileExt:%s, cmd01:%s", bkFileExt, cmd01)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", cmd01}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}
	}
	mylog.Logger.Info("SetDecompressedDir cmd01:%s", cmd01)
	full.LocalFullBackupDir = prefix
	mylog.Logger.Info("GetDecompressedDir: Decompressed Dir is:%s", full.LocalFullBackupDir)
}

// GetDecompressedDir 获取 DecpDir 的值,全备解压目录
// 如全备名是 3-TENDISPLUS-FULL-slave-127.0.0.x-30002-20230810-050140.tar
// 则值为 3-TENDISPLUS-FULL-slave-127.0.0.x-30002-20230810-050140
func (full *TendisFullBackPull) GetDecompressedDir() (decpDir string) {
	if full.LocalFullBackupDir != "" {
		return full.LocalFullBackupDir
	}
	full.SetDecompressedDir()
	if full.Err != nil {
		return
	}
	return full.LocalFullBackupDir
}

// CheckDecompressedDirIsOK 检查全备解压文件夹 是否存在,数据是否完整
// 数据是否完整:通过判断是否有clustermeta.txt、${rocksdbIdx}/backup_meta文件来确认
// NOCC:golint/fnsize(设计如此)
func (full *TendisFullBackPull) CheckDecompressedDirIsOK() (isExists, isCompelete bool, msg string) {

	mylog.Logger.Info("开始检查全备(已解压)目录是否存在,是否完整")
	isExists = false
	isCompelete = false

	decpDir := full.GetDecompressedDir()
	if full.Err != nil {
		return
	}
	decpFullPath := filepath.Join(full.SaveDir, decpDir)
	if _, err := os.Stat(decpFullPath); os.IsNotExist(err) {
		msg = fmt.Sprintf("全备解压目录:%s 不存在", decpFullPath)
		mylog.Logger.Info(msg)
		return
	}
	isExists = true //解压目录存在
	if full.TendisType == consts.TendisTypeTendisplusInsance {
		var metaFile string
		metaFile, _ = findDstFileInDir(decpFullPath, "clustermeta.txt")

		if _, err := os.Stat(metaFile); os.IsNotExist(err) {
			//clustermeta.txt 不存在
			msg = fmt.Sprintf("全备解压目录:%s 中找不到 clustermeta.txt 文件", metaFile)
			mylog.Logger.Info(msg)
			isCompelete = false
			return
		}
		full.ResultFullbackup[0].ClusterMeataDir = filepath.Dir(metaFile)
		for i := 0; i < full.KvstoreNums; i++ {
			rocksdbBackupMeta := filepath.Join(full.ResultFullbackup[0].ClusterMeataDir, fmt.Sprintf("%d/backup_meta", i))
			if _, err := os.Stat(rocksdbBackupMeta); os.IsNotExist(err) {
				msg = fmt.Sprintf("全备解压目录:%s/%d/backup_meta 找不到", rocksdbBackupMeta, i)
				mylog.Logger.Info(msg)
				isCompelete = false
				return
			}
		}

	} else if full.TendisType == consts.TendisTypeTendisSSDInsance {
		//todo 这里不存在会有errlog ，预期内的情况？ 看看怎么优化
		mylog.Logger.Info("检查tendis ssd 的全备解压是否有效")
		err := full.tendisSSDBackupVerify(decpFullPath)
		if err != nil {
			msg = fmt.Sprintf("全备解压目录Verify 无效:%s", decpFullPath)
			isCompelete = false
			return
		}
	} else if full.TendisType == consts.TendisTypeRedisInstance {
		// todo 怎样判断是否完整?
		// 1、存在
		// 2、大小接近
		var file, backupFile string
		mylog.Logger.Info("decpFullPath:%s", decpFullPath)
		bkFileExt := full.GetBackupFileExt()
		if full.Err != nil {
			return
		}
		if bkFileExt == ".zst" {
			backupFile = strings.TrimSuffix(full.ResultFullbackup[0].BackupFile, ".zst")
			file, _ = findDstFileInDir(decpFullPath, backupFile)

		} else if bkFileExt == ".rdb" {
			backupFile = full.ResultFullbackup[0].BackupFile
			file, _ = findDstFileInDir(decpFullPath, backupFile)
		} else if bkFileExt == ".lzo" {
			backupFile = strings.TrimSuffix(full.ResultFullbackup[0].BackupFile, ".lzo")
			file, _ = findDstFileInDir(decpFullPath, backupFile)
		}

		if _, err := os.Stat(file); os.IsNotExist(err) {
			msg = fmt.Sprintf("全备解压目录:%s 中找不到 %s 文件", decpFullPath, backupFile)
			mylog.Logger.Info(msg)
			isCompelete = false
			return
		}

	}

	msg = fmt.Sprintf("解压目录存在且完整:%s", decpFullPath)
	mylog.Logger.Info(msg)
	//解压文件存在且是完整的
	return true, true, msg
}

// tendisSSDBackupVerify 确定tendissd备份是否是有效的
func (task *TendisFullBackPull) tendisSSDBackupVerify(backupFullDir string) (err error) {

	verifyBin := consts.TredisverifyBin
	if !util.FileExists(verifyBin) {
		task.Err = fmt.Errorf("%s not exists", verifyBin)
		mylog.Logger.Error(task.Err.Error())
		return
	}
	cmd := fmt.Sprintf(`
export LD_PRELOAD=/usr/local/redis/bin/deps/libjemalloc.so;
export LD_LIBRARY_PATH=LD_LIBRARY_PATH:/usr/local/redis/bin/deps;
%s %s  1 2>/dev/null
	`, verifyBin, backupFullDir)
	mylog.Logger.Info(cmd)
	_, err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	if err != nil {
		err = fmt.Errorf("backupData(%s) verify failed", backupFullDir)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// CheckLocalBackupFileIsOK 检查本地全备(未解压) 是否存在,是否完整
func (full *TendisFullBackPull) CheckLocalBackupFileIsOK() (isExists, isCompelete bool, msg string) {
	mylog.Logger.Info("开始检查本地全备文件(未解压)是否存在,是否完整")

	mylog.Logger.Info("full.LocalFullBackupDir:%s", full.LocalFullBackupDir)
	//TODO 通过gse检查saveRemoteDidr备份文件是否存在,大小如何
	// 这里当前只是 简单检查下saveMyyDir中备份文件是否存在,大小是否ok
	full.SetDecompressedDir()
	if full.Err != nil {
		msg = fmt.Sprintf("本地全备(未解压):%s 不存在", full.LocalFullBackupDir)
		mylog.Logger.Info(msg)
		return false, false, msg
	}
	if full.SaveDir != "" {
		bkFileFullPath := filepath.Join(full.SaveDir, full.LocalFullBackupDir)
		mylog.Logger.Info("bkFileFullPath:%s", bkFileFullPath)
		var bkFileFullPathFile string
		if full.TendisType == consts.TendisTypeTendisplusInsance || full.TendisType == consts.TendisTypeTendisSSDInsance {
			bkFileFullPathFile = fmt.Sprintf("%s%s", bkFileFullPath, ".tar")
		} else if full.TendisType == consts.TendisTypeRedisInstance {
			bkFileExt := full.GetBackupFileExt()
			if full.Err != nil {
				return
			}
			if bkFileExt == ".zst" {
				bkFileFullPathFile = fmt.Sprintf("%s%s", bkFileFullPath, ".aof.zst")
			} else if bkFileExt == ".rdb" {
				bkFileFullPathFile = fmt.Sprintf("%s%s", bkFileFullPath, ".rdb")
			}

		}

		mylog.Logger.Info("bkFileFullPathFile:%s", bkFileFullPathFile)
		bkFileOsInfo, err := os.Stat(bkFileFullPathFile)
		if os.IsNotExist(err) {
			// 解压后就会删除，基本是不存在的
			msg = fmt.Sprintf("本地全备(未解压):%s 不存在", bkFileFullPathFile)
			mylog.Logger.Info(msg)
			return false, false, msg
		}

		isExists = true

		msg = fmt.Sprintf("本地全备(未解压):%s 大小%dGB, 目标大小:%dGB",
			full.LocalFullBackupDir,
			bkFileOsInfo.Size()/1024/1024/1024,
			full.TotalSize()/1024/1024/1024)
		mylog.Logger.Info(msg)
		mylog.Logger.Info("size:%d,full.TotalSize():%d", bkFileOsInfo.Size(), full.TotalSize())
		// 这里获取的文件夹大小和单个文件大小，数据会不一致，有很少的差异，所以比较单位换算为GB
		if bkFileOsInfo.Size()/1024/1024/1024 != full.TotalSize()/1024/1024/1024 {
			msg = fmt.Sprintf("本地全备(未解压):%s 大小%dGB != 目标大小:%dGB",
				full.LocalFullBackupDir,
				bkFileOsInfo.Size()/1024/1024/1024,
				full.TotalSize()/1024/1024/1024)
			mylog.Logger.Info(msg)
			isCompelete = false
			return
		}
		mylog.Logger.Info("CheckLocalBackupFileIsOK: result is ok")
		return true, true, ""
	}
	msg = fmt.Sprintf("SaveDir:%s is empty", full.SaveDir)
	return false, false, msg
}

// DirSize 获取文件夹的大小
func (full *TendisFullBackPull) DirSize(path string) (int64, error) {
	var size int64
	err := filepath.Walk(path, func(_ string, info os.FileInfo, err error) error {
		if !info.IsDir() {
			size += info.Size()
		}
		return err
	})
	return size, err
}

// RmDecompressedDir 删除本地全备解压文件夹
func (full *TendisFullBackPull) RmDecompressedDir() {
	decpDir := full.GetDecompressedDir()
	if full.Err != nil {
		return
	}
	decpFullPath := filepath.Join(full.SaveDir, decpDir)
	if _, err := os.Stat(decpFullPath); os.IsNotExist(err) {
		//本地全备解压文件夹不存在
		return
	}
	rmCmd := fmt.Sprintf("cd %s && rm -rf %s 2>/dev/null", full.SaveDir, decpDir)
	_, full.Err = util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 30*time.Minute)
	if full.Err != nil {
		return
	}
	msg := fmt.Sprintf("全备文件夹(已解压):%s 删除成功", decpDir)
	mylog.Logger.Info(msg)
	return
}

// RmLocalBakcupFile 删除本地全备(未解压)文件
func (full *TendisFullBackPull) RmLocalBakcupFile() {
	bkFileFullPath := filepath.Join(full.SaveDir, full.LocalFullBackupDir)
	if _, err := os.Stat(bkFileFullPath); os.IsNotExist(err) {
		return
	}
	bkFileExt := full.GetBackupFileExt()
	if full.Err != nil {
		return
	}
	var backupFiles string
	// rdb 没压缩，不用处理
	if bkFileExt == "split" {
		// 2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30000-20230311-214752.split.004
		// 需要的：2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30000-20230311-214752
		backupFiles = fmt.Sprintf("%s.split.*", full.GetDecompressedDir())
	} else if bkFileExt == ".tar" {
		backupFiles = fmt.Sprintf("%s.tar", full.GetDecompressedDir())
	} else if bkFileExt == ".zst" {
		backupFiles = fmt.Sprintf("%s.aof.zst", full.GetDecompressedDir())
		DecompressDir := filepath.Join(full.SaveDir, full.GetDecompressedDir())
		rmCmd := fmt.Sprintf("cd %s && rm -rf %s 2>/dev/null", DecompressDir, backupFiles)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 30*time.Minute)
		if full.Err != nil {
			return
		}
		msg := fmt.Sprintf("本地全备(未解压):%s 删除成功", backupFiles)
		mylog.Logger.Info(msg)
		return
	}
	rmCmd := fmt.Sprintf("cd %s && rm -rf %s 2>/dev/null", full.SaveDir, backupFiles)
	_, full.Err = util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 30*time.Minute)
	if full.Err != nil {
		return
	}
	msg := fmt.Sprintf("本地全备(未解压):%s 删除成功", backupFiles)
	mylog.Logger.Info(msg)
	return
}

// Decompressed ... 解压文件
// NOCC:golint/fnsize(设计如此)
func (full *TendisFullBackPull) Decompressed() {
	mylog.Logger.Info("Decompressed start ...")
	var cmd01 string
	bkFileExt := full.GetBackupFileExt()
	if full.Err != nil {
		return
	}

	if bkFileExt == ".tar" {
		// 只有一个备份文件，并且后缀为.tar
		if len(full.ResultFullbackup) == 1 {
			cmd01 = fmt.Sprintf("tar -xf %s", full.ResultFullbackup[0].BackupFile)
		}

	} else if bkFileExt == ".tar.gz" || bkFileExt == ".tgz" {
		if len(full.ResultFullbackup) == 1 {
			cmd01 = fmt.Sprintf("tar -xf %s", full.ResultFullbackup[0].BackupFile)
		}
	} else if bkFileExt == ".zst" {
		mylog.Logger.Info("len(full.ResultFullbackup) is %d", len(full.ResultFullbackup))
		mylog.Logger.Info("Decompressed_bkFileExt is %s", bkFileExt)
		if len(full.ResultFullbackup) == 1 {
			// 检查 zst 是否存在
			_, err := os.Stat(consts.ZstdBin)
			if err != nil && os.IsNotExist(err) {

				err = fmt.Errorf("Decompress: 解压工具 zst 不存在,"+
					"请检查 %s是否存在 err:%v", consts.ZstdBin, err)
				mylog.Logger.Error(err.Error())
				full.Err = err
				return

			}
			// 未解压文件
			cmd01 = fmt.Sprintf(" cd %s && %s -d %s ", full.GetDecompressedDir(),
				consts.ZstdBin, full.ResultFullbackup[0].BackupFile)
		}
		prefix := strings.TrimSuffix(full.ResultFullbackup[0].BackupFile, ".aof.zst")
		mkcmd := fmt.Sprintf("cd %s && mkdir -p %s ", full.SaveDir, prefix)
		mylog.Logger.Info("SetDecompressedDir bkFileExt:%s, mkcmd:%s", bkFileExt, mkcmd)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", mkcmd}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}
		// 将备份文件mv到解压目录下
		DecompressDir := filepath.Join(full.SaveDir, full.GetDecompressedDir())
		mvCmd := fmt.Sprintf("cd %s && mv %s %s ", full.SaveDir, full.ResultFullbackup[0].BackupFile, DecompressDir)
		mylog.Logger.Info("将备份文件mv到解压目录下 mvCmd:%s", mvCmd)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", mvCmd}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}

	} else if bkFileExt == ".lzo" {
		mylog.Logger.Info("Decompressed_bkFileExt is %s", bkFileExt)
		mylog.Logger.Info("len(full.ResultFullbackup) is %d", len(full.ResultFullbackup))
		if len(full.ResultFullbackup) == 1 {
			// 检查 lzop 是否存在
			_, err := os.Stat(consts.LzopBin)
			if err != nil && os.IsNotExist(err) {
				mylog.Logger.Error("Decompress: 解压工具 lzop 不存在,"+
					"请检查 %s  是否存在 err:%v", consts.LzopBin, err)
				mylog.Logger.Error(err.Error())
				full.Err = err
				return

			}
			cmd01 = fmt.Sprintf(" cd %s && %s -d %s ", full.GetDecompressedDir(),
				consts.LzopBin, full.ResultFullbackup[0].BackupFile)

		}
		prefix := strings.TrimSuffix(full.ResultFullbackup[0].BackupFile, ".aof.lzo")
		mkcmd := fmt.Sprintf("cd %s && mkdir -p %s ", full.SaveDir, prefix)
		mylog.Logger.Info("SetDecompressedDir bkFileExt:%s, mkcmd:%s", bkFileExt, mkcmd)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", mkcmd}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}
		// 将备份文件mv到解压目录下
		DecompressDir := filepath.Join(full.SaveDir, full.GetDecompressedDir())
		mvCmd := fmt.Sprintf("cd %s && mv %s %s ", full.SaveDir, full.ResultFullbackup[0].BackupFile, DecompressDir)
		mylog.Logger.Info("将备份文件mv到解压目录下 mvCmd:%s", mvCmd)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", mvCmd}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}

	} else if bkFileExt == ".rdb" {
		// 将备份文件mv到目录下,rdb不用解压
		DecompressDir := filepath.Join(full.SaveDir, full.GetDecompressedDir())
		cmd01 := fmt.Sprintf("cd %s && mkdir -p %s ", full.SaveDir, DecompressDir)
		mylog.Logger.Info("SetDecompressedDir bkFileExt:%s, cmd01:%s", bkFileExt, cmd01)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", cmd01}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}

		mvCmd := fmt.Sprintf("cd %s && mv %s %s ", full.SaveDir, full.ResultFullbackup[0].BackupFile, DecompressDir)
		mylog.Logger.Info("将备份文件mv到解压目录下 mvCmd:%s", mvCmd)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", mvCmd}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}
	} else if bkFileExt == "split" {
		// 2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30000-20230311-214752.split.004
		backupFilesPrefix := strings.Split(full.ResultFullbackup[0].BackupFile, ".split")[0]
		cmd01 = fmt.Sprintf("cat %s.* |tar x ", backupFilesPrefix)
		mylog.Logger.Info("Decompressed cmd01:%s", cmd01)
	}
	if cmd01 != "" {
		decDir01 := full.GetDecompressedDir()
		mylog.Logger.Info("Decompressed: decDir01 is:%s", decDir01)
		//将全备文件解压到指定目录下
		cmd01 = fmt.Sprintf("cd %s  && %s", full.SaveDir, cmd01)
		msg := fmt.Sprintf("解压命令:%s", cmd01)
		mylog.Logger.Info(msg)
		_, full.Err = util.RunLocalCmd("bash", []string{"-c", cmd01}, "", nil, 1800*time.Second)
		if full.Err != nil {
			return
		}
		isExists, isCompelete, msg := full.CheckDecompressedDirIsOK()
		if full.Err != nil {
			return
		}
		if isExists == false || isCompelete == false {
			//如果不存在或不完整
			full.Err = errors.New(msg)
			mylog.Logger.Error(full.Err.Error())
			return
		}
		//rm 源文件
		full.RmLocalBakcupFile()
	}
	return
}

// PullFullbackDecompressed 拉取全备文件并解压,可重试
// 1: 本地全备.tar, 全备(已解压)文件夹 均不存在 =>拉取、解压;
// 2. 本地全备.tar不存在、全备(已解压)文件夹 存在:
// - 全备(已解压)文件夹 完整 => 直接返回;
// - 全备(已解压)文件夹 不完整 => 删除全备(已解压)文件夹,重新拉取、解压;
// 3. 本地全备.tar存在、全备(已解压)文件夹 不存在:
// - 本地全备.tar 完整, => 解压;
// - 本地全备.tar 不完整 => 删除 本地全备.tar,重新拉取、解压;
// 4. 本地全备.tar存在、全备(已解压)文件夹 存在
// - 本地全备.tar 完整 => 删除 全备(已解压)文件夹,重新解压(有理由怀疑上一次解压失败了,本地全备.tar 来不及删除)
// - 本地全备.tar 不完整 => 删除本地全备.tar + 删除 全备(已解压)文件夹, 重新拉取、解压;
// NOCC:golint/fnsize(设计如此)
func (full *TendisFullBackPull) PullFullbackDecompressed() {

	// 备份文件 （未解压）
	localBkIsExists, localBkIsCompelete, _ := full.CheckLocalBackupFileIsOK()
	if full.Err != nil {
		return
	}
	mylog.Logger.Info("localBkIsExists:%v,localBkIsCompelete:%v ", localBkIsExists, localBkIsCompelete)
	// 这里解压 ，不然会走到 else if localBkIsExists == true && decpDirIsExists == true 那里才是第一次解压
	full.Decompressed()
	if full.Err != nil {
		return
	}
	// 已解压的备份文件
	decpDirIsExists, decpIsCompelete, _ := full.CheckDecompressedDirIsOK()
	if full.Err != nil {
		return
	}
	mylog.Logger.Info("decpDirIsExists:%v,decpIsCompelete:%v", decpDirIsExists, decpIsCompelete)

	//1: 本地全备.tar, 全备(已解压)文件夹 均不存在 =>报错，需要flow重新下载;
	if localBkIsExists == false && decpDirIsExists == false {
		mylog.Logger.Info("localBkIsExists:%v,localBkIsCompelete:%v,decpDirIsExists:%v,decpIsCompelete:%v ",
			localBkIsExists, localBkIsCompelete, decpDirIsExists, decpIsCompelete)
		mylog.Logger.Info("1: 本地全备.tar, 全备(已解压)文件夹 均不存在 =>报错，需要flow重新下载")
		full.RetryDownloadFiles()
		if full.Err != nil {
			return
		}

	} else if localBkIsExists == false && decpDirIsExists == true {
		//2. 本地全备.tar不存在、全备(已解压)文件夹 存在:
		//- 全备(已解压)文件夹 完整 => 直接返回;
		//- 全备(已解压)文件夹 不完整 => 删除全备(已解压)文件夹,报错，需要flow重新下载;
		mylog.Logger.Info("localBkIsExists:%v,localBkIsCompelete:%v,decpDirIsExists:%v,decpIsCompelete:%v ",
			localBkIsExists, localBkIsCompelete, decpDirIsExists, decpIsCompelete)
		mylog.Logger.Info("2. 本地全备.tar不存在、全备(已解压)文件夹 存在")
		if decpIsCompelete == true {
			mylog.Logger.Info("2. 全备(已解压)文件夹 完整 => 直接返回;")
			return
		}
		mylog.Logger.Info("2.全备(已解压)文件夹 不完整 => 删除全备(已解压)文件夹,报错，需要flow重新下载")
		full.RmDecompressedDir()
		if full.Err != nil {
			return
		}
		full.RetryDownloadFiles()
		if full.Err != nil {
			return
		}

	} else if localBkIsExists == true && decpDirIsExists == false {
		//3. 本地全备.tar存在、全备(已解压)文件夹 不存在:
		//- 本地全备.tar 完整, => 解压;
		//- 本地全备.tar 不完整 => 删除 本地全备.tar,报错，需要flow重新下载;;
		mylog.Logger.Info("localBkIsExists:%v,localBkIsCompelete:%v,decpDirIsExists:%v,decpIsCompelete:%v ",
			localBkIsExists, localBkIsCompelete, decpDirIsExists, decpIsCompelete)

		if localBkIsCompelete == true {
			mylog.Logger.Info("3. 本地全备.tar 完整, => 解压")
			full.Decompressed()
			return
		}
		mylog.Logger.Info("3.本地全备.tar 不完整 => 删除 本地全备.tar,报错，需要flow重新下载")

		full.RmLocalBakcupFile()
		if full.Err != nil {
			return
		}
		full.RetryDownloadFiles()
		if full.Err != nil {
			return
		}

	} else if localBkIsExists == true && decpDirIsExists == true {
		//4. 本地全备.tar存在、全备(已解压)文件夹 存在
		// 本地解压目录完整则返回
		//- 本地全备.tar 完整 => 删除 全备(已解压)文件夹,重新解压(有理由怀疑上一次解压失败了,本地全备.tar 来不及删除)
		//- 本地全备.tar 不完整 => 删除本地全备.tar + 删除 全备(已解压)文件夹, 报错，需要flow重新下载;
		mylog.Logger.Info("localBkIsExists:%v,localBkIsCompelete:%v,decpDirIsExists:%v,decpIsCompelete:%v ",
			localBkIsExists, localBkIsCompelete, decpDirIsExists, decpIsCompelete)

		if decpIsCompelete == true {
			mylog.Logger.Info("4. 本地解压目录完整则返回")
			return

		}
		if localBkIsCompelete == true {
			mylog.Logger.Info("4. 本地全备.tar 完整 => 删除 全备(已解压)文件夹,重新解压(有理由怀疑上一次解压失败了,本地全备.tar 来不及删除)")
			full.RmDecompressedDir()
			if full.Err != nil {
				return
			}
			full.Decompressed()
			return
		}
		mylog.Logger.Info("4. 本地全备.tar 不完整 => 删除本地全备.tar + 删除 全备(已解压)文件夹, 报错，需要flow重新下载")
		full.RmDecompressedDir()
		if full.Err != nil {
			return
		}
		full.RmLocalBakcupFile()
		if full.Err != nil {
			return
		}
		full.RetryDownloadFiles()
		if full.Err != nil {
			return
		}
		return
	}

}

// RestoreBackup 在目标tendisplus上执行restorebackup命令
// 参数backupDir: 代表从目标tendisplus来看,全备的位置
// (其实 参数backupDir 和 full.SaveLocalDir full.SaveRemoteDir是同一个文件夹, 但是是不同视角)
func (full *TendisFullBackPull) RestoreBackup(dstTendisIP string, dstTendisPort int, dstTendisPasswd string) error {

	redisAddr := fmt.Sprintf("%s:%s", dstTendisIP, strconv.Itoa(dstTendisPort))
	msg := fmt.Sprintf("master:%s开始导入全备", redisAddr)
	mylog.Logger.Info(msg)
	//再次探测tendisplus连接性
	redisCli, err := myredis.NewRedisClient(redisAddr, dstTendisPasswd, 0, consts.TendisTypeTendisplusInsance)
	if err != nil {
		return err
	}
	defer redisCli.Close()

	if full.ResultFullbackup[0].ClusterMeataDir == "" {
		err = fmt.Errorf("全备文件夹不存在,请检查:%s", full.ResultFullbackup[0].ClusterMeataDir)
		mylog.Logger.Error(err.Error())
		return err

	}
	mylog.Logger.Info("full.ResultFullbackup[0].ClusterMeataDir:%s", full.ResultFullbackup[0].ClusterMeataDir)
	//这里会强制(force)恢复全备,检查tendisplus是否为空需要自己完成
	restoreCmd := fmt.Sprintf("%s  -h %s -p %d -a %s --no-auth-warning restorebackup all %s force",
		consts.TendisplusRediscli, dstTendisIP, dstTendisPort, dstTendisPasswd, full.ResultFullbackup[0].ClusterMeataDir)
	logCmd := fmt.Sprintf("%s -h %s -p %d -a xxxx --no-auth-warning restorebackup all %s force",
		consts.TendisplusRediscli, dstTendisIP, dstTendisPort, full.ResultFullbackup[0].ClusterMeataDir)
	mylog.Logger.Info("开始恢复全备,恢复命令:%s", logCmd)

	ret01, err := util.RunLocalCmd("bash", []string{"-c", restoreCmd}, "", nil, 600*time.Second)
	mylog.Logger.Info("恢复全备执行结果:%v", ret01)
	if err != nil {
		mylog.Logger.Error(fmt.Sprintf("恢复全备失败,详情:%v", err))
		return err
	}
	ret01 = strings.TrimSpace(ret01)
	if strings.Contains(ret01, "ERR:") == true {
		mylog.Logger.Error(fmt.Sprintf("恢复全备失败,err:%v,cmd:%s", err, logCmd))

		return err
	}
	msg = fmt.Sprintf("%s:%d 恢复全备成功", dstTendisIP, dstTendisPort)
	mylog.Logger.Info(msg)

	return nil
}

// GetTendisplusHearbeatKey 根据tendisplus ip port 获取心跳key
func (full *TendisFullBackPull) GetTendisplusHearbeatKey(masterIP string, masterPort int) string {
	Heartbeat := fmt.Sprintf("%s_%s:heartbeat", masterIP, strconv.Itoa(masterPort))
	return Heartbeat
}

// ClusterMeta 全备的meta信息
type ClusterMeta struct {
	Slot          string `json:"slot"`
	Flag          string `json:"flag"`
	ConfigEpoch   int    `json:"configEpoch"`
	CurrentEpoch  int    `json:"currentEpoch"`
	LastVoteEpoch int    `json:"lastVoteEpoch"`
}

// GetClusterMeata 从解压的目录中读取clustermeta.txt文件信息
func (task *TendisInsRecoverTask) GetClusterMeata() (meta *ClusterMeta, err error) {
	// 新增逻辑，在不执行binlog相关的代码时，这里会报错
	// "msg":"task.BackupFileDir: 为空，请检查RestoreBackup功能处的解压和赋值情况"
	task.BackupFileDir = task.FullBackup.LocalFullBackupDir
	mylog.Logger.Info("task BackupFileDir:%s", task.BackupFileDir)
	// 上面2行为新增逻辑，
	if task.BackupFileDir == "" {
		err = fmt.Errorf("task.BackupFileDir:%s 为空，请检查RestoreBackup功能处的解压和赋值情况", task.BackupFileDir)
		task.runtime.Logger.Error(err.Error())
		return nil, err
	}
	metaFile := filepath.Join(task.RecoverDir, task.BackupFileDir, "clustermeta.txt")
	_, err = os.Stat(metaFile)
	if err != nil {
		err = fmt.Errorf("%s os.Stat fail,err:%v", metaFile, err)
		task.runtime.Logger.Error(err.Error())
		return
	}
	fileData, err := os.ReadFile(metaFile)
	if err != nil {
		err = fmt.Errorf("读取clusterMeta文件:%s失败,err:%v", metaFile, err)
		task.runtime.Logger.Error(err.Error())
		return
	}
	task.runtime.Logger.Info("clustermeta:%s,fileData:%s", metaFile, fileData)
	meta = &ClusterMeta{}
	fileLines := strings.Split(string(fileData), "\n")
	for _, line := range fileLines {
		line = strings.TrimSpace(line)
		list01 := strings.Split(line, ":")
		if len(list01) == 0 {
			continue
		}
		if len(list01) < 2 {
			continue
		}
		if list01[0] == "slot" {
			meta.Slot = list01[1]
		} else if list01[0] == "flag" {
			meta.Flag = list01[1]
		} else if list01[0] == "configEpoch" {
			meta.ConfigEpoch, _ = strconv.Atoi(list01[1])
		} else if list01[0] == "currentEpoch" {
			meta.CurrentEpoch, _ = strconv.Atoi(list01[1])
		} else if list01[0] == "lastVoteEpoch" {
			meta.LastVoteEpoch, _ = strconv.Atoi(list01[1])
		}
	}
	if meta.Slot == "" {
		err = fmt.Errorf("读取clusterMeta文件:%s失败,meta.Slot(%s)信息为空", metaFile, meta.Slot)
		task.runtime.Logger.Error(err.Error())
		return
	}
	return
}

// RocksdbBackupMeta Rocksdb 备份元数据
type RocksdbBackupMeta struct {
	BackupType    int       `json:"backupType"`
	BinlogPos     uint64    `json:"binlogpos"`
	StartTimeSec  int64     `json:"startTimeSec"`
	StartTime     time.Time `json:"startTime"`
	EndTimeSec    int64     `json:"endTimeSec"`
	EndTime       time.Time `json:"endTime"`
	UseTimeSec    int       `json:"useTimeSec"`
	BinlogVersion int       `json:"binlogVersion"`
}

// GetRocksdbBackupMeta 获取全备中某个kvstore(rocksdb)的元数据信息
func (task *TendisInsRecoverTask) GetRocksdbBackupMeta(rocksIdx int) (meta *RocksdbBackupMeta, err error) {
	task.runtime.Logger.Info("GetRocksdbBackupMeta start ... ")
	// 解压后的文件和文件名有关，在RestoreBackup 中确定
	// 直接赋值测试
	// task.BackupFileDir = "/data/dbbak/recover_redis/2005000194-TENDISPLUS-FULL-slave-127.0.0.x-30010-20230311-214730"
	task.BackupFileDir = task.FullBackup.LocalFullBackupDir
	mylog.Logger.Info("task BackupFileDir:%s", task.BackupFileDir)
	if task.BackupFileDir == "" {
		err = fmt.Errorf("task.BackupFileDir:%s 为空,请检查RestoreBackup功能处的解压和赋值情况", task.BackupFileDir)
		task.runtime.Logger.Error(err.Error())
		return
	}
	metaFile := filepath.Join(task.RecoverDir, task.BackupFileDir, strconv.Itoa(rocksIdx), "backup_meta")
	_, err = os.Stat(metaFile)
	if err != nil {
		err = fmt.Errorf("%s os.Stat fail,err:%v", metaFile, err)
		task.runtime.Logger.Error(err.Error())
		return
	}
	task.runtime.Logger.Info("backup_meta metaFile:%s", metaFile)
	fileData, err := os.ReadFile(metaFile)
	if err != nil {
		err = fmt.Errorf("读取backup_meta文件:%s失败,err:%v", metaFile, err)
		task.runtime.Logger.Error(err.Error())
		return
	}
	meta = &RocksdbBackupMeta{}
	err = json.Unmarshal(fileData, meta)
	if err != nil {
		err = fmt.Errorf("GetRocksdbBackupMeta json.Unmarshal fail,err:%v,fileData:%s", err, string(fileData))
		task.runtime.Logger.Error(err.Error())
		return
	}
	if meta.StartTimeSec <= 0 {
		err = fmt.Errorf("读取backup_meta文件:%s失败,meta.StartTimeSec(%d)<=0", metaFile, meta.StartTimeSec)
		task.runtime.Logger.Error(err.Error())
		return
	}
	meta.StartTime = time.Unix(meta.StartTimeSec, 0)
	meta.EndTime = time.Unix(meta.EndTimeSec, 0)
	return

}

// RecoverTredisFromRocksdb 恢复目标tendis ssd
// (其实 参数backupDir 和 full.SaveLocalDir full.SaveRemoteDir是同一个文件夹, 但是是不同视角)
// NOCC:golint/fnsize(设计如此)
func (full *TendisFullBackPull) RecoverTredisFromRocksdb(dstTendisIP string,
	dstTendisPort int, dstTendisPasswd string) error {

	redisAddr := fmt.Sprintf("%s:%s", dstTendisIP, strconv.Itoa(dstTendisPort))
	msg := fmt.Sprintf("master:%s开始导入全备", redisAddr)
	mylog.Logger.Info(msg)
	//再次探测tendisplus连接性
	redisCli, err := myredis.NewRedisClient(redisAddr, dstTendisPasswd, 0, consts.TendisTypeTendisSSDInsance)
	if err != nil {
		return err
	}
	defer redisCli.Close()

	var infoRet map[string]string
	infoRet, full.Err = redisCli.Info("server")
	if full.Err != nil {
		return full.Err
	}
	masterVersion := infoRet["redis_version"]
	mylog.Logger.Info("Get redis_version success redis_version:%s", masterVersion)

	var ssdDataDir string
	ssdDataDir, full.Err = redisCli.GetDir()
	if full.Err != nil {
		return full.Err
	}
	// "Get SsdDataDir success SsdDataDir:/data1/redis/15000/data"
	mylog.Logger.Info("Get SsdDataDir success SsdDataDir:%s", ssdDataDir)

	//1、shutdown
	err = redisCli.Shutdown()
	if err != nil {
		return err
	}
	mylog.Logger.Info("master(%s) shutdown success", redisAddr)

	if full.LocalFullBackupDir == "" {
		err = fmt.Errorf("全备文件夹不存在,请检查:%s", full.LocalFullBackupDir)
		mylog.Logger.Error(err.Error())
		return err

	}
	mylog.Logger.Info("full.LocalFullBackupDir:%s", full.LocalFullBackupDir)

	fullFilePath := fmt.Sprintf("%v/%v", full.SaveDir, full.LocalFullBackupDir)
	if _, err := os.Stat(fullFilePath); os.IsNotExist(err) {
		err = fmt.Errorf("全备文件夹不存在,请检查:%s", full.LocalFullBackupDir)
		mylog.Logger.Error(err.Error())
		return err
	}

	DepsDir := "/usr/local/redis/bin/deps"
	if _, err := os.Stat(DepsDir); os.IsNotExist(err) {
		err = fmt.Errorf("%s:不存在,请检查:%s", DepsDir, DepsDir)
		mylog.Logger.Error(err.Error())
		return err
	}

	nowtime := time.Now().Local().Format(consts.FilenameTimeLayout)
	rockdbDir := filepath.Join(ssdDataDir, "rocksdb")
	bakDir := filepath.Join(filepath.Dir(ssdDataDir), "backup_rocksdb."+nowtime)
	// 2、mv 掉本地的数据,mv 到备份目录
	mvCmd := fmt.Sprintf("mv %s %s", rockdbDir, bakDir)
	mylog.Logger.Info(mvCmd)
	util.RunBashCmd(mvCmd, "", nil, 2*time.Hour)
	util.LocalDirChownMysql(bakDir)

	// 3、备份文件恢复
	var extraOpt string
	if strings.Contains(masterVersion, "v1.2") {
		extraOpt = " 1"
	} else if strings.Contains(masterVersion, "v1.3") {
		extraOpt = ""
	} else {
		full.Err = fmt.Errorf("unsupported tendis version:%s,exit.", masterVersion)
		mylog.Logger.Error(full.Err.Error())
		return full.Err
	}
	restoreTool := full.getRestoreTool(dstTendisIP, masterVersion, dstTendisPort)
	if full.Err != nil {
		return full.Err
	}

	restoreCmd := fmt.Sprintf(`
	export LD_PRELOAD=%s/libjemalloc.so
	export LD_LIBRARY_PATH=LD_LIBRARY_PATH:%s
	%s %s %s %s
	`, DepsDir, DepsDir, restoreTool, fullFilePath, rockdbDir, extraOpt)
	mylog.Logger.Info(restoreCmd)

	var ret string
	ret, full.Err = util.RunLocalCmd("bash", []string{"-c", restoreCmd}, "", nil, 2*time.Hour)
	mylog.Logger.Info("restore command result:" + ret)
	if full.Err != nil {
		mylog.Logger.Error(fmt.Sprintf("恢复全备失败,详情:%v", err))
		return full.Err
	}

	if util.FileExists(rockdbDir) {
		mylog.Logger.Info("restore ok, %s generated", rockdbDir)
	} else {
		full.Err = fmt.Errorf("restore command failed, %s not generated", rockdbDir)
		mylog.Logger.Error(full.Err.Error())
		return full.Err
	}
	util.LocalDirChownMysql(rockdbDir)

	ret01 := strings.TrimSpace(ret)
	if strings.Contains(ret01, "ERR:") == true {
		mylog.Logger.Error(fmt.Sprintf("恢复全备失败,err:%v,cmd:%s", err, restoreCmd))
		return full.Err
	}

	// 4、拉起节点
	startScript := filepath.Join("/usr/local/redis/bin", "start-redis.sh")
	_, full.Err = util.RunLocalCmd("su", []string{consts.MysqlAaccount, "-c", startScript + " " + strconv.Itoa(
		dstTendisPort)}, "", nil, 30*time.Second)
	if full.Err != nil {
		return full.Err
	}
	mylog.Logger.Info(fmt.Sprintf("su %s -c \"%s\"", consts.MysqlAaccount,
		startScript+"  "+strconv.Itoa(dstTendisPort)))
	time.Sleep(2 * time.Second)

	//再次探测tendisplus连接性->拉起是否成功
	redisCli, err = myredis.NewRedisClient(redisAddr, dstTendisPasswd, 0, consts.TendisTypeTendisplusInsance)
	if err != nil {
		return err
	}
	defer redisCli.Close()

	msg = fmt.Sprintf("%s:%d 恢复全备成功", dstTendisIP, dstTendisPort)
	mylog.Logger.Info(msg)

	return nil
}

func (full *TendisFullBackPull) getRestoreTool(dstTendisIP, masterVersion string, dstTendisPort int) (restoreTool string) {

	if strings.Contains(masterVersion, "v1.2.") {
		restoreTool = "/usr/local/redis/bin/rr_restore_backup"
	} else if strings.Contains(masterVersion, "v1.3.") {
		restoreTool = "/usr/local/redis/bin/tredisrestore"
	} else {
		full.Err = fmt.Errorf("redisMaster(%s:%d) version:%s cannot find restore-tool",
			dstTendisIP, dstTendisPort, masterVersion)
		mylog.Logger.Error(full.Err.Error())
		return
	}
	if !util.FileExists(restoreTool) {
		full.Err = fmt.Errorf("redis(%s) restore_tool:%s not exists", dstTendisIP, restoreTool)
		mylog.Logger.Error(full.Err.Error())
		return
	}
	return
}

// RecoverCacheRedisFromBackupFile 恢复目标tendis cache
// NOCC:golint/fnsize(其他)
func (full *TendisFullBackPull) RecoverCacheRedisFromBackupFile(sourceIP string,
	sourcePort int, dstTendisIP string, dstTendisPort int, dstTendisPasswd string) {

	newRedisAddr := fmt.Sprintf("%s:%s", dstTendisIP, strconv.Itoa(dstTendisPort))
	oldnewRedisAddr := fmt.Sprintf("%s:%s", sourceIP, strconv.Itoa(sourcePort))
	msg := fmt.Sprintf("master:%s开始导入全备", newRedisAddr)
	mylog.Logger.Info("RecoverCacheRedisFromBackupFile: start recover"+
		"redis:%s from redis:%s aof or rdb ... ", newRedisAddr, oldnewRedisAddr)
	mylog.Logger.Info(msg)
	//再次探测tendis连接性
	redisCli, err := myredis.NewRedisClient(newRedisAddr, dstTendisPasswd, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		mylog.Logger.Error(err.Error())
		full.Err = err
		return
	}
	defer redisCli.Close()

	//1、检查全备文件是否存在
	if full.LocalFullBackupDir == "" {
		err = fmt.Errorf("全备文件夹不存在,请检查:%s", full.LocalFullBackupDir)
		mylog.Logger.Error(err.Error())
		full.Err = err
		return
	}
	mylog.Logger.Info("full.LocalFullBackupDir:%s", full.LocalFullBackupDir)

	//全备解压完整目录
	fullFilePath := fmt.Sprintf("%v/%v", full.SaveDir, full.LocalFullBackupDir)
	if _, err := os.Stat(fullFilePath); os.IsNotExist(err) {
		err = fmt.Errorf("全备文件夹不存在,请检查:%s", full.LocalFullBackupDir)
		mylog.Logger.Error(err.Error())
		full.Err = err
		return
	}

	// 2、停dbmon 作为整体在所有任务开始前操作(前置任务已完成)

	//3、shutdown 关闭节点
	mylog.Logger.Info("redis:%s begin to shutdown", newRedisAddr)
	err = redisCli.Shutdown()
	if err != nil {
		mylog.Logger.Error("执行shutdown失败:err:%v", err)
		full.Err = err
		return
	}
	mylog.Logger.Info("master(%s) shutdown success", newRedisAddr)

	//4、  修改 配置文件appendonly 可以采用命令模式 先config set appendonly yes,在config rewrite 写入配置文件，
	// 只是这样兼容不了以前的instance.conf 配置模式
	redisConfDir := filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(dstTendisPort), "redis.conf")
	_, err = os.Stat(redisConfDir)
	if err != nil && os.IsNotExist(err) {
		redisConfDir = filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(dstTendisPort), "instance.conf")
		_, err = os.Stat(redisConfDir)
		if err != nil && os.IsNotExist(err) {
			err := fmt.Errorf("没有找到redis.conf配置文件和instance.conf配置文件")
			mylog.Logger.Error("recoverRedisFromAof failed 没有找到redis.conf配置文件和instance.conf配置文件")
			full.Err = err
			return
		}

	}
	mylog.Logger.Info("配置文件为:%s", redisConfDir)

	// 获取 appendonly 值
	getAppendonlyCmd := fmt.Sprintf(`grep -E '^appendonly' %s|awk '{print $2}'|head -1`, redisConfDir)
	appendonly, err := util.RunBashCmd(getAppendonlyCmd, "", nil, 10*time.Minute)
	if err != nil {
		mylog.Logger.Error("get appendonly failed: %v", err)
		full.Err = err
		return
	}
	mylog.Logger.Info("appendonly:%s", appendonly)
	var dataPath, backupFile, backupFilePath string

	if strings.Contains(full.ResultFullbackup[0].BackupFile, ".aof.zst") ||
		strings.Contains(full.ResultFullbackup[0].BackupFile, ".aof.lzo") {
		// 解压后文件
		backupFile := strings.TrimSuffix(full.ResultFullbackup[0].BackupFile,
			filepath.Ext(full.ResultFullbackup[0].BackupFile))
		backupFilePath = filepath.Join(fullFilePath, backupFile)
		dataPath = filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(dstTendisPort), "data", "appendonly.aof")
		if appendonly != "yes" {
			// 修改appendonly 值为yes ,用aof 文件拉起redis
			modifyAppendonlyCmd := fmt.Sprintf("sed -i  's/appendonly no/appendonly yes/' %s", redisConfDir)
			mylog.Logger.Info(modifyAppendonlyCmd)
			_, err = util.RunLocalCmd("bash", []string{"-c", modifyAppendonlyCmd}, "", nil, 10*time.Minute)
			if err != nil {
				err = fmt.Errorf("modify appendonly 失败,err:%v", err)
				mylog.Logger.Error(err.Error())
				full.Err = err
				return
			}

		}
		// 如果存在原来的aof文件，则删除，一般是新部署的节点不会存在
		oldAofdir := filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(dstTendisPort),
			"data", "appendonly.aof")
		rmAofCmd := fmt.Sprintf("rm %s", oldAofdir)
		_, err = os.Stat(oldAofdir)
		if err == nil && !os.IsNotExist(err) {
			mylog.Logger.Info("删除原来存在的aof文件:%s", rmAofCmd)
			_, err = util.RunLocalCmd("bash", []string{"-c", rmAofCmd}, "", nil, 10*time.Minute)
			if err != nil {
				err = fmt.Errorf("rm appendonly 失败,err:%v", err)
				mylog.Logger.Error(err.Error())
				full.Err = err
				return
			}
		}

	} else if strings.Contains(full.ResultFullbackup[0].BackupFile, ".rdb") {
		backupFile = full.ResultFullbackup[0].BackupFile
		backupFilePath = filepath.Join(fullFilePath, backupFile)
		dataPath = filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(dstTendisPort), "data", "dump.rdb")
		if appendonly == "yes" {
			mylog.Logger.Info("appendonly value is:%s,need modify appendonly=no to use rdb", appendonly)
			// 修改appendonly 值为no ,用rdb 文件拉起redis
			modifyAppendonlyCmd := fmt.Sprintf("sed -i  's/appendonly yes/appendonly no/' %s", redisConfDir)
			mylog.Logger.Info(modifyAppendonlyCmd)
			_, err = util.RunLocalCmd("bash", []string{"-c", modifyAppendonlyCmd}, "", nil, 10*time.Minute)
			if err != nil {
				err = fmt.Errorf("modify appendonly 失败,err:%v", err)
				mylog.Logger.Error(err.Error())
				full.Err = err
				return
			}
		}

		// 如果存在原来的rdb文件，则删除，用最新的rdb拉起
		oldRdbdir := filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(dstTendisPort), "data", "dump.rdb")
		rmRdbCmd := fmt.Sprintf("rm %s", oldRdbdir)
		_, err = os.Stat(oldRdbdir)
		if err == nil && !os.IsNotExist(err) {
			mylog.Logger.Info("删除原来存在的dump.rdb文件:%s", rmRdbCmd)
			_, err = util.RunLocalCmd("bash", []string{"-c", rmRdbCmd}, "", nil, 10*time.Minute)
			if err != nil {
				err = fmt.Errorf("rm dump.rdb 失败,err:%v", err)
				mylog.Logger.Error(err.Error())
				full.Err = err
				return
			}
		}

	}
	mylog.Logger.Info("dataPath:%s", dataPath)

	// 确保data 目录不为空
	if dataPath == "" {
		err = fmt.Errorf("get dataPath failed,dataPath:%s", dataPath)
		full.Err = err
		mylog.Logger.Error(err.Error())
		return
	}
	// 5、移动和重命名 备份文件
	util.LocalDirChownMysql(backupFilePath)
	mvCmd := fmt.Sprintf("mv -f %s %s ", backupFilePath, dataPath)
	mylog.Logger.Info("RecoverCacheRedisFromBackupFile: mvCmd:%s", mvCmd)
	_, err = util.RunLocalCmd("bash", []string{"-c", mvCmd}, "", nil, 10*time.Minute)
	if err != nil {
		err = fmt.Errorf("mv aof file failed,err:%v", err)
		full.Err = err
		mylog.Logger.Error(err.Error())
		return
	}

	// 6、加载备份文件，拉起节点
	err = full.WaitForStartRedis(dstTendisIP, dstTendisPort, dstTendisPasswd)
	if err != nil {
		mylog.Logger.Error("WaitForStartRedis failed :%v", err)
		full.Err = err
		return
	}

	//再次探测tendis连接性->拉起是否成功
	redisCli, err = myredis.NewRedisClient(newRedisAddr, dstTendisPasswd, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		mylog.Logger.Error("NewRedisClient failed :%v", err)
		full.Err = err
		return
	}
	defer redisCli.Close()
	// 7、拉起Dbmon 作为整体在所有任务结束后操作 (前置任务来完成)

	msg = fmt.Sprintf("%s:%d 恢复全备成功", dstTendisIP, dstTendisPort)
	mylog.Logger.Info(msg)

	return
}

// WaitForStartRedis 加载redis
func (full *TendisFullBackPull) WaitForStartRedis(dstTendisIP string, dstTendisPort int, dstTendisPasswd string) error {

	mylog.Logger.Info("WaitForStartRedis:start-redis.sh,addr:%s:%d", dstTendisIP, dstTendisPort)
	// 加载备份文件，拉起节点
	startScript := filepath.Join(consts.UsrLocal, "redis", "bin", "start-redis.sh")
	mylog.Logger.Info(fmt.Sprintf("su %s -c \"%s\"",
		consts.MysqlAaccount, startScript+"  "+strconv.Itoa(dstTendisPort)))
	_, err := util.RunLocalCmd("su", []string{consts.MysqlAaccount, "-c",
		startScript + "  " + strconv.Itoa(dstTendisPort)}, "", nil, 20*time.Minute)
	if err != nil {
		err = fmt.Errorf("WaitForStartRedis failed:%v", err)
		return err
	}
	time.Sleep(30 * time.Second)

	newRedisAddr := fmt.Sprintf("%s:%s", dstTendisIP, strconv.Itoa(dstTendisPort))
	retryTimeLimit := 6
	// 等待加载redis
	for {
		if retryTimeLimit == 0 {
			break
		}
		// NewRedisClient 这里也会去ping
		_, err = myredis.NewRedisClient(newRedisAddr, dstTendisPasswd, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			if retryTimeLimit > 0 {
				mylog.Logger.Warn("WaitForStartRedis info:%v", err)
				retryTimeLimit--
				time.Sleep(10 * time.Second)
				continue
			}
			mylog.Logger.Error("WaitForStartRedis fail newRedisAddr:%s,retry times:%d,err:%v", newRedisAddr, retryTimeLimit, err)
			return err
		}
		mylog.Logger.Info("WaitForStartRedis finish success")
		break
	}
	return nil

}
