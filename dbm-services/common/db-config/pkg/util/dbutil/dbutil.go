package util

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"gorm.io/gorm"
)

// ConnectAdminProxy TODO
func ConnectAdminProxy(user, password, address string) (*sql.DB, error) {
	config := fmt.Sprintf("%s:%s@tcp(%s)/?timeout=10s&maxAllowedPacket=%s",
		user,
		password,
		address,
		"4194304")
	db, err := sql.Open("mysql", config)
	if err != nil {
		return nil, err
	}

	return db, nil
}

// NewConn TODO
func NewConn(user, password, address, dbName string) (*sql.DB, error) {
	config := fmt.Sprintf("%s:%s@tcp(%s)/%s?timeout=10s",
		user,
		password,
		address, dbName)
	db, err := sql.Open("mysql", config)
	if err != nil {
		return nil, err
	}
	var ctx2SecondTimeout, cancelFunc2SecondTimeout = context.WithTimeout(context.Background(), time.Second*5)
	defer cancelFunc2SecondTimeout()
	if err = db.PingContext(ctx2SecondTimeout); err != nil {
		db.Close()
		return nil, err
	}
	// set for db connection
	// setupDB(db)
	return db, nil
}

// DBExec TODO
func DBExec(exeuteSQL string, db *sql.DB) error {
	var (
		err error
	)
	_, err = db.Exec(exeuteSQL)
	return err
}

// DBQuery TODO
func DBQuery(querySQL string, db *sql.DB) ([]map[string]sql.RawBytes, error) {
	var (
		err error
	)

	rows, err := db.Query(querySQL)
	if err != nil {
		return nil, err
	}

	columns, err := rows.Columns()
	if err != nil {
		return nil, err
	}

	values := make([]sql.RawBytes, len(columns))
	scanArgs := make([]interface{}, len(values))
	for i := range values {
		scanArgs[i] = &values[i]
	}

	results := make([]map[string]sql.RawBytes, 0)

	// Fetch rows
	for rows.Next() {
		// get RawBytes from data
		result := make(map[string]sql.RawBytes, 0)
		err = rows.Scan(scanArgs...)
		if err != nil {
			return nil, err
		}
		for i, col := range values {
			if col == nil {
				// value = "NULL"
				result[columns[i]] = nil
			} else {
				result[columns[i]] = col
			}
			// fmt.Println(columns[i], ": ", value)
		}
		results = append(results, result)
	}

	fmt.Println("results:", results)

	return results, err
}

// ExecuteRawSQL TODO
func ExecuteRawSQL(db *gorm.DB, sql string, i interface{}) error {
	return db.Raw(sql).Scan(i).Error
}

// ConvDBResultToStr TODO
func ConvDBResultToStr(objMap map[string]interface{}) map[string]string {
	objMapRes := make(map[string]string, 0)
	for colName, colValue := range objMap {
		if colValue == nil {
			// value = "NULL"
			objMapRes[colName] = ""
		} else {
			// value = string(col)
			objMapRes[colName] = fmt.Sprintf("%v", colValue)
		}
	}
	return objMapRes
}

/*
func main() {
  db, err := gorm.Open("mysql", "user:password@/dbname?charset=utf8&parseTime=True&loc=Local")
  defer db.Close()
}
*/
