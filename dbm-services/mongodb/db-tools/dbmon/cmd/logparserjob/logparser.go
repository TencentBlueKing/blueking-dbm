// Package logparserjob 将mongolog转为json格式
package logparserjob

import (
	"bufio"
	"context"
	"dbm-services/mongodb/db-tools/dbmon/pkg/fileinfo"
	"dbm-services/mongodb/db-tools/dbmon/pkg/fileutil"
	"dbm-services/mongodb/db-tools/dbmon/pkg/mongologparser"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"time"

	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.uber.org/zap"

	rotatelogs "github.com/lestrrat/go-file-rotatelogs"
	"github.com/nxadm/tail"
	"github.com/pkg/errors"
)

// FileSeekInfo 缓存文件名和偏移量
type FileSeekInfo struct {
	FileName      string `json:"FileName"`      // 读取的文件名
	Offset        int64  `json:"Offset"`        // 文件偏移量
	Inode         uint64 `json:"Inode"`         // 文件inode
	CacheFileName string `json:"CacheFileName"` // Cache文件名，作用不大
	UpdateCount   uint64 `json:"-"`             // 用于记录更新次数
}

// Update 更新offset到变量
// @param offset 偏移量
// @param updateInode 是否更新inode.
func (si *FileSeekInfo) Update(offset int64, updateInode bool) error {
	si.UpdateCount++
	si.Offset = offset
	if updateInode {
		// 不确定GetFileIno的成本，只在必要的时候才更新inode
		si.Inode = fileinfo.GetFileIno(si.FileName)
	}
	return nil
}

// UpdateAndSave 将文件名和偏移量保存到文件中，方便下次启动时读取
// @param offset 偏移量
// @param updateInode 是否更新inode.
func (si *FileSeekInfo) UpdateAndSave(offset int64, updateInode bool) error {
	si.Update(offset, updateInode)
	return si.Save(updateInode)
}

// Save 将文件名和偏移量保存到文件中，方便下次启动时读取
// @param offset 偏移量
// @param updateInode 是否更新inode.
func (si *FileSeekInfo) Save(updateInode bool) error {
	if updateInode {
		// 不确定GetFileIno的成本，只在必要的时候才更新inode
		si.Inode = fileinfo.GetFileIno(si.FileName)
	}
	content, _ := json.Marshal(si)
	err := os.WriteFile(si.CacheFileName, content, 0666)
	si.UpdateCount = 0
	return err
}

// LoadSeekInfoFromCacheFile 加载文件名和偏移量
func LoadSeekInfoFromCacheFile(cacheFileName string, fileName string) *FileSeekInfo {
	if fileName == "" || cacheFileName == "" {
		return nil
	}
	si := &FileSeekInfo{
		FileName:      fileName,
		Offset:        0,
		CacheFileName: cacheFileName,
	}

	// 如何文件不存在，则创建一个空的FileSeekInfo
	if !fileutil.FileExists(cacheFileName) {
		return si
	}

	// 如果文件存在，则读取文件内容，获取文件名和偏移量
	content, err := os.ReadFile(cacheFileName)
	if err != nil {
		return si
	}
	cacheSi := &FileSeekInfo{}
	err = json.Unmarshal(content, cacheSi)

	if err != nil {
		si.CacheFileName = cacheFileName
		return si
	}

	cacheSi.CacheFileName = cacheFileName
	offset, err := fileutil.GetFileSize(fileName)
	if err != nil {
		// 如果文件不存在或无法获取大小，使用缓存中的offset
		offset = cacheSi.Offset
	}
	if cacheSi.Inode > 0 {
		ino := fileinfo.GetFileIno(fileName)
		// 当文件存在，Inode没有变化，并且offset未重置的情况下，才使用缓存文件
		if ino == cacheSi.Inode && cacheSi.FileName == fileName && cacheSi.Offset <= offset {
			return cacheSi
		}
	}

	return si
}

// precheck 检查输入参数
// @param srcFileName 源文件名
// @param dirName 输出目录
// @param outFileName 输出文件名
// @return err 错误信息
func precheck(srcFileName, dirName, outFileName string) (err error) {
	fileAbsPath, err := filepath.Abs(srcFileName)
	if err != nil {
		err = errors.Wrap(err, "get abs path")
		return
	}
	srcDirName := filepath.Dir(fileAbsPath)
	dirName, err = filepath.Abs(dirName)
	if err != nil {
		err = errors.Wrap(err, "get abs path")
		return
	}

	err = os.MkdirAll(dirName, 0755)
	if err != nil {
		err = errors.Wrap(err, "mkdir failed")
		return
	}

	if srcDirName == dirName {
		err = errors.New("cannot use file's dir as output dir")
		return
	}

	if outFileName == "" {
		err = errors.New("outFileName cannot be empty")
		return
	}
	return nil
}

// ParseFile parse the log file and write the parsed log messages to the output file
// ParseFile 要保证ctx.Done()时能正确退出。
func ParseFile(srcFileName string, dirName, outFileName string, follow bool,
	ctx, osCtx context.Context, metaInfo []byte, logger *zap.Logger) (succ int, fail int, err error) {
	if err = precheck(srcFileName, dirName, outFileName); err != nil {
		return
	}
	dirName, _ = filepath.Abs(dirName)
	dstDir := fmt.Sprintf("%s/%s", dirName, outFileName) + ".%Y%m%d-%H%M"
	// todo 同一分钟内如果日志数量过多，要过滤掉.

	// 文件最多只保留4小时，每10分钟一个文件
	// 日志丢失一点问题不大，因为日志是用来分析的，不是用来做数据源的，但不要把磁盘写满了
	dstWriter, err := rotatelogs.New(
		dstDir,
		rotatelogs.WithMaxAge(4*time.Hour),
		rotatelogs.WithRotationTime(time.Minute*10),
	)
	if err != nil {
		err = errors.Wrap(err, "failed to create rotatelogs")
		logger.Error("failed to create rotatelogs", zap.Error(err))
		return
	}
	return parseFileTo(srcFileName, dstWriter, dirName, follow, ctx, osCtx, metaInfo, logger)
}

// parseFileTo 是 ParseFile 的可注入版本，dstWriter 由调用方提供（rotatelogs 或测试用的失败 writer）。
// 若 dstWriter 实现 io.Closer，退出时会关闭。
func parseFileTo(srcFileName string, dstWriter io.Writer, dirName string, follow bool,
	ctx, osCtx context.Context, metaInfo []byte, logger *zap.Logger) (succ int, fail int, err error) {
	seekCacheFile := path.Join(dirName, ".seek")

	// 如果文件不存在: seekInfo.Offset = 0
	// 如果文件小于Offset: seekInfo.Offset = 0
	seekCache := LoadSeekInfoFromCacheFile(seekCacheFile, srcFileName)
	logger.Info(fmt.Sprintf("using seek info: %+v", seekCache))
	seekInfo := tail.SeekInfo{Offset: seekCache.Offset, Whence: io.SeekStart}

	tailHandle, err := tail.TailFile(
		srcFileName, tail.Config{
			Location:      &seekInfo,
			Follow:        follow,
			ReOpen:        follow && true,
			MustExist:     true,
			CompleteLines: true,
		})
	if err != nil {
		if c, ok := dstWriter.(io.Closer); ok {
			_ = c.Close()
		}
		err = errors.Wrap(err, "seek")
		return
	}
	// rotatelogs 每次 Write 都落到 syscall。缓冲后按秒 flush，轮转仍按 flush 时刻切文件。
	bufWriter := bufio.NewWriterSize(dstWriter, 32*1024)
	// writeErr 记录首个写入/刷盘错误。bufio.Writer 出错后内部 err 被置住，后续 Write/Flush
	// 全部短路返回旧错误且 n=0。此时继续推进 offset 会让这段日志既不落盘、重启后也被跳过。
	// 因此一旦写入失败就停止消费，只保存已成功输出对应的读取位置。
	var writeErr error
	writeLine := func(p []byte) bool {
		if writeErr != nil {
			return false
		}
		if _, e := bufWriter.Write(p); e != nil {
			writeErr = e
			logger.Error("write json log failed", zap.Error(e))
			return false
		}
		return true
	}
	flush := func() bool {
		if writeErr != nil {
			return false
		}
		if e := bufWriter.Flush(); e != nil {
			writeErr = e
			logger.Error("flush json log failed", zap.Error(e))
			return false
		}
		return true
	}

	// 如果metaInfo不为空，且最后一个字符不是逗号，则添加逗号
	if len(metaInfo) > 0 && metaInfo[len(metaInfo)-1] != ',' {
		metaInfo = append(metaInfo, ',')
	}

	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	// Print the text of each received line
	prevNum := -1
	prevOffset := int64(0)
	prevTime := primitive.NewDateTimeFromTime(time.Now())
	// pendingOffset 是已缓冲但尚未刷盘的行对应的读取位置；只有 flush 成功后才提交到 seekCache。
	// 这样磁盘满等写入失败时，.seek 不会指向未落盘的内容，重启后能从上次成功位置续读。
	pendingOffset := seekCache.Offset
	pendingInodeUpdate := false
	// commit 把 pendingOffset 提交到 seekCache，仅在 flush 成功后调用。
	commit := func() {
		if pendingInodeUpdate || pendingOffset != seekCache.Offset {
			_ = seekCache.Update(pendingOffset, pendingInodeUpdate)
			pendingInodeUpdate = false
		}
	}
	for {
		select {
		case <-osCtx.Done():
			logger.Info("osCtx done, stop parsing")
			goto END
		case <-ctx.Done():
			logger.Info("context done, stop parsing")
			goto END
		case <-ticker.C:
			// 每秒刷盘并保存 offset。只有 flush 成功才提交 pendingOffset。
			if !flush() {
				logger.Info("stop parsing after write failure")
				goto END
			}
			commit()
			err = seekCache.Save(false)
			logger.Debug(fmt.Sprintf("save seekinfo %+v", seekCache), zap.Error(err))
		case line := <-tailHandle.Lines:
			if line == nil {
				// channel 已关闭。follow 时继续读会在关闭的 channel 上空转。
				logger.Info("tail closed, stop parsing", zap.Bool("follow", follow))
				goto END
			}

			logger.Debug("line info received", zap.String("line", line.Text),
				zap.Int("num", line.Num),
				zap.Int64("SeekInfo", line.SeekInfo.Offset),
				zap.Time("time", line.Time))

			p, err := mongologparser.GetParser([]byte(line.Text))
			if err != nil {
				logger.Warn("failed to get parser", zap.Error(err))
				continue
			}

			msg, err := p.Parse([]byte(line.Text))
			if err != nil {
				logger.Warn("failed to parse", zap.Error(err))
				fail++
				continue
			}

			if msg != nil {
				succ++
			} else {
				msg = &mongologparser.MongoLogMsg{
					Ctx:      "parse failed",
					DateTime: prevTime,
				}
				fail++
			}

			msg.Line.Num, msg.Line.Time, msg.Line.OffSet = line.Num, line.Time, line.SeekInfo.Offset
			msg.Line.TimeDiff = int64(msg.DateTime.Time().Sub(msg.Line.Time).Seconds())
			msgJson, _ := json.Marshal(msg)
			// 在{} 中插入 metaInfo. metaInfo 可以为空 []byte{}
			ok := true
			if len(metaInfo) > 0 {
				ok = writeLine(msgJson[0:1]) && writeLine(metaInfo) && writeLine(msgJson[1:])
			} else {
				ok = writeLine(msgJson)
			}
			if ok {
				ok = writeLine([]byte("\n"))
			}
			if !ok {
				// 写入失败，停止消费。pendingOffset 未提交，重启后从上次成功位置续读。
				logger.Info("stop parsing after write failure")
				goto END
			}

			if prevNum > line.Num || prevNum == -1 {
				logger.Info("line number reset, update inode",
					zap.Int("prevNum", prevNum), zap.Int("lineNum", line.Num))
			}
			// 记录待提交的读取位置；行号重置或 offset 回退时，提交时一并更新 inode。
			pendingOffset = line.SeekInfo.Offset
			if prevNum > line.Num || prevNum == -1 || prevOffset > line.SeekInfo.Offset {
				pendingInodeUpdate = true
			}
			prevNum, prevOffset, prevTime = line.Num, line.SeekInfo.Offset, msg.DateTime
		}
	}

END:
	// 退出前尽力刷盘。flush 成功才提交 pendingOffset，失败则只保留已提交的位置，
	// 未落盘的内容重启后会重读。
	if flush() {
		commit()
	}
	seekCache.Save(true)
	logger.Info("stop tail handle")
	// 不要再调用 Cleanup。它和 Stop 都会 RemoveWatch，全局计数会被减成负数，
	// 下一次 Watch 不再注册 inotify，tail 就只能在重新打开文件时读到当时的末尾。
	if stopErr := tailHandle.Stop(); stopErr != nil {
		logger.Error("stop tail handle failed", zap.Error(stopErr))
		if err == nil {
			err = stopErr
		}
	}
	if c, ok := dstWriter.(io.Closer); ok {
		if closeErr := c.Close(); closeErr != nil {
			logger.Error("close dst writer failed", zap.Error(closeErr))
			if err == nil {
				err = closeErr
			}
		}
	}
	// 写入失败是最早发生的错误，优先返回，便于上层识别。
	if writeErr != nil && err == nil {
		err = errors.Wrap(writeErr, "write json log failed")
	}
	logger.Info("ParseFile done")
	return
}
