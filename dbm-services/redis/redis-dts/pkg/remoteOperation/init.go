package remoteOperation

// RemoteOperation remote server operations interface
type RemoteOperation interface {
	RemoteDownload(srcDir, dstDir string, fileName string, bwlimitMB int64) (err error)
	RemoteBash(cmd string) (ret string, err error)
}
