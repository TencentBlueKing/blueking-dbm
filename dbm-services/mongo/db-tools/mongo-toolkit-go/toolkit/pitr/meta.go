package pitr

import (
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"encoding/json"
	"fmt"
	log "github.com/sirupsen/logrus"
	"os"
	"path"
)

// BackupMeta Backup Result Meta Info
type BackupMeta struct {
	MetaDir    string
	BackupType string
	ConnInfo   *mymongo.MongoHost
	LastResult *BackupResult
}

// NewBackupMeta Deprecated
func NewBackupMeta(dir string, backupType string, conn *mymongo.MongoHost, lastResult *BackupResult) (*BackupMeta, error) {
	m := new(BackupMeta)
	m.MetaDir = dir
	m.BackupType = backupType
	m.ConnInfo = conn
	m.LastResult = lastResult

	if false == TestFileWriteable(m.GetMetaFileName()) {
		return nil, fmt.Errorf("write %s err", m.GetMetaFileName())
	}
	return m, nil
}

// TestFileWriteable Test file writeable
func TestFileWriteable(filePath string) bool {
	file, err := os.OpenFile(filePath, os.O_WRONLY, 0666)
	if err != nil {
		if os.IsPermission(err) {
			return false
		}
	}
	file.Close()
	return true

}

// GetMetaFileName Get meta file name
func (b *BackupMeta) GetMetaFileName() string {
	MetaFileName := fmt.Sprintf("meta.%s-%s-%s.json", b.ConnInfo.Host, b.ConnInfo.Port, b.BackupType)
	return path.Join(b.MetaDir, MetaFileName)
}

// GetLastBackup Get last backup result
func (b *BackupMeta) GetLastBackup() (*BackupResult, error) {
	contentByte, err := os.ReadFile(b.GetMetaFileName())
	if err != nil {
		contentByte = []byte(`{}`)
	}

	log.Infof("GetLastBackup read %v", string(contentByte))
	m2 := new(BackupMeta)
	if err := json.Unmarshal(contentByte, &m2); err != nil {
		return nil, err
	} else {
		return m2.LastResult, nil
	}
}

// SaveBackup Save backup result to meta file
func (b *BackupMeta) SaveBackup(result *BackupResult) error {
	metaPath := b.GetMetaFileName()
	b.LastResult = result
	contentBytes, err := json.Marshal(b)
	log.Infof("metaPath: %s %s", metaPath, contentBytes)
	if err == nil {
		return os.WriteFile(metaPath, contentBytes, 0644)
	}
	return err
}
