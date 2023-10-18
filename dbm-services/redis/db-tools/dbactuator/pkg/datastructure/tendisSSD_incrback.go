package datastructure

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/customtime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// TredisRocksDBIncrBackItem tendisSSD 指定rocksdb的增备信息项
type TredisRocksDBIncrBackItem struct {
	Incr             int                   `json:"incr"`
	NodeIP           string                `json:"node_ip"`
	FileName         string                `json:"filename"`
	BackupFile       string                `json:"backup_file"`
	DecompressedFile string                `json:"decompressedFile"` //解压后的文件名
	BinlogIdx        int64                 `json:"binlogIdx"`
	BackupTaskid     int64                 `json:"backup_taskid"` // 任务ID
	BackupSize       int64                 `json:"backup_size"`   // 文件大小
	BinlogStartPos   uint64                `json:"binlogStartPos"`
	BinlogEndPos     uint64                `json:"binlogEndPos"`
	BackupStart      customtime.CustomTime `json:"backup_start"` //binlog文件中获取,代表 上一个binlog文件最后一条binlog的时间
	BackupEnd        customtime.CustomTime `json:"backup_end"`   //备份文件上传备份系统成功时间

}

// TredisRocksDBIncrBack tendisSSD 节点拉取增备
type TredisRocksDBIncrBack struct {
	FileName string `json:"filename"`
	SourceIP string `json:"sourceIp"`
	//保存文件的目录(如果是在k8s中,则代表node 上的dir)
	SaveNodeDir string `json:"saveRemoteDir"`
	//保存备份文件的本地目录

	SaveMyDir string `json:"saveLocalDir"`
	//保存文件的服务器(如果是k8s中,则代表node ip)
	SaveHost  string    `json:"saveHost"`
	StartTime time.Time `json:"startTime"` //拉取增备的起始时间
	EndTime   time.Time `json:"endTime"`   //拉取增备的结束时间
	// #./tredisbinlog logfile --start-datetime=1111 --stop-datetime=22222 --start-position=333333
	//  --stop-position=55555 --keys=1,2,4,5,6,7,8,9

	FullStartPos      uint64 `json:"fullStartPos"`        //回档导入增备时,--start-position 这里是全备文件传入的position
	RecoveryTimePoint string `json:"recovery_time_point"` //回档导入增备时,--end-datetime
	//每个rocksdb 最靠近(小于) startTime 的binlog,
	//binlog的BackupStart时间小于startTime
	PerRocksNearestStart *TredisRocksDBIncrBackItem
	//每个rocksdb 最靠近(大于) endTime 的binlog
	//binlog的BackupStart时间大于endTime
	PerRocksNearestEnd *TredisRocksDBIncrBackItem

	//value: 每个rocksdb对应的binlog列表,按照文件index从小到大排序
	ResultSortBinlog []*TredisRocksDBIncrBackItem `json:"resultSortBinlog"`
	//key: binlog file name
	//value: 文件对应的binlog项
	ResultBinlogMap map[string]*TredisRocksDBIncrBackItem `json:"resultBinlogMap"`

	Err error `json:"-"` //错误信息
}

// NewTredisRocksDBIncrBack 新建tendisssd rocksdb的binlog拉取任务
// FileName=fileName 过滤信息
// sourceIP 查询 IP 源
// startTime 拉取增备的开始时间 -> 全备份的开始时间
// endTime 拉取增备份的结束时间 -> 回档时间
func NewTredisRocksDBIncrBack(filename, sourceIP string, fullStartPos uint64, startTime, endTime,
	saveHost, saveNodeDir, saveMyDir, recoveryTimePoint string) (ret *TredisRocksDBIncrBack) {
	mylog.Logger.Info("NewTredisRocksDBIncrBack start ...")

	ret = &TredisRocksDBIncrBack{
		FileName:          filename,
		SourceIP:          sourceIP,
		SaveHost:          saveHost,
		SaveNodeDir:       saveNodeDir,
		SaveMyDir:         saveMyDir,
		FullStartPos:      fullStartPos,
		RecoveryTimePoint: recoveryTimePoint,
	}
	layout := "2006-01-02 15:04:05"
	var err error
	ret.StartTime, err = time.ParseInLocation(layout, startTime, time.Local)
	if err != nil {
		ret.Err = fmt.Errorf("startTime:%s time.parse fail,err:%s,layout:%s", startTime, err, layout)
		mylog.Logger.Error(ret.Err.Error())
		return ret
	}
	ret.EndTime, err = time.ParseInLocation(layout, endTime, time.Local)
	if err != nil {
		ret.Err = fmt.Errorf("endTime:%s time.parse fail,err:%s,layout:%s", endTime, err, layout)
		mylog.Logger.Error(ret.Err.Error())
		return ret
	}
	mylog.Logger.Info("StartTime:%s,EndTime:%s", ret.StartTime, ret.EndTime)
	if ret.EndTime.Before(ret.StartTime) == true || ret.EndTime.Equal(ret.StartTime) == true {
		ret.Err = fmt.Errorf("tendisssd binlog拉取,endtime:%s 小于等于 startTime:%s",
			endTime, startTime)
		mylog.Logger.Error(ret.Err.Error())
		return ret
	}
	if ret.StartTime.After(time.Now()) == true {
		//未来时间
		ret.Err = fmt.Errorf("binlogPull startTime:%s > time.Now()", startTime)
		mylog.Logger.Error(ret.Err.Error())
		return ret
	}
	if ret.EndTime.After(time.Now()) == true {
		//未来时间
		ret.Err = fmt.Errorf("binlogPull endTime:%s > time.Now()", endTime)
		mylog.Logger.Error(ret.Err.Error())
		return ret
	}
	ret.ResultSortBinlog = []*TredisRocksDBIncrBackItem{}
	ret.ResultBinlogMap = make(map[string]*TredisRocksDBIncrBackItem)
	return
}

// getSeqFromFile，获取文件中的序列号
func (incr *TredisRocksDBIncrBack) getSeqFromFile(fpath string) uint64 {
	mylog.Logger.Info("getSeqFromFile start ...")
	DepsDir := "/usr/local/redis/bin/deps"
	//获取文件第一行（包含序列号）
	// firstline, err := exec.Command(filepath.Join(binPath, "tredisbinlog"),
	// "--with-timestamp", "--with-seq", fpath).Output()
	getSeqCmd := fmt.Sprintf(`
	export LD_PRELOAD=%s/libjemalloc.so
	export LD_LIBRARY_PATH=LD_LIBRARY_PATH:%s
	%s --with-timestamp --with-seq  %s 
	`, DepsDir, DepsDir, consts.TredisBinlogBin, fpath)
	mylog.Logger.Info("获取 binlog 获取文件第一行（包含序列号）,命令:%v", getSeqCmd)
	firstline, err := util.RunLocalCmd("bash", []string{"-c", getSeqCmd}, "", nil, 1*time.Hour)

	if err != nil {
		mylog.Logger.Error(fmt.Sprintf("解析binlog失败,详情:%v", err))
		incr.Err = err
		return 0
	}
	mylog.Logger.Info("解析binlog成功")
	mylog.Logger.Debug("解析binlog成功,firstline:%v", firstline)
	//如果获取到第一行
	if len(firstline) > 0 {
		//将第一行按空格分割为三部分
		f := strings.Fields(string(firstline))
		//返回第二部分（序列号）
		seq, err := strconv.Atoi(f[1])
		if err != nil {
			mylog.Logger.Error(fmt.Sprintf("解析binlog,分割firstline失败,详情:%v", err))
		}
		mylog.Logger.Info("getSeqFromFile file:%s seq:%d", fpath, seq)
		return uint64(seq)
	}
	//如果未获取到第一行，返回-1
	return 0
}

// AddBinlogToMap 添加binlog项到 ResultBinlogMap,ResultSortBinlog中
func (incr *TredisRocksDBIncrBack) AddBinlogToMap(item01 *TredisRocksDBIncrBackItem) {
	if item01 == nil {
		return
	}
	if _, ok := incr.ResultBinlogMap[item01.BackupFile]; ok == true {
		//去重
		return
	}
	incr.ResultBinlogMap[item01.BackupFile] = item01
	incr.ResultSortBinlog = append(incr.ResultSortBinlog, item01)
}

// GetTredisIncrbacks 查询特定端口的binlog备份文件
// NOCC:golint/fnsize(设计如此)
func (incr *TredisRocksDBIncrBack) GetTredisIncrbacks(binlogFileList []FileDetail) (backs []*TredisRocksDBIncrBackItem) {
	mylog.Logger.Info("GetTredisIncrbacks start ...")
	layout := "2006-01-02 15:04:05"
	mylog.Logger.Info("fileName:%s", incr.FileName)
	// tredis示例：  binlog-127.0.0.x-30000-7-0003612-20230326232536.log.zst
	// ssd示例：  binlog-127.0.0.x-30000-0000386-20230420021655.log.zst

	binlogReg := regexp.MustCompile(`^*?-(\d+)-(\d+)-(\d+).log.zst`)
	layout1 := "20060102150405"
	for _, str01 := range binlogFileList {
		back01 := &TredisRocksDBIncrBackItem{}
		taskID, _ := strconv.Atoi(str01.TaskID)
		// size, _ := strconv.Atoi(str01.Size)
		if taskID < 0 || str01.Size < 0 {
			//backup_taskid 小于0 或backup_size 小于0的备份,是无效备份
			msg := fmt.Sprintf("filename:%s  incrBackup:%s backupTaskid:%s<0  backupSize:%d<0 is invalid,skip...",
				incr.FileName, str01.FileName, str01.TaskID, str01.Size)
			mylog.Logger.Info(msg)
			continue
		}
		back01.BackupTaskid, _ = strconv.ParseInt(str01.TaskID, 10, 64)
		back01.BackupSize, _ = strconv.ParseInt(strconv.Itoa(str01.Size), 10, 64)
		back01.BackupFile = str01.FileName
		mylog.Logger.Info("BackupFile:%s", back01.BackupFile)
		back01.NodeIP = str01.SourceIP
		mylog.Logger.Info("BackupSize:%d", back01.BackupSize)
		mylog.Logger.Debug("BackupTaskid:%d", back01.BackupTaskid)
		match01 := binlogReg.FindStringSubmatch(str01.FileName)

		if len(match01) != 4 {
			incr.Err = fmt.Errorf(
				"filename:%s  backup:%v format not correct,backupFile:%s cann't find rocksdbIdx/binlogIdx/createTime",
				incr.FileName, back01, str01.FileName)
			mylog.Logger.Error(incr.Err.Error())
			return
		}
		bkCreateTime, err01 := time.ParseInLocation(layout1, match01[3], time.Local)
		if err01 != nil {
			incr.Err = fmt.Errorf(
				"backup file createTime:%s time.parese fail,err:%s,layout1:%s",
				match01[3], err01, layout1)
			mylog.Logger.Error(incr.Err.Error())
			return
		}

		back01.BinlogIdx, _ = strconv.ParseInt(match01[2], 10, 64)
		back01.BackupStart.Time = bkCreateTime                                                       //不要用backupStart值
		back01.BackupEnd.Time, err01 = time.ParseInLocation(layout, str01.FileLastMtime, time.Local) //文件最后修改时间
		if err01 != nil {
			incr.Err = fmt.Errorf(
				"backup file lastTime:%s time.parese fail,err:%s,layout:%s",
				str01.FileLastMtime, err01, layout)
			mylog.Logger.Error(incr.Err.Error())
			return
		}

		// 过滤节点维度的文件,这里比较重要，因为flow传下来的是这台机器涉及到的所有节点信息，
		// 这里是针对单节点的，所以需要过滤出来，这个值返回给前置函数
		if strings.Contains(back01.BackupFile, incr.FileName) {
			backs = append(backs, back01)
		}
	}
	mylog.Logger.Info("len(backs):%d", len(backs))
	mylog.Logger.Info("TredisRocksDBIncrBackItem:%v", backs[0])
	return
}

// GetTredisIncrbacksSpecRocks 获取startTime~endTime时间段内的binlog
// NOCC:golint/fnsize(设计如此)
func (incr *TredisRocksDBIncrBack) GetTredisIncrbacksSpecRocks(binlogFileList []FileDetail) {

	// 获取startTime~endTime时间段内的binlog
	// layout := "20060102"
	layout02 := "2006-01-02 15:04:05"
	//从备份列表中选择最靠近 startTime 的文件,
	// nearestStartBk.BackupStart 小于等于 StartTime
	var nearestStartBk *TredisRocksDBIncrBackItem = nil
	//从备份列表中选择最靠近 endTime 的文件,
	// nearestEndBk.BackupStart 大于等于 EndTime
	var nearestEndBk *TredisRocksDBIncrBackItem = nil
	//这里查询范围广一些，再过滤
	backs := incr.GetTredisIncrbacks(binlogFileList)
	for _, bk01 := range backs {
		bkItem := bk01
		//只需要那些BackupStart <= incr.StartTime 的binlog
		if bkItem.BackupStart.Before(incr.StartTime) == true ||
			bkItem.BackupEnd.Equal(incr.StartTime) == true {
			if nearestStartBk == nil {
				// 第一次找到 BackupStart 小于 startTime 的备份
				nearestStartBk = bkItem
			} else {
				// nearestStartBk.BackupStart < 该备份BackupStart <= incr.StartTime
				// 或者
				// nearestStartBk.BackupStart == 该备份BackupStart 同时 该备份BinlogIdx < nearestStartBk.BinlogIdx
				// (同一时间大量写入时可能一秒钟生成多个binlog文件,此时同一秒生成的所有binlog都保留,所以 nearestStartBk.BinlogIdx是最小的)

				//  如binlog-127.0.0.x-30010-0-0002495-20230311124436.log.zst： BinlogIdx是0002495
				if bkItem.BackupStart.After(nearestStartBk.BackupStart.Time) == true ||
					(bkItem.BackupStart.Equal(nearestStartBk.BackupStart.Time) == true &&
						bkItem.BinlogIdx < nearestStartBk.BinlogIdx) {
					nearestStartBk = bkItem
				}

			}
		}

		//只需要那些BackupStart >= incr.EndTime 的binlog
		if bkItem.BackupStart.After(incr.EndTime) == true ||
			bkItem.BackupStart.Equal(incr.EndTime) == true {
			if nearestEndBk == nil {
				//第一次找到 BackupStart  大于等于 endTIme的备份
				nearestEndBk = bkItem
			} else {
				// incr.EndTime <= 该备份BackupStart < nearestEndBk.BackupStart.
				// 或者
				// nearestEndBk.BackupStart == 该备份BackupStart 同时 该备份BinlogIdx > nearestStartBk.BinlogIdx
				// (同一时间大量写入时可能一秒钟生成多个binlog文件,此时同一秒生成的所有binlog都保留,所以 nearestEndBk.BinlogIdx是最大的)
				if bkItem.BackupStart.Before(nearestEndBk.BackupStart.Time) == true ||
					(bkItem.BackupStart.Equal(nearestEndBk.BackupStart.Time) == true &&
						bkItem.BinlogIdx > nearestEndBk.BinlogIdx) {
					nearestEndBk = bkItem
				}
			}
		}

	}

	if nearestStartBk == nil {
		incr.Err = fmt.Errorf("filename:%s  向前%d天,没有找到时间 小于 startTime:%s的binlog",
			incr.FileName,

			LastNDaysIncrBack(),
			incr.StartTime.Local().Format(layout02))
		mylog.Logger.Error(incr.Err.Error())
		return
	}

	msg := fmt.Sprintf("filename:%s 找到距离startTime:%s最近(小于)的binlog:%s,binlogStart:%s",
		incr.FileName,

		incr.StartTime.Local().Format(layout02),
		nearestStartBk.BackupFile,
		nearestStartBk.BackupStart.Local().Format(layout02))
	mylog.Logger.Info(msg)

	if nearestEndBk == nil {
		incr.Err = fmt.Errorf("filename:%s  向后%d天,没有找到时间大于endTime:%s的binlog",
			incr.FileName,

			LastNDaysIncrBack(),
			incr.EndTime.Local().Format(layout02))
		mylog.Logger.Error(incr.Err.Error())
		return
	}

	msg = fmt.Sprintf("filename:%s 找到距离endTime:%s最近(大于)的binlog:%s,binglogEnd:%s",
		incr.FileName,

		incr.EndTime.Local().Format(layout02),
		nearestEndBk.BackupFile,
		nearestEndBk.BackupStart.Local().Format(layout02))
	mylog.Logger.Info(msg)

	//成功获取到 nearestStartBk nearestEndBk,继续获取两者之间的binlog
	start01 := nearestStartBk.BackupStart.Time
	// end01 := nearestEndBk.BackupStart.Time
	// 使用 最后一个binlog文件上传备份系统成功时间, 而不是 binlog 文件名中的时间(也就是binlog文件生成时间)
	// 因为6月1日生成的binlog,有可能6月2日才上传成功
	// 而在dba redis中 或者 备份系统中 只有 6月2号的记录里面才能查询到该 binlog文件
	end01 := nearestEndBk.BackupEnd.Time
	//start02 对应nearestStartBk.BackupStart 当天0点0分0秒
	//end02 对应nearestEndBk.BackupStart 当天0点0分0秒
	//我们需要将 start02 end02之间所有day的binlog都筛选到
	start02 := time.Date(start01.Year(), start01.Month(), start01.Day(), 0, 0, 0, 0, start01.Location())
	end02 := time.Date(end01.Year(), end01.Month(), end01.Day(), 0, 0, 0, 0, end01.Location())
	incr.AddBinlogToMap(nearestStartBk)
	incr.AddBinlogToMap(nearestEndBk)

	incr.PerRocksNearestStart = nearestStartBk
	incr.PerRocksNearestEnd = nearestEndBk

	for start02.Before(end02) == true || start02.Equal(end02) == true {

		backs := incr.GetTredisIncrbacks(binlogFileList)

		for _, bk01 := range backs {
			bkItem := bk01
			if (bkItem.BackupStart.After(nearestStartBk.BackupStart.Time) == true ||
				bkItem.BackupStart.Equal(nearestStartBk.BackupStart.Time) == true) &&
				(bkItem.BackupStart.Before(nearestEndBk.BackupStart.Time) == true ||
					bkItem.BackupStart.Equal(nearestEndBk.BackupStart.Time) == true) {
				incr.AddBinlogToMap(bkItem)
			}
		}
		start02 = start02.Add(1 * 24 * time.Hour)
	}
	//按照binlog index排序
	sort.Slice(incr.ResultSortBinlog, func(i, j int) bool {
		return incr.ResultSortBinlog[i].BinlogIdx < incr.ResultSortBinlog[j].BinlogIdx
	})

	incr.isGetAllBinlogInfo()
	if incr.Err != nil {
		return
	}
	return
}

/*
判断binlog文件是否连续,是否重复;
- 重复则报错;
- 不连续则返回缺失的binlog index,如 2,3,5,8 则返回缺失的4,6,7
*/
func getTredisNotReadyBinlogs(sortBinlogs []*TredisRocksDBIncrBackItem) ([]string, error) {
	var ret []string
	var err error
	preListIdx := 0
	preBinlogIdx := sortBinlogs[0].BinlogIdx
	for idx, bin01 := range sortBinlogs {
		binItem := bin01
		if idx == preListIdx {
			//第一个元素忽略
			continue
		}
		if binItem.BinlogIdx <= preBinlogIdx {
			//如果后面的binlog index小于等于前一个binlog index
			err = fmt.Errorf("当前binlog index:%d <= 前一个binlog index:%d", binItem.BinlogIdx, preBinlogIdx)
			mylog.Logger.Error(err.Error())
			mylog.Logger.Error(err.Error())
			return ret, err
		}
		if binItem.BinlogIdx == preBinlogIdx+1 {
			//符合预期
			preBinlogIdx = binItem.BinlogIdx
			continue
		}
		preBinlogIdx++
		for preBinlogIdx < bin01.BinlogIdx {
			ret = append(ret, fmt.Sprintf("%d", preBinlogIdx))
			preBinlogIdx++
		}
	}
	return ret, nil
}

/*
判断所需binlog文件信息是否已全部获取到;
- ResultSortBinlog 第二个binlog文件序号 必须 只比 第一个binlog 文件序号大1
- ResultSortBinlog 倒数第一个binlog文件序号 必须 只比 倒数第二个binlog文件序号大 1
- 最后一个文件序号 减去 第一个文件序号 等于 len(ResultSortBinlog)+1
- ResultSortBinlog 第一个binlog.BackupStart必须小于 startTime, 第二个binlog.BackupStart必须大于 startTime
- ResultSortBinlog 最后一个binlog.BackupStart必须大于 endTime, 倒数第二个binlog.BackupStart必须小于 endTime
*/
// NOCC:golint/fnsize(设计如此)
func (incr *TredisRocksDBIncrBack) isGetAllBinlogInfo() (ret bool) {
	mylog.Logger.Info("isGetAllBinlogInfo start ...")
	cnt := len(incr.ResultSortBinlog)
	mylog.Logger.Info("ResultSortBinlog len:%d", cnt)
	layout := "2006-01-02 15:04:05"

	if cnt < 2 {
		//至少会包含两个binlog文件,第一个BackupStart小于 startTime, 第二个BackupStart 大于 endTime
		str01 := ""
		for _, bk01 := range incr.ResultSortBinlog {
			str01 = fmt.Sprintf("%s,%s", str01, bk01.BackupFile)
		}
		incr.Err = fmt.Errorf(
			"filename:%s 拉取[%s ~ %s]时间段的binlog,至少包含2个binglo,当前%d个binlog,详情:%s",
			incr.FileName,
			incr.StartTime.Local().Format(layout),
			incr.EndTime.Local().Format(layout),
			cnt, str01)
		mylog.Logger.Error(incr.Err.Error())
		mylog.Logger.Error(incr.Err.Error())
		return false
	}
	firstBinlog := incr.ResultSortBinlog[0]
	secondBinlog := incr.ResultSortBinlog[1]

	lastBinlog := incr.ResultSortBinlog[cnt-1]
	beforeLastBinlog := incr.ResultSortBinlog[cnt-2]

	if secondBinlog.BinlogIdx-firstBinlog.BinlogIdx != 1 {
		incr.Err = fmt.Errorf(
			"filename:%s 拉取[%s ~ %s]时间段的binlog,第一binlog:%s 和 第二binlog:%s 不连续",
			incr.FileName,
			incr.StartTime.Local().Format(layout),
			incr.EndTime.Local().Format(layout),
			firstBinlog.BackupFile, secondBinlog.BackupFile,
		)

		mylog.Logger.Error(incr.Err.Error())
		return
	}
	if lastBinlog.BinlogIdx-beforeLastBinlog.BinlogIdx != 1 {
		incr.Err = fmt.Errorf(
			"filename:%s 拉取[%s ~ %s]时间段的binlog,倒数第二binlog:%s 和 倒数第一binlog:%s 不连续",
			incr.FileName,
			incr.StartTime.Local().Format(layout),
			incr.EndTime.Local().Format(layout),
			beforeLastBinlog.BackupFile, lastBinlog.BackupFile,
		)
		mylog.Logger.Error(incr.Err.Error())

		return
	}
	//是否连续
	binIndexList, err := getTredisNotReadyBinlogs(incr.ResultSortBinlog)
	if err != nil {
		incr.Err = err
		return false
	}
	if len(binIndexList) > 0 {
		incr.Err = fmt.Errorf("缺失的binlog共%d个,缺失的binlog index是:%s",
			len(binIndexList), strings.Join(binIndexList, ","))

		mylog.Logger.Error(incr.Err.Error())
		return false
	}
	//第一个binlog.BackupStart必须小于等于 startTime,大于则报错
	if firstBinlog.BackupStart.After(incr.StartTime) == true {
		incr.Err = fmt.Errorf(
			"filename:%s ,第一个binog:%s,binlogStart:%s 大于startTime(全备时间):%s",
			incr.FileName,
			firstBinlog.BackupFile,
			firstBinlog.BackupStart.Local().Format(layout),
			incr.StartTime.Local().Format(layout))
		mylog.Logger.Error(incr.Err.Error())

		return false
	}
	//第二个binlog.BackupStart必须大于(等于) startTime,小于则报错
	for idx01 := 1; secondBinlog.BackupStart.Equal(firstBinlog.BackupStart.Time) == true; idx01++ {
		//因为相同时间可能有多个binlog,所以跳过与 firstBinlog.BinlogEnd 相等的
		secondBinlog = incr.ResultSortBinlog[idx01]
	}
	if secondBinlog.BackupStart.Before(incr.StartTime) {
		err = fmt.Errorf(
			"filename:%s ,第二个binlog:%s,binlogStart:%s 时间小于startTime(全备时间):%s",
			incr.FileName,
			secondBinlog.BackupFile,
			secondBinlog.BackupStart.Local().Format(layout),
			incr.StartTime.Local().Format(layout))
		mylog.Logger.Error(err.Error())

		return false
	}
	//倒数第二个binlog.BackupStart必须小于等于 endTime, 大于则报错
	for idx02 := cnt - 2; beforeLastBinlog.BackupStart.Equal(lastBinlog.BackupStart.Time) == true; idx02-- {
		//因为相同时间可能有多个binlog,所以跳过与 lastBinlog.BinlogEnd 相等的
		beforeLastBinlog = incr.ResultSortBinlog[idx02]
	}
	if beforeLastBinlog.BackupStart.After(incr.EndTime) == true {
		incr.Err = fmt.Errorf(
			"filename:%s ,倒数第二个binlog:%s,binlogStart:%s 时间大于endTime(回档目标时间):%s",
			incr.FileName,
			beforeLastBinlog.BackupFile,
			beforeLastBinlog.BackupStart.Local().Format(layout),
			incr.EndTime.Local().Format(layout))
		mylog.Logger.Error(incr.Err.Error())

		return false
	}
	//最后一个binlog.BackupStart必须大于等于 endTime,小于则报错
	if lastBinlog.BackupStart.Before(incr.EndTime) == true {
		incr.Err = fmt.Errorf(
			"filename:%s ,最后一个binlog:%s,binlogStart:%s 时间小于endTime(回档目标时间):%s",
			incr.FileName,
			lastBinlog.BackupFile,
			lastBinlog.BackupStart.Local().Format(layout),
			incr.EndTime.Local().Format(layout))
		mylog.Logger.Error(incr.Err.Error())
		return false
	}
	msg := fmt.Sprintf(`filename:%s找到所有[%s~%s]时间段的binlog,
	共%d个,第一个binlog:%s binlogStart:%s,最后一个binlog:%s binlogStart:%s`,
		incr.FileName,
		incr.StartTime.Local().Format(layout),
		incr.EndTime.Local().Format(layout),
		cnt,
		firstBinlog.BackupFile,
		firstBinlog.BackupStart.Local().Format(layout),
		lastBinlog.BackupFile,
		lastBinlog.BackupStart.Local().Format(layout),
	)
	mylog.Logger.Info(msg)
	return
}

// TotalSize 所有binlog所需磁盘空间大小
func (incr *TredisRocksDBIncrBack) TotalSize() int64 {
	var ret int64 = 0
	for _, bk01 := range incr.ResultSortBinlog {
		bkItem := bk01
		ret = ret + bkItem.BackupSize
	}
	return ret
}

// GetBackupFileExt 获取备份文件后缀(如果后缀无法解压,及时报错)
func (incr *TredisRocksDBIncrBack) GetBackupFileExt(
	item *TredisRocksDBIncrBackItem) (bkFileExt string) {
	bkFileExt = filepath.Ext(item.BackupFile)

	okExt := map[string]bool{
		".tar": true,
		".tgz": true,
		".gz":  true,
		".zip": true,
		".lzo": true,
		".zst": true,
	}

	if strings.HasSuffix(item.BackupFile, ".tar.gz") {
		bkFileExt = ".tar.gz"
		return
	} else if _, ok := okExt[bkFileExt]; ok == true {
		return bkFileExt
	} else {
		incr.Err = fmt.Errorf("无法解压的binlog文件:%s", item.BackupFile)
		mylog.Logger.Error(incr.Err.Error())
		return
	}
}

// getDecompressedFile 获取解压文件,已经解压文件完整路径
func (incr *TredisRocksDBIncrBack) getDecompressedFile(
	item *TredisRocksDBIncrBackItem) (decpFile, decpFileFullPath string) {
	var bkFileExt string = incr.GetBackupFileExt(item)
	if incr.Err != nil {
		return
	}
	item.DecompressedFile = strings.TrimSuffix(item.BackupFile, bkFileExt)
	decpFile = item.DecompressedFile
	decpFileFullPath = filepath.Join(incr.SaveMyDir, decpFile)
	return
}

// CheckLocalDecompressedFilesIsOk 检查本地 增备解压文件 是否ok
// 返回值:
// totalCnt: 全部增备(解压)文件个数
// existsCnt: 本地存在的增备(解压)文件个数, existsList: 本地存在的增备(解压)文件详情
func (incr *TredisRocksDBIncrBack) CheckLocalDecompressedFilesIsOk() (
	totalCnt, existsCnt int, existsList []*TredisRocksDBIncrBackItem,
) {
	mylog.Logger.Info("CheckLocalDecompressedFilesIsOk start ...")
	totalCnt = 0
	existsCnt = 0
	for _, bk01 := range incr.ResultSortBinlog {
		bkItem := bk01
		totalCnt++
		_, decpFileFullPath := incr.getDecompressedFile(bkItem)
		if incr.Err != nil {
			return
		}
		_, err := os.Stat(decpFileFullPath)
		if os.IsNotExist(err) == true {
			continue
		}
		existsCnt++
		existsList = append(existsList, bkItem)
	}
	return
}

// rmLocalDecompressedFiles 删除一些本地 增备(已解压)文件
func (incr *TredisRocksDBIncrBack) rmLocalDecompressedFiles(bkList []*TredisRocksDBIncrBackItem) {
	mylog.Logger.Info("rmLocalDecompressedFiles start ... ")
	rmCnt := 0
	for _, bk01 := range bkList {
		bkItem := bk01
		if bkItem.DecompressedFile == "" {
			continue
		}
		decpFileFullPath := filepath.Join(incr.SaveMyDir, bkItem.DecompressedFile)
		if _, err := os.Stat(decpFileFullPath); os.IsNotExist(err) {
			continue
		}
		rmCmd := fmt.Sprintf("cd %s && rm -f %s 2>/dev/null", incr.SaveMyDir, bkItem.DecompressedFile)
		_, incr.Err = util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 30*time.Minute)
		if incr.Err != nil {
			return
		}
		rmCnt++
	}
	msg := fmt.Sprintf("共删除%d个本地binlog(已解压)文件", rmCnt)
	mylog.Logger.Info(msg)
	return
}

// CheckLocalBackupfilesIsOk 检查本地增备文件是否全部ok
// 返回值:
// totalCnt: 所需的全部增备文件个数
// existsCnt: 本地存在的增备文件个数, existsList: 本地存在的增备文件详情
// sizeOKCnt: 本地存在的增备文件 大小ok 的个数
func (incr *TredisRocksDBIncrBack) CheckLocalBackupfilesIsOk() (
	totalCnt, existsCnt, sizeOKCnt int, existsList []*TredisRocksDBIncrBackItem,
) {
	totalCnt = 0
	existsCnt = 0
	for _, bk01 := range incr.ResultSortBinlog {
		bkItem := bk01
		totalCnt++
		incrBkFile := filepath.Join(incr.SaveMyDir, bkItem.BackupFile)
		incrBkInfo, err := os.Stat(incrBkFile)
		if os.IsNotExist(err) == true {
			continue
		}
		existsCnt++
		existsList = append(existsList, bkItem)
		if incrBkInfo.Size() == bkItem.BackupSize {
			sizeOKCnt++
		}
	}
	return
}

// rmLocalBackupFiles 删除一些本地 增备文件
func (incr *TredisRocksDBIncrBack) rmLocalBackupFiles(bkList []*TredisRocksDBIncrBackItem) {
	rmCnt := 0
	for _, bk01 := range bkList {
		bkItem := bk01
		bkFileFullPath := filepath.Join(incr.SaveMyDir, bkItem.BackupFile)
		if _, err := os.Stat(bkFileFullPath); os.IsNotExist(err) {
			continue
		}
		rmCmd := fmt.Sprintf("cd %s && rm -f %s 2>/dev/null", incr.SaveMyDir, bkItem.BackupFile)
		_, incr.Err = util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 30*time.Minute)
		if incr.Err != nil {
			return
		}
		rmCnt++
	}
	msg := fmt.Sprintf("共删除%d个本地binlog(未解压)文件", rmCnt)
	mylog.Logger.Info(msg)
	return
}

// checkPulledFileOK 检查文件下载是否成功
func (incr *TredisRocksDBIncrBack) checkPulledFileOK(item *TredisRocksDBIncrBackItem) (err error) {

	if incr.SaveMyDir != "" {
		incrBkFile := filepath.Join(incr.SaveMyDir, item.BackupFile)
		bkFileInfo, err := os.Stat(incrBkFile)
		if err != nil {
			err = fmt.Errorf("pod:%s 本地binlog文件:%s 信息获取失败,err:%v",
				incr.FileName, incrBkFile, err)
			mylog.Logger.Error(err.Error())
			return err
		}
		bkFileSize := bkFileInfo.Size()
		if item.BackupSize != bkFileSize {
			err = fmt.Errorf("本地binlog文件:%s 大小(%d) 不等于 redis备份记录大小:%d",
				incrBkFile, bkFileSize, item.BackupSize)
			mylog.Logger.Error(err.Error())
			return err
		}
		msg := fmt.Sprintf(" 本地binlog文件:%s 确认ok", incrBkFile)
		mylog.Logger.Info(msg)
	}
	return nil
}

// CheckAllPulledFilesOK 是否所有本地binlog都拉取ok
func (incr *TredisRocksDBIncrBack) CheckAllPulledFilesOK() {
	mylog.Logger.Info("CheckAllPulledFilesOK start ... ")
	errList := []string{}
	successCnt := 0
	failCnt := 0
	totalCnt := 0
	for _, bk01 := range incr.ResultSortBinlog {
		bkItem := bk01
		totalCnt++
		err := incr.checkPulledFileOK(bkItem)
		if err != nil {
			errList = append(errList, err.Error())
		} else {
			successCnt++
		}
	}
	failCnt = len(errList)
	if failCnt > 0 {
		list01 := []string{}
		//只打印前5条信息
		if failCnt > 5 {
			list01 = errList[:5]
		} else {
			list01 = errList
		}
		incr.Err = fmt.Errorf(
			" 检查本地binlog文件失败,成功%d个,失败%d个,共%d个,失败示例:%s",
			successCnt, failCnt, totalCnt, strings.Join(list01, "\n"),
		)
		mylog.Logger.Error(incr.Err.Error())
		return
	}
	msg := fmt.Sprintf(
		" 检查本地binlog文件全部成功,成功%d个,失败%d个,共%d个",
		successCnt, failCnt, totalCnt)
	mylog.Logger.Info(msg)

	return
}

// CheckAllBinlogFiles ..
// - 如果所有 增备(已解压)文件 全部存在,则直接return;
// - 如果所有 增备(未解压)文件 全部存在,且大小校验ok,则直接 return;
// - 否则删除 本地存在的增备(已解压)文件、增备(未解压)文件;
// - 继续拉取文件;
func (incr *TredisRocksDBIncrBack) CheckAllBinlogFiles() {
	mylog.Logger.Info("CheckAllBinlogFiles start ... ")
	// //检查拉取的文件是否ok,下面逻辑有检查，这部分是不是放在最开始，
	// 但是这里只是检查未解压的，对于解压的还是得这个函数检查更全面，所以还需要这个函数功能嘛？
	// incr.CheckAllPulledFilesOK()
	var msg string
	decpTotalCnt, decpExistsCnt, decpExistsList := incr.CheckLocalDecompressedFilesIsOk()
	if incr.Err != nil {
		return
	}
	if decpTotalCnt == decpExistsCnt {
		msg = fmt.Sprintf("rollbackPod:%s  本地已存在%d个 增备(已解压文件),无需重新拉取增备文件...",
			incr.FileName, decpTotalCnt)
		mylog.Logger.Info(msg)
		return
	}
	incr.rmLocalDecompressedFiles(decpExistsList)
	if incr.Err != nil {
		return
	}

	localTotalCnt, localExistsCnt, sizeOkCnt, localExistsList := incr.CheckLocalBackupfilesIsOk()
	if incr.Err != nil {
		return
	}
	if localTotalCnt == localExistsCnt && localTotalCnt == sizeOkCnt {
		msg = fmt.Sprintf("rollbackPod:%s  本地已存在%d个 增备(未解压文件),无需重新拉取增备文件...",
			incr.FileName, localTotalCnt)
		mylog.Logger.Info(msg)
		return
	}
	mylog.Logger.Info("localExistsList:%v", localExistsList)
	// 文件大小不一样，这里先注释
	// incr.rmLocalBackupFiles(localExistsList)
	if incr.Err != nil {
		return
	}
}

// DecompressedOne 解压一个binlog文件
func (incr *TredisRocksDBIncrBack) DecompressedOne(item *TredisRocksDBIncrBackItem) {
	var cmd string
	var bkFileExt string = incr.GetBackupFileExt(item)
	if incr.Err != nil {
		return
	}
	if bkFileExt == ".tar" {
		cmd = fmt.Sprintf("cd %s && tar -xf %s",
			incr.SaveMyDir, item.BackupFile)
	} else if bkFileExt == ".tar.gz" {
		cmd = fmt.Sprintf("cd %s && tar -zxf %s",
			incr.SaveMyDir, item.BackupFile)
	} else if bkFileExt == ".tgz" {
		cmd = fmt.Sprintf("cd %s && tar -zxf %s",
			incr.SaveMyDir, item.BackupFile)
	} else if bkFileExt == ".gz" {
		cmd = fmt.Sprintf("cd %s && gunzip %s",
			incr.SaveMyDir, item.BackupFile)
	} else if bkFileExt == ".zip" {
		cmd = fmt.Sprintf("cd %s && unzip %s",
			incr.SaveMyDir, item.BackupFile)
	} else if bkFileExt == ".lzo" {
		cmd = fmt.Sprintf("cd %s && lzop -d %s",
			incr.SaveMyDir, item.BackupFile)
	} else if bkFileExt == ".zst" {
		cmd = fmt.Sprintf("cd %s && %s -d %s",
			incr.SaveMyDir, consts.ZstdBin, item.BackupFile)
	}
	if cmd != "" {
		var decpFileFullPath string
		item.DecompressedFile, decpFileFullPath = incr.getDecompressedFile(item)
		msg := fmt.Sprintf("binlog解压命令:%s", cmd)
		mylog.Logger.Info(msg)

		_, incr.Err = util.RunLocalCmd("bash", []string{"-c", cmd}, "", nil, 600*time.Second)
		if incr.Err != nil {
			return
		}
		_, err := os.Stat(decpFileFullPath)
		if err != nil {
			incr.Err = fmt.Errorf("解压binlog:%s => %s 失败,err:%v",
				item.BackupFile, decpFileFullPath, err)
			mylog.Logger.Error(incr.Err.Error())

			return
		}
		msg = fmt.Sprintf("解压binlog:%s成功", item.BackupFile)
		mylog.Logger.Info(msg)

		//rm 源文件
		rmCmd := fmt.Sprintf("cd %s && rm -f %s 2>/dev/null", incr.SaveMyDir, item.BackupFile)
		_, incr.Err = util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 30*time.Minute)
		if incr.Err != nil {
			return
		}
		msg = fmt.Sprintf("删除binlog源文件:%s完成", item.BackupFile)
		mylog.Logger.Info(msg)
	}
}

// DecompressedAll 解压全部binlog文件
func (incr *TredisRocksDBIncrBack) DecompressedAll() {
	mylog.Logger.Info("DecompressedAll start ...")
	if len(incr.ResultSortBinlog) == 0 {
		incr.Err = fmt.Errorf(
			"filename:%s  binlog信息为空(len:%d),无法解压,请先获取binlog信息",
			incr.FileName, len(incr.ResultSortBinlog))
		mylog.Logger.Error(incr.Err.Error())
		return
	}
	errList := []string{}
	successCnt := 0
	failCnt := 0
	totalCnt := 0
	for _, bk01 := range incr.ResultSortBinlog {
		bkItem := bk01
		totalCnt++
		incr.DecompressedOne(bkItem)
		if incr.Err != nil {
			errList = append(errList, incr.Err.Error())
		} else {
			successCnt++
		}
	}
	failCnt = len(errList)
	if failCnt > 0 {
		list01 := []string{}
		//只打印前5条信息
		if failCnt > 5 {
			list01 = errList[:5]
		} else {
			list01 = errList
		}
		incr.Err = fmt.Errorf(
			"解压pod:%s  binlog文件失败,成功%d个,失败%d个,共%d个,失败示例:%s",
			incr.FileName, successCnt, failCnt, totalCnt, strings.Join(list01, "\n"),
		)
		mylog.Logger.Error(incr.Err.Error())
		return
	}
	msg := fmt.Sprintf("解压pod:%s  binlog文件全部成功,成功%d个,失败%d个,共%d个",
		incr.FileName, successCnt, failCnt, totalCnt)
	mylog.Logger.Info(msg)
	return
}

// Decompressed ..
// 如果所有 增备(已解压)文件 全部存在,则直接return;
// 否则删除 本地存在的增备(已解压)文件;
// 继续执行解压;
func (incr *TredisRocksDBIncrBack) Decompressed() {
	mylog.Logger.Info("DecompressedAllIfNotExists start .. ")
	var msg string
	decpTotalCnt, decpExistsCnt, decpExistsList := incr.CheckLocalDecompressedFilesIsOk()
	if incr.Err != nil {
		return
	}
	if decpTotalCnt == decpExistsCnt {
		msg = fmt.Sprintf("rollbackPod:%s 本地已存在%d个 增备(已解压文件),无需执行解压...",
			incr.FileName, decpTotalCnt)
		mylog.Logger.Info(msg)
		return
	}
	incr.rmLocalDecompressedFiles(decpExistsList)
	if incr.Err != nil {
		return
	}
	incr.DecompressedAll()
}

// getNewResultSortBinlog 导入全部binlog
func (incr *TredisRocksDBIncrBack) getNewResultSortBinlog() {
	mylog.Logger.Info("getNewResultSortBinlog start ...")
	var first_incr *TredisRocksDBIncrBackItem
	if len(incr.ResultSortBinlog) == 0 || len(incr.ResultSortBinlog) == 1 {
		return
	} else if len(incr.ResultSortBinlog) > 1 {
		for _, bk01 := range incr.ResultSortBinlog {
			bkItem := bk01
			incrBackFile := filepath.Join(incr.SaveMyDir, bkItem.DecompressedFile)
			// # binlog 的start_seq 小于全备份的seq 并且 binlog的end_seq 大于全备份seq ：这样就找到了所有需要加载的binlog
			// if ( $incr_list[$i]->{start_seq} <= $full_seq and $incr_list[$i]->{end_seq} >= $full_seq )
			// 查询下载的范围更大些 ，再通过bingseq 来决定加载的文件 ？(new_incr_list) 这里获取这个值，必须文件已经下载了才能获取得到
			seq := incr.getSeqFromFile(incrBackFile)
			if seq <= 0 {
				err := fmt.Errorf("获取到的seq%d<=0,不符合预期", seq)
				mylog.Logger.Error(err.Error())

			}
			mylog.Logger.Info("getNewResultSortBinlog filename:%s seq:%d", incrBackFile, seq)
			bkItem.BinlogStartPos = seq

		}
		// 遍历ResultSortBinlog ，对end_seq赋值,前面已经校验过文件index的连续性和对此排序（GetTredisIncrbacksSpecRocks 函数里）
		for i := 0; i < len(incr.ResultSortBinlog)-1; i++ {
			incr.ResultSortBinlog[i].BinlogEndPos = incr.ResultSortBinlog[i+1].BinlogStartPos
			// binlog 的start_seq 小于全备份的seq 并且 binlog的end_seq 大于全备份seq ：这样就找到了第一个binlog文件
			// NOCC:tosa/linelength(设计如此)
			if incr.ResultSortBinlog[i].BinlogStartPos <= incr.FullStartPos && incr.ResultSortBinlog[i].BinlogEndPos >= incr.FullStartPos {
				first_incr = incr.ResultSortBinlog[i]
			}

		}
		var newResultSortBinlog []*TredisRocksDBIncrBackItem
		// binlog 的start_seq 小于全备份的seq 并且 binlog的end_seq 大于全备份seq -》 第一个binlog文件
		if first_incr != nil {
			for i := 0; i < len(incr.ResultSortBinlog); i++ {
				//找到第一个文件后面的所有文件
				if incr.ResultSortBinlog[i].BinlogStartPos >= first_incr.BinlogStartPos {
					newResultSortBinlog = append(newResultSortBinlog, incr.ResultSortBinlog[i])
				}
			}
		}
		// 找到最后需要加载的所有binlog文件
		incr.ResultSortBinlog = newResultSortBinlog

	}

}

// ImportAllBinlogToTredis 导入全部binlog
func (incr *TredisRocksDBIncrBack) ImportAllBinlogToTredis(tplusIP string, tplusPort int, tplusPasswd string) {
	mylog.Logger.Info("ImportAllBinlogToTredis start ...")
	// 获取需要加载的binlog文件,之前的ResultSortBinlog是范围更大点的
	incr.getNewResultSortBinlog()
	for _, bk01 := range incr.ResultSortBinlog {
		bkItem := bk01
		incr.ImportOneBinlogToTredis(tplusIP, tplusPort, tplusPasswd, bkItem)
		if incr.Err != nil {
			return
		}
	}
	msg := fmt.Sprintf("filename:%s  共成功导入%d个binlog",
		incr.FileName, len(incr.ResultSortBinlog))
	mylog.Logger.Info(msg)
	return
}

// ImportOneBinlogToTredis 导入一个binlog文件到tredis中
// NOCC:golint/fnsize(设计如此)
func (incr *TredisRocksDBIncrBack) ImportOneBinlogToTredis(tplusIP string, tplusPort int,
	tplusPasswd string, bkItem *TredisRocksDBIncrBackItem) {
	mylog.Logger.Info("ImportOneBinlogToTredis start ... ")
	DepsDir := "/usr/local/redis/bin/deps"
	if _, err := os.Stat(DepsDir); os.IsNotExist(err) {
		err = fmt.Errorf("目录不存在,请检查:%s", DepsDir)
		mylog.Logger.Error(err.Error())
		incr.Err = err
		return
	}

	incrBackFile := filepath.Join(incr.SaveMyDir, bkItem.DecompressedFile)
	incrBackFilePath := strings.TrimSuffix(incrBackFile, filepath.Ext(incrBackFile))

	cmdfile := fmt.Sprintf("%s.cmd", incrBackFile)
	outfile := fmt.Sprintf("%s.out", incrBackFile)
	// incr.RecoveryTimePoint := "2022-01-01 00:00:00" // 待转换的字符串时间
	layout := "2006-01-02 15:04:05" // 字符串时间格式
	t, err := time.Parse(layout, incr.RecoveryTimePoint)
	if err != nil {
		err = fmt.Errorf("%s:时间转换失败,请检查:%v", incr.RecoveryTimePoint, err)
		mylog.Logger.Error(err.Error())
		return
	}
	endtime := t.Unix() * 1000 // 转换为 Unix 时间戳，*1000 转为毫秒

	restoreCmd := fmt.Sprintf(`
	export LD_PRELOAD=%s/libjemalloc.so
	export LD_LIBRARY_PATH=LD_LIBRARY_PATH:%s
	%s --start-position=%d --end-datetime=%d  %s >/%s
	`, DepsDir, DepsDir, consts.TredisBinlogBin, incr.FullStartPos, endtime, incrBackFile, cmdfile)

	mylog.Logger.Info("解析binlog,命令:%v", restoreCmd)
	ret01, err := util.RunLocalCmd("bash", []string{"-c", restoreCmd}, "", nil, 1*time.Hour)
	if err != nil {
		mylog.Logger.Error(fmt.Sprintf("解析binlog失败,详情:%v", err))
		incr.Err = err
		return
	}
	ret01 = strings.TrimSpace(ret01)
	if strings.Contains(ret01, "ERR:") == true {
		mylog.Logger.Error(fmt.Sprintf("解析binlog失败,cmd:%s,err:%s", restoreCmd, ret01))
		incr.Err = fmt.Errorf("解析binlog失败")
		return
	}
	//You can force human readable output when writing to a file or in pipe to other commands by using --no-raw.
	// NOCC:tosa/linelength(设计如此)
	importCmd := fmt.Sprintf("%s --no-raw --no-auth-warning -h %s -p %d -a %s < %s > %s", consts.RedisCliBin, tplusIP, tplusPort,
		tplusPasswd, cmdfile, outfile)
	mylog.Logger.Info("binlog 写入命令:%v", importCmd)
	_, err = util.RunLocalCmd("bash", []string{"-c", importCmd}, "", nil, 1*time.Hour)
	if err != nil {
		mylog.Logger.Error(fmt.Sprintf("导入binlog 命令失败,详情:%v", err))
		incr.Err = err
		return
	}
	ok_ret, err_ret, all_ret := 0, 0, 0
	ret := make(map[string]int)

	outF, _ := os.Open(filepath.Join(incrBackFilePath, outfile))
	scanner := bufio.NewScanner(outF)
	for scanner.Scan() {
		line := scanner.Text()
		fields := strings.Split(line, " ")
		f1 := fields[0]

		all_ret++

		var reply_type string
		first_char := string(f1[0])

		if f1 == "OK" {
			ok_ret++
		} else if f1 == "(error)" {
			err_ret++
		} else if first_char == "\"" {
			reply_type = "(string)"
			ok_ret++
		} else if first_char == "(" {
			reply_type = f1
			ok_ret++
		} else {
			reply_type = "unknown"
			err_ret++
		}

		ret[reply_type]++
	}
	outF.Close()

	msg := ""
	for k, v := range ret {
		msg += fmt.Sprintf("'%s':%d,", k, v)
	}
	msg = strings.TrimSuffix(msg, ",")

	msg = (fmt.Sprintf("LOAD BINLOG %s, binlog count: %d, succ: %d, err: %d. detail: %s\n",
		incrBackFilePath, all_ret, ok_ret, err_ret, msg))
	mylog.Logger.Info(msg)
	if err_ret == 0 && all_ret > 0 {
		mylog.Logger.Info("err_ret == 0 && all_ret > 0")
		// 先注释测试，后续这些中间文件需要删除
		os.Remove(filepath.Join(incrBackFilePath, cmdfile))
		os.Remove(filepath.Join(incrBackFilePath, outfile))
	}

	mylog.Logger.Info("binlog:%s 导入 %s:%d成功", bkItem.BackupFile, tplusIP, tplusPort)
	return
}
