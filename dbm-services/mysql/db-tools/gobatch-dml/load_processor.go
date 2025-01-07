// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package main

import (
	"context"
	"database/sql"
	"fmt"
	"io"
	"sync"
	"sync/atomic"

	"github.com/pkg/errors"
)

type PrintProcessor struct {
	headerInited bool
	writer       io.WriteCloser

	opt *Options
}

type OutputProcessor interface {
	Process(string, context.Context) error
	HandleHeader(context.Context) error
	HandleFooter(error, context.Context) error
}

func (p *PrintProcessor) HandleHeader(ctx context.Context) error {
	if p.writer == nil {
		return errors.New("writer is not inited")
	}
	if p.headerInited {
		return nil
	}
	var err error
	defer func() {
		p.headerInited = true
	}()

	var sqls []string
	if p.opt.DisableLogBin {
		sqls = append(sqls, "set session sql_log_bin=0")
	}
	if p.opt.LockTable {
		sqls = append(sqls, fmt.Sprintf("LOCK TABLE %s WRITE", p.opt.TableName))
	}
	if p.opt.DisableAutocommit {
		sqls = append(sqls, "BEGIN")
	}
	for _, s := range sqls {
		_, err = p.writer.Write([]byte(s + ";\n"))
		if err != nil {
			return err
		}
	}
	return nil
}

func (p *PrintProcessor) HandleFooter(internalErr error, ctx context.Context) error {
	var err error
	if p.opt.DisableAutocommit {
		if internalErr != nil {
			_, err = p.writer.Write([]byte("ROLLBACK;\n"))
		} else {
			_, err = p.writer.Write([]byte("COMMIT;\n"))
		}
	}
	if p.opt.LockTable {
		_, err = p.writer.Write([]byte("UNLOCK TABLES;\n"))
	}
	return err
}

func (p *PrintProcessor) Process(sql string, ctx context.Context) error {
	_, err := p.writer.Write([]byte(sql + ";\n"))
	if err != nil {
		return err
	}
	return nil
}

type LoadProcessor struct {
	headerInited bool
	dbConn       *sql.DB
	oneConn      *sql.Conn
	//autoCommit   bool

	opt *Options

	mu                sync.Mutex
	rowsAffectedTotal int64
}

func (p *LoadProcessor) HandleHeader(ctx context.Context) error {
	if p.dbConn == nil {
		return errors.New("db connection is not inited")
	}
	if p.headerInited {
		return nil
	}
	var err error
	defer func() {
		p.headerInited = true
	}()

	var sqls []string
	if p.opt.DisableLogBin {
		sqls = append(sqls, "set session sql_log_bin=0")
	}
	if p.opt.LockTable {
		sqls = append(sqls, fmt.Sprintf("LOCK TABLE %s WRITE", p.opt.TableName))
	}
	// 正常 / 异常结束，都要 UNLOCK TABLES

	if p.opt.DisableAutocommit || p.opt.LockTable {
		if p.oneConn == nil {
			p.oneConn, err = p.dbConn.Conn(ctx)
			if err != nil {
				return err
			}
		}
	}
	if p.opt.DisableAutocommit {
		// 事务操作
		sqls = append(sqls, "BEGIN")
		for _, s := range sqls {
			if p.opt.DryRun {
				fmt.Println(s, ";")
			}
			_, err = p.oneConn.ExecContext(ctx, s)
			if err != nil {
				if p.opt.LockTable {
					_, _ = p.oneConn.ExecContext(ctx, "UNLOCK TABLES")
				}
				return errors.WithMessagef(err, "run sql: %s", s)
			}
		}
	} else {
		sqls = append(sqls, "set session autocommit=1")

		for _, s := range sqls {
			if p.opt.DryRun {
				fmt.Println(s, ";")
			}
			_, err = p.dbConn.ExecContext(ctx, s)
			if err != nil {
				if p.opt.LockTable {
					_, _ = p.dbConn.ExecContext(ctx, "UNLOCK TABLES")
				}
				return errors.WithMessagef(err, "run sql: %s", s)
			}
		}
	}
	return nil
}
func (p *LoadProcessor) HandleFooter(internalErr error, ctx context.Context) error {
	var err error
	if p.dbConn == nil {
		return errors.New("db connection is not inited")
	}
	if p.opt.DisableAutocommit {
		if internalErr != nil {
			_, err = p.oneConn.ExecContext(ctx, "ROLLBACK")
		} else {
			_, err = p.oneConn.ExecContext(ctx, "COMMIT")
		}
	}
	if p.opt.LockTable {
		_, err = p.oneConn.ExecContext(ctx, "UNLOCK TABLES")
	}
	return err
}

// Process 如果 开启事务，Process失败后会自动回滚
func (p *LoadProcessor) Process(query string, ctx context.Context) error {
	var err error
	var res sql.Result
	if p.opt.DisableAutocommit { // 开启事务中
		if p.opt.DryRun {
			fmt.Println(query, ";")
		}
		p.mu.Lock()
		res, err = p.oneConn.ExecContext(ctx, query)
		if err != nil {
			_, _ = p.oneConn.ExecContext(ctx, "ROLLBACK")
		}
		p.mu.Unlock()
	} else {
		res, err = p.dbConn.ExecContext(ctx, query)
	}
	if err != nil {
		if p.opt.LockTable {
			_, _ = p.oneConn.ExecContext(ctx, "UNLOCK TABLES")
		}
		return errors.WithMessage(err, query)
	} else {
		rowsAffected, _ := res.RowsAffected()
		atomic.AddInt64(&p.rowsAffectedTotal, rowsAffected)
	}
	return nil
}
