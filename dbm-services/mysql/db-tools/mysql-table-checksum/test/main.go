package main

import (
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/checker"
	"fmt"
)

func main() {
	out := checker.Output{}
	fmt.Println(out.ZipString())
}
