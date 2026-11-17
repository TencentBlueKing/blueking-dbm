package atomredis

import (
	"bufio"
	"bytes"
	"fmt"
	"hash/maphash"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

const (
	// keysDupCheckShardBytes 单个分片期望的原始数据大小,决定内存占用上限.
	// 分片内用 map[string]uint32 计数,实际内存约为分片原始大小的 2~3 倍
	keysDupCheckShardBytes int64 = 64 * 1024 * 1024
	// keysDupCheckMaxShards 最大分片数,避免同时打开过多文件句柄
	keysDupCheckMaxShards = 256
	// keysDupCheckShowCnt 日志中最多展示的重复key个数
	keysDupCheckShowCnt = 20
	// keysDupCheckReadBufSize 读缓冲大小
	keysDupCheckReadBufSize = 1024 * 1024
	// keysDupCheckWriteBufSize 单个分片写缓冲大小
	keysDupCheckWriteBufSize = 64 * 1024
)

// keysDupResult keys文件重复行检查结果
type keysDupResult struct {
	TotalLines uint64 // 总行数
	DupKeys    uint64 // 出现多次的不同行的个数
	DupLines   uint64 // 多余的行数(各重复行出现次数-1 之和)
	DupFile    string // 重复行输出文件,每行格式: <出现次数> <行内容>
	Examples   []string
}

// forEachLine 逐行读取文件,line 不含结尾换行符,fn 返回后 line 内容不再有效.
// 兼容超过缓冲大小的超长行
func forEachLine(path string, fn func(line []byte) error) error {
	f, err := os.Open(path)
	if err != nil {
		return fmt.Errorf("open %s fail,err:%v", path, err)
	}
	defer f.Close()

	reader := bufio.NewReaderSize(f, keysDupCheckReadBufSize)
	var long []byte
	for {
		seg, err := reader.ReadSlice('\n')
		if err == bufio.ErrBufferFull {
			long = append(long, seg...)
			continue
		}
		if len(long) > 0 {
			long = append(long, seg...)
			seg = long
		}
		if err != nil && err != io.EOF {
			return fmt.Errorf("read %s fail,err:%v", path, err)
		}
		if len(seg) > 0 {
			if cbErr := fn(bytes.TrimSuffix(seg, []byte{'\n'})); cbErr != nil {
				return cbErr
			}
		}
		long = long[:0]
		if err == io.EOF {
			return nil
		}
	}
}

// calcKeysDupShards 根据文件大小计算分片数
func calcKeysDupShards(fileSize, shardBytes int64, maxShards int) int {
	if shardBytes <= 0 {
		shardBytes = keysDupCheckShardBytes
	}
	if maxShards <= 0 {
		maxShards = keysDupCheckMaxShards
	}
	n := int((fileSize + shardBytes - 1) / shardBytes)
	if n < 1 {
		n = 1
	}
	if n > maxShards {
		n = maxShards
	}
	return n
}

// checkKeysFileDuplicates 检查 keysFile 是否存在重复行.
// 做法: 先按行内容的hash把文件拆成多个分片文件,相同的行必然落在同一分片;
// 然后逐个分片用 map 计数,内存占用只与单个分片大小有关,与文件总大小无关.
// workDir 用于存放临时分片文件(需要约等于 keysFile 大小的可用磁盘空间),函数返回前会清理.
// 若存在重复行,重复行(及出现次数)会写入 keysFile+".dup" 文件
func checkKeysFileDuplicates(keysFile, workDir string, shardBytes int64, maxShards int,
	logf func(format string, args ...interface{})) (ret keysDupResult, err error) {
	fileInfo, err := os.Stat(keysFile)
	if err != nil {
		return ret, fmt.Errorf("keys file:%s os.Stat fail,err:%v", keysFile, err)
	}
	ret.DupFile = keysFile + ".dup"
	_ = os.Remove(ret.DupFile)

	shardCnt := calcKeysDupShards(fileInfo.Size(), shardBytes, maxShards)
	logf("check duplicate lines,file:%s,size:%dMB,shards:%d", keysFile, fileInfo.Size()/1024/1024, shardCnt)

	shardFiles := []string{keysFile}
	if shardCnt > 1 {
		shardFiles, err = splitKeysFileByHash(keysFile, workDir, fileInfo.Size(), shardCnt, &ret)
		if err != nil {
			return ret, err
		}
		defer func() {
			for _, f := range shardFiles {
				_ = os.Remove(f)
			}
		}()
	} else if err = forEachLine(keysFile, func([]byte) error {
		ret.TotalLines++
		return nil
	}); err != nil {
		return ret, err
	}

	dupFileW, err := os.OpenFile(ret.DupFile, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
	if err != nil {
		return ret, fmt.Errorf("create dup file:%s fail,err:%v", ret.DupFile, err)
	}
	dupW := bufio.NewWriter(dupFileW)
	defer func() {
		if flushErr := dupW.Flush(); err == nil && flushErr != nil {
			err = fmt.Errorf("flush dup file:%s fail,err:%v", ret.DupFile, flushErr)
		}
		_ = dupFileW.Close()
		if ret.DupKeys == 0 {
			_ = os.Remove(ret.DupFile)
		}
	}()

	for _, shard := range shardFiles {
		counts := make(map[string]uint32)
		if err = forEachLine(shard, func(line []byte) error {
			if c, ok := counts[string(line)]; ok {
				counts[string(line)] = c + 1
			} else {
				counts[string(line)] = 1
			}
			return nil
		}); err != nil {
			return ret, err
		}
		// 同一分片内按内容排序输出,结果稳定
		dupKeys := make([]string, 0)
		for k, c := range counts {
			if c > 1 {
				dupKeys = append(dupKeys, k)
			}
		}
		sort.Strings(dupKeys)
		for _, k := range dupKeys {
			c := counts[k]
			ret.DupKeys++
			ret.DupLines += uint64(c - 1)
			if _, err = fmt.Fprintf(dupW, "%d %s\n", c, k); err != nil {
				return ret, fmt.Errorf("write dup file:%s fail,err:%v", ret.DupFile, err)
			}
			if len(ret.Examples) < keysDupCheckShowCnt {
				ret.Examples = append(ret.Examples, fmt.Sprintf("%s(x%d)", k, c))
			}
		}
	}
	return ret, nil
}

// splitKeysFileByHash 按行hash把 keysFile 拆分为 shardCnt 个分片文件,同时统计总行数
func splitKeysFileByHash(keysFile, workDir string, fileSize int64, shardCnt int, ret *keysDupResult) (
	shardFiles []string, err error) {
	// 分片文件总大小约等于原文件大小,先检查磁盘空间
	diskUsg, err := util.GetLocalDirDiskUsg(workDir)
	if err != nil {
		return nil, err
	}
	// 预留10%余量
	if diskUsg.AvailSize < uint64(fileSize)+uint64(fileSize)/10 {
		return nil, fmt.Errorf("disk space not enough to check duplicate lines,dir:%s,avail:%dMB,need:%dMB",
			workDir, diskUsg.AvailSize/1024/1024, (fileSize+fileSize/10)/1024/1024)
	}

	baseName := filepath.Base(keysFile)
	shardFiles = make([]string, 0, shardCnt)
	writers := make([]*bufio.Writer, 0, shardCnt)
	files := make([]*os.File, 0, shardCnt)
	cleanup := func() {
		for _, f := range files {
			_ = f.Close()
		}
	}
	defer func() {
		cleanup()
		if err != nil {
			for _, f := range shardFiles {
				_ = os.Remove(f)
			}
			shardFiles = nil
		}
	}()
	for i := 0; i < shardCnt; i++ {
		shardPath := filepath.Join(workDir, fmt.Sprintf("%s.dupcheck.shard%d.tmp", baseName, i))
		// 先登记路径,出错时也能清理
		shardFiles = append(shardFiles, shardPath)
		f, openErr := os.OpenFile(shardPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0600)
		if openErr != nil {
			return shardFiles, fmt.Errorf("create shard file:%s fail,err:%v", shardPath, openErr)
		}
		files = append(files, f)
		writers = append(writers, bufio.NewWriterSize(f, keysDupCheckWriteBufSize))
	}

	seed := maphash.MakeSeed()
	err = forEachLine(keysFile, func(line []byte) error {
		ret.TotalLines++
		w := writers[maphash.Bytes(seed, line)%uint64(shardCnt)]
		if _, wErr := w.Write(line); wErr != nil {
			return wErr
		}
		return w.WriteByte('\n')
	})
	if err != nil {
		return shardFiles, fmt.Errorf("split keys file:%s fail,err:%v", keysFile, err)
	}
	for i, w := range writers {
		if err = w.Flush(); err != nil {
			return shardFiles, fmt.Errorf("flush shard file:%s fail,err:%v", shardFiles[i], err)
		}
	}
	return shardFiles, nil
}

// checkKeysFileDuplicate 检查 keys 文件是否存在重复行,存在则输出重复行并置 task.Err
func (task *RedisInsDtsDataCheckAndRepairTask) checkKeysFileDuplicate() {
	keysFile := task.keyPatternTask.ResultFile
	if !util.FileExists(keysFile) {
		task.getLogger().Warn("keys file not exists,skip duplicate check,file:%s,addr:%s",
			keysFile, task.getSrcRedisAddr())
		return
	}
	ret, err := checkKeysFileDuplicates(keysFile, task.getSaveDir(), keysDupCheckShardBytes,
		keysDupCheckMaxShards, task.getLogger().Info)
	if err != nil {
		task.Err = fmt.Errorf("check keys file duplicate fail,err:%v,file:%s,addr:%s",
			err, keysFile, task.getSrcRedisAddr())
		task.getLogger().Error("%s", task.Err.Error())
		return
	}
	if ret.DupKeys == 0 {
		task.getLogger().Info("keys file has no duplicate lines,file:%s,lines:%d,addr:%s",
			keysFile, ret.TotalLines, task.getSrcRedisAddr())
		return
	}
	task.Err = fmt.Errorf("keys file has duplicate lines,file:%s,totalLines:%d,dupKeys:%d,extraLines:%d,"+
		"dupFile:%s,addr:%s,examples(up to %d):%s", keysFile, ret.TotalLines, ret.DupKeys, ret.DupLines,
		ret.DupFile, task.getSrcRedisAddr(), keysDupCheckShowCnt, strings.Join(ret.Examples, ","))
	task.getLogger().Error("%s", task.Err.Error())
}
