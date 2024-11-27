// Package logparserjob 将mongolog转为json格式
package logparserjob

import (
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
	offset, _ := fileutil.GetFileSize(fileName)
	if cacheSi.Inode > 0 {
		ino := fileinfo.GetFileIno(fileName)
		// 当文件存在，Inode没有变化，并且offset未重置的情况下，才使用缓存文件
		if ino == cacheSi.Inode && cacheSi.FileName == fileName && cacheSi.Offset <= offset {
			return cacheSi
		}
	}

	return si
}

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
	ctx, osCtx context.Context, metaInfo []byte, logger *zap.Logger) (

	succ int, fail int, err error) {
	if err = precheck(srcFileName, dirName, outFileName); err != nil {
		return
	}
	dirName, _ = filepath.Abs(dirName)
	seekCacheFile := path.Join(dirName, ".seek")
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
		fmt.Printf("failed to create rotatelogs: %s", err)
		return
	}

	seekCache := LoadSeekInfoFromCacheFile(seekCacheFile, srcFileName)
	logger.Info(fmt.Sprintf("using seek info: %+v", seekCache))
	seekInfo := tail.SeekInfo{Offset: seekCache.Offset, Whence: io.SeekStart}
	// 如果文件不存在: seekInfo.Offset = 0
	// 如果文件小于Offset: seekInfo.Offset = 0
	t, err := tail.TailFile(
		srcFileName, tail.Config{
			Location:      &seekInfo,
			Follow:        follow,
			ReOpen:        follow && true,
			MustExist:     true,
			CompleteLines: true,
		})
	if err != nil {
		err = errors.Wrap(err, "seek")
		return
	}

	// 如果metaInfo不为空，且最后一个字符不是逗号，则添加逗号
	if len(metaInfo) > 0 && metaInfo[len(metaInfo)-1] != ',' {
		metaInfo = append(metaInfo, ',')
	}

	ticker := time.NewTicker(time.Second)
	// Print the text of each received line
	prevNum := -1
	prevOffset := int64(0)
	prevTime := primitive.NewDateTimeFromTime(time.Now())
	for {
		select {
		case <-osCtx.Done():
			logger.Info("osCtx done, stop parsing")
			goto END
		case <-ctx.Done():
			logger.Info("context done, stop parsing")
			goto END
		case <-ticker.C:
			// 每秒保存一次.
			err = seekCache.Save(true)
			logger.Debug(fmt.Sprintf("save seekinfo %+v", seekCache), zap.Error(err))
		case line := <-t.Lines:
			if line == nil {
				if follow {
					continue
				} else {
					// 非follow模式下，这表示文件读取完毕
					logger.Info("non-follow, nil received, stop parsing")
					goto END
				}
			}

			logger.Debug("line info received", zap.String("line", line.Text),
				zap.Int("num", line.Num),
				zap.Int64("SeekInfo", line.SeekInfo.Offset),
				zap.Time("time", line.Time))

			p, err := mongologparser.GetParser([]byte(line.Text))
			if err != nil {
				logger.Warn("failed to get parser: %s", zap.Error(err))
				continue
			}

			msg, err := p.Parse([]byte(line.Text))
			if err != nil {
				logger.Warn("failed to parse: %s\n", zap.Error(err))
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
			if len(metaInfo) > 0 {
				_, _ = dstWriter.Write(msgJson[0:1])
				_, _ = dstWriter.Write(metaInfo)
				_, _ = dstWriter.Write(msgJson[1:])
			} else {
				_, _ = dstWriter.Write(msgJson)
			}
			_, _ = dstWriter.Write([]byte("\n"))

			if prevNum > line.Num || prevNum == -1 {
				logger.Info("line number reset, update inode",
					zap.Int("prevNum", prevNum), zap.Int("lineNum", line.Num))
			}

			// 保存SeekInfo，如果LineNum重置，更新Inode
			err = seekCache.Update(line.SeekInfo.Offset,
				prevNum > line.Num || prevNum == -1 || prevOffset > line.SeekInfo.Offset)

			if err != nil {
				logger.Error("save seek info failed", zap.Error(err))
			}
			prevNum, prevOffset, prevTime = line.Num, line.SeekInfo.Offset, msg.DateTime
		}
	}

END:
	seekCache.Save(true)
	logger.Info("ParseFile done")
	return
}
