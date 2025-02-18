/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package ghost

import (
	"fmt"
	"io"

	"vitess.io/vitess/go/vt/sqlparser"
)

// ParseDDL parses DDL SQL statements and processes ALTER TABLE operations.
// It returns an error if the statement is not an ALTER TABLE or if parsing fails.
func ParseDDL(statement string) (statements []string, err error) {
	// Validate input
	if statement == "" {
		return nil, fmt.Errorf("empty statement")
	}

	p, err := sqlparser.New(sqlparser.Options{})
	if err != nil {
		return nil, fmt.Errorf("failed to create parser: %w", err)
	}

	stmt, err := p.Parse(statement)
	if err != nil {
		return nil, fmt.Errorf("failed to parse statement: %w", err)
	}

	alterStmt, ok := stmt.(*sqlparser.AlterTable)
	if !ok {
		return nil, fmt.Errorf("statement is not an ALTER TABLE")
	}

	// Process each alter option
	for _, opt := range alterStmt.AlterOptions {
		var statement string
		if statement, err = processAlterOption(opt); err != nil {
			return nil, fmt.Errorf("failed to process alter option: %w", err)
		}
		statements = append(statements, statement)
	}
	return statements, nil
}

// IsAlterSQL is used to check whether the input statement is an ALTER TABLE statement.
func IsAlterSQL(statement string) (yes, doSpiderFirst bool) {
	// Validate input
	if statement == "" {
		return false, false
	}

	p, err := sqlparser.New(sqlparser.Options{})
	if err != nil {
		return false, false
	}

	stmt, err := p.Parse(statement)
	if err != nil {
		return false, false
	}
	alterStmt, ok := stmt.(*sqlparser.AlterTable)
	if !ok {
		return false, false
	}
	yes = true
	// Process each alter option
	for _, opt := range alterStmt.AlterOptions {
		switch opt.(type) {
		case *sqlparser.DropColumn:
			return yes, true
		case *sqlparser.DropKey:
			return yes, true
		default:
			return yes, false
		}
	}
	return yes, false
}

// IsUseDb sql is use db
func IsUseDb(statement string) (yes bool, db string) {
	p, err := sqlparser.New(sqlparser.Options{})
	if err != nil {
		return false, ""
	}
	stmt, err := p.Parse(statement)
	if err != nil {
		return false, ""
	}
	useStmt, ok := stmt.(*sqlparser.Use)
	if !ok {
		return false, ""
	}
	return true, useStmt.DBName.String()
}

// processAlterOption handles individual ALTER TABLE options
func processAlterOption(opt sqlparser.AlterOption) (statement string, err error) {
	buf := sqlparser.NewTrackedBuffer(nil)

	switch v := opt.(type) {
	case *sqlparser.AddColumns:
		v.Format(buf)
	case *sqlparser.AddIndexDefinition:
		v.Format(buf)
	case *sqlparser.DropColumn:
		v.Format(buf)
	case *sqlparser.DropKey:
		v.Format(buf)
	case *sqlparser.ModifyColumn:
		v.Format(buf)
	case *sqlparser.ChangeColumn:
		v.Format(buf)
	case sqlparser.TableOptions:
		v.Format(buf)
	case *sqlparser.RenameIndex:
		v.Format(buf)
	default:
		return "", fmt.Errorf("unsupported alter option: %T", v)
	}

	return buf.String(), nil
}

// ParseSQLFile reads and parses SQL file into individual SQL statements
func ParseSQLFile(fileContent string) ([]string, error) {
	// Create SQL parser
	parser, err := sqlparser.New(sqlparser.Options{
		TruncateUILen:  512,
		TruncateErrLen: 0,
	})
	if err != nil {
		return nil, err
	}
	tokens := parser.NewStringTokenizer(fileContent)
	// Split content into individual statements
	statements := make([]string, 0)

	// Parse each statement
	for {
		var stmt sqlparser.Statement
		stmt, err = sqlparser.ParseNext(tokens)
		if err != nil {
			if err == io.EOF {
				return statements, nil
			}
			return nil, fmt.Errorf("failed to parse SQL statement: %w", err)
		}
		// Convert statement back to string and append to results
		buf := sqlparser.NewTrackedBuffer(nil)
		stmt.Format(buf)
		statements = append(statements, buf.String())
	}
}

// ParseSqlSchemaInfo 解析SQL dbname tbname
func ParseSqlSchemaInfo(statement string) (dbName string, tbName string, err error) {
	// Validate input
	if statement == "" {
		return "", "", fmt.Errorf("empty statement")
	}

	p, err := sqlparser.New(sqlparser.Options{})
	if err != nil {
		return "", "", fmt.Errorf("failed to create parser: %w", err)
	}
	stmt, err := p.Parse(statement)
	if err != nil {
		return "", "", fmt.Errorf("failed to parse table from statement: %w", err)
	}
	alterStmt, ok := stmt.(*sqlparser.AlterTable)
	if !ok {
		return "", "", fmt.Errorf("statement is not an ALTER TABLE")
	}
	buf := sqlparser.NewTrackedBuffer(nil)
	alterStmt.Table.Format(buf)
	return p.ParseTable(buf.String())
}
