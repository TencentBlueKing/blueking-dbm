package backup

// COSBackupClient TODO
type COSBackupClient struct {
}

// Init TODO
func (o *COSBackupClient) Init() error {
	return nil
}

// Upload TODO
func (o *COSBackupClient) Upload(fileName string) (string, error) {
	return "123", nil
}

// Query TODO
func (o *COSBackupClient) Query(taskId string) (int, error) {
	return 4, nil
}
