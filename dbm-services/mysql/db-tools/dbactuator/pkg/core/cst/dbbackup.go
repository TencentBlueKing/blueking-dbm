package cst

import "fmt"

// BackupFile TODO
const BackupFile = "dbbackup"

// BackupDir TODO
const BackupDir = "dbbackup-go"

// GetNewConfigByPort TODO
func GetNewConfigByPort(port int) string {
	return fmt.Sprintf("%s.%d.ini", BackupFile, port)
}
