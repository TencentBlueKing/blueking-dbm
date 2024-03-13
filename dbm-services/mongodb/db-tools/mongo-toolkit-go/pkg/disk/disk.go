// Package disk . 用于获得某个文件所在的磁盘的总容量、可用容量、已用容量、文件总数、可用文件数、文件系统类型、磁盘的主设备号和次设备号
// cp from https://github.com/minio/minio/tree/master/internal/disk
package disk

// Info stat fs struct is container which holds following values
// Total - total size of the volume / disk
// Free - free size of the volume / disk
// Files - total inodes available
// Ffree - free inodes available
// FSType - file system type
type Info struct {
	Total  uint64
	Free   uint64
	Used   uint64
	Files  uint64
	Ffree  uint64
	FSType string
	Major  uint32
	Minor  uint32
}

// DevID is the drive major and minor ids
type DevID struct {
	Major uint32
	Minor uint32
}
