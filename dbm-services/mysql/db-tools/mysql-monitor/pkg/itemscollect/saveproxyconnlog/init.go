// Package saveproxyconnlog 将 proxy 连接日志保存到后端 MySQL
package saveproxyconnlog

import (
	"context"
	"fmt"
	"log/slog"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/go-viper/mapstructure/v2"
	"github.com/jmoiron/sqlx"
)

var name = "save-proxy-connlog"

const defaultMaxLines = 10000 // 默认过载保护阈值

// Checker 保存 proxy connlog 到后端 MySQL
type Checker struct {
	db *sqlx.DB

	// MaxLines 每一次处理的最大行数, 默认 10000. 超过阈值的 conn_log 会被丢弃掉
	MaxLines int `mapstructure:"max_lines"`
	// WriteBatch 写入到后端 proxy_conn_log 的每批大小, 默认 100
	WriteBatch int `mapstructure:"write_batch"`
}

// Run 执行主流程
// 1. 获取 connlog 文件路径
// 2. 基于 offset 扫描新增日志（参照 mysqlerrlog 的 reg 文件机制）
// 3. 获取后端 MySQL 连接，建表并清理历史数据
// 4. 批量写入扫描到的日志条目
// 5. 保存新的 offset
func (c *Checker) Run() (msg string, err error) {
	// 获取 connlog 文件路径
	connLogFilePath := fmt.Sprintf(`/data/mysql-proxy/%d/log/mysql-proxy.log`, config.MonitorConfig.Port)

	// 基于 offset 扫描新增日志
	entries, newOffset, err := scanConnLog(connLogFilePath, c.MaxLines)
	if err != nil {
		return "", err
	}

	// 无论是否有新数据，都保存 offset（更新 inode 信息）
	defer func() {
		if newOffset.Inode != 0 {
			_ = saveOffset(newOffset)
		}
	}()

	// 没有新数据，直接返回
	if len(entries) == 0 {
		return "", nil
	}

	slog.Info("scanned new connlog entries", slog.Int("count", len(entries)))

	// 获取后端 MySQL 连接
	conn, err := c.db.Connx(context.Background())
	if err != nil {
		slog.Error("get backend connection failed", slog.String("error", err.Error()))
		return "", err
	}
	defer func() {
		_ = conn.Close()
	}()

	// 初始化连接（关闭 binlog）
	err = initConn(context.Background(), conn)
	if err != nil {
		return "", err
	}

	// 批量写入
	err = batchWrite(context.Background(), conn, entries, config.MonitorConfig.Ip, c.WriteBatch)
	if err != nil {
		return "", err
	}

	// 清理历史数据
	err = cleanOldData(context.Background(), conn, config.MonitorConfig.Ip)
	if err != nil {
		slog.Warn("clean old data failed, continue", slog.String("error", err.Error()))
		// 清理失败不影响主流程
	}

	return "", nil
}

// Name 监控项名称
func (c *Checker) Name() string {
	return name
}

// New 创建 Checker 实例
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	c := &Checker{
		db:         cc.ProxyDB,
		MaxLines:   defaultMaxLines,
		WriteBatch: defaultBatchSize,
	}

	// 从自定义配置中加载 max_lines / write_batch
	opts := cc.GetCustomOptions(name)
	if len(opts) > 0 {
		if err := mapstructure.Decode(opts, c); err != nil {
			slog.Warn("decode custom options failed, use defaults", slog.String("error", err.Error()))
		}
	}
	return c
}

// Register 注册监控项
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}
