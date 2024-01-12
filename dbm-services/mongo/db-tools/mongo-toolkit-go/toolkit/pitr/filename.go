package pitr

import (
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	//	log "github.com/sirupsen/logrus"
	"fmt"
	"path"
	"strconv"
	"strings"
	"time"
)

const BackupFileVersionV0 = "v0"
const BackupFileVersionV1 = "v1"

// BackupFileName $output_dir = "mongodump-$name-INCR-$nodeip-$port-$ymdh-$suffix";
type BackupFileName struct {
	Version   string //V0 V1
	Dir       string
	Suffix    string
	FileName  string
	FileSize  int64
	Type      string
	Host      string
	Port      string
	Name      string
	StartTime time.Time
	EndTime   time.Time
	FirstTs   TS
	LastTs    TS
	V0FullStr string
	V0IncrSeq uint32
}

// SetSuffix .tar .tar.gz ...
func (f *BackupFileName) SetSuffix(s string) {
	f.Suffix = s
}

// GetV0FullStr Return V0FullStr
func (f *BackupFileName) GetV0FullStr() (string, error) {
	if f.V0FullStr != "" {
		return f.V0FullStr, nil
	}
	f.V0FullStr = f.StartTime.Format("2006010215")
	return f.V0FullStr, nil
}

// GetFullPath Return FullPath
func (f *BackupFileName) GetFullPath() string {
	return path.Join(f.Dir, f.FileName)
}

// GetFileName Return FileName
func (f *BackupFileName) GetFileName() (string, error) {
	uid, err := f.GetFileUniqName()
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%s%s", uid, f.Suffix), nil
}

// GetFileUniqName Return FileUniqName
func (f *BackupFileName) GetFileUniqName() (string, error) {
	switch f.Version {
	case BackupFileVersionV0:
		if f.Type == BackupTypeFull {
			hourStr := f.StartTime.Format("2006010215")
			lastSecStr := time.Unix(int64(f.LastTs.Sec), 0).Format("20060102150405")
			return fmt.Sprintf("mongodump-%s-%s-%s-%s-%s-%s", f.Name, f.Type, f.Host, f.Port, hourStr, lastSecStr), nil
		} else if f.Type == BackupTypeIncr {
			if f.V0IncrSeq <= 0 {
				return "", fmt.Errorf("incr seq error")
			}
			if f.V0FullStr == "" {
				return "", fmt.Errorf("full str error")
			}
			lastTimeStr := time.Unix(int64(f.LastTs.Sec), 0).Format("20060102150405")
			return fmt.Sprintf("mongodump-%s-%s-%s-%s-%s-%d-%s", f.Name, f.Type, f.Host,
				f.Port, f.V0FullStr, f.V0IncrSeq, lastTimeStr), nil
		}
	case BackupFileVersionV1:
		if f.Type == BackupTypeFull {
			lastTs := f.LastTs
			if lastTs.Sec == 0 {
				lastTs.Sec = uint32(f.EndTime.Unix())
			}
			TimeStr := time.Unix(int64(lastTs.Sec), 0).Format("20060102150405")
			return fmt.Sprintf("mongodump-v1-%s-%s-%s-%s-%s-%d", f.Name, f.Type, f.Host, f.Port, TimeStr, lastTs.I), nil
		} else if f.Type == BackupTypeIncr {
			firstTs := f.FirstTs
			lastTs := f.LastTs
			// INCR 备份时，会插入产生一条oplog，所以firstTimeStr 和 lastTimeStr 都不会为0
			firstTimeStr := time.Unix(int64(firstTs.Sec), 0).Format("20060102150405")
			lastTimeStr := time.Unix(int64(lastTs.Sec), 0).Format("20060102150405")
			return fmt.Sprintf("mongodump-v1-%s-%s-%s-%s-%s-%d-%s-%d",
				f.Name, f.Type, f.Host, f.Port, firstTimeStr, firstTs.I, lastTimeStr, lastTs.I), nil
		}

	}
	return "", fmt.Errorf("bad backupType,version: (%s,%s) ", f.Type, f.Version)
}

// MakeFileName 生成文件对象
func MakeFileName(version string, connInfo *mymongo.MongoHost, backupType string, startTime, endTime time.Time,
	firstTs, lastTs *TS, fullStr string, incrSeq uint32) (*BackupFileName, error) {
	if firstTs == nil || lastTs == nil || firstTs.Sec == 0 || lastTs.Sec == 0 {
		return nil, fmt.Errorf("bad ts info")
	}
	backupFile := new(BackupFileName)
	backupFile.Version = version
	backupFile.Type = backupType
	backupFile.Host = connInfo.Host
	backupFile.Port = connInfo.Port
	backupFile.Name = connInfo.Name
	backupFile.StartTime = startTime
	backupFile.EndTime = endTime
	backupFile.FirstTs = *firstTs
	backupFile.LastTs = *lastTs
	backupFile.V0FullStr = fullStr
	backupFile.V0IncrSeq = incrSeq
	return backupFile, nil
}

// MakeFileNameV1 Deprecated
func MakeFileNameV1(connInfo *mymongo.MongoHost, backupType string, startTime, endTime time.Time, firstTs, lastTs *TS) (string, error) {
	if firstTs == nil || lastTs == nil || firstTs.Sec == 0 || lastTs.Sec == 0 {
		return "", fmt.Errorf("bad ts info")
	}
	// firstTs lastTs 最初由parseTs产生，不会为nil
	if backupType == BackupTypeFull {
		// 一致性时间点为 备份结束时间
		if lastTs.Sec == 0 {
			lastTs.Sec = uint32(endTime.Unix())
		}
		TimeStr := time.Unix(int64(lastTs.Sec), 0).Format("20060102150405")
		return fmt.Sprintf("mongodump-v1-%s-%s-%s-%s-%s-%d",
			connInfo.Name, backupType, connInfo.NodeIp, connInfo.Port, TimeStr, lastTs.I), nil
	} else if backupType == BackupTypeIncr {
		// INCR 备份时，会插入产生一条oplog，所以firstTimeStr 和 lastTimeStr 都不会为0
		firstTimeStr := time.Unix(int64(firstTs.Sec), 0).Format("20060102150405")
		lastTimeStr := time.Unix(int64(lastTs.Sec), 0).Format("20060102150405")
		return fmt.Sprintf("mongodump-v1-%s-%s-%s-%s-%s-%d-%s-%d",
			connInfo.Name, backupType, connInfo.NodeIp, connInfo.Port, firstTimeStr,
			firstTs.I, lastTimeStr, lastTs.I), nil
	} else {
		return "", fmt.Errorf("bad backupType %s", backupType)
	}
}

// DecodeFileV0FULL Parse FileName : mongodump-app-set-name-FULL-1.1.1.1-11111-2018031304-20180313041134.tar.gz
func DecodeFileV0FULL(filename string) (*BackupFileName, error) {
	bfn := new(BackupFileName)
	bfn.Type = BackupTypeFull
	bfn.Version = BackupFileVersionV0
	bfn.FileName = filename

	filename = strings.TrimPrefix(filename, "mongodump-")
	filename = strings.TrimSuffix(filename, ".gz")
	filename = strings.TrimSuffix(filename, ".tar")

	fields := strings.Split(filename, "-")
	fn := len(fields)

	if fn <= 7 {
		return nil, fmt.Errorf("bad format")
	}

	if vv, err := ConvertFileNameTimeStringToTs(fields[fn-1], "0"); err == nil {
		bfn.LastTs.Sec = vv.Sec
		bfn.LastTs.I = vv.I
	} else {
		return nil, fmt.Errorf("bad format: LastTs (%s %s)err:%v", fields[fn-1], "0", err)
	}

	bfn.V0FullStr = fields[fn-2]
	bfn.Port = fields[fn-3]
	bfn.Host = fields[fn-4]

	if fields[fn-5] != BackupTypeFull {
		return nil, fmt.Errorf("bad format:Type")
	}

	bfn.Name = strings.Join(fields[:fn-5], "-")
	return bfn, nil
}

// DecodeFileV0INCR Parse FileName
func DecodeFileV0INCR(filename string) (*BackupFileName, error) {
	bfn := new(BackupFileName)
	bfn.Type = BackupTypeIncr
	bfn.Version = BackupFileVersionV0
	bfn.FileName = filename

	filename = strings.TrimPrefix(filename, "mongodump-")
	filename = strings.TrimSuffix(filename, ".gz")
	filename = strings.TrimSuffix(filename, ".oplog.rs.bson")
	filename = strings.TrimSuffix(filename, "-oplog.rs.bson")
	fields := strings.Split(filename, "-")
	fn := len(fields)

	if fn < 9 {
		return nil, fmt.Errorf("bad format: len %d", fn)
	}

	if vv, err := ConvertFileNameTimeStringToTs(fields[fn-1], "0"); err == nil {
		bfn.LastTs.Sec = vv.Sec
		bfn.LastTs.I = vv.I
	} else {
		// 	err = fmt.Errorf("bad format: LastTs (%s %s) err:%v full:%+v len:%d", fields[fn-1], "0", err, fields, len(fields))
		return nil, fmt.Errorf("bad format: LastTs (%s %s)err:%v", fields[fn-1], "0", err)
	}

	if vv, err := strconv.ParseUint(fields[fn-2], 10, 64); err != nil {
		return nil, fmt.Errorf("bad format: V0IncrSeq:%v", err)
	} else {
		bfn.V0IncrSeq = uint32(vv)
	}

	bfn.V0FullStr = fields[fn-3]
	bfn.Port = fields[fn-4]
	bfn.Host = fields[fn-5]

	if fields[fn-6] != BackupTypeIncr {
		return nil, fmt.Errorf("bad format: Type")
	}

	bfn.Name = strings.Join(fields[:fn-6], "-")
	return bfn, nil
}

// DecodeFileV1FULL Parse FileName
func DecodeFileV1FULL(filename string) (*BackupFileName, error) {
	bfn := new(BackupFileName)
	bfn.Type = BackupTypeFull
	bfn.Version = BackupFileVersionV1
	bfn.FileName = filename

	filename = strings.TrimPrefix(filename, "mongodump-v1-")
	filename = strings.TrimSuffix(filename, ".gz")
	filename = strings.TrimSuffix(filename, ".tar")

	fields := strings.Split(filename, "-")
	fn := len(fields)

	if fn <= 7 {
		return nil, fmt.Errorf("bad format: field len < 7 ")
	}

	if vv, err := ConvertFileNameTimeStringToTs(fields[fn-2], fields[fn-1]); err == nil {
		bfn.LastTs.Sec = vv.Sec
		bfn.LastTs.I = vv.I
	} else {
		return nil, fmt.Errorf("bad format: LastTs (%s %s)err:%v", fields[fn-2], fields[fn-1], err)
	}

	bfn.Port = fields[fn-3]
	bfn.Host = fields[fn-4]

	if fields[fn-5] != BackupTypeFull {
		return nil, fmt.Errorf("bad format:Type")
	}

	bfn.Name = strings.Join(fields[:fn-5], "-")
	return bfn, nil
}

// DecodeFileV1INCR Parse FileName
func DecodeFileV1INCR(filename string) (*BackupFileName, error) {
	bfn := new(BackupFileName)
	bfn.Type = BackupTypeIncr
	bfn.Version = BackupFileVersionV1
	bfn.FileName = filename

	filename = strings.TrimPrefix(filename, "mongodump-v1-")
	filename = strings.TrimSuffix(filename, ".gz")
	filename = strings.TrimSuffix(filename, ".oplog.rs.bson")
	filename = strings.TrimSuffix(filename, "-oplog.rs.bson") //

	fields := strings.Split(filename, "-")
	fn := len(fields)

	if fn <= 9 {
		return nil, fmt.Errorf("bad format: field len < 9 ")
	}

	if vv, err := ConvertFileNameTimeStringToTs(fields[fn-2], fields[fn-1]); err == nil {
		bfn.LastTs.Sec = vv.Sec
		bfn.LastTs.I = vv.I
	} else {
		return nil, fmt.Errorf("bad format: LastTs (%s %s)err:%v", fields[fn-2], fields[fn-1], err)
	}

	if vv, err := ConvertFileNameTimeStringToTs(fields[fn-4], fields[fn-3]); err == nil {
		bfn.FirstTs.Sec = vv.Sec
		bfn.FirstTs.I = vv.I
	} else {
		return nil, fmt.Errorf("bad format: FirstTs:%v", err)
	}

	bfn.Port = fields[fn-5]
	bfn.Host = fields[fn-6]

	if fields[fn-7] != BackupTypeIncr {
		return nil, fmt.Errorf("bad format:Type")
	}

	bfn.Name = strings.Join(fields[:fn-7], "-")
	return bfn, nil
}

//根据备份文件名，返回这个文件名的如下信息
// Host Port
// 类型
// 全备    - 一致性时间
// 增量备份 - 开始时间和结束时间

// DecodeFilename Parse FileName
func DecodeFilename(filename string) (*BackupFileName, error) {
	if strings.HasPrefix(filename, "mongodump-v1") {
		if strings.HasSuffix(filename, "oplog.rs.bson.gz") || strings.HasSuffix(filename, "oplog.rs.bson") {
			return DecodeFileV1INCR(filename)
		} else if strings.HasSuffix(filename, ".tar") || strings.HasSuffix(filename, ".tar.gz") {
			return DecodeFileV1FULL(filename)
		}
		return nil, fmt.Errorf("bad format: Suffix")
	} else if strings.HasPrefix(filename, "mongodump-") {
		if strings.HasSuffix(filename, "oplog.rs.bson.gz") || strings.HasSuffix(filename, "oplog.rs.bson") {
			return DecodeFileV0INCR(filename)
		} else if strings.HasSuffix(filename, ".tar") || strings.HasSuffix(filename, ".tar.gz") {
			return DecodeFileV0FULL(filename)
		}
		return nil, fmt.Errorf("bad format: Suffix")
	}

	return nil, fmt.Errorf("bad format: Prefix")
}
